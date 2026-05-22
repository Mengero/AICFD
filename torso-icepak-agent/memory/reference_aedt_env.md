---
name: reference-aedt-env
description: "User's local ANSYS AEDT + Python environment for PyAEDT work"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 5ccdc319-ff98-4562-9ec4-aee00a465789
---

Reference machine setup for PyAEDT / Icepak work on this Windows machine:

- **Python interpreter** the user wants Claude to use:
  `C:\Users\Jiong Chen\AppData\Local\Python\pythoncore-3.14-64\python.exe`
  (Python 3.14.5). Pip 26.x is wired up.
- **ANSYS AEDT install:**
  `C:\Program Files\ANSYS Inc\v252\AnsysEM\ansysedt.exe` (AEDT version 2025.2).
- **PyAEDT package:** `ansys-aedt-core` (v0.27.x is installed). The legacy
  `pyaedt` import path no longer works — use `from ansys.aedt.core import Icepak, ...`.
  `pip install pyaedt` is a meta-pull that still ends up installing the new
  package under the `ansys.aedt.core` namespace.
- **AEDT GUI sessions hold an .aedt.lock** next to the project file. Working
  on a copy (`shutil.copy2` of just the .aedt) avoids that conflict — AEDT
  regenerates `.aedtresults/` next to the copy on solve. Don't carry results
  over from the baseline if you want a fresh solve.
- **License/process model:** `new_desktop=True` on the `Icepak(...)` ctor
  spawns a fresh AEDT process per script run, which coexists with a GUI
  session the user may have open on the same baseline.

Engineering project lives under
`C:\Users\Jiong Chen\Documents\tmp_sim_files\_FIG4_P0_torso\70mm case\`.
See [[reference-torso-project]] for project-specific structure.
