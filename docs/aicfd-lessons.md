# Lessons Learned — Icepak Mesh Sensitivity Driver

> Running log of rules from the user and technical findings about AEDT / PyAEDT
> for this project. Updated as we go. Read this first before resuming.

## Summary — top 10 lessons from this study

(Compiled 2026-05-20 after 7 iterations + the convergence-troubleshooting
discussion. See later sections for the full evidence and code references.)

### Convergence rigor depends on the use case (engineering judgment)

There are two different "converged" bars:

1. **Engineering converged** — the physical metrics you care about
   (mass flow, max temperature, ΔP, ΔT) have stopped changing iter-to-iter
   beyond your error tolerance. Residual oscillations and bounded spikes
   are fine if the bulk numbers are stable. This is enough for most
   design decisions and trade studies.
2. **Numerically converged** — every residual is monotonically below its
   target (typically 1e-3 for flow, 1e-6 for energy) with no spikes at
   the end. Required for: acceptance criteria, regulatory filings,
   publication, safety-critical work, and any case where you have to
   *defend* the result.

User stated 2026-05-20: "if you are targeting a non-oscillates simulation,
you don't need a fully clean run; but if you want to make sure the
simulation does converge and no spike at the end, you need to run a
fully one." Use this to decide how hard to push the solver.

**For the noduct dockport fix** specifically: the catastrophic K=10¹²
blowup was eliminated, mass flow converged to 7.74 g/s and held stable
for 500+ iterations. That's bar 1 (engineering converged). To reach
bar 2, the next escalation is
`Sequential Solve of Flow and Energy Equations = false`.

### Process / monitoring (very important — added late, learned the hard way)

**Monitor long solves actively; never just wait.** When you launch a
multi-hour Icepak solve, set up a watchdog *alongside* it that polls the
live `.sd` residual files every ~30–60 s. The watchdog should be silent
when residuals decay smoothly, and shout when they spike, go NaN, or
plateau. Kill bad runs at minute 10 instead of riding them out for an
hour. See `scripts/watch_solve.py` and `~/.claude/.../memory/feedback_monitor_dont_wait.md`.

### Mesh-convergence engineering

1. **"Same cell count, different distribution" is not the same mesh.** iter_06
   and iter_04 had nearly identical cell counts (~10–11 M) but gave Fan2 ΔP
   answers ~5 % apart. Where cells *are* matters as much as *how many*. A
   convergence study that only sweeps cell count will mislead you.
2. **Convergence is per-metric, not per-mesh.** In this project, max heat-source
   T / dT / mass flow / Fan1 ΔP were mesh-converged at the baseline; Fan2 ΔP
   alone needed global refinement to 1.5 mm. Always check *every* metric you
   care about separately — don't lump them.
3. **Test orthogonal refinement axes before declaring convergence.** I called
   the mesh converged at iter_04 after a global-only sweep; iter_06 (local
   axis) immediately broke that. The honest test is to refine each major
   mesh knob independently *and* in combination.
4. **The baseline mesh can be biased, not just noisy.** Baseline → iter_04
   moved Fan2 ΔP by ~5 % in a *consistent* direction. That's bulk-air
   under-resolution, not random spread. Cheaper meshes systematically miss
   the converged answer in a predictable direction.
5. **Solver convergence ≠ mesh convergence.** iter_03/05/06/07 ended with
   Continuity above the 10⁻³ target; their *metrics* were still stable
   across mesh changes. Don't conflate "Continuity stalled" with "result
   untrustworthy" — momentum / energy converging plus stable bulk metrics is
   usually enough for engineering answers.
6. **Energy balance is the cheapest sanity check.** 200 W chip in, ~200 W
   out via the env opening across every iteration (<0.01 W gap). If that
   balance breaks, *any* metric from that solve is suspect.

### Process / methodology

