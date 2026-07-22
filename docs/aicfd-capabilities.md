# What Claude Can Do for CFD Simulation

A one-page overview of how an AI agent (Claude, via Claude Code + PyAEDT) drives
Ansys Icepak thermal-CFD work — headless, end to end.

## Across the simulation lifecycle

- **Build & import** — pull CAD/STEP into Icepak, assign materials, set object
  priorities, and **merge multi-source package decks** into one clean design.
- **Mesh** — coarsest-viable-first, then run grid-independence studies that check
  each metric (max temperature, ΔP, mass flow, ΔT) separately.
- **Solve & converge** — run steady-state turbulent solves with a reproducible
  convergence recipe and a cheapest-first escalation ladder when a run misbehaves.
- **Monitor** — watch live residuals on long solves and **kill bad runs early**
  instead of riding them out for an hour.
- **Post-process** — extract results and fields straight from disk; render flow
  and temperature images; never re-solve just to make a graph.
- **Analyze** — scale a fan/blower's P-Q curve to a new size and RPM to pick or
  seed a fan.

## How it works

Everything runs in Python (`ansys-aedt-core`) with no manual GUI clicking. The
agent writes and runs the scripts, reads the solver logs, diagnoses failures,
and reports the numbers back — and it carries a growing library of hard-won
lessons so it doesn't repeat past mistakes.

## Why it's worth it

Profiling a recent model-merge task showed the actual CFD work was **~24 seconds**
inside a **45-minute** session — the rest was setup, launches, and iteration. The
agent absorbs that overhead: you describe the goal in plain language, it handles
the tooling.

!!! note "Honest limits"
    AEDT is fragile when driven headless (cold launches can crash; solution
    context can't be recovered after reopening a solved project). The agent works
    around these with a persistent session, disk-first extraction, and careful
    license handling — documented in the lessons pages alongside this one.
