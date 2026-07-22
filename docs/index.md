# My AI Toolkit

A personal knowledge base of AI agents and tools I use across different domains. Each section below documents how I set up, prompt, and review a specific AI workflow.

## Topics

- **AICFD** — Driving Ansys AEDT simulations with AI agents and pyaedt.
    - [Overview](aicfd.md) — Workflow, prompt structure, and example prompts.
    - [What Claude Can Do for CFD](aicfd-capabilities.md) — One-page overview of how the agent drives Icepak thermal-CFD end to end (for sharing).
    - [Agent Operating Manual](aicfd-agent-prompt.md) — Operating rules, AEDT pitfalls, and disk-extraction reference for an Icepak/PyAEDT agent session.
    - [Mesh Sensitivity Lessons](aicfd-lessons.md) — Running log of rules and findings from the Icepak mesh sensitivity study.
    - [Convergence Lessons (HPC)](aicfd-convergence-lessons.md) — Turbulence model, initialization, and discretization recipe distilled from the `noduct` convergence fight on HPC.
    - [Model Merge & Alignment Lessons](aicfd-model-merge-lessons.md) — Merging multi-source package decks (QAM8797P + 5G + WiFi) into one Icepak design: attach-don't-launch, the supported priority API, interface-outranks-substrate ordering, and non-destructive validation.
    - [Icepak Persistence Pack](aicfd-persistence-pack.md) — Installable bundle (CLAUDE.md + AGENT_PROMPT + LESSONS + memory + scripts) so a fresh agent on a new Windows/HPC machine inherits accumulated project knowledge.
- **AI Academic Writing** — Using AI to support academic writing workflows.
    - [Overview](academic-writing.md) — "Armored" academic copyeditor system prompt.
    - [Programmatic .docx Editing](docx-editing-lessons.md) — Lessons learned editing Word manuscripts via XML.
    - [Nature Paper Writing Lessons](nature-paper-writing-lessons.md) — Ten framing-and-craft moves distilled from a real Nature Physics paper, plus a pre-submit self-check.
- **Useful Tools** — Interactive browser tools that live on this site.
    - [Blower Scaling Calculator](tool-blower-scaling.md) — Replicates the Foxconn fan scaling spreadsheet with an editable P-Q curve and side-by-side base/scaled chart.

---

> Add a new topic by dropping a `.md` file in `docs/` and adding it to `mkdocs.yml`.
