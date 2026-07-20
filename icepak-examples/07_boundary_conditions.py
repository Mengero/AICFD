#!/usr/bin/env python3
"""
07_boundary_conditions.py -- assign boundary conditions.

Icepak exposes a family of assign_* methods on the app object. This example
dispatches by a short `kind` name so you can see the common ones in one place;
anything not in the table falls back to getattr(ipk, "assign_<kind>").

Common kinds -> method:
  source            -> assign_source           (heat source / total power)
  solid_block       -> assign_solid_block
  hollow_block      -> assign_hollow_block
  free_opening      -> assign_free_opening
  pressure_opening  -> assign_pressure_free_opening
  velocity_opening  -> assign_velocity_free_opening
  mass_flow_opening -> assign_mass_flow_free_opening
  grille            -> assign_grille
  stationary_wall   -> assign_stationary_wall
  resistance        -> assign_resistance
  blower_type1      -> assign_blower_type1

Each method's kwargs differ; check the pyaedt docstring for the one you use. The
two examples in main() are illustrative -- edit assignment names/values to match
your model.

    $PY 07_boundary_conditions.py --project M.aedt --design IcepakDesign1
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _session import IcepakSession, add_common_args  # noqa: E402

DISPATCH = {
    "source": "assign_source",
    "solid_block": "assign_solid_block",
    "hollow_block": "assign_hollow_block",
    "free_opening": "assign_free_opening",
    "pressure_opening": "assign_pressure_free_opening",
    "velocity_opening": "assign_velocity_free_opening",
    "mass_flow_opening": "assign_mass_flow_free_opening",
    "grille": "assign_grille",
    "stationary_wall": "assign_stationary_wall",
    "resistance": "assign_resistance",
    "blower_type1": "assign_blower_type1",
}


def assign_boundary(ipk, kind, **kwargs):
    method_name = DISPATCH.get(kind, f"assign_{kind}")
    method = getattr(ipk, method_name, None)
    if method is None:
        raise ValueError(f"unknown boundary kind '{kind}' (no ipk.{method_name})")
    result = method(**kwargs)
    print(f"    applied {kind} -> {method_name}")
    return result


def main():
    ap = add_common_args(argparse.ArgumentParser())
    args = ap.parse_args()

    with IcepakSession(args) as ipk:
        print("objects:", ipk.modeler.object_names[:20], "...")
        print("\nEdit main() to assign the boundaries your model needs, e.g.:")
        print('    assign_boundary(ipk, "source", assignment="chip",')
        print('                    thermal_condition="Total Power", assignment_value="2W")')
        print('    assign_boundary(ipk, "grille", assignment=["vent_face"],')
        print('                    free_area_ratio=0.75)')

        # --- Uncomment and adapt to actually assign ---
        # assign_boundary(ipk, "source", assignment="chip",
        #                 thermal_condition="Total Power", assignment_value="2W")

    print(">>> done. Run the pre-solve checklist before solving (see 08_...).")


if __name__ == "__main__":
    main()
