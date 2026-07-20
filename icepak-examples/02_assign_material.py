#!/usr/bin/env python3
"""
02_assign_material.py -- assign materials to objects.

Two equivalent PyAEDT ways, both shown:
  * per object:  ipk.modeler[name].material_name = "copper"
  * in bulk:     ipk.assign_material(["a", "b"], "copper")

The material must exist in the project's material library. Built-in names that
always exist include: "Al-Extruded", "copper", "FR-4 epoxy", "steel_mild",
"Air", "pcb". Add a custom one with ipk.materials.add_material("MyMat").

Edit MATERIAL_MAP for your model, then run. As written (empty map) it only prints
guidance, so it is safe to run against any project.

    $PY 02_assign_material.py --project /path/to/Model.aedt --design IcepakDesign1
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _session import IcepakSession, add_common_args  # noqa: E402

# {object_name: material_name}
MATERIAL_MAP = {
    # "heatsink": "Al-Extruded",
    # "PCB":      "FR-4 epoxy",
    # "chip":     "copper",
}


def assign_materials(ipk, material_map: dict) -> dict:
    results = {}
    existing = set(ipk.modeler.object_names)
    for name, material in material_map.items():
        if name not in existing:
            print(f"    [skip] '{name}' not in model")
            results[name] = (False, "object not found")
            continue
        try:
            has_mat = ipk.materials.exists_material(material)
        except Exception:
            has_mat = None  # API varies across versions; just try to set it
        if has_mat is False:
            print(f"    [warn] material '{material}' not in library; "
                  f"add via ipk.materials.add_material('{material}') if this fails")

        obj = ipk.modeler[name]
        before = obj.material_name
        obj.material_name = material            # <-- the assignment
        after = obj.material_name
        ok = (after or "").lower() == material.lower()
        print(f"    '{name}': {before!r} -> {after!r} ({'ok' if ok else 'CHECK'})")
        results[name] = (ok, f"{before} -> {after}")
    return results


def main():
    ap = add_common_args(argparse.ArgumentParser())
    args = ap.parse_args()

    with IcepakSession(args) as ipk:
        if MATERIAL_MAP:
            assign_materials(ipk, MATERIAL_MAP)
        else:
            print("MATERIAL_MAP is empty -- edit it at the top of this file.")
            print("Bulk form for the same thing:")
            print("    ipk.assign_material(['heatsink', 'lid'], 'Al-Extruded')")

    print(">>> done. Run the pre-solve checklist before solving (see 08_...).")


if __name__ == "__main__":
    main()
