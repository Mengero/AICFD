"""Single-shot status snapshot for a running Icepak solve.

Reads the latest line of the live .sd files (residuals + monitor) under
a project's .aedtresults/ folder and prints a compact table with
convergence flags. No AEDT process touched.

Usage:
  python scripts/heartbeat.py <path/to/folder_containing_.aedt>

Designed to be wrapped by `Monitor` in a periodic loop, e.g.
  while true; do python scripts/heartbeat.py outputs/foo/; sleep 300; done
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Convergence targets (match the SOLVER_FIXES in fix_noduct_convergence.py)
TARGETS = {
    "Continuity": 1e-3,
    "XVelocity":  1e-3,
    "YVelocity":  1e-3,
    "ZVelocity":  1e-3,
    "Energy":     1e-6,
    "K":          1e-3,
    "Omega":      1e-3,
}

LINE_RE = re.compile(r"^\s*([-+0-9.eE]+)\s+(.*)$")
KV_RE = re.compile(r"([A-Za-z_]+)\s*\(\s*([-+0-9.eE]+)\s*\)")


def _find_files(folder: Path):
    """Return (mon0_residuals, mon1_monitors) paths under .aedtresults/."""
    mon0 = next(folder.rglob("*S67_MON0_V*.sd"), None)
    mon1 = next(folder.rglob("*S67_MON1_V*.sd"), None)
    return mon0, mon1


def _last_line_data(path: Path | None) -> tuple[int | None, dict[str, float]]:
    if path is None or not path.exists():
        return None, {}
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None, {}
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return None, {}
    m = LINE_RE.match(lines[-1])
    if not m:
        return None, {}
    try:
        iter_n = int(float(m.group(1)))
    except ValueError:
        iter_n = None
    kv: dict[str, float] = {}
    for k, v in KV_RE.findall(m.group(2)):
        try:
            kv[k] = float(v)
        except ValueError:
            pass
    return iter_n, kv


def _fmt(v: float | None, fmt: str = "{:.3e}") -> str:
    if v is None:
        return "    —    "
    try:
        return fmt.format(v)
    except Exception:
        return str(v)


def _flag(name: str, val: float | None) -> str:
    if val is None or name not in TARGETS:
        return "   "
    return "OK " if val <= TARGETS[name] else "!! "


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: heartbeat.py <folder>")
        return 2
    folder = Path(argv[0])
    if not folder.exists():
        print(f"[hb] folder missing: {folder}")
        return 2

    mon0, mon1 = _find_files(folder)
    iter_r, res = _last_line_data(mon0)
    iter_m, mon = _last_line_data(mon1)
    iter_n = iter_r or iter_m

    if iter_n is None:
        print("[hb] no .sd data yet (solver still meshing?)")
        return 0

    # Convergence summary
    keys = ["Continuity", "XVelocity", "YVelocity", "ZVelocity", "Energy", "K", "Omega"]
    converged = sum(
        1 for k in keys
        if k in res and k in TARGETS and res[k] <= TARGETS[k]
    )
    total_tracked = sum(1 for k in keys if k in res and k in TARGETS)

    # Format the table
    mass_flow_g = (mon.get("MassFlow") or 0) * 1000  # convert kg/s -> g/s
    vol_flow_L = (mon.get("VolumeFlow") or 0) * 1000  # m3/s -> L/s
    t_mon = mon.get("Temperature")

    # Build everything as a single string; emit as ONE print so the Monitor
    # tool batches it into a single notification (it splits per-line within
    # 200 ms which scattered earlier reports).
    parts: list[str] = []
    parts.append(f"[hb] iter {iter_n:>4d}  conv {converged}/{total_tracked}  "
                 f"| residuals (target -> current):")
    for k in keys:
        if k in res:
            target = TARGETS.get(k)
            tgt_str = f"{target:.0e}" if target else "  -  "
            parts.append(f"    {_flag(k, res[k])}{k:<11s}  {tgt_str} -> {_fmt(res[k])}")
    t_str = f"{t_mon:>7.3f}" if t_mon is not None else "    -   "
    parts.append(f"  monitors:  MassFlow {mass_flow_g:>8.4f} g/s  "
                 f"VolFlow {vol_flow_L:>8.4f} L/s  T_mon {t_str} C")
    sys.stdout.write(" || ".join(parts) + "\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
