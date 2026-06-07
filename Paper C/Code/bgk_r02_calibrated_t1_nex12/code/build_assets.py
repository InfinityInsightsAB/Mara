from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


SCRIPT_DIR = Path(__file__).resolve().parent
RUN_ROOT = SCRIPT_DIR.parent
PACKAGE_ROOT = RUN_ROOT.parent.parent
DATA_ROOT = PACKAGE_ROOT / "Raw data" / RUN_ROOT.name
CONFIG_PATH = DATA_ROOT / "config" / "rerun_config.json"
if not CONFIG_PATH.exists():
    CONFIG_PATH = RUN_ROOT / "config" / "rerun_config.json"


def configured_case_id() -> str:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))["case_id"]


CASE_ID = configured_case_id()
if CASE_ID != RUN_ROOT.name:
    DATA_ROOT = PACKAGE_ROOT / "Raw data" / CASE_ID
REFERENCE_DIR = DATA_ROOT / "reference_values"
PATH_REFERENCE_DIR = REFERENCE_DIR / "path_sweep"
PLOT_DATA_DIR = DATA_ROOT / "plot_data"
FIGURE_DIR = PACKAGE_ROOT / "Figures"
METADATA_DIR = DATA_ROOT / "metadata"
BENCHMARK_CSV = REFERENCE_DIR / f"{CASE_ID}_benchmark_steps1200_paths1200000_table.csv"
ASSET_MANIFEST = METADATA_DIR / f"{CASE_ID}_asset_manifest.csv"

METHODS = [
    ("benchmark", "LSMC", "#1f4e79", "o"),
    ("hybrid", "Hybrid LSMC-PDE", "#c4601a", "s"),
]
MANIFEST_FIELDS = ["kind", "source_path", "destination_path", "sha256", "settings", "notes"]


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def package_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PACKAGE_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def manifest_path(value: str | Path) -> str:
    if isinstance(value, Path):
        return package_relative(value)
    return ";".join(package_relative(Path(part)) for part in str(value).split(";"))


def record(manifest: list[dict[str, str]], kind: str, source: str | Path, dest: Path, settings: str, notes: str) -> None:
    manifest.append(
        {
            "kind": kind,
            "source_path": manifest_path(source),
            "destination_path": package_relative(dest),
            "sha256": file_hash(dest) if dest.exists() else "",
            "settings": settings,
            "notes": notes,
        }
    )


def path_csv_path(slug: str, euler_steps: int) -> Path:
    return PATH_REFERENCE_DIR / f"{CASE_ID}_path_sweep_{slug}_steps{euler_steps}_direct_ref1200_paths1200000_table.csv"


def plot_csv_path(slug: str, euler_steps: int, method: str) -> Path:
    return PLOT_DATA_DIR / f"{CASE_ID}_path_sweep_steps{euler_steps}_{slug}_{method}.csv"


def step_csv_path(paths: int) -> Path:
    return REFERENCE_DIR / f"{CASE_ID}_step_sweep_all_ref1200_direct_samepaths{paths//1000}k_s24487296_table.csv"


def finite(value: Any) -> float:
    out = float(value)
    if not math.isfinite(out):
        raise ValueError(f"Non-finite value {value}")
    return out


def validate_sources(config: dict[str, Any]) -> None:
    benchmark_rows = read_rows(BENCHMARK_CSV)
    if len(benchmark_rows) != 5:
        raise ValueError(f"benchmark row count should be 5, got {len(benchmark_rows)}")
    expected_strikes = {int(item["K"]) for item in config["strikes"]}
    if {int(float(row["K"])) for row in benchmark_rows} != expected_strikes:
        raise ValueError("benchmark strikes are incomplete")
    for path_budget in config["step_sweep"]["paths"]:
        path = REFERENCE_DIR / f"{CASE_ID}_step_sweep_all_ref1200_direct_samepaths{int(path_budget)//1000}k_s24487296_table.csv"
        rows = read_rows(path)
        if len(rows) != 40:
            raise ValueError(f"{path} should have 40 rows, got {len(rows)}")
    for scenario in config["strikes"]:
        for euler_steps in config["path_sweep"]["steps"]:
            rows = read_rows(path_csv_path(scenario["slug"], int(euler_steps)))
            if len(rows) != 18:
                raise ValueError(f"path sweep for {scenario['slug']} M={euler_steps} should have 18 rows")


