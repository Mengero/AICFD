# -*- coding: utf-8 -*-
"""Follow-on: opening=0.30, opening_2 in {0.70, 0.90, 0.99}.

Completes the picture with opening=0.30 at the same op2 levels as v4e/v4f.
Same post-CAD-update baseline (fabric inlet 50%-cut), max_iter=1000.
"""
from __future__ import annotations

import csv
import json
import shutil
import sys
import time
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ansys.aedt.core import Icepak  # noqa: E402
from src.sd_parser import extract_iteration_data  # noqa: E402

BASELINE = Path(
    r"C:\Users\Jiong Chen\Documents\tmp_sim_files\_FIG4_P0_torso\70mm case"
    r"\_F04_TORSO_70mm_dockport_foam_opening_study v3.aedt"
)
OUT_BASE = BASELINE.parent / "outputs"
DESIGN_NAME = "v4"
SETUP_NAME = "Setup1"
AEDT_VERSION = "2025.2"
NUM_CORES = 24
NUM_TASKS = 24

OPENINGS = [0.30]
OPENING_2S = [0.70, 0.90, 0.99]
SWEEP_POINTS: list[dict[str, float]] = [
    {"opening": o, "opening_2": o2}
    for o in OPENINGS for o2 in OPENING_2S
]

SOLVER_FIXES: dict[str, object] = {
    "Convergence Criteria - Flow": "1e-3",
    "Convergence Criteria - Energy": "1e-6",
    "Convergence Criteria - Turbulent Kinetic Energy": "1e-3",
    "Convergence Criteria - Turbulent Dissipation Rate": "1e-3",
    "Convergence Criteria - Specific Dissipation Rate": "1e-3",
    "Convergence Criteria - Max Iterations": 1000,
    "Sequential Solve of Flow and Energy Equations": False,
}

CSV_FIELDS = [
    "sweep_idx", "label", "opening", "opening_2",
    "solver_iters", "converged_solver", "solve_seconds",
    "continuity", "k_residual", "omega_residual", "energy_residual",
    "mass_flow_kg_s", "volume_flow_m3_s", "t_fan_passage_c",
    "mrc_heatsource_t_c",
    "fan1_op_pressure_pa", "fan2_op_pressure_pa",
    "fan1_mass_flow_kg_s", "fan2_mass_flow_kg_s",
    "env_heat_in_fan1_w", "input_power_w",
    "out_dir", "error",
]

STATE_FILE = OUT_BASE / "sweep_v4g_state.json"
HISTORY_CSV = OUT_BASE / "sweep_v4g_history.csv"


def _label(point):
    return f"op{point['opening']:.3g}_op2_{point['opening_2']:.3g}".replace(".", "p")


