# Torso Icepak Persistence Pack

!!! note "Windows / HPC bundle, not the live doc site"
    This page describes a **packaged bundle of files** (`CLAUDE.md`,
    `AGENT_PROMPT.md`, `LESSONS.md`, persistent memory files, and helper
    Python scripts) that you install onto a Windows or HPC workstation
    so a fresh Claude Code agent inherits ~3 weeks of accumulated
    project rules, AEDT pitfalls, and working code patterns. The pack
    itself lives in the repo at
    [`torso-icepak-agent/`](https://github.com/Mengero/AICFD/tree/main/torso-icepak-agent).
    Paths in the pack assume a Windows + AEDT 2025.2/2026.x environment.

## What's in the pack

The bundle is structured so each file ends up in a predictable location on the target machine.

| Source path in the pack | Install location on the target machine | What the agent uses it for |
|---|---|---|
| `CLAUDE.md` | `<project_root>/CLAUDE.md` | Auto-loaded briefing. Tells the agent to read `AGENT_PROMPT.md` and `LESSONS.md` first. |
| `docs/AGENT_PROMPT.md` | `<project_root>/AGENT_PROMPT.md` | Operating manual — workflow, escalation ladder, AEDT pitfalls, where data lives on disk, monitoring pattern, post-processing pattern. |
| `docs/LESSONS.md` | `<project_root>/LESSONS.md` | Running notebook — every sweep that's been run, what converged vs diverged, the design map, project-specific gotchas. |
| `memory/MEMORY.md` and 10 sibling `.md` files | `~/.claude/projects/<project_hash>/memory/` | Persistent auto-memory loaded by Claude Code at every session start. Encodes behavioral rules (no permission-asking, active heartbeat parsing, never `taskkill` mid-solve, etc.). |
| `scripts/sd_parser.py` | `<project_root>/src/sd_parser.py` | Parses Icepak `.sd` monitor files and `.SOV` solution overview files. |
| `scripts/heartbeat.py` | `<project_root>/scripts/heartbeat.py` | Emits a single-line residual + monitor summary; called by the `Monitor` tool's 5-min loop. |
| `scripts/sweep_template.py` | `<project_root>/scripts/sweep_<tag>.py` (rename per use) | Canonical parametric sweep driver — one AEDT session per point, fresh open from baseline, no reopen. Appends results to a per-sweep CSV. |

A full file-by-file description is in [`torso-icepak-agent/README.md`](https://github.com/Mengero/AICFD/blob/main/torso-icepak-agent/README.md).

## How to use it — three tiers

The handoff effort depends on whether the target machine already has the persistence installed.

### Tier A — Persistence installed (best, zero manual handoff)

Once you've done the README install on a machine (memory files in `~/.claude/projects/<hash>/memory/`, `CLAUDE.md` in the project root), you provide nothing. Just:

```powershell
cd "<project_root>"
claude
```

Auto-memory loads via system reminder. `CLAUDE.md` auto-loads. The agent reads `AGENT_PROMPT.md` and `LESSONS.md` on its own when starting work. Tell it the task and go.

### Tier B — Same machine, new project location (one prompt)

If you're in a folder where the persistence is not installed but memory still applies (same user, same Claude Code install), the auto-memory still loads. Just point the agent at the docs:

> Read `<path>/CLAUDE.md`, `<path>/AGENT_PROMPT.md`, and `<path>/LESSONS.md` before doing anything.

That's the whole handoff.

### Tier C — Brand-new machine, no install (full upload)

If a colleague is starting fresh with no setup, paste this opener and attach the three docs:

> I'm continuing work on a PyAEDT/Icepak thermal-fluid sweep project. Read these three files in order, then wait for my task: `CLAUDE.md` (briefing), `AGENT_PROMPT.md` (operating manual), `LESSONS.md` (project notebook). These encode rules and project knowledge you don't have by default.

Attach: `CLAUDE.md`, `docs/AGENT_PROMPT.md`, `docs/LESSONS.md`.

For full fidelity (behavioral rules too), also attach `memory/MEMORY.md` plus the 10 memory files — but those are usually overkill for a one-off colleague.

## Practical recommendation

Do the README install on every machine you regularly work on. Then it's Tier A always — you just `cd` and start. The persistence pack is for bootstrapping new environments, not for daily use.

## Where to grab the pack

Browse [`torso-icepak-agent/`](https://github.com/Mengero/AICFD/tree/main/torso-icepak-agent) in this repo, or clone the whole AICFD repo:

```bash
git clone https://github.com/Mengero/AICFD.git
cd AICFD/torso-icepak-agent
```

Then follow the install steps in the pack's own [`README.md`](https://github.com/Mengero/AICFD/blob/main/torso-icepak-agent/README.md).
