# Icepak / PyAEDT example code

Self-contained, copy-and-adapt examples for the operations you do most often when
driving Ansys Icepak from Python. Each script is standalone (only `ansys.aedt.core`
+ a shared connect helper here — **no** external project toolkit), so you can drop
this folder onto any machine with PyAEDT and run.

These back the [AICFD Overview](https://mengero.github.io/AICFD/aicfd/) on the site.

## Files

| File | Operation |
| --- | --- |
| `_session.py` | Shared connect helper (attach vs headless, license reuse, lock cleanup). Imported by the others. |
| `01_connect_and_inspect.py` | Connect and dump objects / fans / mesh regions / boundaries / materials. |
| `02_assign_material.py` | Assign materials (per object and in bulk). |
| `03_assign_priorities.py` | Object overlap priority, including the MRF impeller-outranks-zone rule. |
| `04_setup_mrf_fan.py` | MRF fan: derive spin axis by PCA + set RPM/swirl. |
| `05_mesh_region.py` | Local refinement region + the large-cavity `MaxLevels=0` fix. |
| `06_validate_and_heal.py` | Validate geometry + the light, GUI-equivalent heal. |
| `07_boundary_conditions.py` | Assign sources / openings / grilles / walls / resistances. |
| `08_solve_and_check_convergence.py` | Solve and judge convergence correctly. |
| `solve_watchdog.sh` | Detached, alarming watchdog for batch solves (MPI-deadlock safety). |

## How to run

Use the Python that ships with your Ansys install (it has PyAEDT + the gRPC
bindings). Locate your own paths — don't copy these verbatim.

- **Linux / HPC** (the environment these were developed on):
  ```bash
  PY=/apps/ANSYS/v261/AnsysEM/commonfiles/CPython/3_10/linx64/Release/python/bin/python3.10
  $PY 01_connect_and_inspect.py --project /path/to/Model.aedt --design IcepakDesign1
  ```
- **Windows** (adjust version/paths):
  ```powershell
  py 01_connect_and_inspect.py --project "C:\path\to\Model.aedt" --design IcepakDesign1 --version 2025.2
  ```

Common flags (from `_session.py`): `--project` (required), `--design` (required),
`--version` (default 2026.1), `--headless`, `--clean-locks`, `--no-save`.

By default the scripts **attach** to an already-open AEDT GUI session (reuses the
license). Pass `--headless` to open a fresh non-graphical desktop instead.

## The rules these encode

1. Attach and reuse the license; don't spawn a desktop per script.
2. Never solve without running the pre-solve checklist (boundaries → priorities →
   mesh coverage → geometry validation) first.
3. Validate before solving; heal only with the **light** GUI-equivalent settings
   (the per-entity removal sweeps OFF — they hang; features preserved).
4. **MRF fans:** the solid impeller must outrank the rotating fluid zone.
5. A large cavity mesh region with `MaxLevels>0` meshes but won't solve → set it
   to `0`.
6. **"Normal Completion" ≠ converged** — verify continuity from the `.SOV`.
7. Batch sweeps need a **detached, alarming** watchdog, not a log line.

> Safe to run as-is: the mutating examples (`02`, `03`, `07`) ship with empty
> edit lists and only print guidance until you fill in real object names, so a
> stray run against a project won't change it.