7. **Disk-first beats API.** When the AEDT scripting layer fails or stalls,
   look at `*.SOV`, `*MON*.sd`, `*.profile` in `.aedtresults/` — they're
   plain text and have everything the official API tries to give you. Many
   hours can be saved by checking the output folder *first* instead of
   debugging the API.
8. **Never reopen a closed iteration project via PyAEDT.** The AEDT COM
   layer can't reliably reattach a saved solution context, and repeated
   open/save cycles can *wipe `*.Field/fields.resd`* — destroying the
   actual results. Post-processing must happen in the same session that
   solved. Visualization-only access = AEDT GUI, never PyAEDT.
9. **One variable per iteration.** Every iteration that mixed two changes
   (or used both `max_element_size` and `level`) cost extra debugging. Hold
   *everything* constant except the one knob under test, and the resulting
   delta is unambiguously attributable.

### AEDT-specific gotchas

10. **Mesh adaption fires on a schedule; residual spikes that look like
    "restart events" usually are.** Every ~100–150 iters when adaption is
    enabled the residuals jump together (K and ω the most, Continuity
    second). To judge convergence cleanly, disable adaption and run on a
    frozen mesh. The first spike (≈iter 180) can also be the first-order →
    second-order discretization switch or turbulence-equation activation;
    distinguish via the solver Output Log.


---

## 1. User preferences (rules — apply automatically)

### Autonomy
- **Don't ask permission for routine ops.** `pip install`, running the project
  Python, `mkdir`, `ls`, file edits inside the project tree — just do them.
  See `~/.claude/settings.json` for the allowlist.
- **Don't ask to kick off the next obvious step.** When a multi-stage workflow
  has a defined next action (e.g. "launch iter_02 after the code change"),
  launch it; don't pause and offer to launch.
- **Don't ask for engineering opinion on the next mesh direction either.**
  Pick the most defensible next refinement, set it up, kick it off, report.
  User verbatim 2026-05-19: "if you have idea, just go for it, don't ask my
  opinion." Even the "after-solve review checkpoint" is not a question —
  print the summary, propose the next iter, and immediately launch it. The
  user reviews the previous iteration's GUI plots while the next solve runs,
  and interrupts only if they want to redirect.

### Scope
- **Only mesh changes are allowed per iteration.** Never modify geometry,
  materials, boundary conditions, fans, heat sources, or solver setup.
- **One mesh variation per script invocation.** Solve, save, exit. Don't
  start a new variation in the same process.
- **Original baseline `.aedt` is untouchable.** All work happens on per-iteration
  copies under `outputs/iter_<NN>/`.

