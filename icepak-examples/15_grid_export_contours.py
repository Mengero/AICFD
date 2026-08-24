#!/usr/bin/env python3
"""
15_grid_export_contours.py -- contour images from a HEADLESS box: export field
data on a plane grid with the NATIVE calculator, then render with matplotlib.

>>> WHY NATIVE <<<
Headless AEDT cannot rasterize anything (no GL), and on PyAEDT 0.26.1 the
convenience wrapper `post.export_field_file_on_grid()` is broken twice over:
the scalar path writes an EMPTY grid (`Grid Size: [0 0 0]`, one NaN row -- it
mangles the unit strings) and the `is_vector=True` path crashes the macro engine
at `CalcOp("Smooth")`. The native `ofieldsreporter.ExportOnGrid` works.

>>> THE QUIRKS THIS ENCODES <<<
  * EnterQty names are "Temp" / "Speed" / "Pres" (NOT "Temperature"/"Pressure" --
    those are the *plot* quantity names; the two APIs disagree).
  * Coordinates come back in SI METERS even though the grid was given in mm.
  * "Speed" exports a 3-component vector -> take the magnitude.
  * `Nan` (and exact 0 for temperature) = outside the solution domain -> mask.
  * A plane section = that axis start == stop, step 0.
  * Render in a SEPARATE process if your AEDT process also imports matplotlib
    (GLIBCXX clash on some clusters) -- here we render after release, same
    process is usually fine once AEDT is released; move it out if it crashes.

Usage:
  python3 15_grid_export_contours.py --project X.aedt --design IcepakDesign1 \
      --headless --axis y --coord 0 --out ./plots
"""

from __future__ import annotations

import argparse
from pathlib import Path

from _session import IcepakSession, add_common_args

QUANTITIES = [  # (tag, EnterQty name, colormap, unit, mask_zero)
    ("T", "Temp", "inferno", "degC", True),
    ("V", "Speed", "viridis", "m/s", False),
    ("P", "Pres", "coolwarm", "Pa", False),
]

EXPORT_OPTS = ["NAME:ExportOption", "IncludePtInOutput:=", True, "RefCSName:=", "Global",
               "PtInSI:=", True, "FieldInRefCS:=", False]


def export_plane(ipk, solution, air_body, axis, coord_mm, out_dir, n=220):
    """Export T/V/P on the axis-aligned plane <axis>=<coord_mm> over the air bbox."""
    om = ipk.ofieldsreporter
    bb = ipk.modeler[air_body].bounding_box            # [x0,y0,z0,x1,y1,z1] in mm
    lo, hi = list(bb[:3]), list(bb[3:])
    step = [max((hi[i] - lo[i]) / n, 0.5) for i in range(3)]
    ax = "xyz".index(axis)
    lo[ax] = hi[ax] = coord_mm                          # plane: start == stop
    step[ax] = 0.0                                      # ... step 0 on that axis
    mm = lambda v: f"{v:.6f}mm"
    written = []
    for tag, qty, cmap, unit, mask0 in QUANTITIES:
        fld = out_dir / f"{tag}_{axis}{coord_mm:g}.fld"
        fld.unlink(missing_ok=True)
        om.CalcStack("clear")
        om.EnterQty(qty)
        om.ExportOnGrid(str(fld), [mm(v) for v in lo], [mm(v) for v in hi],
                        [mm(v) for v in step], solution, [], EXPORT_OPTS,
                        "Cartesian", ["0mm", "0mm", "0mm"], False)
        ok = fld.exists() and fld.stat().st_size > 10_000
        print(f"    {fld.name:<14} -> {fld.stat().st_size if fld.exists() else 0} B"
              f"{'' if ok else '  [EMPTY -- check quantity name / solution]'}")
        if ok:
            written.append((fld, tag, cmap, unit, mask0))
    return written


def render(fld, tag, cmap, unit, mask0, axis):
    """Tricontour the .fld to a PNG next to it."""
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = []
    for line in fld.read_text(encoding="latin-1", errors="ignore").splitlines():
        parts = line.split()
        try:
            vals = [float(p) for p in parts]
        except ValueError:
            continue
        if len(vals) >= 4:
            rows.append(vals)
    a = np.array(rows)
    xyz = a[:, :3]
    if np.nanmax(xyz.max(0) - xyz.min(0)) < 5.0:        # SI meters -> mm
        xyz = xyz * 1000.0
    v = np.linalg.norm(a[:, 3:6], axis=1) if a.shape[1] >= 6 else a[:, 3]
    good = np.isfinite(v)
    if mask0:
        good &= v > 1.0                                  # exact 0 = outside domain
    ax_n = "xyz".index(axis)
    ax1, ax2 = [i for i in range(3) if i != ax_n]
    x, y, v = xyz[good, ax1], xyz[good, ax2], v[good]

    fig, axp = plt.subplots(figsize=(10, 8))
    tc = axp.tricontourf(x, y, v, levels=48, cmap=cmap)
    fig.colorbar(tc, ax=axp).set_label(unit)
    names = "XYZ"
    axp.set_xlabel(f"{names[ax1]} [mm]"); axp.set_ylabel(f"{names[ax2]} [mm]")
    axp.set_aspect("equal")
    axp.set_title(f"{fld.stem}   min {v.min():.1f} / max {v.max():.1f} {unit}")
    fig.tight_layout()
    png = fld.with_suffix(".png")
    fig.savefig(png, dpi=130); plt.close(fig)
    print(f"    wrote {png.name}  ({len(v)} pts, {v.min():.1f}..{v.max():.1f} {unit})")


def main():
    ap = add_common_args(argparse.ArgumentParser(description=__doc__))
    ap.add_argument("--air-body", default="TORSOSLINKY",
                    help="fluid body whose bbox bounds the grid")
    ap.add_argument("--axis", choices="xyz", default="y", help="plane normal axis")
    ap.add_argument("--coord", type=float, default=0.0, help="plane coordinate [mm]")
    ap.add_argument("--out", default="./plots", help="output folder")
    args = ap.parse_args()
    out = Path(args.out).resolve(); out.mkdir(parents=True, exist_ok=True)

    with IcepakSession(args) as ipk:
        sol = ipk.nominal_sweep
        assert ipk.setups[0].is_solved, "project is not solved"
        written = export_plane(ipk, sol, args.air_body, args.axis, args.coord, out)

    for fld, tag, cmap, unit, mask0 in written:          # render AFTER release
        render(fld, tag, cmap, unit, mask0, args.axis)


if __name__ == "__main__":
    main()
