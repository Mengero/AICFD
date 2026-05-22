"""Parse AEDT/Icepak .sd monitor files directly off disk.

The `.aedtresults/<design>.results/` folder contains per-iteration residual
and monitor histories as plain-text `.sd` files. Format per line:

    <iteration_number>  Quantity1(value1)Quantity2(value2)Quantity3(value3)...

This module reads them without any AEDT session involvement, so it works
even when the AEDT COM layer is degraded (the common case for closed-then-
reopened Icepak projects).

File naming convention seen in this project:
  <DV>_S67_MON0_V*.sd        — solver residuals per iteration (Continuity,
                               XVelocity, YVelocity, ZVelocity, Energy)
  <DV>_S67_MON1_V*.sd        — monitor quantities per iteration
                               (MassFlow, VolumeFlow, Temperature)
  <DV>_SOL68_MON0_V*.sd      — final residual values (post-solve snapshot)
  <DV>_SOL68_MON1_V*.sd      — final monitor values (post-solve snapshot)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


_QTY_RE = re.compile(r"([A-Za-z][A-Za-z_]*)\s*\(\s*(-?[0-9.eE+-]+)\s*\)")
_LINE_RE = re.compile(r"^\s*(-?[0-9.eE+-]+)\s+(.*)$")


@dataclass
class MonitorSeries:
    """One .sd file parsed: iteration column + per-quantity history."""
    iters: list[float] = field(default_factory=list)
    quantities: dict[str, list[float]] = field(default_factory=dict)

    def last(self, name: str) -> float | None:
        vals = self.quantities.get(name)
        return vals[-1] if vals else None


def parse_sd(path: Path) -> MonitorSeries:
    series = MonitorSeries()
    if not path.exists():
        return series
    text = path.read_text(encoding="utf-8", errors="ignore")
    for line in text.splitlines():
        m = _LINE_RE.match(line)
        if not m:
            continue
        try:
            it = float(m.group(1))
        except ValueError:
            continue
        rest = m.group(2)
        pairs = _QTY_RE.findall(rest)
        if not pairs:
            continue
        series.iters.append(it)
        for k, v in pairs:
            try:
                series.quantities.setdefault(k, []).append(float(v))
            except ValueError:
                series.quantities.setdefault(k, []).append(float("nan"))
    return series


def find_sd_files(results_root: Path) -> dict[str, list[Path]]:
    """Inventory the .sd files under an iteration's .aedtresults/.

    Returns a dict keyed by category — 'residuals', 'monitors',
    'final_residuals', 'final_monitors' — each a list of matching paths
    (usually one each, but parametric designs can yield several).
    """
    out: dict[str, list[Path]] = {
        "residuals": [], "monitors": [],
        "final_residuals": [], "final_monitors": [],
    }
    if not results_root.exists():
        return out
    for p in sorted(results_root.rglob("*.sd")):
        name = p.name
        if "_SOL" in name and "_MON0_" in name:
            out["final_residuals"].append(p)
        elif "_SOL" in name and "_MON1_" in name:
            out["final_monitors"].append(p)
        elif "_MON0_" in name:
            out["residuals"].append(p)
        elif "_MON1_" in name:
            out["monitors"].append(p)
    return out


@dataclass
class IterationData:
    iter_count: int | None = None
    final_residuals: dict[str, float] = field(default_factory=dict)
    final_monitors: dict[str, float] = field(default_factory=dict)
    converged: bool | None = None
    residual_target: float = 1e-3
    sov: dict[str, dict[str, float]] = field(default_factory=dict)


_SOV_SECTION_RE = re.compile(r"\$begin\s+'([^']+)'")
_SOV_KV_RE = re.compile(r"^\s*([A-Za-z0-9_]+)\s*=\s*'?(-?[0-9.eE+-]+)\s*([a-zA-Z_]*[a-zA-Z0-9_]*)?'?")
_KELVIN_TO_C = 273.15


def parse_sov(path: Path) -> dict[str, dict[str, float]]:
    """Parse the Solution Overview (.SOV) text file.

    Format:
        $begin 'SOV'
            $begin 'Temperature'
                MRC_heatsource='326.56137kel'
                airchannel='320.85037kel'
            $end 'Temperature'
            ...
        $end 'SOV'

    Returns nested {section_name: {entity_name: value_in_SI}}.
    Kelvin is auto-converted to Celsius for the Temperature section.
    """
    out: dict[str, dict[str, float]] = {}
    if not path.exists():
        return out
    text = path.read_text(encoding="utf-8", errors="ignore")
    stack: list[str] = []
    current: dict[str, float] | None = None
    for line in text.splitlines():
        m_begin = re.match(r"\s*\$begin\s+'([^']+)'", line)
        m_end = re.match(r"\s*\$end\s+'([^']+)'", line)
        if m_begin:
            section = m_begin.group(1)
            stack.append(section)
            if len(stack) == 2:
                current = {}
                out[section] = current
            continue
        if m_end:
            if stack:
                stack.pop()
            if not stack or len(stack) < 2:
                current = None
            continue
        if current is None:
            continue
        m_kv = _SOV_KV_RE.match(line)
        if not m_kv:
            continue
        key = m_kv.group(1)
        try:
            val = float(m_kv.group(2))
        except ValueError:
            continue
        unit = (m_kv.group(3) or "").lower()
        # Section-aware unit normalization
        section = stack[-1] if stack else ""
        if section == "Temperature" and unit.startswith("kel"):
            val = val - _KELVIN_TO_C
        current[key] = val
    return out


def find_sov_file(results_root: Path) -> Path | None:
    if not results_root.exists():
        return None
    candidates = sorted(results_root.rglob("*.SOV"))
    return candidates[-1] if candidates else None


def extract_iteration_data(results_root: Path,
                           residual_target: float = 1e-3) -> IterationData:
    """Pull everything we can from a per-iteration .aedtresults folder.

    `converged` is True if every momentum/energy residual is at or below
    `residual_target`. Continuity is reported but doesn't gate the boolean
    because Icepak's continuity residual scaling makes the bare value a
    poor convergence indicator on its own.
    """
    files = find_sd_files(results_root)
    data = IterationData(residual_target=residual_target)

    # Prefer the SOL68_MON files (post-solve snapshot). If absent, take
    # the last row of the live MON files.
    for cat_final, cat_live, target in (
        ("final_residuals", "residuals", "final_residuals"),
        ("final_monitors", "monitors", "final_monitors"),
    ):
        path = None
        if files[cat_final]:
            path = files[cat_final][0]
        elif files[cat_live]:
            path = files[cat_live][0]
        if path is None:
            continue
        s = parse_sd(path)
        snapshot: dict[str, float] = {}
        for k, vals in s.quantities.items():
            if not vals:
                continue
            snapshot[k] = vals[-1]
        if target == "final_residuals":
            data.final_residuals = snapshot
        else:
            data.final_monitors = snapshot

    # Iteration count from the live residuals file (last row's iter column).
    if files["residuals"]:
        s = parse_sd(files["residuals"][0])
        if s.iters:
            try:
                data.iter_count = int(s.iters[-1])
            except (TypeError, ValueError):
                pass

    if data.final_residuals:
        momentum_keys = ("XVelocity", "YVelocity", "ZVelocity")
        energy_key = "Energy"
        critical = [data.final_residuals.get(k) for k in momentum_keys]
        critical.append(data.final_residuals.get(energy_key))
        critical = [v for v in critical if v is not None]
        if critical:
            data.converged = all(v <= residual_target for v in critical)

    sov_path = find_sov_file(results_root)
    if sov_path is not None:
        data.sov = parse_sov(sov_path)

    return data
