# Lessons Learned — Icepak Visualization, Snapshots & Plot Bundles

Everything on this page was learned the hard way on a headless Linux HPC node
(AEDT 2026.1, PyAEDT `ansys-aedt-core` 0.26.1, gRPC), post-processing a solved
forced-air electronics-cooling model. It complements
[Solve Integrity & Post-Processing](icepak-solve-postprocess-lessons.md) — that
page gets the *numbers* out; this one gets the *pictures* out.

## The one-paragraph version

Headless AEDT cannot rasterize anything — so contour *images* come from exporting
field *data* on a grid (native `ExportOnGrid`; the PyAEDT wrapper is broken) and
rendering with matplotlib. GUI *plot definitions* are still worth creating
headless (they cost nothing and travel with the project) — put cross-sections on
a **named construction plane**, never on face IDs, or a geometry swap orphans
them. `.dsp` plot bundles come from `SaveFieldsPlots`, but only plots **created in
the same session** save non-empty. True rendered snapshots (model + contour +
legend, any orientation) *are* possible without a human: run AEDT in **GUI mode on
a remote-desktop X display** and drive `ExportModelImageToFile` — but you must
name the plot in `FieldPlotSelections`, freshly-created plots render while
loaded-from-disk ones are blank (streamlines can be force-computed), and an
interactively-open GUI blocks every scripted session via the per-user automation
lock.

## 1. Contour images, headless: export data, render with matplotlib

### 1.1 The PyAEDT grid export is broken — use the native call

