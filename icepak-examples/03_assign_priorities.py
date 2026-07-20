#!/usr/bin/env python3
"""
03_assign_priorities.py -- object overlap priority (the order Icepak resolves
overlapping bodies).

`ipk.mesh.assign_priorities(groups)` takes a list of groups ordered HIGHEST ->
LOWEST. Everything in a group shares that level; higher levels win where bodies
overlap.

>>> MRF RULE <<<  The SOLID impeller/blades must OUTRANK the rotating MRF fluid
zone. If the zone outranks the blades, Icepak replaces the blades with fluid
where they overlap -> the fan spins an empty cylinder -> pure swirl, ~zero net
thrust ("spins but doesn't pump"). Read the solve validation log:
  bug:   "Parts <impeller> and <MRF_zone> intersect. <MRF_zone> will take precedence"
  fixed: "... <impeller> will take precedence"

On a real model, pass the FULL ordered list of bodies, not a 2-item list -- so
you set the whole order deliberately rather than disturbing existing levels.

Edit PRIORITY_ORDER, then run.
    $PY 03_assign_priorities.py --project /path/to/Model.aedt --design IcepakDesign1
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _session import IcepakSession, add_common_args  # noqa: E402

# HIGHEST -> LOWEST. Each inner list is one priority level.
PRIORITY_ORDER = [
    # ["IM_1"],          # solid impeller/blades -- MUST be above the MRF zone
    # ["MRF_zone"],      # rotating fluid zone
    # ["PCB", "chip"],
    # ["enclosure"],
    # ["Region"],        # the air/solution domain is usually lowest
]


def main():
    ap = add_common_args(argparse.ArgumentParser())
    args = ap.parse_args()

    with IcepakSession(args) as ipk:
        objects = set(ipk.modeler.object_names)

        if not PRIORITY_ORDER:
            print("PRIORITY_ORDER is empty -- edit it at the top of this file.")
            print("Example (MRF: impeller outranks the rotating zone):")
            print("    ipk.mesh.assign_priorities([['IM_1'], ['MRF_zone'], ['Region']])")
            return

        # Drop names that don't exist so a typo doesn't abort the whole call.
        cleaned = [[o for o in grp if o in objects] for grp in PRIORITY_ORDER]
        cleaned = [grp for grp in cleaned if grp]
        missing = [o for grp in PRIORITY_ORDER for o in grp if o not in objects]
        if missing:
            print(f"    [warn] not in model, dropped: {missing}")
        if not cleaned:
            print("    [skip] no valid objects in PRIORITY_ORDER")
            return

        ok = ipk.mesh.assign_priorities(cleaned)
        print(f"    assigned {len(cleaned)} priority level(s) -> {ok}")
        print(f"    order (high->low): {cleaned}")

    print(">>> done. Run the pre-solve checklist before solving (see 08_...).")


if __name__ == "__main__":
    main()
