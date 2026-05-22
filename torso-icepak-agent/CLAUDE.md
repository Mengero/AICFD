# Torso Icepak Thermal Sweep Project — Agent Briefing

**You are working on a Figure thermal/fluid simulation project using PyAEDT (`ansys-aedt-core`) to drive Icepak headlessly.** This file is auto-loaded by Claude Code at session start. Read the two documents below *before* taking any action in this directory.

## Read first (always)

1. **`AGENT_PROMPT.md`** — full operating manual. Workflow rules, AEDT pitfalls, where solver data lives on disk, live-solve monitoring pattern, post-processing pattern, escalation ladder for convergence problems.
2. **`LESSONS.md`** — project-specific gotchas + the iteration log of every sweep so far + design map of which (opening, opening_2) values have been tried.

Both files are ~20-30 KB. Read them with the `Read` tool, not via grep — the context is cumulative and you'll miss things skimming.

## Auto-memory

Memory files in `~/.claude/projects/<your-hash>/memory/` are loaded automatically as a system reminder at session start. They encode behavioral rules learned from past sessions (don't ask permission for routine ops, echo heartbeat events with parsed data, never `taskkill` a mid-solve AEDT process, etc.). Respect them.

If memory is NOT showing the expected files, check `MEMORY.md` in the repo root's `memory/` folder and install per `README.md`.

## Project structure

```
70mm case/
├── _F04_TORSO_70mm_dockport_foam_opening_study v3.aedt   # baseline (BC + geometry)
├── AGENT_PROMPT.md
├── LESSONS.md
├── CLAUDE.md
├── scripts/         # one-shot drivers + helpers
│   ├── sweep_*.py   # parametric sweep drivers (sweep_v4e/f/g/...)
│   ├── heartbeat.py # single-line residual + monitor summary; called by Monitor tool
│   └── open_and_inspect.py  # opens .aedt in GUI for visual inspection
├── src/
│   └── sd_parser.py # parses .sd monitor files and .SOV solution overview
└── outputs/
    └── sweep_<tag>_NN_<label>/  # per-case results (one AEDT session each)
```

## How a typical task plays out

1. User says "run a sweep over X..." or "the design is diverging at low opening_2, fix it"
2. Agent reads `LESSONS.md` to see what's been tried, plans the next move
3. For new sweeps: copy a sweep template (e.g. `scripts/sweep_v4g.py`), edit the `OPENINGS` / `OPENING_2S` / output prefix, launch headless via background `Bash`
4. Arm a heartbeat `Monitor` (5-min cadence) that runs `scripts/heartbeat.py` against the current state JSON
5. On every heartbeat event, **parse and echo** the iter/residuals/monitors as a compact table (no bare "OK")
6. When the bash task completes, extract per-case results from `outputs/sweep_*_history.csv` and report

## Things this agent will NOT do without explicit user request

- Re-mesh, re-export, or alter geometry / BCs of the baseline .aedt
- `taskkill` an AEDT process mid-solve (leaks `elec_solve_icepak` license for 10-30 min)
- Reopen a closed iteration .aedt for post-processing (pyaedt loses solution context — see `reference_aedt_close_reopen.md`)
- Run more than one AEDT solve at a time (sequential is the rule)
- Push to a remote or modify git config
