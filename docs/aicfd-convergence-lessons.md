# Icepak `noduct` Convergence — Findings & Setup Recipe

!!! note "Captured on HPC — most lessons are general"
    This study ran on an HPC node, not the author's local workstation.
    The **AEDT version (2026.1), the project paths, the file map at the
    bottom, and the 96 × 96 MPI scale** are HPC-specific — on a different
    machine you must re-locate the AEDT executable, the Python
    interpreter, and the project file, and adjust the MPI configuration
    to fit available cores. **Everything else** — the turbulence-model
    choice, Model Based Flow Initialization, explicit Second-order
    discretization, the SIMPLE-vs-Coupled verdict, mass / energy balance
    rules, disk-first extraction, the detached-launch pattern — is
    general Icepak engineering and transfers to any setup.

Project: `_F04_TORSO_70mm_dockport_foam_opening_study.aedt`, design `noduct`.
Solver: Icepak 2026.1 (Fluent backend), CPU, 96 tasks × 96 cores.
Mesh: 6.86 M cells (Global + MeshRegion1).

---

## Problem

The `noduct` design was unreliable: re-solving the same nominal point
gave a mix of converged and diverged outcomes. Symptoms across the
three pre-existing runs (DV570, DV578, DV579) were identical iter‑1
residuals — i.e. these were re-solves of the same point, not parametric
variations — but DV579 diverged catastrophically to Continuity = 4.3 ×
10¹⁹ while DV570 and DV578 reached Continuity ≈ 2.5 × 10⁻⁴.

**Root cause:** the iter‑1 turbulence state had Omega ≈ 3424 (a 3000×
shock from the uniform initial ω = 1 diss/s being hit by the kOmegaSST
production source term), putting the SIMPLE pressure–velocity algorithm
on the edge of its stable basin. Floating-point non-determinism across
96-task MPI runs was enough to tip individual attempts to diverge.

A secondary issue, surfaced later in the work, is an AEDT-internal
discretization auto-promotion event that fires when Continuity drops
to ≈ 5 × 10⁻⁴. With first-order schemes selected by the user, AEDT
silently steps to higher order at this checkpoint, which kicks the
K equation by 5–6 orders of magnitude. kOmegaSST is too stiff to
absorb the kick; the run plateaus or destabilises. k-ε Realizable
absorbs it. Explicit Second-order from the start prevents the kick
from happening at all.

---

## Iteration log

| iter | change vs baseline | wall | result |
|---|---|---|---|
| 01 | `Use Model Based Flow Initialization = true` | 34 min | iter-1 ω: 3424 → 0.19 ✓. Engineering OK (mass 0.02 %, energy 0.5 %), but a K‑blowup at iter 2290 (K: 1e‑3 → 1.08e+3) pushed end-of-run Continuity back to 3 × 10⁻². NOT bar-2. |
| 02 | + `Coupled pressure-velocity formulation = true` | 5 min | **Diverged at iter 38** (Continuity = 1.16 × 10²⁰). Coupled p-v is the WRONG escalation for this mesh — block-implicit linear system has worse conditioning than SIMPLE here. |
| 03 | iter_01 setup + Flow target 1e-6 → 1e-3 + Max Iter 3000 → 2000 | 25 min | **Bar-2 converged** (Cont 8.3e‑4, Energy 9.0e-13). Stops cleanly before the iter-2290 zone. Mass balance 3 × 10⁻⁴ %, energy balance 9 × 10⁻⁴ %. *Workaround*: stop the solver before the spike fires. |
| 04 | iter_01 + K/ω URF 0.6 → 0.3 (kOmegaSST) | 35 min | Still spiked at iter 1441; plateaued at Cont = 5.6 × 10⁻². URF damping alone is insufficient. |
| 05 | iter_01 + `Turbulent Model Eqn = kepsilonRealizable` (turbulence-model swap) | 32 min | **Converged with scheme change ✓**. Energy 8.57e‑13, mass 0.029 %, energy 6 × 10⁻⁵ %. K-spike STILL fires at iter ~2330 but k-ε absorbs it and the run completes cleanly. |
| 06 | iter_05 + all transport-eqn discretization schemes = `Second` explicitly | 50 min | **Cleanest residual trajectory yet.** Analyzer reports zero major spikes; Continuity + velocities show monotonic decay. Energy 1.27e‑12 (just above target). Engineering metrics within 3 % of iter_05. |

---

## Final recommended setup

For reproducibly converged steady-state CFD of this geometry:

```yaml
Setup1:
  # Turbulence model (the single most important change vs baseline)
  Turbulent Model Eqn: kepsilonRealizable        # not kOmegaSST

  # Initialization — eliminates the iter-1 ω shock
  Solution Initialization - Use Model Based Flow Initialization: true

  # Discretization — set explicitly so AEDT's auto-promotion doesn't fire
  Discretization Scheme - Momentum:                       Second
  Discretization Scheme - Temperature:                    Second
  Discretization Scheme - Turbulent Kinetic Energy:       Second
  Discretization Scheme - Turbulent Dissipation Rate:     Second
  Discretization Scheme - Specific Dissipation Rate:      Second

  # Pressure-velocity — SIMPLE works fine; Coupled diverges this case
  Coupled pressure-velocity formulation: false

  # Convergence targets
  Convergence Criteria - Flow:             1e-6
  Convergence Criteria - Energy:           1e-12
  Convergence Criteria - Max Iterations:   3000
```

Everything else (URFs, BCs, mesh, fan/grille/opening definitions) stays
at the baseline values.

---

## Production engineering numbers

From iter_06 (most rigorous setup):

