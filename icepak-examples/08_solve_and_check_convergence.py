#!/usr/bin/env python3
"""
08_solve_and_check_convergence.py -- solve and judge convergence correctly.

The reliable criterion:
  1. ipk.analyze_setup(name, blocking=True) RETURNS A BOOL. True = the setup
     solved. This is the primary signal -- do NOT decide convergence by globbing
     the results dir for 'fields.resd' (that gives false negatives).
  2. ipk.export_convergence(setup) dumps the residual table for the record.

>>> "Normal Completion" != converged. <<<  It only means the solver hit its
iteration cap. VERIFY FROM THE PHYSICS: open the .SOV in
<project>.aedtresults/<Design>.results/ and read the Volume Flow Rate block --
per-opening flows should sum to ~0 (continuity satisfied). A wildly non-zero sum
means it diverged despite the banner.

If a stiff MRF/pumping flow diverges: lower pressure/momentum under-relaxation,
enable no-reverse-flow on openings, add iterations (see the Convergence Lessons
page on the site).

    $PY 08_solve_and_check_convergence.py --project M.aedt --design IcepakDesign1 \
        --setup Setup1
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _session import IcepakSession, add_common_args  # noqa: E402


def parse_last_residual(path: Path):
    """Best-effort: return the numeric values on the last data row of the .conv."""
    if not path.exists():
        return None
    rows = []
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith(("//", "#", "$")):
            continue
        nums = []
        for tok in line.replace(",", " ").split():
            try:
                nums.append(float(tok))
            except ValueError:
                pass
        if len(nums) >= 2:
            rows.append(nums)
    return rows[-1] if rows else None


def main():
    ap = add_common_args(argparse.ArgumentParser())
    ap.add_argument("--setup", default="Setup1")
    ap.add_argument("--cores", type=int, default=None)
    args = ap.parse_args()

    # NOTE: on a real workflow, run the pre-solve checklist (boundaries, priorities,
    # mesh coverage, geometry validation) BEFORE this. This example assumes you have.
    with IcepakSession(args) as ipk:
        print(f">>> solving {args.setup} (blocking) ...")
        ok = bool(ipk.analyze_setup(name=args.setup, cores=args.cores, blocking=True))
        print(f"    analyze_setup returned: {ok}")

        conv = Path(f"convergence_{args.setup}.conv")
        try:
            exported = ipk.export_convergence(setup=args.setup, output_file=str(conv))
            last = parse_last_residual(Path(exported) if exported else conv)
            print(f"    final residual row: {last}")
        except Exception as e:
            print(f"    [warn] export_convergence: {e}")

        print("\n>>> VERIFY THE PHYSICS before trusting this:")
        print(f"    results dir: {getattr(ipk, 'results_directory', '<project>.aedtresults')}")
        print("    open the .SOV -> Volume Flow Rate block; per-opening flows should sum to ~0.")
        print("    MRF fan? check blade-tip speed ~= omega*r.")

    print(">>> done" if ok else ">>> analyze_setup returned False -- inspect residuals in AEDT")


if __name__ == "__main__":
    main()
