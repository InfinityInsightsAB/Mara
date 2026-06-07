from __future__ import annotations

import csv
import hashlib
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parents[1]
OVERLEAF_DIR = PROJECT_ROOT / "Working Files" / "Manuscript Overleaf"
PLOT_DATA_DIR = ROOT / "outputs" / "plot_data"
LOCAL_FIGURE_DIR = ROOT / "figures"
OVERLEAF_FIGURE_DIR = OVERLEAF_DIR / "figures" / "numerical"
MANIFEST_PATH = ROOT / "outputs" / "step_sweep_figure_manifest.csv"

SCENARIOS = [
    ("K=70 put", "K=70", "k70"),
    ("K=80 put", "K=80", "k80"),
    ("OTM put", "K=90", "k90"),
    ("ATM", "K=100", "k100"),
    ("ITM put", "K=110", "k110"),
]

METHODS = [
    ("benchmark", "LSMC", "#1f4e79", "o"),
    ("hybrid", "Hybrid LSMC-PDE", "#c4601a", "s"),
]

MANIFEST_COLUMNS = [
    "figure_id",
    "script_path",
    "input_data",
    "output_path",
    "format",
    "sha256",
    "settings",
    "notes",
]


def ensure_dirs() -> None:
    LOCAL_FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    OVERLEAF_FIGURE_DIR.mkdir(parents=True, exist_ok=True)


def sha256_for(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def load_rows(path: Path) -> list[dict[str, float]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [
            {
                "euler_steps": float(row["euler_steps"]),
                "rel_error_pct": float(row["rel_error_pct"]),
                "yerr_minus_pct": float(row["yerr_minus_pct"]),
                "yerr_plus_pct": float(row["yerr_plus_pct"]),
            }
            for row in reader
        ]


def rcparams() -> None:
    plt.rcParams.update(
        {
            "font.family": "STIXGeneral",
            "mathtext.fontset": "stix",
            "font.size": 11,
            "axes.titlesize": 12,
            "axes.labelsize": 11,
            "axes.linewidth": 0.8,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "legend.fontsize": 10,
            "figure.dpi": 300,
            "savefig.dpi": 300,
        }
    )


def figure_ymax(path_label: str) -> float:
    ymax = 0.0
    for _, _, slug in SCENARIOS:
        for method, _, _, _ in METHODS:
            path = PLOT_DATA_DIR / f"step_sweep_{path_label}_{slug}_{method}.csv"
            rows = load_rows(path)
            for row in rows:
                ymax = max(ymax, row["rel_error_pct"] + row["yerr_plus_pct"])
    return max(1.0, 1.15 * ymax)


def render_figure(path_label: str, path_text: str) -> list[dict[str, str]]:
    ymax = figure_ymax(path_label)
    fig, axes = plt.subplots(3, 2, figsize=(10.5, 8.2), constrained_layout=True)
    axes_flat = axes.flatten()
    input_paths: list[str] = []
    for axis, (_, title, slug) in zip(axes_flat[:5], SCENARIOS):
        for method, label, color, marker in METHODS:
            data_path = PLOT_DATA_DIR / f"step_sweep_{path_label}_{slug}_{method}.csv"
            input_paths.append(str(data_path))
            rows = load_rows(data_path)
            x = [row["euler_steps"] for row in rows]
            y = [row["rel_error_pct"] for row in rows]
            yerr = [
                [row["yerr_minus_pct"] for row in rows],
                [row["yerr_plus_pct"] for row in rows],
            ]
            axis.errorbar(
                x,
                y,
                yerr=yerr,
                fmt=f"{marker}-",
                color=color,
                linewidth=1.4,
                markersize=4.8,
                capsize=3.0,
                elinewidth=1.0,
                markeredgewidth=0.8,
                label=label,
            )
        axis.set_title(f"${title}$")
        axis.set_xlim(22, 98)
        axis.set_ylim(0, ymax)
        axis.set_xticks([24, 48, 72, 96])
        axis.grid(True, which="major", color="#d8d8d8", linewidth=0.6)
        axis.set_facecolor("white")
    legend_axis = axes_flat[5]
    legend_axis.axis("off")
    handles = [
        Line2D([0], [0], color=color, marker=marker, linewidth=1.4, markersize=5.0, label=label)
        for _, label, color, marker in METHODS
    ]
    legend_axis.legend(handles=handles, loc="upper left", frameon=False)
    legend_axis.text(
        0.02,
        0.56,
        "Benchmark: LSMC, 1200 steps, 1.2M paths",
        ha="left",
        va="top",
        fontsize=10,
    )
    legend_axis.text(
        0.02,
        0.38,
        "Error bars: propagated 95% confidence intervals",
        ha="left",
        va="top",
        fontsize=10,
    )
    fig.supxlabel("Number of Steps")
    fig.supylabel("Relative Error (%)")
    figure_name = f"step_sweep_{path_label}_direct_relative_error"
    local_pdf = LOCAL_FIGURE_DIR / f"{figure_name}.pdf"
    local_eps = LOCAL_FIGURE_DIR / f"{figure_name}.eps"
    overleaf_pdf = OVERLEAF_FIGURE_DIR / f"{figure_name}.pdf"
    overleaf_eps = OVERLEAF_FIGURE_DIR / f"{figure_name}.eps"
    fig.savefig(local_pdf, bbox_inches="tight")
    fig.savefig(local_eps, format="eps", bbox_inches="tight")
    plt.close(fig)
    shutil.copy2(local_pdf, overleaf_pdf)
    shutil.copy2(local_eps, overleaf_eps)
    settings = f"matched {path_text}-path step sweep; five strikes; relative error"
    return [
        {
            "figure_id": figure_name,
            "script_path": str(Path(__file__).resolve()),
            "input_data": ";".join(sorted(set(input_paths))),
            "output_path": str(local_pdf),
            "format": "pdf",
            "sha256": sha256_for(local_pdf),
            "settings": settings,
            "notes": "local manuscript figure",
        },
        {
            "figure_id": figure_name,
            "script_path": str(Path(__file__).resolve()),
            "input_data": ";".join(sorted(set(input_paths))),
            "output_path": str(local_eps),
            "format": "eps",
            "sha256": sha256_for(local_eps),
            "settings": settings,
            "notes": "local manuscript figure",
        },
        {
            "figure_id": figure_name,
            "script_path": str(Path(__file__).resolve()),
            "input_data": str(local_pdf),
            "output_path": str(overleaf_pdf),
            "format": "pdf",
            "sha256": sha256_for(overleaf_pdf),
            "settings": settings,
            "notes": "overleaf export",
        },
        {
            "figure_id": figure_name,
            "script_path": str(Path(__file__).resolve()),
            "input_data": str(local_eps),
            "output_path": str(overleaf_eps),
            "format": "eps",
            "sha256": sha256_for(overleaf_eps),
            "settings": settings,
            "notes": "overleaf export",
        },
    ]


def write_manifest(rows: list[dict[str, str]]) -> None:
    with MANIFEST_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    ensure_dirs()
    rcparams()
    manifest_rows: list[dict[str, str]] = []
    manifest_rows.extend(render_figure("20k", "20,000"))
    manifest_rows.extend(render_figure("60k", "60,000"))
    write_manifest(manifest_rows)
    print("Python figure assets generated.")
    print(f"Manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
