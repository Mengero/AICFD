# Lessons Learned — Icepak Solve Integrity & Post-Processing

> Findings from a multi-day conduction-only thermal study (F04 torso MRC, ~211 W,
> 4-case material matrix + boundary sensitivity sweeps) driven headless through
> PyAEDT 0.26.1 / Icepak 2026.1 on Linux HPC.
>
> The theme of this page is **not "how to build a model"** — it's *how to know
> your solve actually happened, and how to get numbers back out of it*. Most of
> the time lost in this study went to solves that silently did nothing and to
> post-processing APIs that fail in non-obvious ways.
>
> Companion pages: [Mesh Sensitivity Lessons](aicfd-lessons.md),
> [Convergence Lessons](aicfd-convergence-lessons.md),
> [Object Priority](https://mengero.github.io/AICFD/icepak-object-priority/).

---

## The one-paragraph version

An Icepak solve can return `True` and produce a full results file **without ever
running the solver**. In-place material property edits do not invalidate a stored
solution, so a "sensitivity study" written the obvious way silently re-exports the
same answer N times. Always gate on `setup.is_solved` *before* solving and treat a
sub-minute "solve" as a red flag. Everything else on this page is a corollary of
"verify, don't trust the return value."

---

## 1. Solve integrity — the traps that cost the most time

### 1.1 In-place material edits do NOT invalidate the solution

**Symptom.** A 5-point thermal-conductivity sweep produced five *identical* rows.

**Cause.** Editing a material's property in place —

```python
ipk.materials["insulation"].thermal_conductivity = 0.3   # <-- does NOT dirty the solution
```

— leaves the setup flagged as solved. `analyze_setup()` then returns `True`
immediately, having done nothing, and the export re-writes the *old* field data.

**What does and doesn't dirty a solution:**

| Change | Invalidates solution? |
| --- | --- |
| Material property edited **in place** | ❌ **No** |
| Object re-assigned to a **different material** | ✅ Yes |
| Boundary condition property edited (HTC, power, temperature) | ✅ Yes |
| Boundary added / deleted | ✅ Yes |
| `solve_inside` toggled | ✅ Yes |
| Geometry / mesh settings changed | ✅ Yes (also re-meshes) |

**Fix.** Create one *new material per sweep point* and re-point the object or
boundary at it. That is a genuine assignment change, so it dirties the solution:

```python
for k in (0.17, 0.28, 0.39, 0.50):
    nm = "insul_k%03d" % round(k * 100)
    if nm not in ipk.materials.material_keys:
        m = ipk.materials.add_material(nm)
        m.thermal_conductivity = k
    bnd.props["Solid Material"] = nm     # re-POINT, don't edit in place
    bnd.update()
```

**Guard it anyway.** Never trust the above without checking:

```python
assert not ipk.setups[0].is_solved, "solution still valid -> solve would be a NO-OP"
```

Full worked example: [`10_material_sweep_no_op_trap.py`](https://github.com/Mengero/AICFD/blob/main/icepak-examples/10_material_sweep_no_op_trap.py).

### 1.2 `analyze_setup()` returning True proves nothing

It reports "the setup is in a solved state", not "I just solved it". Three
independent checks, cheapest first:

1. **`is_solved` before the call** must be `False`.
2. **Wall-clock**. A real solve on this model was 9–60 min. Anything returning in
   seconds did not solve.
3. **Profile inspection** — count the solver stages actually executed:

```python
prof = ipk.get_profile(setup_name)              # dict of stage -> info
stages = [s for s in prof if "Solve" in str(s)]
assert stages, "no Solve stage in profile -> nothing ran"
```

The same trick confirms **mesh reuse**: count `Meshing Process` blocks. If you
passed `revert_to_initial_mesh=False` and geometry is unchanged, you should see
the mesh block only on the *first* solve of the session.

### 1.3 Subnormal material values → FPE that looks like a hang

**Symptom.** Solve "stuck at Solver Initialization" forever.

**Cause.** Two PCB substrates carried
`thermal_conductivity = '6.95252625741579e-310'` — a **subnormal double**, almost
certainly an uninitialised-memory artifact from a model merge. The solver hit a
floating-point exception on iteration 1 and stalled instead of erroring cleanly.

**Detection sweep** — run this on any merged/imported model before solving:

```python
for name in ipk.materials.material_keys:
    try:
        k = float(str(ipk.materials[name].thermal_conductivity.value))
    except (TypeError, ValueError):
        continue
    if 0 < k < 1e-6 or k > 1e6:
        print("SUSPECT %-40s k=%r" % (name, k))
```

Anything below ~1e-6 W/mK is not a real material. Fix from a known-good paired
original rather than guessing.

### 1.4 Triage failures by *how fast* they fail

A hard-won heuristic on this cluster:

| Time to failure | Almost always |
| --- | --- |
| ~6 s | **Licence** (`DENIED elec_solve_icepak`, `HPC_PARALLEL`) — retry |
| ~60 s+ | **Model error** (bad BC, solver input generation) — retrying is pointless |

So the retry loop should *stop* on slow failures:

```python
if not ok and dt_min > 0.6:
    print("failure took %.1f min -> model error, not licence; stopping" % dt_min)
    break
```

Licence note: `Curl error 60 ... self-signed certificate` from `laas.ansys.com`
is a **stale OS CA bundle** (`ssl_verify=19`), not a leaked token — checkouts were
logging clean check-ins throughout.

---

## 2. Network (two-resistor) boundary conditions

Used to model a package as junction → case / junction → board resistances rather
than a solid block.

### 2.1 PyAEDT registers only the first face

`NetworkObject.add_face_node()` builds the node list correctly but
`props["Faces"]` ends up holding **only the first face id**. `create()` then
fails with:

```
script macro error: boundary 'ufs': face '74190' is not assigned to the
network and cannot be a node.
```

**Workaround** — write the face list back explicitly before `create()`:

```python
net = NetworkObject(ipk, name=nm, create=False)
for fid, _ in spec["faces"]:
    net.add_face_node(assignment=fid, name="Face%d" % fid,
                      thermal_resistance="NoResistance")
net.add_internal_node(name="Internal", power=spec["power"],
                      mass="0.001kg", specific_heat="1000J_per_Kelkg")
for i, (fid, rv) in enumerate(spec["faces"], 1):
    net.add_link("Face%d" % fid, "Internal", rv, "Link%d" % i)

net.props["Faces"] = [f for f, _ in spec["faces"]]   # <-- REQUIRED workaround
assert net.create()
```

### 2.2 The body under a network must have `solve_inside = False`

**Symptom.** `Failed to generate solver input file` / `Engine Detected Error`,
~60 s in (i.e. the "model error" bucket above).

**Cause.** A network boundary replaces the body's internal conduction. If the
body is still solved as a solid, the solver has two conflicting descriptions.
Every one of the 21 pre-existing networks in the model sat on
`solve_inside = False` bodies; the two newly-converted ones did not.

```python
for o in ("ARC_COMPONENT13", "Solid_8"):
    ipk.modeler[o].solve_inside = False
```

### 2.3 Finding which object owns a face

You get face ids from the network spec but need the owning body:

```python
want = {74189, 74190, 84548, 84549}
for o in ipk.modeler.object_names:
    fids = set(ipk.modeler[o].faces_ids)
    hit = want & fids
    if hit:
        print("%-24s owns %s (of %d faces)" % (o, sorted(hit), len(fids)))
```

Full example: [`11_network_boundary_two_resistor.py`](https://github.com/Mengero/AICFD/blob/main/icepak-examples/11_network_boundary_two_resistor.py).

---

## 3. Getting numbers out — post-processing that works

Three complementary exports. **You need all three**; none is a superset.

| Route | Gives you | Misses |
| --- | --- | --- |
| `ExportSolutionOverview` (SOV) | Per-object max temperature + per-object heat flow | **Stationary Wall temperatures** |
| Fields Summary | Per-boundary heat flow rate, min/max/mean temperature | Object-interior values |
| Native field calculator | Arbitrary per-body min/max/mean of any quantity | Slow, one scalar per call |

### 3.1 Solution Overview — component temperatures

```python
ipk.odesign.ExportSolutionOverview([
    "SetupName:=", S, "DesignVariationKey:=", "",
    "ExportFilePath:=", str(out / "sov.txt"),
    "TimeStep:=", -1, "Overwrite:=", True])
```

Parse the `# Maximum Temperatures` and `# Heat flows for objects` sections.
**SOV does not report Stationary Wall surface temperatures** — that omission cost
a re-run when a report needed boundary temperatures.

### 3.2 Fields Summary — per-boundary heat flow and temperature

```python
sol = "%s : SteadyState" % S
bn = [b.name for b in ipk.boundaries]
for q, fn in (("HeatFlowRate", "heatflow.csv"), ("Temperature", "btemp.csv")):
    calc = []
    for b in bn:
        calc += ["Calculation:=",
                 ["Boundary", "Surface", b, q, "", "Adjacent", "Reduced", "", True]]
    ipk.osolution.EditFieldsSummarySetting(
        ["SolutionName:=", sol, "Variation:=", ""] + calc)
    ipk.osolution.ExportFieldsSummary(
        ["SolutionName:=", sol, "DesignVariationKey:=", "",
         "ExportFileName:=", str(out / fn), "IntrinsicValue:=", ""])
```

Quantity strings are `HeatFlowRate` and `Temperature` (not `Temp` here — see the
calculator below, which wants the opposite). This route can fail with
`Failed to execute gRPC AEDT command: EditFieldsSummarySetting` for
non-boundary entity types (e.g. `["Object","Volume",...]`); fall back to the
calculator.

**Always check the energy balance closes** from the heat-flow export — sinks
should sum to total dissipated power. Ours closed to within 0.05 %, which is what
lets you trust everything else.

### 3.3 Native field calculator — per-body temperatures

The escape hatch when the summary APIs refuse. Two non-obvious argument quirks:

```python
oFR = ipk.ofieldsreporter
oFR.SetPlotsSolutionContext([], S, "SteadyState")
oFR.CalcStack("clear")
oFR.EnterQty("Temp")        # "Temp", NOT "Temperature"
oFR.EnterVol("Lid_Top")     # a SINGLE STRING — passing a list fails
oFR.CalcOp("Maximum")       # or "Minimum" / "Value"
oFR.CalculatorWrite(str(path), ["Solution:=", sol], [])
```

Then scrape the trailing float out of the written `.fld` file.

### 3.4 PyAEDT visualisation is broken on this version — go native

Three bugs hit in PyAEDT 0.26.1 + Icepak 2026.1:

- `IcepakConstants` has no `default_solution` → breaks `export_field_file()`
- …same, breaks `plot_field_from_fieldplot()`
- `_parse_aedtplt` raises `IndexError` on **its own** 107 MB output file

Don't fight it. Export scalars natively and plot with matplotlib.

Full example: [`12_export_results_and_parse.py`](https://github.com/Mengero/AICFD/blob/main/icepak-examples/12_export_results_and_parse.py)
and [`13_native_field_calculator.py`](https://github.com/Mengero/AICFD/blob/main/icepak-examples/13_native_field_calculator.py).

---

## 4. Running long headless solves without shooting yourself in the foot

### 4.1 `pgrep`/`pkill` match their own command line

This wasted 22 minutes in one instance and caused several exit-143 self-kills:

```bash
while pgrep -f 'v2_run.py'; do sleep 30; done    # NEVER EXITS — matches itself
```

The shell running the loop has `v2_run.py` in its own `/proc/*/cmdline`. Fixes:

```bash
while pgrep -f '[v]2_run.py' >/dev/null; do sleep 30; done   # bracket trick
pgrep -f x.py | grep -v $$                                    # or exclude own PID
```

The same bracket trick is needed for every `ps | grep` status check.

### 4.2 A 2-minute tool timeout will kill your heredoc

If a wait-loop and a `cat > script.py <<EOF` live in the *same* command, the
timeout kills the whole thing and **the script is never written** — while a
follow-up `ps | grep` may still report "running" because it matches itself
(§4.1). That combination produces a convincing illusion of a running job.

**Rule: write the file in one short call, launch it in another.** Verify with
`ls -la` that the file exists and is non-zero before believing anything.

### 4.3 Launch detached, poll a log

```bash
nohup setsid $PY sweep.py < /dev/null > sweep.log 2>&1 & disown
```

`setsid` + `< /dev/null` keeps it alive past the parent shell; then poll the log
for an explicit `SWEEP_DONE` sentinel that the script prints last.

### 4.4 Busy vs stuck — read `/proc`, not `ps`

`ps` shows **average** CPU over process lifetime, so a long-running job that
stalled an hour ago still looks busy. Measure an instantaneous delta:

```python
def cpu_ticks(pid):
    f = open("/proc/%d/stat" % pid).read().split()
    return int(f[13]) + int(f[14])          # utime + stime

t0 = cpu_ticks(pid); time.sleep(10); t1 = cpu_ticks(pid)
print("%.0f%% CPU" % ((t1 - t0) / 10 / os.sysconf("SC_CLK_TCK") * 100))
```

### 4.5 Stale lock files

A killed `ansysedt` leaves `Project.aedt.lock` behind and the next open silently
goes read-only. Clear it *after* confirming no live process:

```python
if not subprocess.run(["pgrep", "-f", "ansysedt"],
                      capture_output=True, text=True).stdout.strip():
    Path(str(aedt) + ".lock").unlink(missing_ok=True)
```

### 4.6 Environment

```bash
PY=/apps/ANSYS/v261/AnsysEM/commonfiles/CPython/3_10/linx64/Release/python/bin/python3.10
export LD_LIBRARY_PATH=/apps/ANSYS/v261/AnsysEM
export TMPDIR=/data/home/jiong/.icepak_tmp   # also TEMP and TMP
```

Point `TMPDIR` at fast local scratch — a results tree for one design hit **8.8 GB**.

---

## 5. Study-design discipline (the non-code lessons)

These came from user corrections and were the most valuable lessons of the study.

### 5.1 Change exactly one thing — verify it, don't assume it

A charging case appeared to improve by **−7 K** when convective softgoods walls
were added. It hadn't: a newly *modelled `AIR` body* had come along in the same
save. The isolated effect of the walls was only **1–3 K**.

> User: *"Is all the TIM and material property the same before and after? or else
> we are not comparing apple to apple."*

**Rule.** Before attributing a delta to a change, diff the *whole* configuration
between the two runs — materials, bodies, boundary count, power total — and print
that diff into the run log. A `MATCHECK` line at the top of every solve log
(which materials are present) makes this a one-second check afterwards.

### 5.2 Do exactly the scope asked — no helpful extras

> User: *"stop, what are you doing? You only need to delete the 2 SOFTGOODS_CONV
> boundary condition, that is it, nothing else change."*

Bundling extra "while I'm in here" work into a controlled comparison destroys the
control. If extra output seems useful, do it as a **separate** run.

### 5.3 Report every quantity that was asked for

> User: *"I think you didn't give me the temperature of the battery_air boundary
> under normal operating condition."*

When asked for "temperature and power", the table needs both columns for **every**
case. Build the report table programmatically from the parsed exports so columns
can't be dropped by hand.

### 5.4 Name things by what they are, and check aliases

Two boundaries named `StationaryWall1` and `SEAFOAM_CONV` turned out to be the
**same surface** (identical face id 117271, identical area 0.0019559 m²), which
briefly produced a wrong "3 walls added, 1 removed" narrative. Compare face ids
and areas, not names.

---

## 6. Thermal-engineering notes worth keeping

### 6.1 ψ (characteristic parameter) vs true R

- **True R** = ΔT / Q<sub>through that path</sub>
- **ψ** = ΔT / Q<sub>total device power</sub>

They are only equal when the path carries all the heat. In a multi-path package
(lid + board + heat pipes) ψ is what you can compute from a solved field without
resolving the split; it is a **lower bound** on true R. Label it as ψ — calling a
ψ value "Rjc" overstates the path's conductance.

### 6.2 TIM thermal impedance

Z = t / k (units m²K/W). For a fixed k, thinning the bondline is linear in Z, so
0.75 mm → 0.25 mm cuts TIM impedance by exactly **3×**. Worth checking before
buying a higher-k material.

### 6.3 Where high-k TIM actually pays

In the 4-case matrix, upgrading TIM/EMI/shell moved components by **1 K to 26 K**
depending entirely on whether they sat on the upgraded path. Components on
their own network resistances (e.g. a UFS at 10 / 20.2 °C/W) barely moved — once a
package's internal resistance dominates, external TIM improvements stop mattering.
**Find the dominant resistance before optimising anything.**

---

## 7. Known bug to fix in the local pipeline

`~/Documents/ICEPAK_PIPELINE/icepak_lib/ops.py` — the `assign_priorities()`
docstring says groups are passed **"HIGHEST to LOWEST"**. That is **wrong and
inverted**; the API takes them **lowest → highest** (`PriorityNumber = index + 1`,
higher number wins). Acting on the docstring makes moulds erase the dies inside
them. That file lives outside this repo, so it is recorded here rather than
patched. See the
[Object Priority page](https://mengero.github.io/AICFD/icepak-object-priority/)
for the full rule.
