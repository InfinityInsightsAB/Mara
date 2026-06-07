from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


CASE_ID = "bgk_r02_t1_delta05_nex12"

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parents[1]
OVERLEAF_DIR = PROJECT_ROOT / "Working Files" / "Manuscript Overleaf"

REFERENCE_DIR = ROOT / "reference_values"
PATH_REFERENCE_DIR = REFERENCE_DIR / "path_sweep"
OUTPUT_DIR = ROOT / "outputs"
PLOT_DATA_DIR = OUTPUT_DIR / "plot_data"
LOCAL_TABLE_DIR = ROOT / "tables"
LOCAL_FIGURE_DIR = ROOT / "figures"
OVERLEAF_DATA_DIR = OVERLEAF_DIR / "data" / "numerical"
OVERLEAF_TABLE_DIR = OVERLEAF_DIR / "tables" / "numerical"
OVERLEAF_FIGURE_DIR = OVERLEAF_DIR / "figures" / "numerical"
MANIFEST_PATH = OUTPUT_DIR / f"{CASE_ID}_asset_manifest.csv"
METADATA_PATH = OUTPUT_DIR / f"{CASE_ID}_metadata.json"

BENCHMARK_CSV = REFERENCE_DIR / f"{CASE_ID}_benchmark_steps1200_paths1200000_table.csv"
STEP_CSVS = {
    20_000: REFERENCE_DIR / f"{CASE_ID}_step_sweep_all_ref1200_direct_samepaths20k_s24487296_table.csv",
    60_000: REFERENCE_DIR / f"{CASE_ID}_step_sweep_all_ref1200_direct_samepaths60k_s24487296_table.csv",
}

SCENARIOS = [
    ("K=70 put", "K=70", "70", "k70"),
    ("K=80 put", "K=80", "80", "k80"),
    ("OTM put", "K=90", "90", "k90"),
    ("ATM", "K=100", "100", "k100"),
    ("ITM put", "K=110", "110", "k110"),
]
STEP_SWEEP_STEPS = [24, 48, 72, 96]
STEP_SWEEP_PATHS = [20_000, 60_000]
SOURCE_PATH_GRID = [250, 500, 1000, 2000, 5000, 10000, 20000, 40000, 60000]
REPORTED_PATH_GRID = [250, 1000, 5000, 10000, 20000, 40000, 60000]
PATH_SWEEP_STEPS = [48, 60]
METHODS = [
    ("benchmark", "LSMC", "#1f4e79", "o"),
    ("hybrid", "Hybrid LSMC-PDE", "#c4601a", "s"),
]

MANIFEST_COLUMNS = [
    "kind",
    "source_path",
    "destination_path",
    "sha256",
    "settings",
    "notes",
]


def ensure_dirs() -> None:
    for path in (
        OUTPUT_DIR,
        PLOT_DATA_DIR,
        LOCAL_TABLE_DIR,
        LOCAL_FIGURE_DIR,
        OVERLEAF_DATA_DIR,
        OVERLEAF_TABLE_DIR,
        OVERLEAF_FIGURE_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)


def sha256_for(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def record_manifest(
    manifest: list[dict[str, str]],
    *,
    kind: str,
    source_path: Path | str,
    destination_path: Path | str,
    settings: str,
    notes: str,
) -> None:
    destination = Path(destination_path)
    manifest.append(
        {
            "kind": kind,
            "source_path": str(source_path),
            "destination_path": str(destination),
            "sha256": sha256_for(destination),
            "settings": settings,
            "notes": notes,
        }
    )


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str | int | float]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in fieldnames})


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def copy_and_record(
    source: Path,
    destination: Path,
    manifest: list[dict[str, str]],
    *,
    kind: str,
    settings: str,
    notes: str,
) -> None:
    shutil.copy2(source, destination)
    record_manifest(
        manifest,
        kind=kind,
        source_path=source,
        destination_path=destination,
        settings=settings,
        notes=notes,
    )


def ci_bounds(price: float, se: float) -> tuple[float, float]:
    half_width = 1.96 * se
    return price - half_width, price + half_width