def write_plot_data(config: dict[str, Any], manifest: list[dict[str, str]]) -> None:
    reported = {int(value) for value in config["path_sweep"]["reported_paths"]}
    fieldnames = ["paths", "rel_error_pct", "yerr_minus_pct", "yerr_plus_pct"]
    for euler_steps in config["path_sweep"]["steps"]:
        for scenario in config["strikes"]:
            source = path_csv_path(scenario["slug"], int(euler_steps))
            rows = read_rows(source)
            for method, _, _, _ in METHODS:
                output: list[dict[str, Any]] = []
                for row in rows:
                    if row["method"] != method or int(row["paths"]) not in reported:
                        continue
                    rel = 100.0 * finite(row["rel_error_direct"])
                    rel_low = 100.0 * finite(row["rel_ci_lower_direct"])
                    rel_high = 100.0 * finite(row["rel_ci_upper_direct"])
                    output.append(
                        {
                            "paths": int(row["paths"]),
                            "rel_error_pct": f"{rel:.6f}",
                            "yerr_minus_pct": f"{rel - rel_low:.6f}",
                            "yerr_plus_pct": f"{rel_high - rel:.6f}",
                        }
                    )
                output.sort(key=lambda item: int(item["paths"]))
                dest = plot_csv_path(scenario["slug"], int(euler_steps), method)
                write_rows(dest, fieldnames, output)
                record(
                    manifest,
                    "plot_data",
                    source,
                    dest,
                    f"{euler_steps} steps; reported path grid",
                    f"{method} plot data for K={scenario['K']}",
                )


def load_plot_rows(path: Path) -> list[dict[str, float]]:
    return [
        {
            "paths": finite(row["paths"]),
            "rel_error_pct": finite(row["rel_error_pct"]),
            "yerr_minus_pct": finite(row["yerr_minus_pct"]),
            "yerr_plus_pct": finite(row["yerr_plus_pct"]),
        }
        for row in read_rows(path)
    ]


def rcparams() -> None:
    plt.rcParams.update(
        {
            "font.family": "STIXGeneral",
            "mathtext.fontset": "stix",
            "font.size": 15,
            "axes.titlesize": 17,
            "axes.labelsize": 16,
            "axes.linewidth": 1.0,
            "xtick.labelsize": 14,
            "ytick.labelsize": 14,
            "legend.fontsize": 15,
            "figure.labelsize": 16,
            "xtick.major.size": 5.0,
            "ytick.major.size": 5.0,
            "xtick.major.width": 1.0,
            "ytick.major.width": 1.0,
            "figure.dpi": 300,
            "savefig.dpi": 300,
        }
    )


def render_path_figure(config: dict[str, Any], euler_steps: int, manifest: list[dict[str, str]]) -> None:
    rcparams()
    reported = config["path_sweep"]["reported_paths"]
    ymax = 0.0
    input_paths: list[str] = []
    for scenario in config["strikes"]:
        for method, _, _, _ in METHODS:
            data_path = plot_csv_path(scenario["slug"], euler_steps, method)
            input_paths.append(str(data_path))
            for row in load_plot_rows(data_path):
                ymax = max(ymax, row["rel_error_pct"] + row["yerr_plus_pct"])
    ymax = max(1.0, 1.15 * ymax)

    fig, axes = plt.subplots(3, 2, figsize=(10.8, 8.4), constrained_layout=True)
    axes_flat = axes.flatten()
    for axis, scenario in zip(axes_flat[:5], config["strikes"]):
        for method, label, color, marker in METHODS:
            rows = load_plot_rows(plot_csv_path(scenario["slug"], euler_steps, method))
            x = [row["paths"] for row in rows]
            y = [row["rel_error_pct"] for row in rows]
            yerr = [[row["yerr_minus_pct"] for row in rows], [row["yerr_plus_pct"] for row in rows]]
            axis.errorbar(
                x,
                y,
                yerr=yerr,
                fmt=f"{marker}-",
                color=color,
                linewidth=1.8,
                markersize=6.2,
                capsize=3.3,
                elinewidth=1.1,
                markeredgewidth=0.9,
                label=label,
            )
        axis.set_title(f"$K={int(scenario['K'])}$")
        axis.set_xscale("log")
        axis.set_xlim(220, 70000)
        axis.set_ylim(0, ymax)
        axis.set_xticks(reported)
        axis.set_xticklabels(
            ["250" if int(value) == 250 else f"{int(value) // 1000}k" for value in reported],
            rotation=0,
            ha="center",
        )
        axis.grid(True, which="major", color="#d8d8d8", linewidth=0.6)
        axis.grid(True, which="minor", color="#eeeeee", linewidth=0.4)
        axis.set_facecolor("white")
    legend_axis = axes_flat[5]
    legend_axis.axis("off")
    handles = [
        Line2D([0], [0], color=color, marker=marker, linewidth=1.8, markersize=6.8, label=label)
        for _, label, color, marker in METHODS
    ]
    legend_axis.legend(handles=handles, loc="upper left", frameon=False)
    fig.supxlabel("Number of Paths")
    fig.supylabel("Relative Error (%)")

    stem = f"path_sweep_steps{euler_steps}_direct_relative_error"
    dest = FIGURE_DIR / f"{stem}.pdf"
    fig.savefig(dest, bbox_inches="tight")
    record(manifest, "figure", ";".join(sorted(input_paths)), dest, f"{euler_steps}-step path sweep", "pdf figure")
    plt.close(fig)


