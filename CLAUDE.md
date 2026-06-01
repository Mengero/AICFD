# AICFD Toolkit — Agent Briefing

You are in the **AICFD knowledge-base repo** (published at https://mengero.github.io/AICFD/). This is an MkDocs Material site that documents an Icepak / PyAEDT thermal-simulation workflow plus related agent prompts, lessons, and tools.

## Read first when the task is AICFD-related

When the user's request involves Icepak, PyAEDT, fan / blower scaling, mesh sensitivity, convergence troubleshooting, or any other thermal-CFD agent work, read these in order before acting:

1. `docs/aicfd.md` — overview of the workflow, recommended prompt structure, example prompts.
2. `docs/aicfd-agent-prompt.md` — operating manual. Process rules, AEDT pitfalls, disk-first extraction pattern, solver escalation ladder.
3. `docs/aicfd-lessons.md` — mesh sensitivity log. Every iteration tried, what converged vs diverged, recommended production mesh.
4. `docs/aicfd-convergence-lessons.md` — HPC convergence recipe. Turbulence model, initialization, discretization choices.

For the installable bundle that ships these onto a fresh machine, see `docs/aicfd-persistence-pack.md` and the `torso-icepak-agent/` directory.

## Repo layout

- `docs/` — MkDocs source. Every page here renders at `https://mengero.github.io/AICFD/<filename-without-md>/`.
- `torso-icepak-agent/` — installable Tier-A persistence pack for a separate Icepak project. Don't render inside the site.
- `data/foxconn-blower-scaling/` — Apple Numbers source plus per-table CSV exports backing the Blower Scaling Calculator.
- `mkdocs.yml` — site config (theme, navigation, markdown extensions).
- `.github/workflows/deploy.yml` — GitHub Pages deploy on every push to `main`.

## Conventions

- **Never push to `main` without an explicit user request.** The site is served from `main`; any broken markdown fails the deploy via `mkdocs build --strict`.
- Path examples in the docs (`C:\Users\Jiong Chen\AppData\Local\Python\...`, `C:\Program Files\ANSYS Inc\v252\AnsysEM\...`) are from one specific Windows machine. On a new device, locate the actual install paths instead of copying these.
- Style: minimalist black-and-white with Inter / JetBrains Mono. New docs should use plain markdown — headings, lists, code blocks, `!!! note` admonitions. Avoid color or decoration.
- New top-level topics need both an entry in `mkdocs.yml`'s `nav:` and a bullet in `docs/index.md`'s topic list.
