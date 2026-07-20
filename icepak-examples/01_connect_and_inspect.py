#!/usr/bin/env python3
"""
01_connect_and_inspect.py -- connect and dump what's in the model.

Read-only. The first thing to do on any model: discover the real object names,
fans, mesh regions, boundaries, and materials so every later edit uses names that
actually exist (a typo'd name silently does nothing or aborts a solve).

Run (Linux/HPC example interpreter shown; use your own -- see README):
    PY=/apps/ANSYS/v261/AnsysEM/commonfiles/CPython/3_10/linx64/Release/python/bin/python3.10
    $PY 01_connect_and_inspect.py --project /path/to/Model.aedt --design IcepakDesign1
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _session import IcepakSession, add_common_args  # noqa: E402


def list_fans(ipk):
    """Native Fan components (Type == 'Fan')."""
    fans = []
    for name in ipk.native_component_names:
        nc = ipk.native_components.get(name)
        try:
            if nc and nc.props.get("NativeComponentDefinitionProvider", {}).get("Type") == "Fan":
                fans.append(name)
        except Exception:
            pass
    return fans


def main():
    ap = add_common_args(argparse.ArgumentParser())
    args = ap.parse_args()

    with IcepakSession(args) as ipk:
        objects = ipk.modeler.object_names
        print(f"\n=== {len(objects)} objects ===")
        for n in objects[:60]:
            try:
                mat = ipk.modeler[n].material_name
            except Exception:
                mat = "?"
            print(f"    {n:<40} material={mat}")
        if len(objects) > 60:
            print(f"    ... (+{len(objects) - 60} more)")

        print(f"\n=== fans ===\n    {list_fans(ipk)}")
        print(f"\n=== mesh regions ===\n    {[r.name for r in ipk.mesh.meshregions]}")
        print(f"\n=== boundaries ===")
        for b in ipk.boundaries:
            print(f"    {b.name:<30} type={getattr(b, 'type', '?')}")

    print(">>> done")


if __name__ == "__main__":
    main()
