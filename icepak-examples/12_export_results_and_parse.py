#!/usr/bin/env python3
"""
12_export_results_and_parse.py -- export a solved Icepak case and parse it into tables.

Three export routes exist and NONE is a superset of the others:

  ExportSolutionOverview (SOV)   per-OBJECT max temperature + per-object heat flow
                                 >>> does NOT report Stationary Wall temperatures <<<
  Fields Summary                 per-BOUNDARY heat flow rate + min/max/mean temperature
  Native field calculator        arbitrary per-body min/max/mean (see example 13)

Forgetting the SOV gap above cost a re-run when a report needed wall temperatures.
Export SOV *and* Fields Summary every time -- they are cheap next to a solve.

Quantity naming is inconsistent across the two APIs, which is easy to trip on:
    Fields Summary  ->  "HeatFlowRate" / "Temperature"
    Field calculator ->  "Temp"        (see example 13)

ALWAYS check the energy balance from the heat-flow export: the sinks must sum to
the total dissipated power. If that closes (ours did, to 0.05%), you can trust the
rest of the numbers. If it doesn't, stop and find out why before reporting.

    $PY 12_export_results_and_parse.py --project M.aedt --design IcepakDesign6 \
        --headless --no-save --outdir ./out --tag case1
    $PY 12_export_results_and_parse.py --parse-only --outdir ./out --tag case1
"""

import argparse
import csv
import os
import re
import sys
from pathlib import Path


# --------------------------------------------------------------------------- export

def export_all(ipk, setup_name, outdir, tag):
    outdir.mkdir(parents=True, exist_ok=True)
    sol = f"{setup_name} : SteadyState"

    ipk.odesign.ExportSolutionOverview(
        ["SetupName:=", setup_name, "DesignVariationKey:=", "",
         "ExportFilePath:=", str(outdir / f"sov_{tag}.txt"),
         "TimeStep:=", -1, "Overwrite:=", True])

    names = [b.name for b in ipk.boundaries]
    for qty, fn in (("HeatFlowRate", f"heatflow_{tag}.csv"),
                    ("Temperature", f"btemp_{tag}.csv")):
        calc = []
        for b in names:
            calc += ["Calculation:=",
                     ["Boundary", "Surface", b, qty, "", "Adjacent", "Reduced", "", True]]
        # NOTE: this can fail with "Failed to execute gRPC AEDT command:
        # EditFieldsSummarySetting" for non-boundary entity types such as
        # ["Object","Volume",...]. For those, use the field calculator (example 13).
        ipk.osolution.EditFieldsSummarySetting(
            ["SolutionName:=", sol, "Variation:=", ""] + calc)
        ipk.osolution.ExportFieldsSummary(
            ["SolutionName:=", sol, "DesignVariationKey:=", "",
             "ExportFileName:=", str(outdir / fn), "IntrinsicValue:=", ""])
    print(f"    exported sov/heatflow/btemp for tag '{tag}' -> {outdir}")


# ---------------------------------------------------------------------------- parse

def _num(x):
    try:
        return float(str(x).split()[0])     # values carry units: "12.3 W"
    except (ValueError, IndexError):
        return None


def parse_fields_summary(path, value_col, extra_cols=None):
    """Fields Summary CSV -> {boundary_name: value}. Rows start with 'Boundary'."""
    out = {}
    with open(path) as fh:
        for row in csv.reader(fh):
            if len(row) > value_col and row[0] == "Boundary":
                if extra_cols:
                    out[row[2]] = {k: _num(row[i]) for k, i in extra_cols.items()}
                else:
                    out[row[2]] = _num(row[value_col])
    return out


def parse_sov(path):
    """Solution Overview -> (power_by_object, maxtemp_by_object)."""
    mode, power, temp = None, {}, {}
    for line in Path(path).read_text(errors="replace").splitlines():
        if line.startswith("#"):
            if "Heat flows for objects" in line:
                mode = "P"
            elif "Maximum Temperatures" in line:
                mode = "T"
            else:
                mode = None
            continue
        if not mode:
            continue
        m = re.match(r"^(\S.*?)\s{2,}(-?[\d.]+)", line.strip())
        if not m:
            continue
        name = m.group(1).strip().rstrip("*").strip()
        if name.lower().startswith(("boundary", "object")):
            continue
        (power if mode == "P" else temp)[name] = float(m.group(2))
    return power, temp


def report(outdir, tag):
    outdir = Path(outdir)
    power, temp = parse_sov(outdir / f"sov_{tag}.txt")
    heat = parse_fields_summary(outdir / f"heatflow_{tag}.csv", 8)
    btemp = parse_fields_summary(outdir / f"btemp_{tag}.csv", 9,
                                 {"min": 7, "max": 8, "mean": 9})

    total_in = sum(power.values())
    # Sinks show up as NEGATIVE heat flow; skip composite "a::b" entries.
    total_out = sum(abs(v) for k, v in heat.items()
                    if v and v < 0 and "::" not in k)
    print(f"\n=== ENERGY BALANCE ({tag}) ===")
    print(f"  dissipated in : {total_in:10.3f} W")
    print(f"  through sinks : {total_out:10.3f} W")
    err = abs(total_out - total_in) / total_in * 100 if total_in else float("nan")
    print(f"  imbalance     : {err:10.3f} %   {'OK' if err < 1 else '<-- INVESTIGATE'}")

    print(f"\n=== TOP 15 COMPONENT MAX TEMPERATURES ({tag}) ===")
    for n, t in sorted(temp.items(), key=lambda kv: -kv[1])[:15]:
        print(f"  {n[:34]:<34} {t:8.2f} C")

    print(f"\n=== BOUNDARY HEAT FLOW / TEMPERATURE ({tag}) ===")
    print(f"  {'boundary':<24}{'Q [W]':>11}{'Tmin':>9}{'Tmax':>9}{'Tmean':>9}")
    for n in sorted(heat, key=lambda k: -abs(heat[k] or 0)):
        if "::" in n:
            continue
        b = btemp.get(n, {})
        q = heat[n] or 0.0
        print(f"  {n[:24]:<24}{q:11.4f}"
              f"{b.get('min', float('nan')):9.2f}"
              f"{b.get('max', float('nan')):9.2f}"
              f"{b.get('mean', float('nan')):9.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="./out")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--parse-only", action="store_true",
                    help="skip AEDT entirely and just re-parse existing exports")
    ap.add_argument("--setup", default=None)
    args, rest = ap.parse_known_args()

    if not args.parse_only:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from _session import IcepakSession, add_common_args
        ap2 = add_common_args(argparse.ArgumentParser())
        ap2.add_argument("--outdir", default="./out")
        ap2.add_argument("--tag", required=True)
        ap2.add_argument("--parse-only", action="store_true")
        ap2.add_argument("--setup", default=None)
        a2 = ap2.parse_args()
        with IcepakSession(a2) as ipk:
            export_all(ipk, a2.setup or ipk.setups[0].name, Path(a2.outdir).resolve(),
                       a2.tag)
        args = a2

    report(Path(args.outdir).resolve(), args.tag)


if __name__ == "__main__":
    main()
