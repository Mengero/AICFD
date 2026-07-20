#!/usr/bin/env python3
"""
04_setup_mrf_fan.py -- set up a Moving-Reference-Frame (rotating) fan.

Two things matter and this script does both:

  1. Derive the impeller's SPIN AXIS from geometry (PCA on its vertices) instead
     of guessing -- the smallest-variance principal axis is the disc normal = the
     spin axis. You get center/axis/radius/half_height to place the cylindrical
     MRF fluid zone around the impeller.

  2. Set the fan's RPM/swirl. PyAEDT has no direct MRF primitive; an MRF fan is a
     native Fan component whose rotation lives in OperatingRPM / Swirl / SwirlType
     under NativeComponentDefinitionProvider. We mutate those and commit with
     nc.update().

Then enforce the priority rule in 03_assign_priorities.py (impeller > MRF zone).

Physics check after solving: blade-tip speed should match omega*r
(e.g. 5000 rpm, r=40 mm -> ~21 m/s). Pure swirl + ~0 axial = priority bug.

WARNING: the RPM write path is verified against the .aedt structure but the first
time you use it on a new setup, record an "edit fan RPM" macro in the AEDT GUI and
diff the emitted call; align if it differs.

    $PY 04_setup_mrf_fan.py --project M.aedt --design IcepakDesign1 \
        --impeller IM_1 --rpm 5000
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _session import IcepakSession, add_common_args  # noqa: E402


def list_fans(ipk):
    fans = []
    for name in ipk.native_component_names:
        nc = ipk.native_components.get(name)
        try:
            if nc and nc.props.get("NativeComponentDefinitionProvider", {}).get("Type") == "Fan":
                fans.append(name)
        except Exception:
            pass
    return fans


def identify_spin_axis(ipk, name: str, z_positive: bool = True) -> dict:
    """PCA on the object's vertices: smallest-variance axis = spin axis."""
    import numpy as np  # ships with the Ansys CPython

    o = ipk.modeler[name]
    pts = []
    for v in o.vertices:
        try:
            pts.append(list(v.position))
        except Exception:
            pass
    P = np.asarray(pts, float)
    if len(P) < 4:
        raise ValueError(f"'{name}': only {len(P)} vertices; not enough for PCA")

    center = P.mean(0)
    X = P - center
    cov = X.T @ X / len(P)
    _, eigvecs = np.linalg.eigh(cov)         # ascending eigenvalues
    axis = eigvecs[:, 0]                      # smallest variance = spin axis
    if z_positive and axis[2] < 0:
        axis = -axis

    bb = o.bounding_box                        # [xmin,ymin,zmin,xmax,ymax,zmax]
    bc = np.array([(bb[0] + bb[3]) / 2, (bb[1] + bb[4]) / 2, (bb[2] + bb[5]) / 2])
    Xb = P - bc
    along = Xb @ axis
    perp = np.linalg.norm(Xb - np.outer(along, axis), axis=1)
    return {
        "center": bc.round(3).tolist(),
        "axis": [round(float(a), 4) for a in axis],
        "radius": round(float(perp.max()), 3),
        "half_height": round(float(abs(along).max()), 3),
    }


def set_fan_rpm(ipk, fan_name, rpm=None, swirl=0, swirl_type="Magnitude"):
    if fan_name not in ipk.native_component_names:
        raise ValueError(f"fan '{fan_name}' not found; have {list_fans(ipk)}")
    nc = ipk.native_components[fan_name]
    prov = nc.props["NativeComponentDefinitionProvider"]
    prov["ModelAs"] = "3D"
    if rpm is not None:
        prov["OperatingRPM"] = str(rpm)
    prov["Swirl"] = str(swirl)
    prov["SwirlType"] = swirl_type
    ok = nc.update()
    print(f"    fan '{fan_name}': RPM={prov.get('OperatingRPM')} "
          f"Swirl={prov.get('Swirl')} SwirlType={prov.get('SwirlType')} -> {ok}")
    return ok


def main():
    ap = add_common_args(argparse.ArgumentParser())
    ap.add_argument("--impeller", required=True, help="solid impeller/blades object name")
    ap.add_argument("--rpm", type=float, default=None)
    args = ap.parse_args()

    with IcepakSession(args) as ipk:
        spin = identify_spin_axis(ipk, args.impeller)
        print("\nMRF zone geometry to use (cylinder about the impeller):")
        for k in ("center", "axis", "radius", "half_height"):
            print(f"    {k:<12} = {spin[k]}")

        if args.rpm is not None:
            fans = list_fans(ipk)
            if fans:
                set_fan_rpm(ipk, fans[0], rpm=args.rpm, swirl=0)
            else:
                print("    (no native fan component found; RPM not set)")

    print("\n>>> done. Next: set priority so the impeller OUTRANKS the MRF zone "
          "(03_assign_priorities.py), then run the pre-solve checklist (08_...).")


if __name__ == "__main__":
    main()
