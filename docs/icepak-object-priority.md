# Icepak Object Priority — ordering, verification, and a tiering recipe

Where two solids occupy the same space, Icepak keeps exactly one of them: the one
with the **higher `PriorityNumber`**. The loser is erased in the overlap region and
replaced by the winner's material. Get the direction wrong and you silently solve a
different model than the one you drew — a mold eats its own die, or a rotating fluid
zone eats the fan blades.

This page records what was verified on AEDT **2026.1** / PyAEDT **0.26.1**
(2026-07-24, `MOD_WIFI.aedt` / `IcepakDesign1`, a 214-object phone-board model).

## 1. The API takes groups LOWEST → HIGHEST

```python
ipk.mesh.assign_priorities([
    ["Region"],            # PriorityNumber = 1  (lowest, loses every overlap)
    ["gap_pad"],           # PriorityNumber = 2
    ["package_mold"],      # PriorityNumber = 3
    ["die"],               # PriorityNumber = 4  (highest, wins every overlap)
])
```

PyAEDT builds the list by enumeration — `PriorityNumber = index + 1`:

```python
for level, objects in enumerate(assignment):
    level += 1
    ...
    {"EntityList": ..., "PriorityNumber": level, "PriorityListType": "3D"}
```

and its own docstring is explicit:

> Each list corresponds to one priority level **from low to high**. This means that
> the first list has the lowest priority while the last list has the highest
> priority. Objects not explicitly passed in the lists are assigned to a priority
> level lower than the objects in the first list.

!!! danger "This repo previously documented the opposite"
    `03_assign_priorities.py` and the operation catalog said "HIGHEST → LOWEST", and
    the shipped MRF example was `[['IM_1'], ['MRF_zone'], ['Region']]` — which puts
    the impeller at `PriorityNumber=1` and **reproduces** the very blade-erasure bug
    the example warns about. Fixed 2026-07-24. The same wrong claim is in
    `ICEPAK_PIPELINE/icepak_lib/ops.py` (`set_priorities` docstring) — outside this
    repo, still to fix.

Two corollaries worth remembering:

- **Unlisted objects sink to the bottom.** Anything you omit lands below your first
  group, so a partial list is a silent demotion — pass the full ordered set.
- **2D and 3D are ranked separately.** PyAEDT splits each group into `PriorityListType`
  `"3D"` and `"2D"` entries at the same `PriorityNumber`. Sheet bodies (zero-volume
  heat-source sheets, for instance) do not compete with solids.

## 2. The return value is meaningless

`assign_priorities()` ends in an unconditional `return True`. It reports success
even if nothing happened. **Always verify externally.** Two independent ways:

**Re-read the saved `.aedt`.** Priorities are plain text:

```python
blocks = re.findall(r"\$begin 'PriorityListParameters'(.*?)\$end 'PriorityListParameters'",
                    text, re.S)
# each block: EntityList(<id>, <id>, ...) + PriorityNumber=<n> + PriorityListType='3D'
```

!!! warning "`EntityList` holds many comma-separated IDs"
    A regex like `EntityList\((\d+)\)` matches only single-object levels and silently
    misses every multi-object level. On the model above that showed 5 of 11 levels —
    enough to look plausible and be wrong. Capture `EntityList\(([^)]*)\)` and split.

    `EntityList` stores object **IDs**, not names. Build the map from
    `ipk.modeler[name].id`. Don't try to infer it from the ordering of
    `$begin 'GeometryPart'` blocks — the part ID and the operation ID differ.

**Read the validation log.** After assignment, Icepak prints one line per nested
pair:

```text
[info] Part SDR753_DIE is contained in SDR753_MOLD that has a higher priority.
       Part SDR753_MOLD will take precedence over part SDR753_DIE
```

That line is a **defect report** for a die inside a mold — the mold is erasing the
die. When the ordering is right, these lines disappear. This is the cheapest
priority audit available: no meshing, no solve.

## 3. Validate does *not* check overlaps by default

