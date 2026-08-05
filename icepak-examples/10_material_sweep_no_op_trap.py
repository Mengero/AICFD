#!/usr/bin/env python3
"""
10_material_sweep_no_op_trap.py -- run a material sensitivity sweep that ACTUALLY solves.

>>> THE TRAP <<<
Editing a material property IN PLACE does NOT invalidate a stored Icepak solution:

    ipk.materials["insul"].thermal_conductivity = 0.3    # solution stays "valid"

analyze_setup() then returns True *immediately without solving*, and your export
re-writes the previous field data. A 5-point sweep done this way produces 5
IDENTICAL rows and looks completely plausible. This actually happened.

What dirties a solution:
    material property edited in place ....... NO
    object/boundary re-pointed to a NEW material ... YES
    boundary property edited (HTC, power, T) ...... YES
    boundary added / deleted ..................... YES
    solve_inside toggled ......................... YES
    geometry / mesh settings ..................... YES (also re-meshes)

So: create one material PER SWEEP POINT and re-point the consumer at it.

Then GATE every solve on `setup.is_solved == False` and treat a sub-minute
"solve" as a red flag. Never trust the analyze_setup() return value alone.

    $PY 10_material_sweep_no_op_trap.py --project M.aedt --design IcepakDesign1 \
        --headless --boundary BATTERY_AIR --values 0.17,0.28,0.39,0.50 --outdir ./out
"""

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _session import IcepakSession, add_common_args  # noqa: E402


def ensure_material(ipk, name, k):
    """Create (or reuse) a material whose conductivity is `k`. Returns the name."""
    if name not in ipk.materials.material_keys:
        m = ipk.materials.add_material(name)
        m.thermal_conductivity = k
        print(f"    created material {name} (k={k})")
    return name


def solve_guarded(ipk, setup_name, label, min_minutes=1.0):
    """Solve, but PROVE it really ran. Returns elapsed minutes."""
    setup = ipk.setups[0] if not setup_name else \
        next(s for s in ipk.setups if s.name == setup_name)

    # GATE 1 -- the solution must be dirty, else this call is a no-op.
    if setup.is_solved:
        raise SystemExit(
            f"[{label}] ABORT: setup still marked solved -> this solve would be a "
            "NO-OP and you would export stale data. The change you made did not "
            "invalidate the solution (see the module docstring)."
        )

    t0 = time.time()
    ok = bool(ipk.analyze_setup(name=setup.name, blocking=True,
                                revert_to_initial_mesh=False))
    dt = (time.time() - t0) / 60.0
    print(f"    [{label}] analyze_setup={ok} in {dt:.1f} min")
    if not ok:
        # Fast failure == licence (retry); slow failure == model error (don't).
        kind = "LICENCE (retryable)" if dt < 0.6 else "MODEL ERROR (do not retry)"
        raise SystemExit(f"[{label}] solve failed after {dt:.1f} min -> {kind}")

    # GATE 2 -- wall clock. A real solve is minutes, not seconds.
    if dt < min_minutes:
        print(f"    [{label}] *** WARNING: {dt:.2f} min is suspiciously fast; "
              "verify a Solve stage exists in the profile ***")

    # GATE 3 -- the profile must contain a Solve stage.
    try:
        prof = ipk.get_profile(setup.name)
        stages = [s for s in prof if "Solve" in str(s)]
        meshes = [s for s in prof if "Mesh" in str(s)]
        print(f"    [{label}] profile: {len(stages)} solve stage(s), "
              f"{len(meshes)} mesh stage(s)  <- mesh should be reused after case 1")
        if not stages:
            raise SystemExit(f"[{label}] ABORT: no Solve stage in profile.")
    except SystemExit:
        raise
    except Exception as e:
        print(f"    [{label}] [warn] could not read profile: {e}")
    return dt


def export(ipk, setup_name, outdir, tag):
    """SOV (component temps) + Fields Summary (per-boundary heat flow & temps)."""
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
        ipk.osolution.EditFieldsSummarySetting(
            ["SolutionName:=", sol, "Variation:=", ""] + calc)
        ipk.osolution.ExportFieldsSummary(
            ["SolutionName:=", sol, "DesignVariationKey:=", "",
             "ExportFileName:=", str(outdir / fn), "IntrinsicValue:=", ""])
    print(f"    [{tag}] exported to {outdir}")


def main():
    ap = add_common_args(argparse.ArgumentParser())
    ap.add_argument("--setup", default=None, help="setup name (default: first)")
    ap.add_argument("--boundary", required=True,
                    help="boundary whose 'Solid Material' gets re-pointed each case")
    ap.add_argument("--values", required=True,
                    help="comma-separated conductivities, e.g. 0.17,0.28,0.39,0.50")
    ap.add_argument("--outdir", default="./sweep_out")
    args = ap.parse_args()

    ks = [float(v) for v in args.values.split(",")]
    outdir = Path(args.outdir).resolve()

    with IcepakSession(args) as ipk:
        setup_name = args.setup or ipk.setups[0].name

        for k in ks:
            tag = "k%03d" % round(k * 100)
            print(f"\n===== {args.boundary} solid material k = {k} W/mK =====")

            mat = ensure_material(ipk, "insul_%s" % tag, k)

            bnd = next((b for b in ipk.boundaries
                        if b.name.upper() == args.boundary.upper()), None)
            if bnd is None:
                raise SystemExit(f"boundary {args.boundary} not found")

            # RE-POINT (not an in-place edit) -- this is what dirties the solution.
            bnd.props["Solid Material"] = mat
            if not bnd.update():
                raise SystemExit("boundary update() failed")

            # Read back: never assume the write landed.
            got = next(b.props.get("Solid Material") for b in ipk.boundaries
                       if b.name.upper() == args.boundary.upper())
            print(f"    Solid Material -> {mat} (readback {got})")
            assert got == mat, f"readback mismatch: {got}"

            ipk.save_project()
            solve_guarded(ipk, setup_name, tag)
            export(ipk, setup_name, outdir, tag)

    print("\nSWEEP_DONE")
    print("Sanity check: the exported rows MUST differ between cases. If any two "
          "are byte-identical, a solve was a no-op despite the gates.")


if __name__ == "__main__":
    main()
