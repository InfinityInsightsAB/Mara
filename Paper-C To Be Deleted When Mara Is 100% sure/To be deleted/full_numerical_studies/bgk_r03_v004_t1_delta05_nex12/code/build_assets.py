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


RUN_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = RUN_ROOT / "config" / "rerun_config.json"
RESULTS_DIR = RUN_ROOT / "results"
REFERENCE_DIR = RESULTS_DIR / "reference_values"
PATH_REFERENCE_DIR = REFERENCE_DIR / "path_sweep"
PLOT_DATA_DIR = RESULTS_DIR / "plot_data"
FIGURE_DIR = RUN_ROOT / "figures"
TABLE_DIR = RUN_ROOT / "tables"
METADATA_DIR = RESULTS_DIR / "metadata"


def configured_case_id() -> str:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))["case_id"]


CASE_ID = configured_case_id()
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


def record(manifest: list[dict[str, str]], kind: str, source: str | Path, dest: Path, settings: str, notes: str) -> None:
    manifest.append(
        {
            "kind": kind,
            "source_path": str(source),
            "destination_path": str(dest),
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


def ci_bounds(value: float, se: float) -> tuple[float, float]:
    return value - 1.96 * se, value + 1.96 * se


def fmt_int(value: int | str) -> str:
    return f"{int(value):,}"


def fmt_pct(value: str) -> str:
    return f"{100.0 * finite(value):.3f}\\%"


def fmt_price(value: str | float) -> str:
    return f"{finite(value):.3f}"


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
            "font.size": 11,
            "axes.titlesize": 12,
            "axes.labelsize": 11,
            "axes.linewidth": 0.8,
            "xtick.labelsize": 9,
            "ytick.labelsize": 10,
            "legend.fontsize": 10,
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
                linewidth=1.4,
                markersize=4.8,
                capsize=3.0,
                elinewidth=1.0,
                markeredgewidth=0.8,
                label=label,
            )
        axis.set_title(f"$K={int(scenario['K'])}$")
        axis.set_xscale("log")
        axis.set_xlim(220, 70000)
        axis.set_ylim(0, ymax)
        axis.set_xticks(reported)
        axis.set_xticklabels([fmt_int(value) for value in reported], rotation=35, ha="right")
        axis.grid(True, which="major", color="#d8d8d8", linewidth=0.6)
        axis.grid(True, which="minor", color="#eeeeee", linewidth=0.4)
        axis.set_facecolor("white")
    legend_axis = axes_flat[5]
    legend_axis.axis("off")
    handles = [
        Line2D([0], [0], color=color, marker=marker, linewidth=1.4, markersize=5.0, label=label)
        for _, label, color, marker in METHODS
    ]
    legend_axis.legend(handles=handles, loc="upper left", frameon=False)
    r_value = float(config["model_env"]["GDMR_R"])
    v0_value = float(config["model_env"]["GDMR_V0"])
    legend_axis.text(0.02, 0.58, f"Case: r={r_value:.2f}, v0={v0_value:.2f}, delta1=delta2=0.5", ha="left", va="top", fontsize=10)
    legend_axis.text(0.02, 0.40, "Benchmark: LSMC, 1200 steps, 1.2M paths", ha="left", va="top", fontsize=10)
    legend_axis.text(0.02, 0.22, "Error bars: propagated 95% confidence intervals", ha="left", va="top", fontsize=10)
    fig.supxlabel("Number of Paths")
    fig.supylabel("Relative Error (%)")

    stem = f"{CASE_ID}_path_sweep_steps{euler_steps}_direct_relative_error"
    for ext in ("pdf", "png", "eps"):
        dest = FIGURE_DIR / f"{stem}.{ext}"
        fig.savefig(dest, format=ext if ext == "eps" else None, bbox_inches="tight")
        record(manifest, "figure", ";".join(sorted(input_paths)), dest, f"{euler_steps}-step path sweep", f"{ext} figure")
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
                linewidth=1.4,
                markersize=4.8,
                capsize=3.0,
                elinewidth=1.0,
                markeredgewidth=0.8,
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
        Line2D([0], [0], color=color, marker=marker, linewidth=1.4, markersize=5.0, label=label)
        for _, label, color, marker in METHODS
    ]
    legend_axis.legend(handles=handles, loc="upper left", frameon=False)
    legend_axis.text(0.02, 0.58, f"Path budget: {fmt_int(path_budget)}", ha="left", va="top", fontsize=10)
    legend_axis.text(0.02, 0.40, "Benchmark: LSMC, 1200 steps, 1.2M paths", ha="left", va="top", fontsize=10)
    legend_axis.text(0.02, 0.22, "Error bars: propagated 95% confidence intervals", ha="left", va="top", fontsize=10)
    fig.supxlabel("Number of Euler Steps")
    fig.supylabel("Relative Error (%)")

    stem = f"{CASE_ID}_step_sweep_{path_budget//1000}k_direct_relative_error"
    for ext in ("pdf", "png", "eps"):
        dest = FIGURE_DIR / f"{stem}.{ext}"
        fig.savefig(dest, format=ext if ext == "eps" else None, bbox_inches="tight")
        record(manifest, "figure", source, dest, f"{path_budget} path step sweep", f"{ext} figure")
    plt.close(fig)


