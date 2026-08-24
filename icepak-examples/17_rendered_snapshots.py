#!/usr/bin/env python3
"""
17_rendered_snapshots.py -- REAL rendered snapshots (model + field plot + legend,
any orientation) from a script, using GUI-mode AEDT on an X display.

>>> WHY GUI MODE <<<
Pure headless (-ng) AEDT has no GL context: native image export returns nothing
and the PyVista path crashes. But if the machine has ANY live X display (a
remote-desktop session like DISPLAY=:1, or Xvfb), a scripted GUI-mode session
renders everything. An AEDT window will pop up on that display while it runs --
warn whoever owns the desktop.

>>> THE FOUR TRAPS THIS ENCODES <<<
 1. An interactively-open AEDT GUI holds the PER-USER automation lock: any
    scripted session dies at SetActiveDesign ("access to the requested resource
    is not permitted") EVEN ON A DIFFERENT PROJECT. Close the GUI first.
 2. ExportModelImageToFile's "FieldPlotSelections" MUST name the plot; empty
    string silently omits the contour (tell: byte-identical PNGs across fields).
 3. Plots loaded from a reopened project have no computed data and render blank:
    cut-planes are deleted + recreated here. Streamlines CANNOT be created by
    script (undocumented 'Particle Trace Definitions' args) -- but a GUI-created
    streamline is force-computed by UpdateQuantityFieldsPlots + UpdateAllFieldsPlots,
    after which it snapshots fine. Human draws it once; scripts snapshot forever.
 4. ExportPlotImageToFile does not exist in Icepak 2026.1. Use ExportModelImageToFile.

Run on a COPY of the solved project (reopening solved projects for post is safer
on a copy) and set DISPLAY before launching, e.g.:

  DISPLAY=:1 python3 17_rendered_snapshots.py --project COPY.aedt \
      --design IcepakDesign2 --plane Plane1 --wireframe --out ./plots
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from ansys.aedt.core import Icepak

VIEWS = ("front", "back", "left", "right", "top", "bottom", "isometric")
CUTPLANES = [("TEMPERATURE_CROSSECTION", "Temperature", 0),
             ("VELOCITY_CROSSECTION", "Speed", 2),
             ("PRESSURE_CROSSSECTION", "Pressure", 0)]


def snap(oe, path, orient, plotname):
    oe.ExportModelImageToFile(str(path), 1600, 1200,
        ["NAME:SaveImageParams", "ShowAxis:=", "False", "ShowGrid:=", "False",
         "ShowRuler:=", "False", "ShowRegion:=", "Default", "Selections:=", "",
         "FieldPlotSelections:=", plotname,          # <-- trap 2: must name the plot
         "Orientation:=", orient])
    size = path.stat().st_size if path.exists() else 0
    print(f"      {path.name:<44} {size} B")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project", required=True)
    ap.add_argument("--design", required=True)
    ap.add_argument("--version", default="2026.1")
    ap.add_argument("--plane", default="Plane1", help="construction plane for cut-planes")
    ap.add_argument("--wireframe", action="store_true",
                    help="set Display Wireframe on all objects (unobstructed contours)")
    ap.add_argument("--out", default="./plots")
    args = ap.parse_args()

    assert os.environ.get("DISPLAY"), "set DISPLAY (e.g. :1) -- GUI mode needs an X display"
    out = Path(args.out).resolve(); out.mkdir(parents=True, exist_ok=True)

    # GUI mode = the renderer. new_desktop=True: own instance (user GUI must be closed).
    ipk = Icepak(project=str(Path(args.project).resolve()), design=args.design,
                 version=args.version, non_graphical=False, new_desktop=True)
    try:
        assert ipk.setups[0].is_solved, "project is not solved"
        sol = ipk.nominal_sweep
        oe = ipk.modeler.oeditor

        if args.wireframe:                                   # GUI Render->Wireframe equivalent
            objs = list(ipk.modeler.object_names)
            oe.ChangeProperty(["NAME:AllTabs", ["NAME:Geometry3DAttributeTab",
                ["NAME:PropServers"] + objs,
                ["NAME:ChangedProps", ["NAME:Display Wireframe", "Value:=", True]]]])
            print(f"    wireframe ON ({len(objs)} objects)")

        # cut-planes: recreate in-session (trap 3), snapshot one at a time
        for name, qty, refn in CUTPLANES:
            if name in ipk.post.field_plots:
                ipk.post.field_plots[name].delete()
            p = ipk.post.create_fieldplot_cutplane(assignment=[args.plane], quantity=qty,
                                                   setup=sol, plot_name=name)
            if not p:
                print(f"    [warn] {name} creation failed"); continue
            try:
                p.IsoVal = "Tone"; p.Refinement = refn; p.update()
            except Exception:
                pass
            oe.FitAll()
            print(f"    == {name} ==")
            for orient in VIEWS:
                snap(oe, out / f"snap_{name.split('_')[0]}_{orient}.png", orient, name)
            p.delete()

        # streamline: GUI-created only -- force-compute the loaded plot, then snapshot
        streamlines = [n for n in ipk.post.field_plots
                       if "STREAM" in n.upper()]
        for name in streamlines:
            om = ipk.ofieldsreporter
            for call, cargs in (("UpdateQuantityFieldsPlots", ("Speed",)),
                                ("UpdateAllFieldsPlots", ())):
                try:
                    getattr(om, call)(*cargs)
                except Exception as e:
                    print(f"    [warn] {call}: {e}")
            oe.FitAll()
            print(f"    == {name} (GUI-created, force-computed) ==")
            for orient in VIEWS:
                snap(oe, out / f"snap_{name}_{orient}.png", orient, name)
        if not streamlines:
            print("    (no streamline plot in the design -- create one in the GUI once,"
                  " scripts can then snapshot it)")
    finally:
        ipk.release_desktop()


if __name__ == "__main__":
    main()