| Quantity | Value |
|---|---|
| MRC heatsource temperature | **51.96 °C** (325.11 K) |
| Total input power | 200.0 W ✓ |
| Energy balance | 0.011 % closure |
| Mass balance | 0.012 % closure |
| External mass in / out | 8.34 / 8.34 g/s |
| Fan1 — mass flow / operating ΔP | 8.36 g/s / **20.86 Pa** |
| Fan2 — mass flow / operating ΔP | 8.40 g/s / **20.39 Pa** |

Cross-check: iter_05 (k-ε, default First-order) gave 51.7 °C and Fan
ΔP ≈ 20 Pa; iter_03 (kOmegaSST, stop-clean) gave 52.1 °C and 21 Pa.
The three independent setups agree to within ~3 % on every metric.

---

## Lessons that generalize

1. **Always enable Model Based Flow Initialization on Icepak Turbulent
   steady-state cold-starts.** Uniform turbulence init (K = 1, ω = 1)
   gets shocked by the k-ω production source term at iter 1; Model
   Based Init solves a Laplace velocity field first and derives K, ω
   from gradients. Exceptions: restarts from a converged solution,
   buoyancy/natural-convection-dominated flows, laminar runs, transient.

2. **Don't escalate to Coupled pressure-velocity when SIMPLE works.**
   On this mesh, Coupled p-v diverged in 38 iterations because the
   block-implicit linear system was worse-conditioned than SIMPLE.
   Always try "loosen the convergence target / cap max iterations / fix
   initialization" before "change the solver formulation" when the
   diagnosis is late-iter destabilisation rather than early-iter
   divergence.

3. **kOmegaSST + this mesh is borderline stable; k-ε Realizable is
   robust.** Both models converge to the same engineering numbers, but
   k-ε absorbs the discretization-shock spikes that kOmegaSST cannot.
   For industrial enclosures with fans, openings, and heatsinks, k-ε
   Realizable is the safer default.

4. **AEDT's discretization auto-promotion is a real source of K-spikes.**
   When user-set first-order schemes are left at the default, AEDT
   auto-promotes the advection stencils to higher order once Continuity
   crosses an internal threshold (≈ 5 × 10⁻⁴ on this case). The switch
   is instantaneous and kicks K/ω by 5–6 orders of magnitude. **Set the
   schemes explicitly to `Second` from the start** to prevent the
   silent switch and get clean monotonic residuals.

5. **Disk-first extraction.** Icepak writes every metric you need to
   plain-text files in `<project>.aedtresults/<design>.results/`:
   * `*_S67_MON0_V*.sd` — per-iter residuals (Continuity, velocities,
     K, ω or ε, then Energy in the energy phase)
   * `*_S67_MON1_V*.sd` — per-iter monitor values (MassFlow,
     VolumeFlow, Temperature on the configured face)
   * `*_S67_V*_*.SOV` — Solution Overview: per-boundary Temperature,
     Mass Flow Rate, Heat Transfer Rate, Operating Pressure Points,
     Input Power
   * `*_S67_V*.profile` — cell count, MPI configuration, timing
   Parse these directly — the PyAEDT `FieldSummary` /
   `get_scalar_field_value` / `get_temperature_extremum` helpers crash
   on nominal-only Icepak projects and can corrupt the `.aedtresults`
   directory in the process.

6. **Long Icepak solves must be launched fully detached.** The Bash
   shell that calls `analyze()` has a 10-minute timeout in many
   harnesses. Use
   `nohup setsid ./run_pyaedt.sh ... < /dev/null > log 2>&1 & disown`
   so the Python process survives the parent shell exiting. Otherwise
   the runner is killed mid-solve, AEDT continues solving as an orphan,
   and no SOV / summary.json is ever written.

7. **Mass and energy balances must exclude internal boundaries.**
   Fan1, Fan2 in this project are internal fans (not domain openings);
   so is `Grille` (porous-fabric resistance). Only `Opening1`,
   `Opening2`, `Grille1` are true domain-external boundaries. The mass
   sum across externals must be ~0 and the heat-transfer-rate sum
   across externals must be `−Input Power`. Forgetting to exclude the
   internals gives a fake ~50 % imbalance and makes you doubt
   genuinely-converged results.

---

## File map

```
70mm/
├── _F04_TORSO_70mm_dockport_foam_opening_study.aedt        baseline
├── configs/
│   └── study.yaml                                          project + watchdog config
├── outputs/
│   ├── iter_03/_F04_TORSO_..._aedt                         kOmegaSST stop-clean
│   ├── iter_05/_F04_TORSO_..._aedt                         k-ε, default First-order
│   ├── iter_06/_F04_TORSO_..._aedt                         k-ε, explicit Second-order ← recommended
│   ├── iter_NN/setup.yaml                                  per-iter setup overrides
│   ├── iter_NN/summary.json                                full disk-snapshot of the run
│   ├── iter_NN/residuals.png                               residual-history plot
│   └── history.csv                                         flat table of all iters
├── scripts/
│   ├── run_iteration.py                                    end-to-end runner
│   ├── watch_solve.py                                      live disk-tailing watchdog
│   └── plot_residuals.py                                   residual plotter
└── src/
    ├── sd_parser.py                                        .sd / .SOV / .profile parsers
    ├── post.py                                             snapshot + engineering metrics
    └── setup_override.py                                   setup property override helper
```

Open any `iter_NN/_F04_TORSO_70mm_dockport_foam_opening_study.aedt` in
the AEDT GUI for post-processing — **never re-open via PyAEDT**, which
wipes the field results on close.