### Compute
- **CPU only.** Do not switch to `GPU_SOLVER` (a separate setup that exists
  in the project but isn't part of this study).
- **Tasks × cores: 24 × 24** (user's choice — oversubscribed on a 24-thread
  machine, but they explicitly asked for it). Live in `configs/study.yaml`.

### Project-specific physics decisions
- **Inlet and outlet both live on the `env` boundary** — `env` is one
  Total-Pressure Opening with 2 faces (IDs `11578`, `11569`). One is the
  inlet, one is the outlet. The face split by temperature would tell us
  which is which, but the API for that is broken (see §3).
- **Fin-base target = `VAPORCHAMBERBASEPLATE_1`** for the "max fin-base T"
  metric (not the 100+ `FINS_*` parts).
- **`Grille` is internal porous-fabric resistance**, not an opening.

---

## 2. Project specifics (this Icepak project)

### File locations
| What | Path |
|---|---|
| Original baseline `.aedt` | `_F04_TORSO_70mm_foam_opening_study.aedt` (this folder) |
| Per-iteration outputs | `outputs/iter_<NN>/` |
| Cumulative metrics | `outputs/history.csv` |
| Mesh config (you edit each iter) | `configs/mesh.yaml` |
| Machine paths + post hints | `configs/study.yaml` |
| Source modules | `src/` |
| Entry script | `scripts/run_mesh_iteration.py` |

### Design tree
- Design: `IcepakDesign1` (steady-state)
- Setups: `Setup1` (CPU — what we solve), `GPU_SOLVER` (GPU — leave alone)
- Optimetrics: `ParametricSetup1` (prior sweeps on `opening`)
- Setup1 properties: **max 1000 iterations**, problem type `TemperatureAndFlow`,
  flow `Laminar`, radiation `Off`
- Parametric variable: `opening`, nominal value `0.2`

### Boundaries
- `MRC_heatsource`
- `Grille` (internal porous fabric, NOT an opening)
- `env` (Total-Pressure Opening, 2 faces = inlet + outlet)
- `airchannel`

### Mesh (read from the baseline .aedt text on 2026-05-19)

The baseline has a comprehensive mesh setup already:

```
Global mesh region:
  MeshMethod=MesherHD
  MaxElementSize X/Y/Z = 3 mm         ← already 3mm; iter_02 was a no-op
  MinElementsInGap = 3
  MinElementsOnEdge = 2
  MaxSizeRatio = 2
  EnableMLM = true, MaxLevels = 3      → effective min element ≈ 0.375 mm
  MinGap X/Y/Z = 0.5 mm
  BufferLayers = 0
  OptimizePCBMesh = true

MeshRegion1 (Objects=11890):
  MaxElementSize X/Y/Z = 1.5 mm        ← local refined region
  MaxLevels = 2, 2D MLM XY
  MinGap X/Y/Z = 0.1 mm

MeshOperation1 (Objects=18374): MinLevel=MaxLevel=2 (level-based)
MeshOperation2 (Objects=17410): MinLevel=MaxLevel=2 (level-based)
```

- iter_01 baseline cells: **6,800,687**
- iter_01 solve wall-clock: **2,141.6 s** (≈ 35:42)
- **Implication:** tightening the *global* `MaxElementSize` below 3 mm is the
  cleanest first refinement direction; reducing the local 1.5 mm in
  MeshRegion1 is the second; bumping level-based ops from 2 to 3 is the
  third. Reducing `MinGap` and bumping `MaxLevels` are independent finer
  knobs.

### Field overlays (already in the design tree from prior work)
- `Speed`, `Speed2`, `Speed3`, `Speed4`
- `Temperature`
- `Velocity`

### Environment
- Python: `C:\Users\Jiong Chen\AppData\Local\Python\pythoncore-3.14-64\python.exe`
  (Python 3.14.5)
- AEDT: `C:\Program Files\ANSYS Inc\v252\AnsysEM\ansysedt.exe` (v252 = 2025.2)
- PyAEDT package: `ansys-aedt-core` 0.27.1 (legacy `import pyaedt` doesn't
  work; use `from ansys.aedt.core import Icepak, ...`)

---

## 3. AEDT / PyAEDT pitfalls

### CATASTROPHIC: never reopen an iteration `.aedt` via PyAEDT
- Each `release_desktop(close_projects=True)` saves the project, and on a
  closed-then-reopened Icepak project the AEDT COM layer can't relink the
  solution context.
- **Repeated open/close cycles WIPE `.aedtresults/<design>.results/*.Field/`.**
  Confirmed empirically 2026-05-19: after 4 probe sessions opened iter_01,
  the entire `DV*_SOL*_V*.Field/fields.resd` folder was deleted. The `.aedt`
  shell file remains valid; the actual solved field data is gone.
- **Visualization rule:** open per-iteration `.aedt` files **only in the AEDT
  GUI**. Never via PyAEDT. The `rerun_post.py` pattern is impossible — don't
  reintroduce it.

### `FieldSummary.export_csv` is broken on nominal-only projects
- PyAEDT 0.27 code path:
  ```
  variations = self._app.available_variations.variations(setup, True)[0]
  ```
  Throws `IndexError` when `variations()` returns `[]` — which it does for
  this design because `osolution.GetAvailableVariations("Setup1")` raises
  `script macro error: solution 'setup1' was not found`.
- **All `icepak.post.evaluate_*_quantity(...)` calls fail downstream** of
  this bug. Even calling AEDT's `ExportFieldsSummary` directly via
  `icepak.odesign.ExportFieldsSummary(...)` silently no-ops (no CSV
  produced) for this project.
- **Workaround for now:** automated extraction yields only cell count
  (parsed from `.profile`) + Python wall-clock. T / P / dT / dP / fin-base T
  must be read visually from the AEDT GUI per iteration.
- Future workaround to try: the Fields Reporter / Calculator module via
  `oModule = oDesign.GetModule("FieldsReporter")` — different API path,
  may sidestep the FieldSummary bug.

### NEVER `taskkill` an AEDT solve — leaks Icepak license tokens

**iter learned 2026-05-20:** if you `Stop-Process -Force` an `ansysedt.exe`
that is mid-solve, the `elec_solve_icepak` floating license tokens it
holds are NOT returned to the Ansys license server. Subsequent solve
attempts then fail in 4–6 s with the generic PyAEDT log:

```
PyAEDT ERROR: Error in Solving Setup Setup1
[solve] Setup1: 4.3s (FAILED)
```

This looks identical to a mesh failure, but it's actually a licensing
denial. The real error is in
`C:\Users\<u>\AppData\Local\Temp\.ansys\ansyscl.<host>.log`:

```
DENIED  elec_solve_icepak
"Insufficient count is available to satisfy the feature request.
 elec_solve_icepak (Ansys Electronics Enterprise - Shared Web: 0 available of 2 needed)"
```

**Recovery:** wait 10–30 min for the license server idle timeout to
release the orphan tokens, then retry. If after 30 min it still fails,
the licensing admin needs to manually release the checkout on the Ansys
license server (no user-side fix).

**Avoidance:** don't force-kill mid-solve. If a solve has obviously
diverged, two safer options:
1. Let it run to max_iterations (cheaper than re-acquiring licenses).
2. Use PyAEDT's `icepak.odesktop.AbortAndCloseProject()` or
   `oDesktop.QuitApplication()` for a graceful shutdown that returns
   licenses cleanly.

### Local refinement: `max_element_size` and `level` are MUTUALLY EXCLUSIVE

**iter_06 first attempt (2026-05-20) failed** because mesh.yaml set both:

```yaml
local_refinements:
  - objects: [VAPORCHAMBERBASEPLATE_1]
    max_element_size: "1mm"
    level: 3
```

`icepak.mesh.assign_mesh_region(assignment=…, level=3, name=…)` creates a
**level-based** subregion. Level-based subregions don't expose
`MaxElementSizeX/Y/Z` on their settings dict; the subsequent attempt to set
them was rejected with `"Setting not available"` *and* corrupted the mesh
state enough that the solve aborted in 16 s ("Error in Solving Setup1").
`src/mesh_override.py` now treats the two modes as exclusive — size-based
regions don't pass `level` to `assign_mesh_region`.

### `get_scalar_field_value` and `get_temperature_extremum` are LANDMINES

**2026-05-20 — confirmed empirically.** These PyAEDT helpers (which I'd
added as an alternative path to `FieldSummary`) crash inside the
`icepak.existing_analysis_sweeps` property accessor with
`'NoneType' object is not iterable` on nominal-only Icepak projects.
**Worse: the crash plus the subsequent `release_desktop` close/save cycle
WIPES the `.sd`, `.SOV`, and `.profile` files from
`.aedtresults/<design>.results/`**, leaving only `fields.resd`. iter_05's
physics numbers were lost this way despite the solve succeeding.

**Rule:** do not call any of these on this design:
- `icepak.post.get_scalar_field_value(...)`
- `icepak.post.get_temperature_extremum(...)`
- `icepak.post.get_field_extremum(...)`

Use disk parsing (`src/sd_parser.py`) instead — the SOV file has every
metric we need, written by the solver itself, with no API risk.

### Disk-first extraction (LESSON learned the hard way)

When the API extraction path silently fails, **read the
`.aedtresults/<design>.results/` folder directly** before debugging the
API any further. The folder contains plain-text files with the data:

- `<DV>_S67_MON0_V*.sd` — per-iteration residuals
  (Continuity, XVelocity, YVelocity, ZVelocity, Energy). One line per
  iteration: `<iter> Continuity(value)XVelocity(value)...`
- `<DV>_S67_MON1_V*.sd` — per-iteration monitor quantities
  (MassFlow, VolumeFlow, Temperature on the monitor face). Same line
  format. The monitor is `Fan2_Passage_Face11871` (Face 11871 on the
  fan passage — these values are at THAT face, not domain averages).
- `<DV>_SOL68_MON0_V*.sd` — final-iteration residual values.
- `<DV>_SOL68_MON1_V*.sd` — final-iteration monitor values.
- `<DV>_S67_V*.profile` — solver profile log with timing breakdown
  and metadata (cores, tasks, processor count).

**Take-away:** the data was on disk for every iteration we ran. The
FieldSummary fight was the wrong investigation. Always inventory the
output directory first. This is now codified in
`~/.claude/projects/.../memory/feedback_check_disk_first.md`.

### Cell count must be grabbed before AEDT closes
- The `.profile` log lives at
  `outputs/iter_<NN>/<name>.aedtresults/IcepakDesign1.results/*.profile`.
- It's **deleted on `release_desktop`**.
- `src/post.py: snapshot_cell_count(results_root)` parses it in-session,
  before close. Don't move this call after `release_desktop`.

### AEDT 2025.2 quantity names
- Velocity scalar is named **`Speed`**, not `Velocity_Magnitude`. Using the
  latter silently fails. Confirmed in `src/field_plots.py`.
- Temperature is just `Temperature`. Pressure is just `Pressure`.

### Boundary face IDs
- A boundary object's faces live at `b.props["Faces"]`, NOT `b.faces` (which
  doesn't exist on `BoundaryObject` for openings).
- `env.props["Faces"]` = `[11578, 11569]`. Use these for per-face plots and
  per-face evaluation.

### PyAEDT install
- `pip install pyaedt` installs the package as `ansys.aedt.core`. The legacy
  `import pyaedt` raises `ModuleNotFoundError`. Use:
  ```python
  from ansys.aedt.core import Icepak
  ```

### Parallel scaling (this design)
- Baseline 8 cores: 2121 s
- 1 task × 12 cores: 2121 s (no change)
- 24 tasks × 24 cores (576 threads on 24-thread machine): 2141 s (slightly
  slower from oversubscription)
- **Implication:** Icepak's laminar pressure-velocity solve doesn't benefit
  past about 12 threads for this mesh size. Diminishing returns; outright
  contention past 24.

---

## 4. Useful patterns

### Launch one iteration
```powershell
& "C:/Users/Jiong Chen/AppData/Local/Python/pythoncore-3.14-64/python.exe" scripts/run_mesh_iteration.py
```

### Edit `configs/mesh.yaml` per iteration
- Tighten global element size:
  ```yaml
  label: "global_3mm"
  mesh:
    global:
      MaxElementSizeX: "3mm"
      MaxElementSizeY: "3mm"
      MaxElementSizeZ: "3mm"
  ```
- Local refinement (e.g. fins):
  ```yaml
  label: "fins_level3"
  mesh:
    global: {}
    local_refinements:
      - name: "fins"
        objects: ["VAPORCHAMBERBASEPLATE_1"]
        level: 3
        max_element_size: "1mm"
  ```

### Inspect a previous iteration visually
1. Open AEDT GUI.
2. `File → Open` → `outputs/iter_<NN>/_F04_TORSO_70mm_foam_opening_study.aedt`.
3. `Field Overlays → Temperature` → double-click any `meshstudy_T_*` plot.
4. `Setup1 → right-click → Solution Overview / Profile / Mesh Viewer`.
5. **Do not open via PyAEDT** under any circumstance (would destroy results).

---

## 5. Iteration log

| iter | label | cells | solve [s] | iter# | conv | **MRC max T [°C]** | dT_air [°C] | Fan1 ΔP [Pa] | total ṁ [g/s] | env Q [W] |
|---|---|---|---|---|---|---|---|---|---|---|
| 01 | baseline | 6,800,687 | 2,141.6 | 208 | ✓ | **53.339** | 12.53 | 28.34 | 15.87 | −199.99 |
| 02 | global_3mm | 6,777,631 | 1,142.9 | 184 | ✓ | **53.308** | 12.52 | 28.27 | 15.88 | −200.00 |
| 03 | global_2mm | 8,003,276 | 3,199.6 | 845 | ✓* | **53.411** | 12.55 | 28.66 | 15.85 | −199.99 |
| 04 | global_1p5mm | 10,515,961 | 3,290.7 | 392 | ✓ | **53.431** | 12.61 | 28.78 | 15.77 | −199.99 |
| 05 | global_1mm | 16,938,666 | 7,073.6 | 822 | ✓\* | **53.337** | 12.60 | 28.49 | 15.77 | −199.99 |
| 06 | MeshRegion1_1mm | 11,042,401 | 3,483.8 | 820 | ✓\* | **53.363** | 12.53 | 28.47 | 25.52 | 15.86 | −199.99 |
| 07 | combined_1p5_and_R1_1mm | 14,760,202 | 5,457.5 | 824 | ✓\* | **53.475** | 12.62 | 29.04 | 26.76 | 15.75 | −199.99 |

\* iter_06 Continuity 1.7e−3, iter_07 Continuity 4.0e−3 (both partial; same
behavior as iter_03 / iter_05 where the finer mesh slowed Continuity but
momentum/energy converged and bulk metrics were stable).

### Fan2 ΔP is NOT mesh-converged (revised verdict — 2026-05-20 evening)

iter_06 broke the earlier "converged" call. Refining the local
`MeshRegion1` (1.5 → 1 mm) instead of the global cap gives a Fan2 ΔP
that **drops back to the iter_01/02/03 range (25.5 Pa)** — the
iter_04/05 "converged" Fan2 ΔP of ~26.8 Pa was a global-refinement
artefact, not the true converged value. The two refinement axes pull
the answer in opposite directions:

| iter | global | MeshRegion1 | cells | Fan2 ΔP |
|---|---|---|---|---|
| 01 | 3 mm (baseline) | 1.5 mm (baseline) | 6.8 M | 25.62 |
| 04 | 1.5 mm | 1.5 mm (baseline) | 10.5 M | **26.74** ↑ |
| 05 | 1.0 mm | 1.5 mm (baseline) | 16.9 M | **26.94** ↑ |
| 06 | 3 mm (baseline) | 1.0 mm | 11.0 M | **25.52** ↓ |

Fan2 ΔP range across mesh strategies = **1.42 Pa (5.5 %)**. iter_07 will
combine global=1.5 mm + MeshRegion1=1.0 mm to see which Fan2 ΔP the
combined refinement converges to. MRC T, dT, total ṁ, and Fan1 ΔP all
look mesh-converged regardless of axis (≤ 0.1 °C, ≤ 1 %, ≤ 0.5 %, ≤ 1 %
spread).

### Final verdict after iter_07 (2026-05-20 late evening)

iter_07 (combined refinement) lands at **Fan2 ΔP = 26.76 Pa**, matching
iter_04's 26.74 Pa to within 0.02 Pa. The pattern across all 7 iterations:

| iter | global | MeshRegion1 | Fan2 ΔP |
|---|---|---|---|
| 01 / 02 / 03 | 3 mm (baseline) | 1.5 mm | ≈ **25.6** |
| 04 | 1.5 mm | 1.5 mm | **26.74** |
| 05 | 1.0 mm | 1.5 mm | **26.94** |
| 06 | 3 mm (baseline) | 1.0 mm | **25.53** |
| 07 | 1.5 mm | 1.0 mm | **26.76** |

**The split is on the GLOBAL cap, not MeshRegion1.** When global is at
the baseline 3 mm, Fan2 ΔP = ~25.6 Pa regardless of MeshRegion1 size.
When global is ≤ 2 mm, Fan2 ΔP = ~26.8 Pa regardless of MeshRegion1 size.
The MeshRegion1 knob doesn't move Fan2 ΔP — it's the bulk-air mesh that
controls the system curve for Fan2.

**The baseline mesh under-resolves the bulk air**, biasing Fan2 ΔP low
by ~5 %. The converged answer is **Fan2 ΔP ≈ 26.8 Pa** at iter_04's
mesh (10.5 M cells, ~55 min). iter_05 confirmed convergence direction;
iter_07 confirmed the local axis adds nothing once global is tight.

**Recommended production mesh: iter_04's setting (global `MaxElementSize 1.5 mm`)**
unless you accept ~5 % bias on Fan2 ΔP for the cheaper baseline (~36 min).

\* iter_05's Continuity ended at 4.75e−3 (target 1e−3). Momentum/Energy
converged; bulk metrics stable; "almost-converged" flag, but the engineering
metrics are mesh-converged regardless. Calling it ✓ for the study.

*iter_03's Continuity residual ended at 2.5e−3 (target 1e−3); momentum/energy
converged so it is flagged ✓ but the mesh refinement made flow convergence
slower (845 iters vs 208).

### Where the numbers come from (disk only — no AEDT API)

- `<iter>_SOL68_MON0_V*.sd` → final residuals (Continuity, XVelocity,
  YVelocity, ZVelocity, Energy)
- `<iter>_SOL68_MON1_V*.sd` → fan-passage monitor (MassFlow, VolumeFlow,
  Temperature at Face 11871)
- `<iter>_*_V*_*.SOV` → Solution Overview — per-boundary
  Temperature, Mass Flow Rate, Heat Transfer Rate, Fan Operating
  Pressure, Input Power. **This is the gold mine** — covers the task
  spec's required metrics in one ~1 KB plain-text file. See
  [[reference-aedt-close-reopen]] memory + `src/sd_parser.py`.

### Engineering conclusion across iter_01 → iter_03

Total spread on the *physics* metrics across these 3 meshes:
- MRC max T (≈ heat-source / fin-base): **±0.05 °C** (0.10 °C peak-to-peak,
  ~0.19 % of the ~53 °C value)
- air ΔT (computed from Q / (ṁ·cₚ) using SOV energy balance): **±0.02 °C**
- Fan1 operating ΔP: **±0.20 Pa (~1.4 %)** — the least converged metric
- env heat removal: <0.01 W spread; energy balance closes to 200 W ✓

**The baseline mesh (iter_01) is already inside engineering convergence**
on the task-spec metrics. The 2 mm refinement (iter_03) cost 3× the solve
time for ≤ 0.1 °C / ≤ 0.4 Pa change. If iter_04 (1.5 mm, in flight) doesn't
show a bigger jump, the study can call iter_01's mesh "good enough."

**Update after iter_04:** Fan2 ΔP jumped +4.37 % iter_03 → iter_04 — the
biggest single-step movement so far. The other metrics still look tight
(MRC T +0.020 °C, Fan1 ΔP +0.43 %, dT +0.062 °C). So the system is *almost*
mesh-converged but Fan2's operating point is still drifting. iter_05 will
push global to 1.0 mm to see if that delta drops below ~1 % (converged) or
keeps moving (need local refinement around the Fan2 inlet).

**Final verdict after iter_05 (2026-05-20):** iter_04 → iter_05 deltas all
within tolerance — Fan2 ΔP settled at +0.73 % (well under the 1 % rule),
MRC T −0.18 %, dT −0.04 %, total ṁ +0.04 %. The Fan2 wobble seen at iter_04
was self-corrected by the next refinement. **Mesh-converged at iter_04
(10.5 M cells, ~55 min).** Baseline iter_01 (6.8 M cells, ~36 min) is
within ~1.4 % of converged on the loosest metric (Fan2 ΔP) — acceptable
for most engineering judgments; pick iter_04's mesh when tighter accuracy
is needed.

### Recommended production mesh

| use case | mesh | cells | solve | trade-off |
|---|---|---|---|---|
| Default engineering (≤2 % accuracy) | **iter_01 baseline** (no overrides) | 6.8 M | ~36 min | cheapest, within 1.4 % on Fan2 ΔP and tighter on everything else |
| Tighter (≤1 % accuracy) | **iter_04 mesh** (`MaxElementSize 1.5 mm` global) | 10.5 M | ~55 min | fully mesh-converged on every task-spec metric |
| Diagnostic / overkill | iter_05 mesh (1.0 mm global) | 16.9 M | ~118 min | no metric gain over iter_04; flow-convergence harder |

### Convergence so far (engineering interpretation)

- **MassFlow at the fan-passage monitor is essentially mesh-converged** —
  total spread across iter_01–03 is 0.32 % (7.817 to 7.842 g/s).
- **The fan-passage T monitor sits at the inlet side** (T = ambient 20 °C
  for all three iters), so doesn't show ΔT. To get air dT and max fin-base T
  we still need the Field Calculator path on the `env` faces /
  `VAPORCHAMBERBASEPLATE_1`. Code added in `src/post.py`; will run for
  iter_05+.
- **iter_03's incomplete convergence is the bigger concern** than refinement
  step size. Before continuing to 1.0 mm, we should understand why the 2 mm
  mesh is harder to converge — likely transition-zone cells with high aspect
  ratio. Possible fixes: bump max iterations above 1000, or relax convergence
  controls; but these are SOLVER settings, not mesh settings (technically out
  of scope). Document and move on.

### Implications for next iterations
- **Global element-size sweep is the wrong knob.** Reducing `MaxElementSizeX/Y/Z` from default to 3 mm changed nothing because the project's pre-authored mesh ops were already finer than 3 mm in the regions that mattered.
- **The real mesh-sensitivity question is in the local mesh ops.** Investigate
  the two `MeshOperation*` definitions (read-only inspection) to see what
  they target and at what size. The convergence study should refine *those*,
  not the global cap.
- **Solve time variability is high** (47% swing on nearly the same mesh).
  Wall-clock alone is not a clean convergence metric — need numerical T / P.

---

## 6. Open follow-ups

- [x] ~~Try the **Fields Reporter / Calculator**~~ — partially done. Added
  `icepak.post.get_scalar_field_value` and `icepak.post.get_temperature_extremum`
  as primary extraction paths in `src/post.py`, with `_direct_field_summary`
  retained as fallback. Will be tested in iter_05 (iter_04 already running with
  old code). If the calculator path also fails, the next thing to try is a
  monkeypatch of `FieldSummary.export_csv` to skip the broken
  `available_variations.variations(setup, True)[0]` call.
- [x] ~~Validate that iter_02's saved field plots include working Speed and
  per-face Temperature plots~~ — done, 9/9 plots succeeded in iter_02.
- [ ] Read `MeshOperation1` / `MeshOperation2` settings from the baseline `.aedt`
  (read-only, no PyAEDT open) to plan a targeted local refinement strategy.
- [ ] Consider dialing tasks back to 8 × 1 = 8 cores given the scaling result
  in §3 — saves machine resources for other work without a meaningful
  solve-time penalty. (User explicitly chose 24×24 currently; keep until they
  ask otherwise.)
- [x] ~~Fix Unicode crash in summary.py (Δ → ASCII)~~ — done.
