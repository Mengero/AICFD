# torso-icepak-agent

Persistence pack for a Claude Code agent that drives Icepak / PyAEDT thermal-fluid sweeps on the Figure torso project. Lets a fresh agent on a new machine inherit ~3 weeks of accumulated rules, project knowledge, and working code patterns.

## What's in here

```
torso-icepak-agent/
├── README.md                 you are here
├── CLAUDE.md                 → install to: <project_root>/CLAUDE.md
├── docs/
│   ├── AGENT_PROMPT.md       → <project_root>/AGENT_PROMPT.md
│   └── LESSONS.md            → <project_root>/LESSONS.md
├── memory/                   → ~/.claude/projects/<project_hash>/memory/
│   ├── MEMORY.md
│   ├── user_role.md
│   ├── feedback_*.md         (5 behavior rules)
│   └── reference_*.md        (4 environment / pitfall references)
└── scripts/                  → <project_root>/scripts/  and src/
    ├── sd_parser.py          → <project_root>/src/sd_parser.py
    ├── heartbeat.py          → <project_root>/scripts/heartbeat.py
    └── sweep_template.py     → <project_root>/scripts/sweep_<tag>.py (rename per use)
```

## Install on a new machine

### 1. Place the project-root files

Drop `CLAUDE.md`, `docs/AGENT_PROMPT.md`, `docs/LESSONS.md` next to the `.aedt` baseline file. Claude Code auto-loads `CLAUDE.md` on every session when the working directory is this folder.

### 2. Install the auto-memory

```powershell
# Find your project hash — Claude Code creates a hash from the working directory
ls ~/.claude/projects/
# Look for a folder like "C--Users-<you>-Documents-..." matching your project path

# Copy memory files in
cp memory/* ~/.claude/projects/<your-hash>/memory/
```

If that hashed folder doesn't exist yet, launch Claude Code once in the project directory (it'll create it), then drop the memory files in.

### 3. Drop in the scripts

```powershell
mkdir <project_root>/scripts <project_root>/src
cp scripts/sd_parser.py <project_root>/src/
cp scripts/heartbeat.py <project_root>/scripts/
cp scripts/sweep_template.py <project_root>/scripts/sweep_<your_tag>.py
```

Edit `sweep_<tag>.py` — change `BASELINE` path, `OPENINGS`, `OPENING_2S`, `STATE_FILE`, `HISTORY_CSV` to your project.

### 4. Verify the agent has the context

Start a Claude Code session in the project directory. The agent's first response should reference rules from `MEMORY.md` (e.g. won't ask permission for `pip install`, will echo heartbeat data, etc.) and should be willing to read `AGENT_PROMPT.md` / `LESSONS.md` before doing real work.

## File roles at a glance

| File | What it tells the agent |
|---|---|
| `CLAUDE.md` | This-project briefing. Auto-loaded. Tells the agent to read AGENT_PROMPT and LESSONS first. |
| `docs/AGENT_PROMPT.md` | Operating manual: workflow, escalation ladder, AEDT pitfalls, where data lives, monitoring pattern, post-processing pattern. |
| `docs/LESSONS.md` | Project notebook: every sweep that's been run, what converged vs diverged, the design map, gotchas specific to this project. |
| `memory/MEMORY.md` | Auto-memory index — loaded into every session. Points at the individual memory files. |
| `memory/user_role.md` | Who the user is, what they work on. |
| `memory/feedback_autonomy.md` | Don't ask permission for routine ops. |
| `memory/feedback_monitor_dont_wait.md` | Active watchdog on long solves; kill bad runs early. |
| `memory/feedback_echo_monitor_events.md` | Parse heartbeats; never bare "OK". |
| `memory/feedback_convergence_rigor.md` | Two convergence bars (engineering vs numerical); pick the one the use case needs. |
| `memory/feedback_check_disk_first.md` | When PyAEDT extraction fails, inventory the result directory before debugging API. |
| `memory/reference_aedt_env.md` | Python / AEDT versions, install paths. |
| `memory/reference_torso_project.md` | Project structure, key object names. |
| `memory/reference_aedt_close_reopen.md` | PyAEDT can't recover solution context after reopen; post-process in-session. |
| `memory/reference_aedt_license_kill.md` | `Stop-Process` on mid-solve AEDT leaks `elec_solve_icepak` for 10-30 min. |
| `scripts/sd_parser.py` | Parses `.sd` (monitor) and `.SOV` (solution overview) files. Used by sweep drivers and post-processing. |
| `scripts/heartbeat.py` | Single-line residual + monitor summary. Called by the `Monitor` tool's 5-min loop. |
| `scripts/sweep_template.py` | Canonical sweep driver. One AEDT session per point, fresh open from baseline, no reopen. Appends results to a per-sweep CSV. |

## Versioning

This pack was assembled on 2026-05-22 after a successful 9-case design map sweep on the v4 / post-CAD-update design. The AGENT_PROMPT and LESSONS files reflect everything learned through that date.

When new lessons emerge, the agent should:
- Append iteration entries + new gotchas to `LESSONS.md`
- Update / add memory files in `~/.claude/projects/<hash>/memory/`
- Periodically re-export this repo to keep the persistence pack current