def _write_state(idx, point, status, out_dir):
    OUT_BASE.mkdir(parents=True, exist_ok=True)
    payload = {
        "sweep_idx": idx,
        "total_points": len(SWEEP_POINTS),
        "design": DESIGN_NAME,
        "point": point,
        "status": status,
        "out_dir": str(out_dir) if out_dir else None,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    STATE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _append_history(row):
    HISTORY_CSV.parent.mkdir(parents=True, exist_ok=True)
    new_file = not HISTORY_CSV.exists()
    with HISTORY_CSV.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        if new_file:
            w.writeheader()
        w.writerow(row)


def _safe_float(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _extract_row(idx, point, out_dir, solve_seconds, solve_ok, error=""):
    results_root = out_dir / f"{BASELINE.stem}.aedtresults"
    row = {
        "sweep_idx": idx,
        "label": _label(point),
        "opening": point["opening"],
        "opening_2": point["opening_2"],
        "solve_seconds": round(solve_seconds, 1) if solve_seconds else None,
        "out_dir": str(out_dir),
        "error": error,
    }
    try:
        d = extract_iteration_data(results_root)
        row["solver_iters"] = d.iter_count
        row["converged_solver"] = d.converged
        row["continuity"] = _safe_float(d.final_residuals.get("Continuity"))
        row["k_residual"] = _safe_float(d.final_residuals.get("K"))
        row["omega_residual"] = _safe_float(d.final_residuals.get("Omega"))
        row["energy_residual"] = _safe_float(d.final_residuals.get("Energy"))
        row["mass_flow_kg_s"] = _safe_float(d.final_monitors.get("MassFlow"))
        row["volume_flow_m3_s"] = _safe_float(d.final_monitors.get("VolumeFlow"))
        row["t_fan_passage_c"] = _safe_float(d.final_monitors.get("Temperature"))
        sov = d.sov or {}
        temp = sov.get("Temperature", {})
        mflow = sov.get("Mass Flow Rate", {})
        htr = sov.get("Total Heat Transfer Rate", {})
        pop = sov.get("Operating Pressure Points", {})
        pin = sov.get("Input Power", {})
        row["mrc_heatsource_t_c"] = _safe_float(temp.get("MRC_heatsource"))
        row["fan1_op_pressure_pa"] = _safe_float(pop.get("Fan1_1"))
        row["fan2_op_pressure_pa"] = _safe_float(pop.get("Fan2_1"))
        row["fan1_mass_flow_kg_s"] = _safe_float(mflow.get("Fan1_1"))
        row["fan2_mass_flow_kg_s"] = _safe_float(mflow.get("Fan2_1"))
        row["env_heat_in_fan1_w"] = _safe_float(htr.get("Fan1_1"))
        row["input_power_w"] = _safe_float(pin.get("MRC_heatsource"))
    except Exception as exc:
        row["error"] = (row["error"] or "") + f"; extract: {exc}"
    return row


def run_point(idx, point):
    label = _label(point)
    out_dir = OUT_BASE / f"sweep_v4g_{idx:02d}_{label}"
    out_dir.mkdir(parents=True, exist_ok=True)
    copy_path = out_dir / BASELINE.name

    _write_state(idx, point, "copying", out_dir)
    print(f"\n[sweep_v4g {idx:02d}/{len(SWEEP_POINTS)}] {point}  ->  {out_dir.name}")
    shutil.copy2(BASELINE, copy_path)

    _write_state(idx, point, "opening_aedt", out_dir)
    print(f"[sweep_v4g {idx:02d}] launching headless AEDT (design={DESIGN_NAME})")
    icepak = Icepak(
        project=str(copy_path),
        design=DESIGN_NAME,
        version=AEDT_VERSION,
        non_graphical=True,
        new_desktop=True,
        close_on_exit=True,
    )

    solve_seconds = float("nan")
    solve_ok = False
    error = ""
    try:
        for var, value in point.items():
            try:
                icepak[var] = str(value)
                print(f"[sweep_v4g {idx:02d}] set {var} = {value}")
            except Exception as exc:
                msg = f"set {var}={value}: {type(exc).__name__}: {exc}"
                print(f"[sweep_v4g {idx:02d}] WARN {msg}")
                error += msg + "; "

        _write_state(idx, point, "applying_solver_fixes", out_dir)
        setup = icepak.get_setup(SETUP_NAME)
        for k, v in SOLVER_FIXES.items():
            try:
                setup.props[k] = v
            except Exception as exc:
                error += f"prop {k}: {exc}; "
        try:
            setup.update()
        except Exception as exc:
            error += f"setup.update: {exc}; "
        print(f"[sweep_v4g {idx:02d}] convergence fixes applied (max_iter=1000)")

        _write_state(idx, point, "solving", out_dir)
        print(f"[sweep_v4g {idx:02d}] solving (tasks={NUM_TASKS}, cores={NUM_CORES})")
        t0 = time.perf_counter()
        try:
            solve_ok = bool(icepak.analyze_setup(SETUP_NAME,
                                                 cores=NUM_CORES, tasks=NUM_TASKS))
        except Exception as exc:
            print(f"[sweep_v4g {idx:02d}] analyze_setup raised:")
            traceback.print_exc()
            error += f"analyze: {exc}; "
        solve_seconds = time.perf_counter() - t0
        print(f"[sweep_v4g {idx:02d}] solve done: {solve_seconds:.1f}s "
              f"({'OK' if solve_ok else 'FAILED'})")
    finally:
        try:
            icepak.save_project()
            print(f"[sweep_v4g {idx:02d}] project saved")
        except Exception as exc:
            print(f"[sweep_v4g {idx:02d}] save_project: {exc}")
            error += f"save: {exc}; "
        try:
            icepak.release_desktop(close_projects=True, close_desktop=True)
            print(f"[sweep_v4g {idx:02d}] desktop released cleanly")
        except Exception as exc:
            print(f"[sweep_v4g {idx:02d}] release_desktop: {exc}")
            error += f"release: {exc}; "

    return _extract_row(idx, point, out_dir, solve_seconds, solve_ok, error)


def main():
    if not BASELINE.exists():
        print(f"[error] baseline not found: {BASELINE}")
        return 2

    OUT_BASE.mkdir(parents=True, exist_ok=True)
    print(f"[sweep_v4g] {len(SWEEP_POINTS)} points (opening=0.30 follow-on)")
    print(f"[sweep_v4g] max_iter=1000  design={DESIGN_NAME}")
    print(f"[sweep_v4g] grid:")
    for i, p in enumerate(SWEEP_POINTS, start=1):
        print(f"  {i:02d}: opening={p['opening']}  opening_2={p['opening_2']}")
    print(f"[sweep_v4g] history -> {HISTORY_CSV}")

    t_overall = time.perf_counter()
    for i, point in enumerate(SWEEP_POINTS, start=1):
        try:
            row = run_point(i, point)
        except Exception:
            print(f"[sweep_v4g {i:02d}] uncaught exception:")
            traceback.print_exc()
            row = {
                "sweep_idx": i,
                "label": _label(point),
                "opening": point["opening"],
                "opening_2": point["opening_2"],
                "error": "uncaught",
            }
        _append_history(row)
        _write_state(i, point, "completed", Path(row.get("out_dir", "")))
        print(f"[sweep_v4g {i:02d}] row appended  ::  MRC T = {row.get('mrc_heatsource_t_c')}  "
              f"Fan1 dP = {row.get('fan1_op_pressure_pa')}  "
              f"Fan2 dP = {row.get('fan2_op_pressure_pa')}")

    total_min = (time.perf_counter() - t_overall) / 60
    _write_state(len(SWEEP_POINTS), {}, "sweep_complete", None)
    print()
    print("=" * 64)
    print(f" v4g sweep complete: {len(SWEEP_POINTS)} points in {total_min:.1f} min")
    print(f" History CSV  : {HISTORY_CSV}")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(main())
