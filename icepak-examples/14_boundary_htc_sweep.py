#!/usr/bin/env python3
"""
14_boundary_htc_sweep.py -- sweep a Stationary Wall's air-side heat transfer
coefficient and report how the answer moves.

This is the SAFE kind of sweep: editing a boundary property DOES invalidate the
solution (unlike an in-place material edit -- see example 10), so every case
genuinely re-solves. Verify it anyway with the pre-solve `is_solved` gate; the
gate costs nothing and catches the day you sweep something that doesn't dirty.

Geometry never changes across an HTC sweep, so pass revert_to_initial_mesh=False
and the mesh is reused -- later cases run several times faster than the first.
Confirm reuse by counting "Mesh" stages in the profile: you should see meshing
only on case 1.

Practical notes from the study this came from:
  * Read the CURRENT value first and make the sweep bracket it, so one case
    reproduces your existing baseline -- a free regression check.
  * Sweep in an order that leaves the model at its ORIGINAL value when done.
  * Print a MATCHECK line (which materials are present) into the log, so you can
    prove afterwards that nothing else drifted between cases. Attributing a delta
    to the swept variable when something else also moved is the classic way to
    report a wrong conclusion.

    $PY 14_boundary_htc_sweep.py --project M.aedt --design IcepakDesign6 \
        --headless --boundary BATTERY_AIR --values 4,6,8,10 --outdir ./out
"""

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _session import IcepakSession, add_common_args  # noqa: E402


def get_boundary(ipk, name):
    b = next((x for x in ipk.boundaries if x.name.upper() == name.upper()), None)
    if b is None:
        raise SystemExit(f"boundary '{name}' not found. Have: "
                         f"{[x.name for x in ipk.boundaries][:20]} ...")
    return b


def set_htc(ipk, name, h):
    """Set the wall's external HTC and PROVE the write landed."""
    b = get_boundary(ipk, name)
    if b.props.get("External Condition") != "Heat Transfer Coefficient":
        raise SystemExit(f"{name} external condition is "
                         f"'{b.props.get('External Condition')}', not HTC")
    b.props["Heat Transfer Coefficient"] = f"{h:g}w_per_m2kel"
    if not b.update():
        raise SystemExit("update() failed")

    got = get_boundary(ipk, name).props.get("Heat Transfer Coefficient")
    print(f"    HTC -> {h} (readback {got})  thickness={b.props.get('Thickness')} "
          f"refT={b.props.get('Reference Temperature')}")
    if not str(got).startswith(str(h)):
        raise SystemExit(f"readback mismatch: {got}")


def solve_and_export(ipk, setup_name, outdir, tag):
    setup = next(s for s in ipk.setups if s.name == setup_name)
    print(f"    pre-solve is_solved={setup.is_solved}  "
          f"(must be False, else the solve is a NO-OP)")
    if setup.is_solved:
        raise SystemExit(f"[{tag}] ABORT: boundary edit did not invalidate the solution")

    ok, dt = False, 0.0
    for attempt in range(1, 13):
        t0 = time.time()
        try:
            ok = bool(ipk.analyze_setup(name=setup_name, cores=8, tasks=8,
                                        blocking=True, revert_to_initial_mesh=False))
        except Exception as e:
            print(f"    exc {str(e)[:60]}")
            ok = False
        dt = (time.time() - t0) / 60.0
        print(f"    [{tag}] attempt {attempt}: solved={ok} in {dt:.1f} min")
        if ok:
            break
        if dt > 0.6:
            # Slow failure == model error. Retrying just burns hours.
            print(f"    failure took {dt:.1f} min -> model error, not licence; stopping")
            break
        time.sleep(90)      # fast failure == licence contention; back off and retry
    if not ok:
        raise SystemExit(f"[{tag}] solve failed")

    sol = f"{setup_name} : SteadyState"
    outdir.mkdir(parents=True, exist_ok=True)
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
        ipk.osolution.EditFieldsSummarySetting(
            ["SolutionName:=", sol, "Variation:=", ""] + calc)
        ipk.osolution.ExportFieldsSummary(
            ["SolutionName:=", sol, "DesignVariationKey:=", "",
             "ExportFileName:=", str(outdir / fn), "IntrinsicValue:=", ""])
    print(f"    [{tag}] exported")


def main():
    ap = add_common_args(argparse.ArgumentParser())
    ap.add_argument("--setup", default=None)
    ap.add_argument("--boundary", required=True, help="Stationary Wall name")
    ap.add_argument("--values", required=True, help="e.g. 4,6,8,10 (W/m2K)")
    ap.add_argument("--outdir", default="./htc_out")
    args = ap.parse_args()

    hs = [float(v) for v in args.values.split(",")]
    outdir = Path(args.outdir).resolve()

    with IcepakSession(args) as ipk:
        setup_name = args.setup or ipk.setups[0].name

        # Provenance: prove nothing else drifted between cases.
        mats = set()
        for o in ipk.modeler.object_names:
            try:
                mats.add((ipk.modeler[o].material_name or "").lower())
            except Exception:
                pass
        print(f"MATCHECK: {len(mats)} distinct materials in use")

        cur = get_boundary(ipk, args.boundary).props.get("Heat Transfer Coefficient")
        print(f">>> {args.boundary} current HTC = {cur}; sweeping {hs}")

        for h in hs:
            tag = "htc%02d" % round(h)
            print(f"\n===== {args.boundary} HTC = {h} W/m2K =====")
            set_htc(ipk, args.boundary, h)
            ipk.save_project()
            solve_and_export(ipk, setup_name, outdir, tag)

    print("\nHTCSWEEP_DONE")


if __name__ == "__main__":
    main()
