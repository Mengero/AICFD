# AICFD

## Workflow Summary

The full AICFD workflow boils down to three steps:

1. **Set up paths** — locate the AEDT executable and Python interpreter. See [Paths](#paths).
2. **Edit and send prompt** (core procedure) — write the prompt that drives the agent. See [Edit and send prompt](#edit-and-send-prompt-core-procedure).
3. **Review simulation results** — wait for the agent to finish running, then check the simulation results. If there is any issue, send a prompt to the agent for modification. See [Review simulation results](#review-simulation-results).

---

## Paths

- **Python:** `C:\Users\Jiong Chen\AppData\Local\Python\pythoncore-3.14-64\python.exe` (use `py` to invoke)
- **pyaedt scripts:** `C:\Users\Jiong Chen\AppData\Local\Python\pythoncore-3.14-64\Scripts` — pip warned this isn't on PATH. Only matters if you want to run `pyaedt.exe` / `ansys-launcher.exe` directly; from Python code it's fine.
- **AEDT:** `C:\Program Files\ANSYS Inc\v252\AnsysEM\ansysedt.exe`

### Quick test snippet to confirm pyaedt can drive AEDT

```python
import ansys.aedt.core
app = ansys.aedt.core.Desktop(version="2025.2", non_graphical=False, new_desktop=True)
hfss = ansys.aedt.core.Hfss()
print(hfss.design_name)
app.release_desktop(close_projects=True, close_desktop=True)
```

## Edit and send prompt (core procedure)

**Recommended Prompt Structure:**

- **Goal:** What do you want to modify or build?
- **Context:** Which files, folders, documents, examples, or error messages are relevant to this task? You can also use `@` to mention specific files as context.
- **Constraints:** What standards, architecture, security requirements, or conventions does Codex need to follow?
- **Done when:** What conditions should be met before the task is considered complete — e.g., tests passing, behavior changing, or a specific bug no longer reproducing?

## Review simulation results

<to be filled>
