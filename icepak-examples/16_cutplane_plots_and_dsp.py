#!/usr/bin/env python3
"""
16_cutplane_plots_and_dsp.py -- cross-section GUI plots on a NAMED construction
plane + a valid .dsp plot bundle.

>>> WHY A CONSTRUCTION PLANE <<<
Users draw section planes in the GUI (Draw -> Plane); plots built on them by
hand reference numeric face/operation IDs. After ANY geometry replacement those
IDs dangle and the plots silently break. Scripted recreation by NAME survives
geometry swaps:

    create_plane("Plane1", base, normal)   ->  oEditor.CreateCutplane
    create_fieldplot_cutplane(["Plane1"])  ->  PlotGeomInfo [1,"Surface","CutPlane",1,"Plane1"]

>>> THE .dsp SAME-SESSION RULE <<<
`SaveFieldsPlots([names], file.dsp)` bundles plot definitions + computed data --
loadable into another design from the GUI. BUT plots loaded from a reopened
project have NO computed data and save a 0-BYTE file (UpdateAllFieldsPlots does
not fix the save). Only plots CREATED in the same session bundle correctly, so
this script always deletes + recreates before saving. Expect ~1.5 MB/plot.

>>> QUANTITY NAMES <<<
Field plots want "Temperature"/"Speed"/"Pressure" (the calculator's
"Temp"/"Pres" names fail here -- the two APIs disagree).

Usage:
  python3 16_cutplane_plots_and_dsp.py --project X.aedt --design IcepakDesign1 \
      --headless --plane-base -51.28 0 1058.25 --plane-normal 0 -1 0
"""

from __future__ import annotations

import argparse
from pathlib import Path

from _session import IcepakSession, add_common_args

PLOTS = [  # (name, plot-quantity, folder, refinement)
    ("TEMPERATURE_CROSSECTION", "Temperature", "Temperature", 0),
    ("VELOCITY_CROSSECTION", "Speed", "Speed", 2),
    ("PRESSURE_CROSSSECTION", "Pressure", "Pressure", 0),
]


def main():
    ap = add_common_args(argparse.ArgumentParser(description=__doc__))
    ap.add_argument("--plane-name", default="Plane1")
    ap.add_argument("--plane-base", nargs=3, type=float, required=True,
                    metavar=("X", "Y", "Z"), help="plane base point [mm]")
    ap.add_argument("--plane-normal", nargs=3, type=float, required=True,
                    metavar=("NX", "NY", "NZ"), help="plane normal direction")
    ap.add_argument("--dsp", default="", help="output .dsp path (default <project>_plots.dsp)")
    args = ap.parse_args()

    with IcepakSession(args) as ipk:
        assert ipk.setups[0].is_solved, "project is not solved"
        sol = ipk.nominal_sweep

        # -- construction plane (idempotent) --------------------------------
        if args.plane_name in ipk.modeler.planes:
            print(f"    plane {args.plane_name} already exists")
        else:
            b, n = args.plane_base, args.plane_normal
            pl = ipk.modeler.create_plane(
                name=args.plane_name,
                plane_base_x=f"{b[0]}mm", plane_base_y=f"{b[1]}mm", plane_base_z=f"{b[2]}mm",
                plane_normal_x=f"{n[0]}mm", plane_normal_y=f"{n[1]}mm", plane_normal_z=f"{n[2]}mm")
            print(f"    created plane {args.plane_name}: {bool(pl)}")

        # -- cut-plane plots: delete + recreate (same-session rule) ---------
        made = []
        for name, qty, folder, refn in PLOTS:
            if name in ipk.post.field_plots:
                ipk.post.field_plots[name].delete()
            p = ipk.post.create_fieldplot_cutplane(
                assignment=[args.plane_name], quantity=qty, setup=sol, plot_name=name)
            if not p:
                print(f"    [warn] {name} creation failed"); continue
            try:
                p.IsoVal = "Tone"; p.Refinement = refn; p.plot_folder = folder; p.update()
            except Exception as e:
                print(f"    [warn] {name} styling: {e}")
            made.append(name)
            print(f"    plot {name} ({qty}) created")

        # -- .dsp bundle -----------------------------------------------------
        dsp = Path(args.dsp) if args.dsp else Path(args.project).with_name(
            Path(args.project).stem + "_plots.dsp")
        dsp.unlink(missing_ok=True)
        ipk.ofieldsreporter.SaveFieldsPlots(made, str(dsp))
        size = dsp.stat().st_size if dsp.exists() else 0
        print(f"    SaveFieldsPlots({len(made)} plots) -> {dsp.name}: {size} B"
              + ("  [EMPTY! plots were not created in this session?]" if size == 0 else ""))


if __name__ == "__main__":
    main()