The design property `'Perform Minimal validation'=true` (Icepak's default) makes
`validate_simple()` skip overlap checking entirely. The log announces it, and it is
easy to skim past:

```text
[info] Performing minimal design validations.
       All design validations except boundary overlap checks will be performed.
```

A clean validation under that flag says nothing about overlaps. Clear it first —
and note that PyAEDT's `design_settings` mapping does **not** expose this property
(it logs `Perform Minimal validation property is not available in design settings`
and does nothing). Use the native call:

```python
ipk.odesign.SetDesignSettings(
    ["NAME:Design Settings Data", "Perform Minimal validation:=", False]
)
ipk.change_validation_settings(entity_check_level="Strict",
                               ignore_unclassified=False, skip_intersections=False)
```

Confirm it took effect by checking that the "minimal design validations" line is
**gone** from the next log.

Also worth separating in your head:

| Message | Comes from | Meaning |
| --- | --- | --- |
| `Part A is contained in B that has a higher priority` | **Validate** | B will erase A — audit your ordering |
| `Parts X and Y intersect. Y will take precedence` | **the mesher** | overlap resolved at mesh time |
| `[error] Parts X and Y intersect` | mesher/solver | same-level solid–solid tie; aborts |

So `validate_simple()` alone will not surface the mesher's precedence messages —
don't conclude "no overlaps" from a clean Validate.

## 4. Choosing the tiers

A physically sensible default for board/package models, lowest → highest:

| Tier | Rationale |
| --- | --- |
| Air region / solution domain | loses to everything |
| **TIM / gel / gap pad** | it is compliant in reality — let the real solids carve it rather than letting it eat them |
| Enclosure walls, chassis, frame | structure yields to the components it holds |
| PCB / substrates | |
| **Big components** — package bodies, molds, lumped network blocks | |
| **Small components nested inside big ones** — dies, BGAs, solder, Cu pillars | the detail you actually care about must survive |

The governing idea: **the more specific body wins.** A die is a refinement of the
mold that surrounds it, so it outranks it.

### Levels are cheap; ties are expensive

Bodies that genuinely interpenetrate must not share a level — a solid–solid tie
aborts with `[error] Parts X and Y intersect`. But bodies that merely **touch** are
safe together, and grouping them keeps the list short and readable.

Distinguish the two by overlap *volume*, which you can do offline from bounding
boxes with no license checked out:

- On the model above, 131 frame bodies overlapped each other by ~1e-21 m³ — pure
  numerical face contact. One shared level, no complaints.
- Its 5 enclosure wall plates overlapped by ~1.2e-9 m³ at the corner joints — real
  interpenetration. Each got its own level.

Bounding-box overlap is an over-estimate (it will flag a thin frame rail "overlapping"
a board slab it merely passes over), so treat it as a **prescreen** that tells you
where to look, and let Icepak's own validation be the authority.

### Nesting can be deeper than two levels

Don't assume "big" and "small" is enough. Containment is often a chain:

```text
SDX75_Mold ⊃ SDX75_CUBOL_OUT ⊃ SDX75_CUBOL_IN
SDX75_SMT  ⊃ SDX75_CUBOL_SR_OUT ⊃ SDX75_CUBOL_SR_IN
```

Flattening those three into two levels puts `CUBOL_IN` and `CUBOL_OUT` in a tie.
Derive the depth mechanically — parent = the smallest bounding box containing ≥90%
of the child — and emit one level per depth. The example model needed 3 depths, and
11 levels total for 187 solids.

## 5. Worked example

`MOD_WIFI.aedt` / `IcepakDesign1`: 214 objects → 187 3D solids to rank (22 non-model
mesh SubRegions and 5 zero-volume heat-source sheets excluded), reduced from 53
import-order levels to 11 deliberate ones:

| `PriorityNumber` | N | Tier |
| --- | --- | --- |
| 1 | 9 | TIM (`gels` material) |
| 2–6 | 1 each | enclosure wall plates (individually — they really overlap) |
| 7 | 131 | frame bodies (one level — they only touch) |
| 8 | 2 | PCB substrates |
| 9 | 25 | package bodies + lumped network blocks |
| 10 | 13 | package internals, containment depth 1 |
| 11 | 2 | package internals, containment depth 2 |

Verified by re-parsing the saved `.aedt` (187 objects across 11 levels) and by the
disappearance of all 17 `contained in ... higher priority` lines from the validation
log.

## 6. Checklist

1. Clear `'Perform Minimal validation'`, set `entity_check_level="Strict"`.
2. Validate **before**; keep the log.
3. Inventory solids; exclude non-model bodies and sheets.
4. Prescreen overlaps from bounding boxes; derive the containment depth chain.
5. Build the list **lowest → highest**; group only bodies that don't truly overlap.
6. `assign_priorities()` — ignore its return value.
7. Validate **after**; confirm no `contained in ... higher priority` lines remain.
8. Re-parse the saved `.aedt` and confirm every solid appears exactly once.
9. Run the pre-solve gate before solving.