def rel_error(value: float, reference: float) -> float:
    if abs(reference) <= 1e-16:
        return 0.0 if abs(value) <= 1e-16 else float("inf")
    return abs(value - reference) / abs(reference)


def rel_error_ci_bounds(value: float, se: float, reference: float) -> tuple[float, float]:
    low, high = ci_bounds(value, se)
    endpoint_errors = (rel_error(low, reference), rel_error(high, reference))
    if low <= reference <= high:
        return 0.0, max(endpoint_errors)
    return min(endpoint_errors), max(endpoint_errors)


def fmt_price(value: str | float) -> str:
    return f"{float(value):.3f}"


def fmt_pct(value: str | float) -> str:
    return f"{100.0 * float(value):.3f}\\%"


def fmt_int(value: int) -> str:
    return f"{value:,}".replace(",", "{,}")


def scenario_rows_by_k(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {str(int(float(row["K"]))): row for row in rows}


def path_csv_path(slug: str, euler_steps: int) -> Path:
    return PATH_REFERENCE_DIR / f"{CASE_ID}_path_sweep_{slug}_steps{euler_steps}_direct_ref1200_paths1200000_table.csv"


def validate_metadata() -> None:
    if not METADATA_PATH.exists():
        raise FileNotFoundError(METADATA_PATH)
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    model = metadata["model_env"]
    expected = {
        "GDMR_R": "0.02",
        "GDMR_DELTA1": "0.5",
        "GDMR_DELTA2": "0.5",
        "GDMR_MATURITY": "1.0",
        "GDMR_EXERCISE_DATES": "12",
    }
    for key, value in expected.items():
        if str(model.get(key)) != value:
            raise ValueError(f"{METADATA_PATH} has {key}={model.get(key)!r}, expected {value!r}")


def validate_sources() -> None:
    validate_metadata()
    benchmark_rows = load_csv(BENCHMARK_CSV)
    if len(benchmark_rows) != 5:
        raise ValueError(f"{BENCHMARK_CSV} should have 5 data rows, found {len(benchmark_rows)}")
    if {int(float(row["K"])) for row in benchmark_rows} != {70, 80, 90, 100, 110}:
        raise ValueError("benchmark strikes are incomplete")
    for row in benchmark_rows:
        if int(row["euler_steps"]) != 1200 or int(row["lsmc_paths"]) != 1_200_000:
            raise ValueError("benchmark row has unexpected step/path setting")

    for path_budget, csv_path in STEP_CSVS.items():
        rows = load_csv(csv_path)
        if len(rows) != 40:
            raise ValueError(f"{csv_path} should have 40 rows, found {len(rows)}")
        keys = {
            (int(float(row["K"])), int(row["euler_steps"]), row["method"])
            for row in rows
        }
        expected = {
            (int(strike), step, method)
            for _, _, strike, _ in SCENARIOS
            for step in STEP_SWEEP_STEPS
            for method, _, _, _ in METHODS
        }
        if keys != expected:
            raise ValueError(f"{csv_path} has unexpected row keys for path budget {path_budget}")

    for _, _, _, slug in SCENARIOS:
        for euler_steps in PATH_SWEEP_STEPS:
            csv_path = path_csv_path(slug, euler_steps)
            rows = load_csv(csv_path)
            if len(rows) != 18:
                raise ValueError(f"{csv_path} should have 18 rows, found {len(rows)}")
            keys = {(int(row["paths"]), row["method"]) for row in rows}
            expected = {
                (paths, method)
                for paths in SOURCE_PATH_GRID
                for method, _, _, _ in METHODS
            }
            if keys != expected:
                raise ValueError(f"{csv_path} has unexpected path/method grid")
            for row in rows:
                for key in ("price_direct", "se_direct", "rel_error_direct"):
                    value = float(row[key])
                    if not math.isfinite(value):
                        raise ValueError(f"{csv_path} contains non-finite {key}")


def benchmark_lookup() -> dict[str, dict[str, str]]:
    return scenario_rows_by_k(load_csv(BENCHMARK_CSV))


def write_path_plot_data(manifest: list[dict[str, str]]) -> None:
    fieldnames = ["paths", "rel_error_pct", "yerr_minus_pct", "yerr_plus_pct"]
    for euler_steps in PATH_SWEEP_STEPS:
        for _, _, strike, slug in SCENARIOS:
            rows = load_csv(path_csv_path(slug, euler_steps))
            for method, _, _, _ in METHODS:
                output_rows: list[dict[str, str | int | float]] = []
                for row in rows:
                    if row["method"] != method or int(row["paths"]) not in REPORTED_PATH_GRID:
                        continue
                    rel = 100.0 * float(row["rel_error_direct"])
                    rel_low = 100.0 * float(row["rel_ci_lower_direct"])
                    rel_high = 100.0 * float(row["rel_ci_upper_direct"])
                    output_rows.append(
                        {
                            "paths": int(row["paths"]),
                            "rel_error_pct": f"{rel:.6f}",
                            "yerr_minus_pct": f"{rel - rel_low:.6f}",
                            "yerr_plus_pct": f"{rel_high - rel:.6f}",
                        }
                    )
                output_rows.sort(key=lambda item: int(item["paths"]))
                local_path = PLOT_DATA_DIR / f"{CASE_ID}_path_sweep_steps{euler_steps}_{slug}_{method}.csv"
                overleaf_path = OVERLEAF_DATA_DIR / f"{CASE_ID}_path_sweep_steps{euler_steps}_{slug}_{method}.csv"
                write_csv(local_path, fieldnames, output_rows)
                record_manifest(
                    manifest,
                    kind="plot_data",
                    source_path=path_csv_path(slug, euler_steps),
                    destination_path=local_path,
                    settings=f"{euler_steps} steps; reported paths 250 to 60,000",
                    notes=f"{method} relative-error plot data, {strike}",
                )
                copy_and_record(
                    local_path,
                    overleaf_path,
                    manifest,
                    kind="overleaf_data",
                    settings=f"{euler_steps} steps; reported paths 250 to 60,000",
                    notes=f"{method} relative-error plot data export, {strike}",
                )


def load_plot_rows(path: Path) -> list[dict[str, float]]:
    rows = load_csv(path)
    return [
        {
            "paths": float(row["paths"]),
            "rel_error_pct": float(row["rel_error_pct"]),
            "yerr_minus_pct": float(row["yerr_minus_pct"]),
            "yerr_plus_pct": float(row["yerr_plus_pct"]),
        }
        for row in rows
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


def render_path48_figure(manifest: list[dict[str, str]]) -> None:
    rcparams()
    euler_steps = 48
    ymax = 0.0
    input_paths: list[str] = []
    for _, _, _, slug in SCENARIOS:
        for method, _, _, _ in METHODS:
            data_path = PLOT_DATA_DIR / f"{CASE_ID}_path_sweep_steps{euler_steps}_{slug}_{method}.csv"
            input_paths.append(str(data_path))
            for row in load_plot_rows(data_path):
                ymax = max(ymax, row["rel_error_pct"] + row["yerr_plus_pct"])
    ymax = max(1.0, 1.15 * ymax)

    fig, axes = plt.subplots(3, 2, figsize=(10.8, 8.4), constrained_layout=True)
    axes_flat = axes.flatten()
    for axis, (_, title, _, slug) in zip(axes_flat[:5], SCENARIOS):
        for method, label, color, marker in METHODS:
            data_path = PLOT_DATA_DIR / f"{CASE_ID}_path_sweep_steps{euler_steps}_{slug}_{method}.csv"
            rows = load_plot_rows(data_path)
            x = [row["paths"] for row in rows]
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
        axis.set_xscale("log")
        axis.set_xlim(220, 70000)
        axis.set_ylim(0, ymax)
        axis.set_xticks(REPORTED_PATH_GRID)
        axis.set_xticklabels([f"{value:,}" for value in REPORTED_PATH_GRID], rotation=35, ha="right")
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
    legend_axis.text(0.02, 0.58, "Case: r=0.02, delta1=delta2=0.5", ha="left", va="top", fontsize=10)
    legend_axis.text(0.02, 0.40, "Benchmark: LSMC, 1200 steps, 1.2M paths", ha="left", va="top", fontsize=10)
    legend_axis.text(0.02, 0.22, "Error bars: propagated 95% confidence intervals", ha="left", va="top", fontsize=10)
    fig.supxlabel("Number of Paths")
    fig.supylabel("Relative Error (%)")

    figure_name = f"{CASE_ID}_path_sweep_steps48_direct_relative_error"
    local_pdf = LOCAL_FIGURE_DIR / f"{figure_name}.pdf"
    local_eps = LOCAL_FIGURE_DIR / f"{figure_name}.eps"
    overleaf_pdf = OVERLEAF_FIGURE_DIR / f"{figure_name}.pdf"
    overleaf_eps = OVERLEAF_FIGURE_DIR / f"{figure_name}.eps"
    fig.savefig(local_pdf, bbox_inches="tight")
    fig.savefig(local_eps, format="eps", bbox_inches="tight")
    plt.close(fig)
    record_manifest(
        manifest,
        kind="figure",
        source_path=";".join(sorted(input_paths)),
        destination_path=local_pdf,
        settings="fixed 48-step path sweep; five strikes; relative error",
        notes="local representative robustness figure, pdf",
    )
    record_manifest(
        manifest,
        kind="figure",
        source_path=";".join(sorted(input_paths)),
        destination_path=local_eps,
        settings="fixed 48-step path sweep; five strikes; relative error",
        notes="local representative robustness figure, eps",
    )
    copy_and_record(
        local_pdf,
        overleaf_pdf,
        manifest,
        kind="overleaf_figure",
        settings="fixed 48-step path sweep; five strikes; relative error",
        notes="representative robustness figure export, pdf",
    )
    copy_and_record(
        local_eps,
        overleaf_eps,
        manifest,
        kind="overleaf_figure",
        settings="fixed 48-step path sweep; five strikes; relative error",
        notes="representative robustness figure export, eps",
    )


def source_rows_for_path20k(euler_steps: int) -> dict[str, dict[str, dict[str, str]]]:
    out: dict[str, dict[str, dict[str, str]]] = {}
    for _, _, strike, slug in SCENARIOS:
        rows = load_csv(path_csv_path(slug, euler_steps))
        out[strike] = {
            row["method"]: row
            for row in rows
            if int(row["paths"]) == 20000
        }
    return out


def write_main_representative_table(manifest: list[dict[str, str]]) -> None:
    rows_by_strike = source_rows_for_path20k(48)
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Representative direct metrics for the robustness case at $48$ steps and $20{,}000$ paths.}",
        r"\label{tab:bgk-r02-t1-delta05-nex12-path48-path20k}",
        r"\small",
        r"\setlength{\tabcolsep}{3pt}",
        r"\begin{tabularx}{\textwidth}{@{}ccc>{\centering\arraybackslash}Xcc>{\centering\arraybackslash}X@{}}",
        r"\toprule",
        r"& \multicolumn{3}{c}{LSMC} & \multicolumn{3}{c}{Hybrid LSMC--PDE} \\",
        r"\cmidrule(lr){2-4}\cmidrule(lr){5-7}",
        r"$K$ & Dir. err. & SE & Confidence interval & Dir. err. & SE & Confidence interval \\",
        r"\midrule",
    ]
    for _, _, strike, _ in SCENARIOS:
        benchmark = rows_by_strike[strike]["benchmark"]
        hybrid = rows_by_strike[strike]["hybrid"]
        b_price, b_se = float(benchmark["price_direct"]), float(benchmark["se_direct"])
        h_price, h_se = float(hybrid["price_direct"]), float(hybrid["se_direct"])
        b_low, b_high = ci_bounds(b_price, b_se)
        h_low, h_high = ci_bounds(h_price, h_se)
        lines.append(
            rf"{strike} & "
            rf"{fmt_pct(benchmark['rel_error_direct'])} & {b_se:.6f} & [{b_low:.6f}, {b_high:.6f}] & "
            rf"{fmt_pct(hybrid['rel_error_direct'])} & {h_se:.6f} & [{h_low:.6f}, {h_high:.6f}] \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}", r"\end{table}"])
    local_path = LOCAL_TABLE_DIR / f"{CASE_ID}_path_sweep_steps48_path20k_table.tex"
    overleaf_path = OVERLEAF_TABLE_DIR / f"{CASE_ID}_path_sweep_steps48_path20k_table.tex"
    text = "\n".join(lines) + "\n"
    write_text(local_path, text)
    record_manifest(
        manifest,
        kind="table",
        source_path=";".join(str(path_csv_path(slug, 48)) for _, _, _, slug in SCENARIOS),
        destination_path=local_path,
        settings="48 steps; representative 20,000-path comparison",
        notes="main robustness representative table",
    )
    copy_and_record(
        local_path,
        overleaf_path,
        manifest,
        kind="overleaf_table",
        settings="48 steps; representative 20,000-path comparison",
        notes="main robustness representative table export",
    )


