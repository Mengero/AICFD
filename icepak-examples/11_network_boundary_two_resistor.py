#!/usr/bin/env python3
"""
11_network_boundary_two_resistor.py -- convert a solid block into a two-resistor
(junction-to-case / junction-to-board) network boundary.

Use this when you want to model a package by its datasheet resistances instead of
resolving its internal construction: an internal node holds the power, and each
exposed face is linked to it through a resistance.

>>> TWO TRAPS, BOTH FATAL, BOTH NON-OBVIOUS <<<

1. PyAEDT only registers the FIRST face.
   NetworkObject.add_face_node() builds the node list correctly, but
   props["Faces"] ends up holding just one face id. create() then dies with:

       script macro error: boundary 'ufs': face '74190' is not assigned to
       the network and cannot be a node.

   Fix: write the full face list back into props["Faces"] before create().

2. The underlying body must have solve_inside = False.
   A network replaces the body's internal conduction. Leave it solved as a solid
   and you get, ~60 s into the solve:

       Failed to generate solver input file / Engine Detected Error

   Check the networks that already work in your model -- ours all sat on
   solve_inside=False bodies, and the two new ones did not.

Note the failure TIMING in trap 2: ~60 s means model error, not licence. A
licence failure comes back in ~6 s. Don't retry a slow failure.

    $PY 11_network_boundary_two_resistor.py --project M.aedt --design IcepakDesign6 \
        --headless --name UFS --faces 74189,74190 --power 4W \
        --resistances 10cel_per_w,20.2cel_per_w
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _session import IcepakSession, add_common_args  # noqa: E402

from ansys.aedt.core.modules.boundary.icepak_boundary import NetworkObject  # noqa: E402


def owning_objects(ipk, face_ids):
    """Map face ids -> the bodies that own them (you need these for solve_inside)."""
    want = set(face_ids)
    owners = {}
    for o in ipk.modeler.object_names:
        try:
            fids = set(ipk.modeler[o].faces_ids)
        except Exception:
            continue
        hit = want & fids
        if hit:
            owners[o] = sorted(hit)
            print(f"    {o:<26} owns {sorted(hit)} (of {len(fids)} faces)")
    missing = want - {f for v in owners.values() for f in v}
    if missing:
        raise SystemExit(f"no object owns face(s) {sorted(missing)}")
    return owners


def make_network(ipk, name, faces, power, mass="0.001kg", cp="1000J_per_Kelkg"):
    """faces: list of (face_id, resistance_string) pairs."""
    # Remove any existing boundary of the same name (e.g. the old Source).
    for b in list(ipk.boundaries):
        if b.name == name:
            print(f"    deleting existing {b.type} '{name}'")
            b.delete()
            break

    net = NetworkObject(ipk, name=name, create=False)
    for fid, _ in faces:
        net.add_face_node(assignment=fid, name=f"Face{fid}",
                          thermal_resistance="NoResistance")
    net.add_internal_node(name="Internal", power=power, mass=mass, specific_heat=cp)
    for i, (fid, rv) in enumerate(faces, 1):
        net.add_link(f"Face{fid}", "Internal", rv, f"Link{i}")

    # ---- TRAP 1 WORKAROUND: PyAEDT only kept the first face id. ----
    print(f"    props['Faces'] before workaround: {net.props.get('Faces')}")
    net.props["Faces"] = [f for f, _ in faces]
    print(f"    props['Faces'] after  workaround: {net.props.get('Faces')}")

    if not net.create():
        raise SystemExit(f"create() failed for network {name}")
    print(f"    created network {name}: nodes={list(net.nodes)} links={list(net.links)}")
    return net


def main():
    ap = add_common_args(argparse.ArgumentParser())
    ap.add_argument("--name", required=True, help="boundary name, e.g. UFS")
    ap.add_argument("--faces", required=True, help="comma-separated face ids")
    ap.add_argument("--power", required=True, help="internal node power, e.g. 4W")
    ap.add_argument("--resistances", required=True,
                    help="one per face, e.g. 10cel_per_w,20.2cel_per_w "
                         "(conventionally junction-to-board, junction-to-case)")
    args = ap.parse_args()

    fids = [int(x) for x in args.faces.split(",")]
    rs = [r.strip() for r in args.resistances.split(",")]
    if len(fids) != len(rs):
        raise SystemExit(f"{len(fids)} faces but {len(rs)} resistances")
    faces = list(zip(fids, rs))

    with IcepakSession(args) as ipk:
        print(f">>> locating bodies that own {fids}")
        owners = owning_objects(ipk, fids)

        # ---- TRAP 2: the body must not also be solved as a solid. ----
        print(">>> enforcing solve_inside = False on the network bodies")
        for o in owners:
            try:
                before = ipk.modeler[o].solve_inside
                if before:
                    ipk.modeler[o].solve_inside = False
                print(f"    {o:<26} solve_inside {before} -> "
                      f"{ipk.modeler[o].solve_inside}")
            except Exception as e:
                print(f"    {o:<26} [warn] {e}")

        print(f">>> building network {args.name}")
        make_network(ipk, args.name, faces, args.power)

        kinds = {b.name: b.type for b in ipk.boundaries}
        print(f"    {args.name} is now: {kinds.get(args.name)}  "
              f"(total boundaries: {len(kinds)})")

    print("\nNETWORK_DONE -- the solution is now invalidated; re-solve before exporting.")


if __name__ == "__main__":
    main()
