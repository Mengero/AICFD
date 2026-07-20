# Model Merge & Alignment Lessons — 5G + WiFi package into one Icepak design

!!! note "Captured on the local Windows workstation — most lessons are general"
    This came out of merging the **Qualcomm QAM8797P** package thermal deck
    with the **5G module** and the **WiFi module (QCA6797AQ)** into a single
    combined Icepak design (`IcepakDesign3` in
    `QAM8797P_ThermalModel_5GWIFI_MERGE.aedt`) on the FIG4 torso project.
    The **AEDT version (2025.2), the file paths, and the object names** are
    project-specific. **Everything else** — the attach-don't-cold-launch
    pattern, split-and-flush progress logging, the supported priority API,
    the interface-outranks-substrate priority rule, non-destructive
    validation, and reading vendor "contained-in" messages — is general
    Icepak/PyAEDT engineering and transfers to any multi-source merge.

Project: `QAM8797P_ThermalModel_5GWIFI_MERGE.aedt`, design `IcepakDesign3`
(SteadyState), 411 objects. Source decks: vendor Rev 2.1 package model
(Icepak / FloTHERM / 6Sigma) + `5G_module.aedt` + `wifi_module.aedt`
(`WIFI_QCA6797AQ.tzr`). AEDT 2025.2, `ansys-aedt-core` 0.27, local Windows box.

---

## The task

"Align" the merged geometry: after the three decks were combined into one
design, every solid needs the right **material** and the stacked parts need
the right **priority** so overlaps resolve correctly. Then **validate**
non-destructively before anyone spends compute meshing or solving. No solve
was run — this is model preparation, not a study.

---

## Lessons

### 1. Cold headless launch crashes on this box — attach to a running GUI

Repeated cold `Desktop(non_graphical=True, new_desktop=True)` launches were
crashing mid-open on this machine. The reliable pattern became: **open the
AEDT GUI + project by hand, then attach the script to its gRPC port** and
never let the script close it.

```python
# ATTACH to the already-running GUI (recommended on this box):
d = pyaedt.Desktop(version="2025.2", non_graphical=False,
                   new_desktop=False, port=50051)
...
# never close the user's GUI when attached:
d.release_desktop(close_projects=False, close_on_exit=False)
```

Cold launch stays available as a `--launch` fallback, but attach is the
default. This is a machine-specific stability workaround, not a PyAEDT rule —
but worth reaching for first whenever cold launches are flaky.

### 2. Split a fragile combined op into single-purpose scripts with flushed progress

When a combined "materials + priority" pass kept dying, it was split into
`part_a_mat_only.py` and `part_a_priority_only.py`, each writing a
per-step progress file that is **`flush()` + `os.fsync()`'d after every
line**. A crash then leaves a on-disk breadcrumb showing exactly which
object it died on — e.g. `[52/119] TIM_GPU -> tim_cpu_gpu_10x`.

```python
def step(m):
    with open(PROG, "a") as f:
        f.write(m + "\n"); f.flush(); os.fsync(f.fileno())
```

This is the disk-first / crash-forensics habit applied to model prep: assume
the process can vanish, and make sure the diagnostics survive it.

### 3. Set priorities with the supported API — never hand-roll `UpdatePriorityList`

A hand-rolled flat `oEditor.UpdatePriorityList(["NAME:UpdatePriorityListData", ...])`
**access-violates / crashes AEDT v252**. Use the supported PyAEDT method,
which builds the correct structured `PriorityListParameters`:

```python
app.mesh.assign_priorities(levels)   # levels is a list of lists
```

Gotcha: `assign_priorities` expects **LOW → HIGH** order (first inner list =
lowest priority). If you author your tiers HIGH → LOW for readability,
`reversed()` them before the call.

### 4. Interfaces must OUTRANK the parts they are squeezed between

In a stacked package, a thin TIM / adhesive / ESD layer sits between two
thick parts. If the thick part has higher priority, it wins at the overlap
and the thin layer's material is silently overwritten — you lose the very
interface resistance you care about. So the interface tier goes on top.

Priority tiers used here, **highest → lowest** (`assign_priorities` got the
reverse, i.e. low→high sizes `[55, 9, 11, 4, 47]`):

