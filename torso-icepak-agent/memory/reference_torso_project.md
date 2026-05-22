---
name: reference-torso-project
description: Structure and key names of the F04 torso Icepak project + mesh-study driver
metadata: 
  node_type: memory
  type: reference
  originSessionId: 5ccdc319-ff98-4562-9ec4-aee00a465789
---

The Icepak project `_F04_TORSO_70mm_foam_opening_study.aedt` (a torso
thermal stack with vapor chamber + fin pack + heat pipes + grille opening
study) lives at:

`C:\Users\Jiong Chen\Documents\tmp_sim_files\_FIG4_P0_torso\70mm case\`

Key names exposed by discovery on first PyAEDT open:

- design : `IcepakDesign1`
- setup  : `Setup1` (only one)
- baseline mesh operations: `MeshOperation1`, `MeshOperation2`
- boundaries: `MRC_heatsource`, `Grille`, `env`, `airchannel`
- objects of interest: 100+ `FINS_*` items, `VAPORCHAMBERBASEPLATE_1`,
  `HEATPIPES_*`
- inlet/outlet are NOT named `inlet`/`outlet`; the openings are `Grille`
  and `env` (need user to map which is air-in vs air-out in
  `configs/study.yaml`).
- For "max fin-base T", the relevant object is `VAPORCHAMBERBASEPLATE_1`,
  not the individual `FINS_*` items.

The mesh-sensitivity driver sits alongside the .aedt in the same folder:

- `scripts/run_mesh_iteration.py` — one solve per invocation
- `configs/study.yaml` — paths + post-processing hints
- `configs/mesh.yaml` — per-iteration mesh overrides (user edits this)
- `src/` — modules (config, project, aedt_session, discovery,
  mesh_override, solver, post, history, summary)
- `outputs/iter_NN/` — per-iteration .aedt copy + plots + JSON +
  history.csv (cumulative)

See [[reference-aedt-env]] for the Python/AEDT install paths.
