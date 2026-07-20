#!/usr/bin/env python3
"""
05_mesh_region.py -- local mesh refinement region (+ the MLM cavity trap).

ipk.mesh.assign_mesh_region(parts) builds a Global-CS subregion box enclosing
`parts` (named "<name>_SubRegion"); then set manual multi-level-meshing (MLM)
settings on it. Use assign_mesh_region(...), NOT the MeshRegion(...) constructor
(that path errors -- GetChildObject -- in some pyaedt builds).

Proven reference values:
  fan region: size 0.5 mm, MLM "3D", MaxLevels 2, buffers 1, around impeller +
              housing + MRF_zone.
  fin region: size 0.7 mm, MLM "2D", MaxLevels 2, buffers 0, around the heatsink.

>>> THE TRAP <<<  Local refinement around SMALL parts with MaxLevels>0 is fine.
A LARGE cavity region with MaxLevels>0 builds a non-conformal mesh ASSEMBLY that
"meshes but won't solve" -- it dies right at the mesh->solver handoff (log reaches
"Populate Solver Input" then errors, before iteration 1). Force that region
uniform with MaxLevels=0 (set_region_max_levels below). EnableMLM can stay True.

    # create a refinement region around some parts:
    $PY 05_mesh_region.py --project M.aedt --design IcepakDesign1 \
        --name MeshRegion_Fan --parts IM_1,housing,MRF_zone --size-mm 0.5 --mlm 3D
    # OR fix a cavity region that meshes-but-won't-solve:
    $PY 05_mesh_region.py --project M.aedt --design IcepakDesign1 \
        --fix-region MeshRegion3
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _session import IcepakSession, add_common_args  # noqa: E402


def create_mesh_region(ipk, name, parts, size_mm, mlm_type="3D",
                       max_levels=2, buffer_layers=1):
    mr = ipk.mesh.assign_mesh_region(parts, name=name)
    mr.manual_settings = True
    s = mr.settings
    for ax in ("MaxElementSizeX", "MaxElementSizeY", "MaxElementSizeZ"):
        s[ax] = f"{size_mm}mm"
    s["EnableMLM"] = True
    s["MaxLevels"] = str(max_levels)
    s["EnforeMLMType"] = mlm_type          # AEDT's actual (misspelled) key -- keep as-is
    s["BufferLayers"] = str(buffer_layers)
    s["MinElementsInGap"] = "3"
    s["MinElementsOnEdge"] = "2"
    s["MaxSizeRatio"] = "2"
    mr.update()
    print(f"    region '{name}': parts={parts} size={size_mm}mm "
          f"MLM={mlm_type} L{max_levels} buffers={buffer_layers}")
    return mr


def set_region_max_levels(ipk, name, max_levels):
    for r in ipk.mesh.meshregions:
        if r.name == name:
            r.manual_settings = True
            r.settings["MaxLevels"] = str(max_levels)
            r.update()
            print(f"    region '{name}': MaxLevels -> {max_levels}")
            return True
    raise ValueError(f"region '{name}' not found; have {[r.name for r in ipk.mesh.meshregions]}")


def main():
    ap = add_common_args(argparse.ArgumentParser())
    ap.add_argument("--name", help="name for a new refinement region")
    ap.add_argument("--parts", help="comma-separated parts to enclose")
    ap.add_argument("--size-mm", type=float, default=0.5)
    ap.add_argument("--mlm", default="3D", choices=["2D", "3D"])
    ap.add_argument("--max-levels", type=int, default=2)
    ap.add_argument("--buffers", type=int, default=1)
    ap.add_argument("--fix-region", help="set this existing region's MaxLevels to 0 (cavity fix)")
    args = ap.parse_args()

    with IcepakSession(args) as ipk:
        if args.fix_region:
            set_region_max_levels(ipk, args.fix_region, 0)
        elif args.name and args.parts:
            parts = [p.strip() for p in args.parts.split(",") if p.strip()]
            create_mesh_region(ipk, args.name, parts, args.size_mm,
                               args.mlm, args.max_levels, args.buffers)
        else:
            print("Nothing to do. Pass either --name + --parts (create), "
                  "or --fix-region <name> (set MaxLevels=0).")

    print(">>> done. Run the pre-solve checklist before solving (see 08_...).")


if __name__ == "__main__":
    main()