def price_matrix_for_step(path_budget: int) -> dict[tuple[int, str, str], str]:
    rows = load_csv(STEP_CSVS[path_budget])
    matrix: dict[tuple[int, str, str], str] = {}
    for row in rows:
        matrix[(int(row["euler_steps"]), row["method"], str(int(float(row["K"]))))] = fmt_price(row["price_direct"])
    return matrix


def price_matrix_for_path(euler_steps: int) -> dict[tuple[int, str, str], str]:
    matrix: dict[tuple[int, str, str], str] = {}
    for _, _, strike, slug in SCENARIOS:
        rows = load_csv(path_csv_path(slug, euler_steps))
        for row in rows:
            if int(row["paths"]) in REPORTED_PATH_GRID:
                matrix[(int(row["paths"]), row["method"], strike)] = fmt_price(row["price_direct"])
    return matrix


def append_price_row(lines: list[str], prefix: str, method: str, values: list[str]) -> None:
    method_label = "LSMC" if method == "benchmark" else "Hybrid"
    lines.append(prefix + f" & {method_label} & " + " & ".join(values) + r" \\")


def write_appendix_tables(manifest: list[dict[str, str]]) -> None:
    benchmark = benchmark_lookup()
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Parameter setting for the positive-rate square-root-exponent robustness case.}",
        r"\label{tab:app-bgk-r02-t1-delta05-nex12-parameters}",
        r"\footnotesize",
        r"\setlength{\tabcolsep}{4pt}",
        r"\begin{tabularx}{0.92\textwidth}{@{}l>{\raggedleft\arraybackslash}X@{}}",
        r"\toprule",
        r"Quantity & Value \\",
        r"\midrule",
        r"$S_0$ & $100$ \\",
        r"$v_0$ & $0.114$ \\",
        r"$v'_0$ & $0.110$ \\",
        r"$r$ & $0.02$ \\",
        r"$T$ & $1$ \\",
        r"$\kappa_1,\kappa_2$ & $5.5,\;0.1$ \\",
        r"$\theta$ & $0.078$ \\",
        r"$\xi_1,\xi_2$ & $2.689,\;0.502$ \\",
        r"$\delta_1,\delta_2$ & $0.5,\;0.5$ \\",
        r"$\rho_{12},\rho_{13},\rho_{23}$ & $-0.982,\;-0.727,\;0.590$ \\",
        r"Exercise dates & $12$ \\",
        r"Strikes & $70,80,90,100,110$ \\",
        r"Hybrid grid & $N_S=301$, $(a_{\min},a_{\max})=(0.30,3.50)$, $q_v=0.999$ \\",
        r"\bottomrule",
        r"\end{tabularx}",
        r"\end{table}",
        "",
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Direct benchmark reference prices for the robustness case. Prices are rounded to three decimal places.}",
        r"\label{tab:app-bgk-r02-t1-delta05-nex12-benchmark-prices}",
        r"\footnotesize",
        r"\setlength{\tabcolsep}{4pt}",
        r"\begin{tabularx}{0.86\textwidth}{@{}l *{5}{>{\centering\arraybackslash}X}@{}}",
        r"\toprule",
        r"Reference setting & $K=70$ & $K=80$ & $K=90$ & $K=100$ & $K=110$ \\",
        r"\midrule",
        r"$1200$ steps, $1{,}200{,}000$ paths & "
        + " & ".join(fmt_price(benchmark[strike]["benchmark_direct_price"]) for _, _, strike, _ in SCENARIOS)
        + r" \\",
        r"\bottomrule",
        r"\end{tabularx}",
        r"\end{table}",
        "",
    ]

    for path_budget in STEP_SWEEP_PATHS:
        matrix = price_matrix_for_step(path_budget)
        lines.extend(
            [
                r"\begin{table}[H]",
                r"\centering",
                rf"\caption{{Direct prices in the robustness fixed-path step sweep with {fmt_int(path_budget)} paths. Prices are rounded to three decimal places.}}",
                rf"\label{{tab:app-bgk-r02-t1-delta05-nex12-step-sweep-{path_budget // 1000}k-prices}}",
                r"\footnotesize",
                r"\setlength{\tabcolsep}{3pt}",
                r"\begin{tabularx}{\textwidth}{@{}c l *{5}{>{\centering\arraybackslash}X}@{}}",
                r"\toprule",
                r"Steps & Method & $K=70$ & $K=80$ & $K=90$ & $K=100$ & $K=110$ \\",
                r"\midrule",
            ]
        )
        for step in STEP_SWEEP_STEPS:
            for method, _, _, _ in METHODS:
                values = [matrix[(step, method, strike)] for _, _, strike, _ in SCENARIOS]
                append_price_row(lines, str(step), method, values)
        lines.extend([r"\bottomrule", r"\end{tabularx}", r"\end{table}", ""])

    for euler_steps in PATH_SWEEP_STEPS:
        matrix = price_matrix_for_path(euler_steps)
        lines.extend(
            [
                r"\begin{table}[H]",
                r"\centering",
                rf"\caption{{Direct prices in the robustness fixed {euler_steps}-step path sweep. Prices are rounded to three decimal places.}}",
                rf"\label{{tab:app-bgk-r02-t1-delta05-nex12-path-sweep-{euler_steps}-prices}}",
                r"\footnotesize",
                r"\setlength{\tabcolsep}{3pt}",
                r"\begin{tabularx}{\textwidth}{@{}c l *{5}{>{\centering\arraybackslash}X}@{}}",
                r"\toprule",
                r"Paths & Method & $K=70$ & $K=80$ & $K=90$ & $K=100$ & $K=110$ \\",
                r"\midrule",
            ]
        )
        for paths in REPORTED_PATH_GRID:
            for method, _, _, _ in METHODS:
                values = [matrix[(paths, method, strike)] for _, _, strike, _ in SCENARIOS]
                append_price_row(lines, fmt_int(paths), method, values)
        lines.extend([r"\bottomrule", r"\end{tabularx}", r"\end{table}", ""])

    local_path = LOCAL_TABLE_DIR / f"{CASE_ID}_appendix_price_tables.tex"
    overleaf_path = OVERLEAF_TABLE_DIR / f"{CASE_ID}_appendix_price_tables.tex"
    text = "\n".join(lines).rstrip() + "\n"
    write_text(local_path, text)
    record_manifest(
        manifest,
        kind="appendix_tables",
        source_path=f"{BENCHMARK_CSV};" + ";".join(str(path) for path in STEP_CSVS.values()),
        destination_path=local_path,
        settings="all direct robustness prices rounded to three decimals",
        notes="appendix robustness tables",
    )
    copy_and_record(
        local_path,
        overleaf_path,
        manifest,
        kind="overleaf_table",
        settings="all direct robustness prices rounded to three decimals",
        notes="appendix robustness table export",
    )


def write_manifest(manifest: list[dict[str, str]]) -> None:
    write_csv(MANIFEST_PATH, MANIFEST_COLUMNS, manifest)


def main() -> None:
    ensure_dirs()
    validate_sources()
    manifest: list[dict[str, str]] = []
    write_path_plot_data(manifest)
    render_path48_figure(manifest)
    write_main_representative_table(manifest)
    write_appendix_tables(manifest)
    write_manifest(manifest)
    print("Robustness manuscript assets generated.")
    print(f"Manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
