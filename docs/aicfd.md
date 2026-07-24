# AICFD

## Workflow Summary

The full AICFD workflow boils down to three steps:

1. **Set up paths** — locate the AEDT executable and Python interpreter. See [Paths](#paths).
2. **Edit and send prompt** (core procedure) — write the prompt that drives the agent. See [Edit and send prompt](#edit-and-send-prompt-core-procedure).
3. **Review simulation results** — wait for the agent to finish running, then check the simulation results. If there is any issue, send a prompt to the agent for modification. See [Review simulation results](#review-simulation-results).

---

## Paths

!!! note "Local environment only"
    The paths below are from the author's machine. On a new device,
    locate the actual install paths first — `where py` (or
    `python --version`) for Python and the matching AEDT executable
    under `C:\Program Files\ANSYS Inc\v<version>\AnsysEM\` — and update
    any config that references them. Don't reuse these hardcoded paths
    verbatim.

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

## Scripted operations and the pre-solve gate

The copy-paste prompt above is enough for a one-off study. For repeated work the
more reliable pattern is a small set of **scripted operations** (each a thin,
verified PyAEDT call) plus a **hard pre-solve gate** so nothing reaches the
solver without passing the checklist. Runnable, self-contained examples for every
operation below live in the repo:

[**`icepak-examples/`**](https://github.com/Mengero/AICFD/tree/main/icepak-examples)
— one script per operation, dependency-free (plain `ansys.aedt.core`), plus a
shared connect helper and the batch-solve watchdog.

!!! note "Environment"
    These examples were developed against a Linux/HPC Ansys install
    (`v261`, Ansys CPython 3.10). The `ansys.aedt.core` API is identical on
    Windows — only the interpreter/AEDT paths differ. Locate your own paths
    (see [Paths](#paths)) rather than copying either machine's verbatim.

### The golden rules (learned the hard way)

1. **Attach, don't spawn.** Reuse the already-open AEDT session; releasing it must
   **not** close the desktop. Licenses are scarce — a chain of edits should cost
   one checkout, not one per script. Use a fresh headless session only when needed.
2. **Never solve without the pre-solve checklist.** After *any* change (geometry,
   fan, priority, material, boundary, mesh) run the checklist first. A bare "quick
   remesh and solve" is the most common way to ship a wrong result.
3. **Always validate — and heal only with the light, GUI-equivalent heal.** Stitch
   + light surface simplify ON; the per-entity removal sweeps (sliver faces, small
   edges, small faces) OFF — those are what make a headless heal hang for minutes.
   Never defeature real holes/chamfers/blends. A good heal barely changes volume.
4. **"Normal Completion" ≠ converged.** It only means the solver hit its iteration
   cap. Verify from the physics (see [Review simulation results](#review-simulation-results)).
5. **MRF fans: the solid impeller must OUTRANK the rotating fluid zone.** Higher
   priority wins on overlap; if the zone outranks the blades, Icepak replaces them
   with fluid and the fan swirls without pumping. Mind the direction of the API:
   `assign_priorities()` takes groups **lowest first**, so the impeller goes *after*
   the zone in the list — see [Object priority](icepak-object-priority.md).
6. **Icepak's Validate skips overlap checks by default.** `'Perform Minimal
   validation'=true` on the design silently suppresses them, so `validate_simple()`
   returns a clean-looking log that never examined a single overlap. Clear the flag
   before you trust a validation.
7. **A large cavity mesh region with multi-level meshing (`MaxLevels>0`) meshes but
   won't solve** — it builds a non-conformal assembly that dies at the solver
   handoff. Force such regions uniform (`MaxLevels=0`).
8. **Tell BUSY from STUCK.** A long heal/solve is fine *if AEDT is computing*.
   Sample the solver's instantaneous CPU; high = crunching, idle for several beats
   = stuck (look at the code/gRPC, not the model).
9. **Batch sweeps need a detached, alarming watchdog** (`setsid`/`nohup` + sentinel
   file + notification), not a log line nobody tails — MRF/Fluent solves can hang
   on MPI deadlock and fail silently overnight.
10. **A "license checkout failed / curl error 60 / self-signed certificate" is
    usually not licensing** — on Linux nodes it's an outdated OS CA bundle. Check
    `curl https://laas.ansys.com/v1/` before touching license config.
11. **Don't trust a PyAEDT call's return value as proof.** Several are hardcoded
    (`assign_priorities` ends in `return True`). Verify the effect by re-reading the
    saved `.aedt` or the validation log.

### The gate

```text
modify → run_preflight(changed_objects=[...]) → resolve findings → solve
```

The checklist walks: (1) boundary conditions touching changed objects,
(2) object priorities / overlaps (incl. the MRF rule), (3) mesh-region coverage,
(4) geometry validation (+ optional heal), (5) gate. It writes a **receipt bound
to the project's file fingerprint**; the solve step refuses to run unless a
*passing* receipt exists whose fingerprint still matches the file on disk. Change
the project after preflight and the receipt goes stale — so "modify then quick-
solve" is impossible by construction.

### Operation catalog

| Operation | PyAEDT call (essence) | Example |
| --- | --- | --- |
| Connect / inspect | `Icepak(project=..., design=..., new_desktop=False)` | `01_connect_and_inspect.py` |
| Assign material | `obj.material_name = "copper"` · `ipk.assign_material([...], "Al-Extruded")` | `02_assign_material.py` |
| Object priorities | `ipk.mesh.assign_priorities([[lo...],[...],[hi...]])` — **lowest first**; return value is a hardcoded `True` | `03_assign_priorities.py` |
| MRF / rotating fan | edit native fan `OperatingRPM`/`Swirl`; spin axis via PCA | `04_setup_mrf_fan.py` |
| Local mesh region | `ipk.mesh.assign_mesh_region(parts)` + manual MLM settings | `05_mesh_region.py` |
| Validate + heal | `ipk.validate_simple()` → `ipk.modeler.heal_objects(...)` (light) | `06_validate_and_heal.py` |
| Boundary conditions | `ipk.assign_source / assign_*_free_opening / assign_grille ...` | `07_boundary_conditions.py` |
| Solve + convergence | `ok = ipk.analyze_setup(...)`; trust the bool, verify physics | `08_solve_and_check_convergence.py` |
| Batch-solve watchdog | detached `ansysedt -batchsolve` monitor + alarm | `solve_watchdog.sh` |

## Review simulation results

Finishing a solve is not the same as trusting it. Review every run before
approving the next change.

**Did it actually converge?**

- Trust the solver's own success flag first: `ipk.analyze_setup(...)` returns a
  bool — `True` means the setup solved. Do **not** judge convergence by globbing
  the results directory for `fields.resd`; that gives false negatives.
- **"Normal Completion" only means the iteration cap was reached**, not that
  residuals fell. Confirm from the residual history and the mass balance.
- Open the `.SOV` file in `*.aedtresults/<Design>.results/` and read the
  **Volume Flow Rate** block: per-opening flows should sum to ≈ 0 (continuity
  satisfied). A wildly non-zero sum means it diverged despite the banner.

**Does the physics make sense?**

- For an MRF fan, check blade-tip speed against `ω·r` (e.g. 5000 rpm, r = 40 mm →
  ≈ 21 m/s). Pure tangential swirl with ~zero net axial flow = the priority bug
  (impeller ranked below the zone).
- Inspect temperature and velocity fields on representative cut planes in the GUI.
  Compare the tracked metrics (max temperature, ΔT, pressure drop, cell count,
  solve time) against the previous iteration and ask whether the trend is
  converging or still drifting.

**If it failed:**

- *Invalid geometry* → heal with the light GUI-equivalent settings
  (`06_validate_and_heal.py`), then re-validate.
- *Diverged / impossible flow* → stabilize the solver: lower pressure/momentum
  under-relaxation, enable no-reverse-flow on openings, add iterations. See the
  [Convergence Lessons (HPC)](aicfd-convergence-lessons.md).
- *Meshes but dies at the solver handoff* → suspect a non-conformal MLM region;
  set the large cavity region's `MaxLevels = 0`.

Then send the agent the specific fix as the next prompt and re-run the gate.
