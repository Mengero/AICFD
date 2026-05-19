# My AI Toolkit

A personal knowledge base of AI agents and workflows I use across different domains. The repo is published as a documentation site so the content is searchable, sidebar-navigable, and reachable from anywhere.

**Live site:** https://mengero.github.io/AICFD/

## What's here

| Page | What it covers |
| --- | --- |
| [Home](docs/index.md) | Landing page with links to every topic. |
| [AICFD](docs/aicfd.md) | Driving Ansys AEDT simulations with AI agents and `pyaedt`. |
| [AI Academic Writing](docs/academic-writing.md) | System prompt for an "Armored" academic copyeditor (thermal-hydraulic & ML). |

## How to read it

The easiest way is the live site above — it has a left sidebar listing every topic, a per-page table of contents on the right, full-text search at the top, and a dark/light toggle.

You can also read the raw Markdown files in `docs/` directly on GitHub.

## How to add a new topic

1. Drop a new `<topic>.md` file in `docs/`.
2. Add a line to the `nav:` section of `mkdocs.yml`:
   ```yaml
   - My New Topic: my-new-topic.md
   ```
3. Commit and push to `main`. The GitHub Actions workflow rebuilds the site automatically.

## How to preview locally

```bash
pip install -r requirements.txt
mkdocs serve
```

Then open http://127.0.0.1:8000/. Changes to `docs/` reload live.

## How it's built

- **Static site generator:** [MkDocs](https://www.mkdocs.org/) with the [Material theme](https://squidfunk.github.io/mkdocs-material/).
- **Hosting:** GitHub Pages, free for public repos.
- **Deploy:** `.github/workflows/deploy.yml` builds and publishes the site on every push to `main`.