| Tier | Contents | Count |
|------|----------|-------|
| 1 (highest) | interface — TIM / adhesive / ESD (`TIMS*`, `Lid_adhesive_*`, `DRAM_Adhesive*`, `ESD_`, `TIM_CPU`, `TIM_GPU`) | 47 |
| 2 | die / package (`SUBSTRATE`, `BGA_EFFECTIVE`, `C4_Bumps`, `Psuedo_Die`) | 4 |
| 3 | spreader — lid / DRAM (`Lid_*`, `DRAM1..4`) | 11 |
| 4 | cooler — seafoam / coral / heatpipe (`PartBody`, `SEAFOAM`, `Body*`, `Surface`) | 9 |
| 5 (lowest) | board / lumped components (`*_BOARD`, `ARC_*`, `Solid*`, connectors, discretes) | 55 |

### 5. Port materials by object name from the previous revision, plus explicit new ones

The 119 object→material assignments were ported **by name** from the prior
thermal design (`IcepakDesign2`), so the merge inherits a vetted map instead
of re-guessing. Two new interface materials were created explicitly:

- `esd_seal` — ESD seal between seafoam and coral cooler, k = 0.2 W/mK
- `tim_cpu_gpu_10x` — CPU/GPU TIM at 10× the base `tim_1_solid_material`
  (2 → 20 W/mK)

The assignment is defensive: only touch objects that exist
(`if name in app.modeler.object_names`), read back `material_name` after
setting, and print any mismatch. 119/119 assigned.

### 6. Validate non-destructively, and use the API that actually exists

Run validation with **`save=False`** so a failed check can't corrupt the
saved model, and capture the messages yourself:

```python
valid = app.odesign.ValidateDesign()                 # returns True/False
msgs  = list(app.odesktop.GetMessages(proj, des, 0)) # full message list
```

`app.validate_full_design(...)` **does not exist** on the Icepak object in
this PyAEDT (`'Icepak' object has no attribute 'validate_full_design'`) —
don't rely on it; `ValidateDesign()` + `GetMessages()` is the portable path.

### 7. "Part X is contained in Y that has higher priority" is INFO, not a problem

Of 232 validation messages, **0 were warnings** — the ~200 "contained in …
will take precedence" lines are `[info]` and are exactly what a correct
priority setup produces (a component enclosure winning over its own internal
parts). Don't chase them.

---

## Validation outcome (this merge)

`ValidateDesign()` → **False**, 232 messages, **10 errors**, 0 warnings:

- **9 × "No material is assigned"** — `Body`, `Body_1..5`, `BODY_6`,
  `B_TO_GPU_CONNECTOR1`, `Solid_8`. The `Body*` solids are the **redesigned
  heatpipe / cooler bodies deliberately left unassigned** pending the
  `hp_200w` heatpipe material — they stay in the cooler priority tier
  regardless. So most of these are known residue, not surprises: the merge is
  materials-complete **except the cooler bodies**.
- **1 × Parasolid entity check failed for `Body_5`** — a geometry-health
  problem on one imported cooler body. Flag for geometry repair before
  meshing; a bad Parasolid body will not mesh.

**Next steps** to clear validation: identify + assign the heatpipe/cooler
bodies (`hp_200w`), sort out `B_TO_GPU_CONNECTOR1` / `Solid_8`, and repair
`Body_5`'s geometry.

---

## File map

Under `…/_FIG4_P0_torso/CPU_ICEPAK/`:

| File | What it is |
|------|-----------|
| `QAM8797P_ThermalModel_5GWIFI_MERGE.aedt` | the merged project / design `IcepakDesign3` |
| `part_a_materials_priority.py` | combined materials + priority pass (attach-by-default), with the full object→material map and priority tiers baked in |
| `part_a_mat_only.py` | materials-only pass with per-object flushed progress |
| `part_a_priority_only.py` | priority-only pass |
| `validate_design.py` | non-destructive `ValidateDesign()` + message capture |
| `validation_report.txt` | the captured errors / warnings / all messages |
| `part_a_progress.txt`, `priority_progress.txt`, `validate_progress.txt` | flushed step breadcrumbs |
| `5G_module.aedt`, `wifi_module.aedt`, `WIFI_QCA6797AQ.tzr` | source module decks |
