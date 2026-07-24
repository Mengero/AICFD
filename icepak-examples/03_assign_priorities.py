#!/usr/bin/env python3
"""
03_assign_priorities.py -- object overlap priority (the order Icepak resolves
overlapping bodies).

>>> ORDER IS LOWEST -> HIGHEST <<<  `ipk.mesh.assign_priorities(groups)` writes
`PriorityNumber = <list index> + 1`, and in Icepak the HIGHER PriorityNumber wins
on overlap. So the FIRST list is the LOWEST priority and the LAST list is the
HIGHEST. PyAEDT's own docstring says so ("from low to high"); verified empirically
on 2026-07-24 (see docs/icepak-object-priority.md). Objects you don't pass at all
land below the first list.

Everything in one group shares that level. Bodies that genuinely overlap must NOT
share a level -- a solid-solid tie aborts the solve with
"[error] Parts X and Y intersect". Bodies that merely touch are fine together.

>>> MRF RULE <<<  The SOLID impeller/blades must OUTRANK the rotating MRF fluid
zone, so the impeller goes LATER in the list than the zone. If the zone outranks
the blades, Icepak replaces the blades with fluid where they overlap -> the fan
spins an empty cylinder -> pure swirl, ~zero net thrust ("spins but doesn't
pump"). Read the solve validation log:
  bug:   "Parts <impeller> and <MRF_zone> intersect. <MRF_zone> will take precedence"
  fixed: "... <impeller> will take precedence"

>>> VERIFY, DON'T TRUST THE RETURN <<<  assign_priorities() ends in an
unconditional `return True` -- the bool proves nothing. Confirm the result by
re-reading the saved .aedt (parse `$begin 'PriorityListParameters'` blocks for
`EntityList` + `PriorityNumber`) or from the validation log.

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

# LOWEST -> HIGHEST. Each inner list is one priority level; the LAST list wins.
PRIORITY_ORDER = [
    # ["Region"],        # the air/solution domain is usually lowest
    # ["enclosure"],
    # ["gap_pad"],       # TIM / gel: let the real solids carve it
    # ["MRF_zone"],      # rotating fluid zone
    # ["IM_1"],          # solid impeller/blades -- MUST come AFTER the MRF zone
    # ["PCB"],
    # ["chip"],          # small bodies nested inside bigger ones go LAST
]


def main():
    ap = add_common_args(argparse.ArgumentParser())
    args = ap.parse_args()

    with IcepakSession(args) as ipk:
        objects = set(ipk.modeler.object_names)

        if not PRIORITY_ORDER:
            print("PRIORITY_ORDER is empty -- edit it at the top of this file.")
            print("Example (lowest first; MRF impeller outranks the zone so it goes last):")
            print("    ipk.mesh.assign_priorities([['Region'], ['MRF_zone'], ['IM_1']])")
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

        # NB: assign_priorities() always returns True -- it is not a success signal.
        ipk.mesh.assign_priorities(cleaned)
        print(f"    assigned {len(cleaned)} priority level(s)")
        for level, grp in enumerate(cleaned, 1):
            print(f"      PriorityNumber={level:<3} {grp}")
        print("    (higher PriorityNumber wins on overlap -- last list is strongest)")

    print(">>> VERIFY: re-read the saved .aedt or the validation log; the return")
    print("    value of assign_priorities() is hardcoded True and proves nothing.")
    print(">>> done. Run the pre-solve checklist before solving (see 08_...).")


if __name__ == "__main__":
    main()