def write_experimental_setting_table(config: dict[str, Any], manifest: list[dict[str, str]]) -> None:
    model = config["model_env"]
    hybrid = config["hybrid_env"]
    rows = [
        ("Model", "gDMR"),
        ("Option", "Bermudan put"),
        (r"$S_0$", model["GDMR_S0"]),
        (r"$K$", "70, 80, 90, 100, 110"),
        (r"$T$", model["GDMR_MATURITY"]),
        (r"$r$", model["GDMR_R"]),
        (r"$v_0$", model["GDMR_V0"]),
        (r"$v'_0$", model["GDMR_VP0"]),
        (r"$\kappa_1$", model["GDMR_KAPPA1"]),
        (r"$\kappa_2$", model["GDMR_KAPPA2"]),
        (r"$\theta$", model["GDMR_THETA"]),
        (r"$\xi_1$", model["GDMR_XI1"]),
        (r"$\xi_2$", model["GDMR_XI2"]),
        (r"$\rho_{12}$", model["GDMR_RHO12"]),
        (r"$\rho_{13}$", model["GDMR_RHO13"]),
        (r"$\rho_{23}$", model["GDMR_RHO23"]),
        (r"$\delta_1$", model["GDMR_DELTA1"]),
        (r"$\delta_2$", model["GDMR_DELTA2"]),
        ("Exercise dates", model["GDMR_EXERCISE_DATES"]),
        ("Benchmark", r"LSMC, 1200 steps, 1,200,000 paths"),
        ("Hybrid asset grid", hybrid["GDMR_HYBRID_ASSET_POINTS"]),
    ]
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{Model and numerical parameters for the standalone positive-rate study.}",
        rf"\label{{tab:{CASE_ID}-experimental-setting}}",
        r"\begin{tabular}{lr}",
        r"\toprule",
        r"Quantity & Value \\",
        r"\midrule",
    ]
    lines.extend(f"{name} & {value} \\\\" for name, value in rows)
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    dest = TABLE_DIR / f"{CASE_ID}_experimental_setting_table.tex"
    dest.write_text("\n".join(lines), encoding="utf-8")
    record(manifest, "table", CONFIG_PATH, dest, "model and numerical setup", "standalone setting table")


def write_benchmark_reference_table(manifest: list[dict[str, str]]) -> None:
    rows = sorted(read_rows(BENCHMARK_CSV), key=lambda item: finite(item["K"]))
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{Benchmark direct LSMC reference prices for the standalone study.}",
        rf"\label{{tab:{CASE_ID}-benchmark-references}}",
        r"\begin{tabular}{rrrrr}",
        r"\toprule",
        r"Strike & Price & SE & CI lower & CI upper \\",
        r"\midrule",
    ]
    for row in rows:
        price = finite(row["benchmark_direct_price"])
        se = finite(row["benchmark_direct_error"])
        low, high = ci_bounds(price, se)
        lines.append(rf"{int(float(row['K']))} & {price:.6f} & {se:.6f} & {low:.6f} & {high:.6f} \\")
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    dest = TABLE_DIR / f"{CASE_ID}_benchmark_reference_table.tex"
    dest.write_text("\n".join(lines), encoding="utf-8")
    record(manifest, "table", BENCHMARK_CSV, dest, "benchmark references", "standalone benchmark table")