`ipk.post.export_field_file_on_grid(...)` on 0.26.1 writes an **empty grid**
(`Grid Size: [0 0 0]`, one NaN row — it mangles the unit strings), and its
`is_vector=True` path crashes the macro engine (`CalcOp("Smooth")` → "abnormal
script termination"). The native calculator works:

```python
om = ipk.ofieldsreporter
om.CalcStack("clear")
om.EnterQty("Temp")                     # "Temp" / "Speed" / "Pres" — calculator names!
om.ExportOnGrid(
    str(fld_path),
    [f"{x0:.6f}mm", f"{y0:.6f}mm", f"{z0:.6f}mm"],   # grid start
    [f"{x1:.6f}mm", f"{y1:.6f}mm", f"{z1:.6f}mm"],   # grid stop
    [f"{sx:.6f}mm", f"{sy:.6f}mm", f"{sz:.6f}mm"],   # grid step
    "Setup1 : SteadyState", [],
    ["NAME:ExportOption", "IncludePtInOutput:=", True, "RefCSName:=", "Global",
     "PtInSI:=", True, "FieldInRefCS:=", False],
    "Cartesian", ["0mm", "0mm", "0mm"], False)
```

For a plane section: set that axis's start = stop and its step = 0.

### 1.2 Reading the `.fld`

* Coordinates come back in **SI meters** even though you asked in mm (×1000 to plot in mm).
* `Speed` returns **three vector columns** — take the magnitude.
* `Nan` (and exact 0 for temperature) = the point is outside the solution domain — mask it.
* Render with `matplotlib.tricontourf` on the two in-plane axes, `Agg` backend.
* matplotlib must run in a **separate process** from anything importing AEDT
  (GLIBCXX clash).

### 1.3 Quantity-name schism

The same physical quantity has *different names per API*: the fields calculator
(`EnterQty`) wants `Temp` / `Speed` / `Pres`; field *plots* (`CreateFieldPlot`,
`create_fieldplot_*`) want `Temperature` / `Speed` / `Pressure`; the Fields
Summary wants `Temperature`. Mixing them up fails with an unhelpful gRPC error.

## 2. Cross-section plots: named construction plane, not face IDs

A user's hand-drawn section plane (GUI: *Draw → Plane*) lives in the design as a
construction `Plane` (`$begin 'Planes'` in the `.aedt`). It does **not** carry
over when geometry is replaced, and any plot that referenced a **numeric face
ID** dangles silently after a geometry swap. Recreate both by name:

```python
ipk.modeler.create_plane(name="Plane1",
    plane_base_x="-51.28mm", plane_base_y="0mm", plane_base_z="1058.25mm",
    plane_normal_x="0mm",    plane_normal_y="-1mm", plane_normal_z="0mm")

p = ipk.post.create_fieldplot_cutplane(assignment=["Plane1"], quantity="Speed",
                                       setup="Setup1 : SteadyState",
                                       plot_name="VELOCITY_CROSSECTION")
p.IsoVal = "Tone"; p.Refinement = 2; p.plot_folder = "Speed"; p.update()
```

Name-based assignments survive geometry changes; ID-based ones do not.
(`create_plane` calls `oEditor.CreateCutplane` under the hood.)

## 3. `.dsp` plot bundles — the same-session rule

`.dsp` is AEDT's loadable bundle of field-plot definitions **+ computed plot
data** (the GUI's *save fields plots* workflow — handy for carrying a plot set
between designs):

```python
ipk.ofieldsreporter.SaveFieldsPlots(["VELOCITY_CROSSECTION", "PRESSURE_CROSSSECTION"],
                                    "/path/bundle.dsp")
```

**The trap:** plots loaded from a reopened project have no computed data, and
`SaveFieldsPlots` then writes a **0-byte file** — `UpdateAllFieldsPlots()` does
*not* fix the save. Only plots **created in the session that saves them**
produce a valid bundle (a 3-plot bundle ≈ 5 MB; a GUI save of 15 rendered plots
was 37 MB). Recipe: delete → recreate → `SaveFieldsPlots` immediately.

## 4. Rendered snapshots without a human (GUI mode on a virtual/remote display)

Pure headless (`-ng`) cannot render: no GL context. But if the machine has a live
X display (e.g. the user's remote-desktop session, `DISPLAY=:1`), a scripted
**GUI-mode** AEDT renders everything:

```python
ipk = Icepak(project=copy_path, design="IcepakDesign2", version="2026.1",
             non_graphical=False, new_desktop=True)      # DISPLAY=:1 in the env
oe = ipk.modeler.oeditor
oe.ExportModelImageToFile(png_path, 1600, 1200,
    ["NAME:SaveImageParams", "ShowAxis:=", "False", "ShowGrid:=", "False",
     "ShowRuler:=", "False", "ShowRegion:=", "Default", "Selections:=", "",
     "FieldPlotSelections:=", "VELOCITY_CROSSECTION",    # <— MUST name the plot
     "Orientation:=", "isometric"])
```

The traps, in the order they bit:

1. **The user's open GUI blocks every scripted session** — the per-user
   automation lock makes any second session die at `SetActiveDesign` with
   *"access to the requested resource is not permitted"*, **even on a different
   project file**. The GUI must be closed first (`-batchsolve` is the one thing
   that coexists with an open GUI).
2. **`FieldPlotSelections` must name the plot.** Empty string = contour silently
   omitted. The tell: byte-identical PNGs across different fields.
3. **Loaded plots render blank** (same root cause as the `.dsp` rule — no
   computed data). Cut-planes: delete + recreate in-session before snapping.
4. **Streamlines can't be created by script** (the `'Particle Trace
   Definitions'` scripting block is undocumented; `CreateFieldPlot` with
   `StreamlinePlot:=True` fails) — but a **GUI-created streamline can be
   force-computed** in a scripted session with
   `UpdateQuantityFieldsPlots("Speed")` + `UpdateAllFieldsPlots()`, after which
   it snapshots fine. So: human creates the streamline once; scripts snapshot it
   forever.
5. `ExportPlotImageToFile` does **not** exist in Icepak 2026.1 (every arg form
   fails). `ExportModelImageToFile` is the exporter.
6. Orientations: `front / back / left / right / top / bottom / isometric`
   (+ `trimetric` / `dimetric`). Isometric is the 45° view. `FitAll()` first.
7. Work on a **copy** of the project — and expect a visible AEDT window to pop
   up on the display while it runs (warn whoever owns the desktop).

### 4.1 Wireframe rendering (unobstructed contours)

The GUI's *Render → Wireframe* equivalent is per-object:

```python
oe.ChangeProperty(["NAME:AllTabs", ["NAME:Geometry3DAttributeTab",
    ["NAME:PropServers"] + all_object_names,
    ["NAME:ChangedProps", ["NAME:Display Wireframe", "Value:=", True]]]])
```

With everything wireframed, a mid-assembly cut-plane or streamline bundle is
fully visible from any orientation. (Per-object `Transparent` on the same tab is
the softer alternative — e.g. air volume 0.75, cosmetic shells 0.85.)

## 5. One more results trap: the stale Solution Overview

After a **BC-only edit + mesh-reuse re-solve** (e.g. a power sweep),
`ExportSolutionOverview`'s *heat-flow* section is correct for the new power, but
its **"Maximum Temperatures For Thermal BCs" block replays the previous solve's
values** — at 2 W it happily reported the 13.8 W solve's 117 °C, physically
impossible. The SOV's own footnote points overlapping objects at the Fields
Summary; make that the rule: **swept/re-solved temperatures always come from the
Fields Summary**, the SOV is for power and flow balance only. (A ~15 M-cell
BC-only sweep point = set `b.props["Total Power"]` + save → 16-core `-batchsolve`
(meshing shows 00:00:00 = reused) → Fields-Summary readout ≈ 16 min/point.)

## Runnable examples

| Script | What it shows |
| --- | --- |
| [`15_grid_export_contours.py`](https://github.com/Mengero/AICFD/blob/main/icepak-examples/15_grid_export_contours.py) | Native `ExportOnGrid` plane sections (T/V/P) → matplotlib contour PNGs. |
| [`16_cutplane_plots_and_dsp.py`](https://github.com/Mengero/AICFD/blob/main/icepak-examples/16_cutplane_plots_and_dsp.py) | Construction plane + name-based cut-plane plots + a valid `.dsp` bundle (same-session rule). |
| [`17_rendered_snapshots.py`](https://github.com/Mengero/AICFD/blob/main/icepak-examples/17_rendered_snapshots.py) | GUI-mode rendered snapshots: `FieldPlotSelections`, wireframe, streamline force-compute, 7 orientations. |