def render_step_figure(config: dict[str, Any], path_budget: int, manifest: list[dict[str, str]]) -> None:
    rcparams()
    source = step_csv_path(path_budget)
    rows = read_rows(source)
    steps = config["step_sweep"]["steps"]
    ymax = 0.0
    for row in rows:
        rel = 100.0 * finite(row["rel_error_direct"])
        rel_high = 100.0 * finite(row["rel_ci_upper_direct"])
        ymax = max(ymax, rel_high, rel)
    ymax = max(1.0, 1.15 * ymax)

    fig, axes = plt.subplots(3, 2, figsize=(10.8, 8.4), constrained_layout=True)
    axes_flat = axes.flatten()
    for axis, scenario in zip(axes_flat[:5], config["strikes"]):
        for method, label, color, marker in METHODS:
            selected = [
                row
                for row in rows
                if row["method"] == method and int(float(row["K"])) == int(scenario["K"])
            ]
            selected.sort(key=lambda item: int(item["euler_steps"]))
            x = [int(row["euler_steps"]) for row in selected]
            y = [100.0 * finite(row["rel_error_direct"]) for row in selected]
            yerr = [
                [100.0 * (finite(row["rel_error_direct"]) - finite(row["rel_ci_lower_direct"])) for row in selected],
                [100.0 * (finite(row["rel_ci_upper_direct"]) - finite(row["rel_error_direct"])) for row in selected],
            ]
            axis.errorbar(
                x,
                y,
                yerr=yerr,
                fmt=f"{marker}-",
                color=color,
                linewidth=1.8,
                markersize=6.2,
                capsize=3.3,
                elinewidth=1.1,
                markeredgewidth=0.9,
                label=label,
            )
        axis.set_title(f"$K={int(scenario['K'])}$")
        axis.set_xticks(steps)
        axis.set_ylim(0, ymax)
        axis.grid(True, which="major", color="#d8d8d8", linewidth=0.6)
        axis.set_facecolor("white")
    legend_axis = axes_flat[5]
    legend_axis.axis("off")
    handles = [
        Line2D([0], [0], color=color, marker=marker, linewidth=1.8, markersize=6.8, label=label)
        for _, label, color, marker in METHODS
    ]
    legend_axis.legend(handles=handles, loc="upper left", frameon=False)
    fig.supxlabel("Number of Euler steps")
    fig.supylabel("Relative Error (%)")

    stem = f"step_sweep_{path_budget//1000}k_direct_relative_error"
    dest = FIGURE_DIR / f"{stem}.pdf"
    fig.savefig(dest, bbox_inches="tight")
    record(manifest, "figure", source, dest, f"{path_budget} path step sweep", "pdf figure")
    plt.close(fig)


def main() -> None:
    config = load_config()
    PLOT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    validate_sources(config)
    manifest: list[dict[str, str]] = []
    write_plot_data(config, manifest)
    for path_budget in config["step_sweep"]["paths"]:
        render_step_figure(config, int(path_budget), manifest)
    for euler_steps in config["path_sweep"]["steps"]:
        render_path_figure(config, int(euler_steps), manifest)
    write_rows(ASSET_MANIFEST, MANIFEST_FIELDS, manifest)
    print(f"[assets] wrote {ASSET_MANIFEST}")


if __name__ == "__main__":
    main()
