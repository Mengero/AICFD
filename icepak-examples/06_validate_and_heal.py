#!/usr/bin/env python3
"""
06_validate_and_heal.py -- validate CAD geometry and heal with the LIGHT,
GUI-equivalent settings only.

Flow: validate -> heal the flagged objects -> re-validate.

ipk.validate_simple(log_file) returns 1 (valid) / 0 (invalid) and writes a log
that names the problem entities. heal_objects takes ONE object at a time.

>>> USE ONLY THE LIGHT HEAL <<<  These kwargs reproduce exactly what the AEDT GUI
emits when you record a Heal (Tools > Record Script). Key points:
  * stitch + light surface simplify ON (simplify_geometry=True, simplify_type=2).
  * remove_silver_faces / remove_small_edges / remove_small_faces = False. These
    per-entity tolerance sweeps are what make a headless heal take MINUTES (a
    ~490-face part never finished). Turning them off is the whole trick.
  * remove_holes / remove_chamfers / remove_blends = False -- preserve real design
    features; never defeature.
A correct heal barely changes volume. This script prints the % volume delta per
object; a large swing means the heal distorted the part -> revisit.

    $PY 06_validate_and_heal.py --project M.aedt --design IcepakDesign1
    $PY 06_validate_and_heal.py --project M.aedt --design IcepakDesign1 --objects a,b,c
"""

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _session import IcepakSession, add_common_args  # noqa: E402

# The light, GUI-equivalent heal. Do not "improve" these -- they match the GUI.
LIGHT_HEAL = dict(
    auto_heal=True, tolerant_stitch=True, simplify_geometry=True, tighten_gaps=True,
    heal_to_solid=False, stop_after_first_stitch_error=False, max_stitch_tolerance=0.001,
    explode_and_stitch=True, geometry_simplification_tolerance=-1, maximum_generated_radius=-1,
    simplify_type=2, tighten_gaps_width=1e-06,
    remove_silver_faces=False, remove_small_edges=False, remove_small_faces=False,
    silver_face_tolerance=0, small_edge_tolerance=0, small_face_area_tolerance=0,
    bounding_box_scale_factor=0,
    remove_holes=False, remove_chamfers=False, remove_blends=False,
    hole_radius_tolerance=0, chamfer_width_tolerance=0, blend_radius_tolerance=0,
    allowable_surface_area_change=5, allowable_volume_change=5,
)


def validate(ipk, log_file="validation.log"):
    log = Path(log_file)
    try:
        ipk.change_validation_settings(entity_check_level="Strict")
    except Exception as e:
        print(f"    [warn] change_validation_settings: {e}")
    status = int(ipk.validate_simple(log_file=str(log)))
    text = log.read_text(errors="replace") if log.exists() else ""
    suspects = []
    if status != 1:
        for obj in ipk.modeler.object_names:
            if re.search(rf"\b{re.escape(obj)}\b", text):
                suspects.append(obj)
    print(f"    validation: {'VALID' if status == 1 else 'INVALID'}"
          + (f"; suspects {suspects}" if suspects else ""))
    return status == 1, suspects


def heal(ipk, objects):
    for name in objects:
        try:
            v0 = float(ipk.modeler[name].volume)
        except Exception:
            v0 = None
        try:
            ok = bool(ipk.modeler.heal_objects(name, **LIGHT_HEAL))
        except Exception as e:
            print(f"    [warn] heal_objects('{name}'): {e}")
            ok = False
        try:
            v1 = float(ipk.modeler[name].volume)
        except Exception:
            v1 = None
        pct = (100.0 * (v1 - v0) / v0) if (v0 and v1) else None
        tail = f"  volume {v0:.1f} -> {v1:.1f} ({pct:+.2f}%)" if pct is not None else ""
        print(f"    heal({name}) -> {ok}{tail}")


def main():
    ap = add_common_args(argparse.ArgumentParser())
    ap.add_argument("--objects", help="comma-separated objects to heal (default: auto from log)")
    args = ap.parse_args()

    with IcepakSession(args) as ipk:
        valid, suspects = validate(ipk, "validation_before.log")
        if valid:
            print(">>> geometry already valid; nothing to heal.")
            return
        targets = ([o.strip() for o in args.objects.split(",")] if args.objects
                   else suspects or list(ipk.modeler.object_names))
        print(f">>> healing {len(targets)} object(s): {targets}")
        heal(ipk, targets)
        valid_after, still = validate(ipk, "validation_after.log")
        if not valid_after:
            print(f">>> STILL INVALID -- manual fix needed for: {still or targets}")

    print(">>> done")


if __name__ == "__main__":
    main()
