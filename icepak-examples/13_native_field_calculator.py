#!/usr/bin/env python3
"""
13_native_field_calculator.py -- per-body temperatures via the NATIVE field
calculator, bypassing PyAEDT's broken visualisation layer.

>>> WHY NATIVE <<<
On PyAEDT 0.26.1 + Icepak 2026.1, three separate bugs make the convenience layer
unusable for field extraction:

  * IcepakConstants has no `default_solution`  -> breaks export_field_file()
  * ...same attribute                          -> breaks plot_field_from_fieldplot()
  * _parse_aedtplt raises IndexError on PyAEDT's OWN 107 MB .aedtplt output

Rather than fight it: pull scalars through the native calculator and plot with
matplotlib.

>>> THE TWO ARGUMENT QUIRKS <<<
  EnterQty("Temp")       -- "Temp", NOT "Temperature" (the Fields Summary API
                            wants "Temperature"; they disagree)
  EnterVol("BodyName")   -- a SINGLE STRING. Passing a list fails.

Also: CalcStack("clear") between queries, or the stack accumulates operands and
you silently read the wrong number.

Typical use -- characteristic package resistances from a solved field:

    psi_JC = (T_junction - T_case)  / Q_total
    psi_JB = (T_junction - T_board) / Q_total

Label these PSI, not R. True R = dT / Q_through_that_path; psi divides by TOTAL
device power, so with heat leaving through several paths psi is a LOWER BOUND on
the true path resistance. Calling a psi value "Rjc" overstates the conductance.

    $PY 13_native_field_calculator.py --project M.aedt --design IcepakDesign6 \
        --headless --no-save --bodies Psuedo_Die,Lid_Top,BGA_EFFECTIVE \
        --material-bodies pcb --power 48 --junction Psuedo_Die
"""

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _session import IcepakSession, add_common_args  # noqa: E402


def body_stat(ipk, setup_name, body, op="Maximum", scratch=None):
    """One scalar: min/max/value of Temp over `body`. Returns float or None."""
    oFR = ipk.ofieldsreporter
    sol = f"{setup_name} : SteadyState"
    out = Path(scratch or tempfile.gettempdir()) / "_calc_scalar.fld"
    try:
        oFR.CalcStack("clear")
        oFR.EnterQty("Temp")          # NOT "Temperature"
        oFR.EnterVol(body)            # single string, NOT a list
        oFR.CalcOp(op)                # "Maximum" | "Minimum" | "Value"
        if out.exists():
            out.unlink()
        oFR.CalculatorWrite(str(out), ["Solution:=", sol], [])
        nums = re.findall(r"-?\d+\.\d+(?:[eE][-+]?\d+)?",
                          out.read_text(errors="replace"))
        return float(nums[-1]) if nums else None
    except Exception as e:
        print(f"    [warn] {body} {op}: {str(e)[:70]}")
        return None


def bodies_of_material(ipk, material):
    """Find bodies by MATERIAL name -- e.g. 'pcb' is a material, not an object.
    Looking for an object literally named 'PCB' finds nothing."""
    hits = []
    for o in ipk.modeler.object_names:
        try:
            if (ipk.modeler[o].material_name or "").lower() == material.lower():
                hits.append(o)
        except Exception:
            pass
    return sorted(hits)


def main():
    ap = add_common_args(argparse.ArgumentParser())
    ap.add_argument("--setup", default=None)
    ap.add_argument("--bodies", default="", help="comma-separated body names")
    ap.add_argument("--material-bodies", default="",
                    help="also include every body made of this MATERIAL, e.g. pcb")
    ap.add_argument("--junction", default=None,
                    help="body to treat as the junction for psi calculations")
    ap.add_argument("--power", type=float, default=None,
                    help="total device power [W] for psi = dT / Q_total")
    args = ap.parse_args()

    with IcepakSession(args) as ipk:
        setup_name = args.setup or ipk.setups[0].name
        oFR = ipk.ofieldsreporter
        try:
            oFR.SetPlotsSolutionContext([], setup_name, "SteadyState")
        except Exception as e:
            print(f"    [warn] SetPlotsSolutionContext: {str(e)[:70]}")

        wanted = [b for b in args.bodies.split(",") if b.strip()]
        known = set(ipk.modeler.object_names)
        missing = [b for b in wanted if b not in known]
        if missing:
            print(f"    [warn] not in model, skipping: {missing}")
        wanted = [b for b in wanted if b in known]

        if args.material_bodies:
            extra = bodies_of_material(ipk, args.material_bodies)
            print(f"    bodies of material '{args.material_bodies}': {extra}")
            wanted += [b for b in extra if b not in wanted]

        print(f"\n{'body':<28}{'max [C]':>10}{'min [C]':>10}")
        results = {}
        for b in wanted:
            hi = body_stat(ipk, setup_name, b, "Maximum")
            lo = body_stat(ipk, setup_name, b, "Minimum")
            results[b] = (hi, lo)
            f = lambda v: f"{v:10.2f}" if v is not None else f"{'--':>10}"  # noqa: E731
            print(f"{b[:28]:<28}{f(hi)}{f(lo)}")

        if args.junction and args.power and results.get(args.junction, (None,))[0]:
            tj = results[args.junction][0]
            print(f"\n=== psi from junction '{args.junction}' "
                  f"(Tj={tj:.2f} C, Q_total={args.power} W) ===")
            print("    (psi = dT / TOTAL power -- a LOWER BOUND on true path R)")
            for b, (hi, _) in results.items():
                if b == args.junction or hi is None:
                    continue
                print(f"    psi to {b[:24]:<24} = {(tj - hi) / args.power:7.4f} C/W")

    print("\nCALC_DONE")


if __name__ == "__main__":
    main()
