# My AI Toolkit

A personal knowledge base of AI agents and tools I use across different domains. Each section below documents how I set up, prompt, and review a specific AI workflow.

## Topics

- **AICFD** — Driving Ansys AEDT simulations with AI agents and pyaedt.
    - [Overview](aicfd.md) — Workflow, prompt structure, and example prompts.
    - [Agent Operating Manual](aicfd-agent-prompt.md) — Operating rules, AEDT pitfalls, and disk-extraction reference for an Icepak/PyAEDT agent session.
    - [Mesh Sensitivity Lessons](aicfd-lessons.md) — Running log of rules and findings from the Icepak mesh sensitivity study.
    - [Convergence Lessons (HPC)](aicfd-convergence-lessons.md) — Turbulence model, initialization, and discretization recipe distilled from the `noduct` convergence fight on HPC.
    - [Torso Icepak Persistence Pack](aicfd-persistence-pack.md) — Installable bundle (CLAUDE.md + AGENT_PROMPT + LESSONS + memory + scripts) so a fresh agent on a new Windows/HPC machine inherits accumulated project knowledge.
    - [Blower Scaling Calculator](aicfd-blower-scaling.md) — Interactive tool replicating the Foxconn fan scaling spreadsheet (geometry, RPM, SPL, P-Q curve).
- **AI Academic Writing** — Using AI to support academic writing workflows.
    - [Overview](academic-writing.md) — "Armored" academic copyeditor system prompt.
    - [Programmatic .docx Editing](docx-editing-lessons.md) — Lessons learned editing Word manuscripts via XML.

---

> Add a new topic by dropping a `.md` file in `docs/` and adding it to `mkdocs.yml`.
