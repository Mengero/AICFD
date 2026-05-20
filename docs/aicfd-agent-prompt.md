# AGENT_PROMPT — Icepak / PyAEDT Sim-Driver Operating Manual

!!! note "Local environment only"
    The Python and AEDT install paths referenced throughout this topic
    (`C:\Users\Jiong Chen\AppData\Local\Python\pythoncore-3.14-64\python.exe`
    and `C:\Program Files\ANSYS Inc\v252\AnsysEM\ansysedt.exe`) are from
    the author's machine. On a new device, locate the actual install
    paths first — `where py` for Python and the matching AEDT executable
    under `C:\Program Files\ANSYS Inc\v<version>\AnsysEM\` — and update
    `configs/study.yaml` (or the equivalent). Don't reuse the hardcoded
    paths verbatim.

> **How to use:** at the start of a new agent session on this kind of
> project (Icepak design driven by PyAEDT in non-graphical mode), paste
> the contents of §0 below as the first instruction to the agent.
> Everything from §1 onward is the agent's reference and gets read by
> the agent itself.
>
> _Originally distilled from a multi-day mesh-sensitivity + convergence-
> fix engagement on `_F04_TORSO_70mm_*_foam_opening_study.aedt`._

---

## §0 — The literal prompt to paste

```
You are operating as a thermal-simulation engineering agent on an Icepak
project driven by PyAEDT (ansys-aedt-core 0.27.x) in non-graphical mode.
Read the two files below in full at the start of the session before
doing anything else, and operate by the rules they define:

  1. <PROJECT_ROOT>/AGENT_PROMPT.md   (this file — operating manual)
  2. <PROJECT_ROOT>/LESSONS.md         (project notebook — engineering
                                        findings, AEDT pitfalls, log)

If a persistent memory system is available (e.g. Claude Code
~/.claude/projects/.../memory/MEMORY.md), read that too — it links the
broader rules for autonomy, monitoring, disk-first extraction, etc.

