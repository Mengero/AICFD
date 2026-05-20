# AICFD

## Workflow Summary

The full AICFD workflow boils down to three steps:

1. **Set up paths** — locate the AEDT executable and Python interpreter. See [Paths](#paths).
2. **Edit and send prompt** (core procedure) — write the prompt that drives the agent. See [Edit and send prompt](#edit-and-send-prompt-core-procedure).
3. **Review simulation results** — wait for the agent to finish running, then check the simulation results. If there is any issue, send a prompt to the agent for modification. See [Review simulation results](#review-simulation-results).

---

## Paths

- **Python:** `C:\Users\Jiong Chen\AppData\Local\Python\pythoncore-3.14-64\python.exe` (use `py` to invoke)
- **pyaedt scripts:** `C:\Users\Jiong Chen\AppData\Local\Python\pythoncore-3.14-64\Scripts` — pip warned this isn't on PATH. Only matters if you want to run `pyaedt.exe` / `ansys-launcher.exe` directly; from Python code it's fine.
- **AEDT:** `C:\Program Files\ANSYS Inc\v252\AnsysEM\ansysedt.exe`

### Quick test snippet to confirm pyaedt can drive AEDT

```python
import ansys.aedt.core
app = ansys.aedt.core.Desktop(version="2025.2", non_graphical=False, new_desktop=True)
hfss = ansys.aedt.core.Hfss()
print(hfss.design_name)
app.release_desktop(close_projects=True, close_desktop=True)
```

## Edit and send prompt (core procedure)

**Recommended Prompt Structure:**

- **Goal:** What do you want to modify or build?
- **Context:** Which files, folders, documents, examples, or error messages are relevant to this task? You can also use `@` to mention specific files as context.
- **Constraints:** What standards, architecture, security requirements, or conventions does Codex need to follow?
- **Done when:** What conditions should be met before the task is considered complete — e.g., tests passing, behavior changing, or a specific bug no longer reproducing?

### Example prompt — mesh sensitivity study on an existing Icepak project

Use this as a copy-paste template when the goal is to iterate on mesh refinement against a project that is already authored. It assumes the geometry, materials, boundary conditions, fans, heat sources, and solver setup are all defined and must not be touched.

```text
## Goal
Run a mesh sensitivity study on an existing Icepak project, driven entirely by
a Python script that uses PyAEDT in non-graphical mode. The goal is to find a
mesh that is converged enough to trust but not larger than necessary. The
script performs exactly one mesh variation per invocation, saves the results,
prints a short summary, and exits. Each iteration is a checkpoint. I review
the result manually, decide whether the run is valid, then specify the next
mesh change. Geometry, boundary conditions, fans, materials, heat sources,
and solver setup must not be modified.

## Context
The baseline project already exists. Use it as the source of truth and do not
rebuild it.

* Reference project: `C:\Users\Jiong Chen\Documents\tmp_sim_files\_FIG4_P0_torso\70mm case\_F04_TORSO_70mm_foam_opening_study.aedt`

Work inside the current repository. If a sensible project layout does not
already exist, create one. For example:

* `src/`: PyAEDT helper modules.
* `scripts/run_mesh_iteration.py`: single-iteration entry point.
* `configs/mesh.yaml`: human-edited mesh settings for the current iteration.
* `outputs/iter_<N>/`: per-iteration project copy, plots, CSV, and log.
* `outputs/history.csv`: cumulative metrics across all iterations.
* `README.md`: usage instructions.
* `requirements.txt`: pinned dependencies.

If the repository already contains PyAEDT helpers or example automation, read
those first and reuse rather than reimplement.

Iteration model:

1. The first run is the baseline. It reads the existing mesh from the project
   exactly as authored, solves, and records metrics.
2. For every subsequent run, the user edits `configs/mesh.yaml` to change one
   or more mesh settings, for example the global element size, a local
   refinement on the heat exchanger fins, or a near-wall layer count. The
   script then opens the baseline project, applies the requested mesh
   overrides, solves, and records metrics.
3. The script never auto-launches the next iteration. It always stops after
   one solve.
4. Between iterations the agent acts autonomously. The only checkpoint where
   the agent must pause and wait for human input is after a solve has
   produced results that I need to validate before approving the next mesh
   change.

Track at minimum these validation metrics every iteration:

* Total cell count and any available mesh quality summary (max skewness, max
  aspect ratio, etc., if exposed by Icepak).
* Air temperature rise across the heat exchanger (T_outlet minus T_inlet).
* Overall pressure drop from inlet to outlet.
* Maximum surface temperature on the heat exchanger fin base.
* Wall-clock solve time.

## Constraints
* Python and PyAEDT must be the only interface. Launch Icepak in
  non-graphical mode. No GUI windows.
* The saved project file at the end of each iteration must remain openable in
  the AEDT GUI so I can visualize the result manually before approving the
  next change.
* Never modify geometry, materials, boundary conditions, fans, heat sources,
  or solver settings. Only mesh.
* One mesh variation per invocation, no batched sweeps.
* Operate autonomously between checkpoints. Do not ask me for permission to:
    * Run Python, scripts, or shell commands.
    * Install or upgrade dependencies (`pip install`, `pip install -r ...`).
    * Read or write files inside this repository or inside `outputs/`.
    * Create directories or move artifacts.
    * Launch AEDT, connect to a desktop session, or release it.
  Just do it. The only point where you must stop and wait for me is after a
  solve completes and simulation results are available for review. At that
  checkpoint, print the summary and stop.
* After each solve, save artifacts, print the summary, and exit. Do not block
  on user input. Do not start a new variation in the same process.
* Do not hardcode machine-specific absolute paths inline. Centralize them in
  the config file. Reference environment uses Python at
  `C:\Users\Jiong Chen\AppData\Local\Python\pythoncore-3.14-64\python.exe`
  and AEDT at
  `C:\Program Files\ANSYS Inc\v252\AnsysEM\ansysedt.exe`.
* Always operate on a copy of the baseline project so the original `.aedt`
  file is never mutated. Save the per-iteration copy under
  `outputs/iter_<N>/`.
* Fail gracefully with an actionable error message if AEDT cannot start, the
  PyAEDT version mismatches, the baseline project is missing, or the
  requested mesh change is invalid.
* Add only essential comments. Keep the code clean and modular so geometry
  loading, mesh override, solve, and post-processing are separable.
* Auto-save these artifacts per iteration into `outputs/iter_<N>/`:
    * The Icepak project copy with the applied mesh.
    * Mesh statistics dump.
    * Velocity and temperature contour images on representative cut planes.
    * A CSV row appended to `outputs/history.csv` with every tracked metric
      plus a short text describing the mesh change applied this iteration.
* Write a short README explaining how to install dependencies, how to run the
  baseline, how to edit `configs/mesh.yaml` for the next iteration, and how
  to open the saved project in AEDT to visualize results.

## Done when
The task is complete only when every condition below holds.

1. A user can run one mesh iteration with a single command, for example
   `python scripts/run_mesh_iteration.py --iter 1`.
2. The script connects to Icepak headless via PyAEDT, applies the mesh
   configuration described in `configs/mesh.yaml`, solves, exports artifacts,
   prints the metrics summary, and exits cleanly without starting a new
   iteration.
3. The original baseline `.aedt` file is unchanged on disk.
4. Each iteration's `outputs/iter_<N>/` folder contains the project copy, the
   cut-plane plots, and a per-iteration summary.
5. `outputs/history.csv` contains a row per iteration with cell count, mesh
   quality, air temperature rise, pressure drop, max fin-base temperature,
   wall-clock solve time, and a short label describing the mesh change.
6. The repository contains a clear `README.md` and `requirements.txt`.
7. The code is structured so the baseline loader, mesh-override layer, solver
   wrapper, and post-processing are easy to read and modify in isolation.
8. After the run, the script prints a concise summary that states:
    * What mesh change was applied this iteration.
    * The new metric values and the delta versus the previous iteration if
      one exists.
    * Whether the trends suggest the result is converging or still drifting.
    * What I should inspect in the AEDT GUI before approving the next
      iteration.
9. While carrying out the task, the agent never asks for permission to run
   commands, install packages, or touch files. The only checkpoint is after
   a solve has produced results for me to validate.
```

## Review simulation results

<to be filled>