def write_step_representative_table(config: dict[str, Any], path_budget: int, manifest: list[dict[str, str]]) -> None:
    selected_step = 72
    rows = read_rows(step_csv_path(path_budget))
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        rf"\caption{{Representative direct metrics at {fmt_int(path_budget)} paths and 72 Euler steps.}}",
        rf"\label{{tab:{CASE_ID}-step{selected_step}-{path_budget//1000}k}}",
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"Strike & LSMC price & LSMC rel. err. & Hybrid price & Hybrid rel. err. \\",
        r"\midrule",
    ]
    for scenario in config["strikes"]:
        selected = {
            row["method"]: row
            for row in rows
            if int(float(row["K"])) == int(scenario["K"]) and int(row["euler_steps"]) == selected_step
        }
        benchmark = selected["benchmark"]
        hybrid = selected["hybrid"]
        lines.append(
            rf"${int(scenario['K'])}$ & {finite(benchmark['price_direct']):.6f} & {fmt_pct(benchmark['rel_error_direct'])} & "
            rf"{finite(hybrid['price_direct']):.6f} & {fmt_pct(hybrid['rel_error_direct'])} \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    dest = TABLE_DIR / f"{CASE_ID}_step_sweep_{path_budget//1000}k_step72_table.tex"
    dest.write_text("\n".join(lines), encoding="utf-8")
    record(manifest, "table", step_csv_path(path_budget), dest, f"{path_budget} paths; 72 steps", "representative step-sweep metrics")


def write_path_representative_table(config: dict[str, Any], euler_steps: int, manifest: list[dict[str, str]]) -> None:
    selected_path = 20_000
    rows_by_strike: dict[str, dict[str, dict[str, str]]] = {}
    source_paths: list[str] = []
    for scenario in config["strikes"]:
        source_path = path_csv_path(scenario["slug"], euler_steps)
        source_paths.append(str(source_path))
        source_rows = read_rows(source_path)
        selected = {
            row["method"]: row
            for row in source_rows
            if int(row["paths"]) == selected_path and row["method"] in ("benchmark", "hybrid")
        }
        rows_by_strike[str(scenario["K"])] = selected
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        rf"\caption{{Representative direct metrics at $20{{,}}000$ paths under the fixed {euler_steps}-step path sweep.}}",
        rf"\label{{tab:{CASE_ID}-path{euler_steps}-path20k}}",
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"Strike & LSMC price & LSMC rel. err. & Hybrid price & Hybrid rel. err. \\",
        r"\midrule",
    ]
    for scenario in config["strikes"]:
        strike = str(scenario["K"])
        benchmark = rows_by_strike[strike]["benchmark"]
        hybrid = rows_by_strike[strike]["hybrid"]
        lines.append(
            rf"${strike}$ & {finite(benchmark['price_direct']):.6f} & {fmt_pct(benchmark['rel_error_direct'])} & "
            rf"{finite(hybrid['price_direct']):.6f} & {fmt_pct(hybrid['rel_error_direct'])} \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    dest = TABLE_DIR / f"{CASE_ID}_path_sweep_steps{euler_steps}_path20k_table.tex"
    dest.write_text("\n".join(lines), encoding="utf-8")
    record(manifest, "table", ";".join(source_paths), dest, f"{euler_steps} steps; 20k paths", "representative path-sweep metrics")


def write_appendix_tables(config: dict[str, Any], manifest: list[dict[str, str]]) -> None:
    benchmark_rows = read_rows(BENCHMARK_CSV)
    source_paths: list[str] = [str(BENCHMARK_CSV)]
    lines = [
        r"\section*{Positive-rate gDMR price tables}",
        r"\begin{table}[htbp]\centering",
        r"\caption{Benchmark prices. Prices are rounded to three decimals.}",
        r"\begin{tabular}{lrrrrr}",
        r"\toprule",
        r"Strike & 70 & 80 & 90 & 100 & 110 \\",
        r"\midrule",
        "LSMC benchmark & "
        + " & ".join(fmt_price(row["benchmark_direct_price"]) for row in sorted(benchmark_rows, key=lambda item: finite(item["K"])))
        + r" \\",
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
        "",
    ]
    for path_budget in config["step_sweep"]["paths"]:
        step_path = REFERENCE_DIR / f"{CASE_ID}_step_sweep_all_ref1200_direct_samepaths{int(path_budget)//1000}k_s24487296_table.csv"
        source_paths.append(str(step_path))
        rows = read_rows(step_path)
        lines.extend(
            [
                r"\begin{table}[htbp]\centering",
                rf"\caption{{Fixed-path step-sweep prices with {fmt_int(path_budget)} paths. Prices are rounded to three decimals.}}",
                r"\begin{tabular}{lrrrr}",
                r"\toprule",
                r"Method/step & 24 & 48 & 72 & 96 \\",
                r"\midrule",
            ]
        )
        for scenario in config["strikes"]:
            for method, label, _, _ in METHODS:
                selected = [
                    row
                    for row in rows
                    if int(float(row["K"])) == int(scenario["K"]) and row["method"] == method
                ]
                selected.sort(key=lambda row: int(row["euler_steps"]))
                lines.append(
                    f"{label} K={scenario['K']} & "
                    + " & ".join(fmt_price(row["price_direct"]) for row in selected)
                    + r" \\"
                )
        lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    for euler_steps in config["path_sweep"]["steps"]:
        lines.extend(
            [
                r"\begin{table}[htbp]\centering",
                rf"\caption{{Fixed {euler_steps}-step path-sweep prices. Prices are rounded to three decimals.}}",
                r"\begin{tabular}{lrrrrrrr}",
                r"\toprule",
                "Method/strike & " + " & ".join(fmt_int(path) for path in config["path_sweep"]["reported_paths"]) + r" \\",
                r"\midrule",
            ]
        )
        for scenario in config["strikes"]:
            path_source = path_csv_path(scenario["slug"], int(euler_steps))
            source_paths.append(str(path_source))
            rows = read_rows(path_source)
            for method, label, _, _ in METHODS:
                selected = [
                    row
                    for row in rows
                    if row["method"] == method and int(row["paths"]) in config["path_sweep"]["reported_paths"]
                ]
                selected.sort(key=lambda row: int(row["paths"]))
                lines.append(
                    f"{label} K={scenario['K']} & "
                    + " & ".join(fmt_price(row["price_direct"]) for row in selected)
                    + r" \\"
                )
        lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    dest = TABLE_DIR / f"{CASE_ID}_appendix_price_tables.tex"
    dest.write_text("\n".join(lines), encoding="utf-8")
    record(manifest, "table", ";".join(source_paths), dest, "appendix-style prices", "sandbox price tables")


def main() -> None:
    config = load_config()
    PLOT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    validate_sources(config)
    manifest: list[dict[str, str]] = []
    write_plot_data(config, manifest)
    write_experimental_setting_table(config, manifest)
    write_benchmark_reference_table(manifest)
    for path_budget in config["step_sweep"]["paths"]:
        render_step_figure(config, int(path_budget), manifest)
        write_step_representative_table(config, int(path_budget), manifest)
    for euler_steps in config["path_sweep"]["steps"]:
        render_path_figure(config, int(euler_steps), manifest)
        write_path_representative_table(config, int(euler_steps), manifest)
    write_appendix_tables(config, manifest)
    write_rows(ASSET_MANIFEST, MANIFEST_FIELDS, manifest)
    print(f"[assets] wrote {ASSET_MANIFEST}")


if __name__ == "__main__":
    main()