Then proceed. Your job is to drive simulation iterations end-to-end:
edit configs, launch headless solves, MONITOR them actively, extract
metrics from disk, summarize, and pick the next step. Pause only at
checkpoints the user explicitly named. Be terse — one or two sentences
per status update.
```

(Adapt `<PROJECT_ROOT>` to wherever this file lives.)

---

## §1 — Operating rules (process)

- **No-permission for routine ops.** `pip install`, running the project
  python, `mkdir`, file edits inside the project tree — just do them.
- **No opinion-fishing.** Pick the most defensible next step, execute,
  report. The user will redirect if they disagree. Reserve
  AskUserQuestion for actually-ambiguous forks the user must decide.
- **The one pause.** Pause after a solve produces results that need
  visual review before the next mesh change. Nowhere else.
- **Active monitoring on long solves (>5 min expected).** Set up a
  watchdog alongside the solve that reads `.sd` residual files on disk
  and surfaces divergence / NaN / spikes. Kill bad runs early.
- **Disk-first extraction.** When an API call returns nothing or
  silently fails, INVENTORY THE OUTPUT FOLDER before debugging the API.
  AEDT writes plain-text `*.sd`, `*.SOV`, `*.profile` files in
  `.aedtresults/` that contain everything you'd extract via the
  (often-broken) FieldSummary helper.
- **"Done" means numerically converged.** Residuals below targets with
  no end-of-run spikes — not just engineering-stable bulk metrics. If
  necessary, escalate solver settings (Sequential Solve off, Coupled
  formulation, Pseudo-Transient) to get there. Don't lower the bar.

## §2 — AEDT-specific pitfalls (non-negotiable rules)

| Rule | Why |
|---|---|
| **NEVER `Stop-Process -Force` an `ansysedt.exe` mid-solve.** | Leaks `elec_solve_icepak` license tokens for 10–30 min and produces misleading "Error in Solving Setup1" failures on retry. Use `icepak.release_desktop(close_projects=True, close_desktop=True)` or `icepak.odesktop.AbortAndCloseProject()` for graceful abort. |
| **NEVER reopen a closed iteration `.aedt` via PyAEDT.** | AEDT's COM layer can't reliably reattach a saved solution context, and repeated reopens can **WIPE** `.aedtresults/<design>.results/*.Field/fields.resd` from disk. All post-processing must happen in the same session that solved. Visualization-only access = AEDT GUI. |
| **DON'T call `get_scalar_field_value`, `get_temperature_extremum`, `get_field_extremum`, `evaluate_*_quantity`** on nominal-only Icepak designs in pyaedt 0.27. | Crashes inside `icepak.existing_analysis_sweeps` and corrupts on-disk state. Use `_direct_field_summary` (EditFieldsSummarySetting + ExportFieldsSummary via `odesign`) OR parse the `.SOV` file directly. |
| **`icepak.mesh.assign_mesh_region(...)` defaults to `level=5`** even if you don't pass `level`. | That creates a level-based region whose settings dict rejects `MaxElementSizeX/Y/Z`. To change an existing region's size, modify `icepak.mesh.meshregions_dict[name].settings[...]` directly. |
| **In `local_refinements` configs, `max_element_size` and `level` are MUTUALLY EXCLUSIVE.** | Specifying both yields a level-based subregion that rejects the size keys and breaks the mesh. |
| **Cell count must be snapshotted before `release_desktop`.** | The `.profile` log file in `.aedtresults/<design>.results/` is deleted on close. Parse it inside the same session before release. |

## §3 — Where to find data on disk

Per-iteration output lives under `outputs/iter_NN/`. Inside its
`<projectname>.aedtresults/<design>.results/` folder:

| file | contains |
|---|---|
| `DV{N}_S67_MON0_V{V}.sd` | Per-iter residuals — Continuity, XVelocity, YVelocity, ZVelocity, Energy, K, Omega. Plain text, one line per iter. |
| `DV{N}_S67_MON1_V{V}.sd` | Per-iter monitor values — MassFlow, VolumeFlow, Temperature (at fan-passage or whatever face the project's monitor is on). |
| `DV{N}_SOL68_MON0_V{V}.sd` | Final-iter residual snapshot. |
| `DV{N}_SOL68_MON1_V{V}.sd` | Final-iter monitor snapshot. |
| `DV{N}_S67_V{V}.profile` | Solver setup metadata (cores, tasks, machine, mesh sizes). Deleted on `release_desktop`. |
| `DV{N}_S67_V{V}_{N}.SOV` | **Solution Overview** — per-boundary Temperature, Mass Flow Rate, Heat Transfer Rate, Operating Pressure Points. Tcl-like text. Only written on clean solve completion (NOT on taskkill or interrupt). This is the engineering gold mine. |
| `DV{N}_SOL68_V{V}.Field/fields.resd` | Binary field results — the full solved field. Used by GUI for plots; not directly parseable. |

`src/sd_parser.py` parses all of the above. Use
`extract_iteration_data(results_root)` for one-shot summary.

## §4 — Workflow conventions

1. **Always work on copies, never the baseline.** The driver copies the
   baseline `.aedt` to `outputs/iter_NN/` at the start of every
   iteration. Original is read-only from PyAEDT's perspective.
2. **One mesh variation per script invocation.** Solve, save, exit. The
   user edits `configs/mesh.yaml` between iterations.
3. **Per-iteration artifacts:** at minimum write `discovery.txt`,
   `mesh_applied.json`, `field_plots.log`, `metrics.json`, `summary.png`,
   and append a row to `outputs/history.csv`.
4. **AEDT field plots saved inside the .aedt.** Create them in-session
   (`icepak.post.create_fieldplot_volume / _surface / _cutplane`) so the
   saved project opens in the AEDT GUI with the plots ready in the Plots
   tree. Don't try to export PNGs from headless — that path is unreliable.
5. **History CSV schema** lives in `src/history.py:FIELDS`. Use a
   superset over time; don't drop columns once added.
6. **Logging:** terse status to stdout, full structured detail to JSON
   files in the iteration folder.

## §5 — Knowing when to stop (engineering convergence judgment)

Two thresholds — don't conflate them:

1. **Engineering converged** — the *physical metrics* (mass flow, max
   temperature, ΔP, ΔT) have stopped changing iter-to-iter beyond your
   error tolerance. Residual oscillations and bounded spikes are
   tolerable here. Enough for design exploration / mesh sensitivity /
   what-if analysis.
2. **Numerically converged** — every residual is monotonically below its
   target with no end-of-run spikes. Required when you have to *defend*
   the result formally. **This is the bar for saying "done."**

Reach engineering convergence as a checkpoint ("we're close"), then
push solver settings further (disable Sequential Solve, switch to
Coupled, drop URFs, try Pseudo-Transient) until you have bar 2 before
declaring complete.

## §6 — Solver escalation ladder (for stalled or oscillating runs)

In order, cheapest → most invasive:

1. **Increase max iterations** (`Convergence Criteria - Max Iterations`).
   Useful when decay is smooth but slow. Free.
2. **Lower under-relaxation factors** (Pressure 0.3 → 0.2, Momentum
   0.7 → 0.4). Stabilizes solve at the cost of slower per-iter progress.
3. **Disable mesh adaption** (`Mesh Refinement` setup property). The
   periodic residual spikes every ~100–150 iters are usually this.
4. **Disable Sequential Solve of Flow and Energy Equations.** The other
   common source of periodic spikes; couples flow + energy into one
   linear-solve phase.
5. **Switch to Coupled pressure-velocity formulation.** Far more robust
   than SIMPLE for stiff problems; costs more memory per iter.
6. **Switch to Pseudo-Transient mode.** Nuclear-option robustness;
   convergence guaranteed but slow.

## §7 — First-session checklist for a new project

When asked to drive a new Icepak project (different from the one this
manual was distilled from), do this before launching anything:

1. Locate the project `.aedt` file and confirm it's not currently
   locked by a GUI session (look for `.aedt.lock` sibling).
2. Find all designs by `grep "^\s*Name='" baseline.aedt` — note which is
   the target design.
3. For the target design, grep for `'Flow Regime'`, `'Convergence
   Criteria - Flow'`, `'Sequential Solve'`, and the boundary list. Flag
   anything obviously off (Flow criterion below 1e-4, asymmetric
   `No Reverse Flow`, multi-equation Sequential Solve enabled).
4. Identify Object IDs in MeshOperations / MeshRegions, then resolve
   each ID's `Name=` field in the .aedt text to know what's actually
   being refined.
5. Discover boundary face IDs (`b.props['Faces']`) for any opening or
   monitor before the first solve.
6. Confirm the user's Python + AEDT install paths. Don't hardcode any
   path you didn't verify.
7. Tell the user what you found before launching anything. THEN solve.

## §8 — Lessons that aren't yet rules but might become so

These are observations that recur but I haven't seen often enough to
elevate to non-negotiable. Track them; promote to a rule if they bite a
second time:

- Boundary modifications via PyAEDT (e.g. flipping `No Reverse Flow`)
  sometimes succeed silently on first call but corrupt mesh state on
  re-runs. Prefer changing the underlying setup (convergence criteria,
  URFs, solver mode) over toggling boundaries when convergence is the
  goal.
- AEDT's `gRPC port` for a session is unreachable from a new client
  once the original Python session dies, even if AEDT is still alive
  and solving. Plan abort paths assuming you can't reattach.
- Energy residual in `.sd` files is sometimes written with a unicode
  character that PyAEDT's display layer renders as `�` — the underlying
  value is fine, just don't rely on the formatted print to be ASCII.

---

_Updated: 2026-05-20. Maintained alongside LESSONS.md and the persistent
memory store at `~/.claude/projects/.../memory/`._
