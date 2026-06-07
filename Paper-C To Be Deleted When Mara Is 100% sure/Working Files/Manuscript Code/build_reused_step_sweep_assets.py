from __future__ import annotations

import csv
import hashlib
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parents[1]
EXTERNAL_SOURCE_DIR = PROJECT_ROOT / "Experiments 26.03"
OVERLEAF_DIR = PROJECT_ROOT / "Working Files" / "Manuscript Overleaf"
REFERENCE_DIR = ROOT / "reference_values"
OUTPUT_DIR = ROOT / "outputs"
PLOT_DATA_DIR = OUTPUT_DIR / "plot_data"
LOCAL_TABLE_DIR = ROOT / "tables"
OVERLEAF_DATA_DIR = OVERLEAF_DIR / "data" / "numerical"
OVERLEAF_TABLE_DIR = OVERLEAF_DIR / "tables" / "numerical"

SOURCE_FILENAMES = {
    "benchmark_main": "bgk_r00_t1_nex12_benchmark_steps1200_paths1200000_table.csv",
    "benchmark_tail": "bgk_r00_t1_nex12_benchmark_steps1200_paths1200000_k80_k70_table.csv",
    "step_sweep_20k": "bgk_r00_t1_nex12_step_sweep_all_ref1200_direct_samepaths20k_s24487296_table.csv",
    "step_sweep_60k": "bgk_r00_t1_nex12_step_sweep_all_ref1200_direct_samepaths60k_s24487296_table.csv",
}

SCENARIO_ORDER = [
    ("K=70 put", "70", "k70"),
    ("K=80 put", "80", "k80"),
    ("OTM put", "90", "k90"),
    ("ATM", "100", "k100"),
    ("ITM put", "110", "k110"),
]

MANIFEST_COLUMNS = [
    "kind",
    "study_type",
    "reuse_mode",
    "source_path",
    "destination_path",
    "sha256",
    "scenario_scope",
    "settings",
    "notes",
    "checksum_source",
]


def ensure_dirs() -> None:
    for path in (
        REFERENCE_DIR,
        OUTPUT_DIR,
        PLOT_DATA_DIR,
        LOCAL_TABLE_DIR,
        OVERLEAF_DATA_DIR,
        OVERLEAF_TABLE_DIR,
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


def external_source_path(key: str) -> Path:
    return EXTERNAL_SOURCE_DIR / SOURCE_FILENAMES[key]


def local_source_path(key: str) -> Path:
    return REFERENCE_DIR / SOURCE_FILENAMES[key]


def study_type_for(key: str) -> str:
    return "benchmark" if "benchmark" in key else "step sweep"


def scope_for(key: str) -> str:
    return "benchmark references" if "benchmark" in key else "five-strike step sweep"


def settings_for(key: str) -> str:
    if key == "benchmark_main" or key == "benchmark_tail":
        return "1200 steps; 1,200,000 paths; direct benchmark"
    if key == "step_sweep_20k":
        return "matched 20,000 paths; steps 24,48,72,96"
    return "matched 60,000 paths; steps 24,48,72,96"


def record_manifest(
    manifest: list[dict[str, str]],
    *,
    kind: str,
    study_type: str,
    reuse_mode: str,
    source_path: Path | str,
    destination_path: Path | str,
    scenario_scope: str,
    settings: str,
    notes: str,
) -> None:
    destination = Path(destination_path)
    manifest.append(
        {
            "kind": kind,
            "study_type": study_type,
            "reuse_mode": reuse_mode,
            "source_path": str(source_path),
            "destination_path": str(destination),
            "sha256": sha256_for(destination),
            "scenario_scope": scenario_scope,
            "settings": settings,
            "notes": notes,
            "checksum_source": str(OUTPUT_DIR / "reused_step_sweep_manifest.csv"),
        }
    )


def ensure_local_source(key: str, manifest: list[dict[str, str]]) -> Path:
    destination = local_source_path(key)
    if destination.exists():
        record_manifest(
            manifest,
            kind="local_reference_input",
            study_type=study_type_for(key),
            reuse_mode="reused_directly",
            source_path=destination,
            destination_path=destination,
            scenario_scope=scope_for(key),
            settings=settings_for(key),
            notes=f"existing local input for {key}",
        )
        return destination
    source = external_source_path(key)
    shutil.copy2(source, destination)
    record_manifest(
        manifest,
        kind="copied_source",
        study_type=study_type_for(key),
        reuse_mode="reused_directly",
        source_path=source,
        destination_path=destination,
        scenario_scope=scope_for(key),
        settings=settings_for(key),
        notes=f"copied external source for {key}",
    )
    return destination


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def ci_bounds(value: float, se: float) -> tuple[float, float]:
    half_width = 1.96 * se
    return value - half_width, value + half_width


def rel_error(value: float, reference: float) -> float:
    scale = abs(reference)
    if scale <= 1e-16:
        return 0.0 if abs(value) <= 1e-16 else float("inf")
    return abs(value - reference) / scale


def rel_error_ci_bounds(value: float, se: float, reference: float) -> tuple[float, float]:
    low_value, high_value = ci_bounds(value, se)
    endpoint_errors = (
        rel_error(low_value, reference),
        rel_error(high_value, reference),
    )
    if low_value <= reference <= high_value:
        return 0.0, max(endpoint_errors)
    return min(endpoint_errors), max(endpoint_errors)


def benchmark_lookup(rows_main: list[dict[str, str]], rows_tail: list[dict[str, str]]) -> dict[str, dict[str, float]]:
    lookup: dict[str, dict[str, float]] = {}
    for row in rows_main:
        lookup[row["scenario"]] = {
            "K": float(row["K"]),
            "price": float(row["benchmark_direct_price"]),
            "se": float(row["benchmark_direct_error"]),
        }
    for row in rows_tail:
        lookup[row["scenario"]] = {
            "K": float(row["K"]),
            "price": float(row["benchmark_direct_price"]),
            "se": float(row["benchmark_direct_error"]),
        }
    return lookup


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, float | int | str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_csv_pair(
    local_path: Path,
    overleaf_path: Path,
    fieldnames: list[str],
    rows: list[dict[str, float | int | str]],
    manifest: list[dict[str, str]],
    *,
    source_path: str,
    study_type: str,
    scenario_scope: str,
    settings: str,
    notes: str,
) -> None:
    write_csv(local_path, fieldnames, rows)
    shutil.copy2(local_path, overleaf_path)
    record_manifest(
        manifest,
        kind="derived_asset",
        study_type=study_type,
        reuse_mode="rebased",
        source_path=source_path,
        destination_path=local_path,
        scenario_scope=scenario_scope,
        settings=settings,
        notes=notes,
    )
    record_manifest(
        manifest,
        kind="overleaf_export",
        study_type=study_type,
        reuse_mode="rebased",
        source_path=local_path,
        destination_path=overleaf_path,
        scenario_scope=scenario_scope,
        settings=settings,
        notes=f"overleaf export for {notes}",
    )


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def write_text_pair(
    local_path: Path,
    overleaf_path: Path,
    text: str,
    manifest: list[dict[str, str]],
    *,
    source_path: str,
    study_type: str,
    scenario_scope: str,
    settings: str,
    notes: str,
) -> None:
    write_text(local_path, text)
    shutil.copy2(local_path, overleaf_path)
    record_manifest(
        manifest,
        kind="derived_asset",
        study_type=study_type,
        reuse_mode="rebased",
        source_path=source_path,
        destination_path=local_path,
        scenario_scope=scenario_scope,
        settings=settings,
        notes=notes,
    )
    record_manifest(
        manifest,
        kind="overleaf_export",
        study_type=study_type,
        reuse_mode="rebased",
        source_path=local_path,
        destination_path=overleaf_path,
        scenario_scope=scenario_scope,
        settings=settings,
        notes=f"overleaf export for {notes}",
    )


def write_benchmark_reference_csv(lookup: dict[str, dict[str, float]], manifest: list[dict[str, str]]) -> None:
    rows: list[dict[str, float | int | str]] = []
    for scenario, strike, _ in SCENARIO_ORDER:
        value = lookup[scenario]
        low, high = ci_bounds(value["price"], value["se"])
        rows.append(
            {
                "scenario": scenario,
                "K": strike,
                "benchmark_direct_price": f"{value['price']:.6f}",
                "benchmark_direct_se": f"{value['se']:.6f}",
                "benchmark_direct_ci_lower": f"{low:.6f}",
                "benchmark_direct_ci_upper": f"{high:.6f}",
            }
        )
    write_csv_pair(
        PLOT_DATA_DIR / "benchmark_direct_references.csv",
        OVERLEAF_DATA_DIR / "benchmark_direct_references.csv",
        [
            "scenario",
            "K",
            "benchmark_direct_price",
            "benchmark_direct_se",
            "benchmark_direct_ci_lower",
            "benchmark_direct_ci_upper",
        ],
        rows,
        manifest,
        source_path=";".join(str(local_source_path(key)) for key in ("benchmark_main", "benchmark_tail")),
        study_type="benchmark",
        scenario_scope="five benchmark strikes",
        settings="1200-step direct benchmark",
        notes="normalized benchmark reference csv",
    )


def write_benchmark_table(lookup: dict[str, dict[str, float]], manifest: list[dict[str, str]]) -> None:
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Direct benchmark reference values used in the numerical comparisons.}",
        r"\label{tab:benchmark-direct-references}",
        r"\small",
        r"\begin{tabularx}{0.82\textwidth}{@{}ccc>{\centering\arraybackslash}X@{}}",
        r"\toprule",
        r"$K$ & Direct price & SE & Confidence interval \\",
        r"\midrule",
    ]
    for scenario, strike, _ in SCENARIO_ORDER:
        value = lookup[scenario]
        low, high = ci_bounds(value["price"], value["se"])
        lines.append(
            rf"{strike} & {value['price']:.6f} & {value['se']:.6f} & [{low:.6f}, {high:.6f}] \\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabularx}",
            r"\end{table}",
        ]
    )
    write_text_pair(
        LOCAL_TABLE_DIR / "benchmark_reference_table.tex",
        OVERLEAF_TABLE_DIR / "benchmark_reference_table.tex",
        "\n".join(lines) + "\n",
        manifest,
        source_path=";".join(str(local_source_path(key)) for key in ("benchmark_main", "benchmark_tail")),
        study_type="benchmark",
        scenario_scope="five benchmark strikes",
        settings="1200-step direct benchmark",
        notes="benchmark reference table",
    )


def grouped_step_rows(rows: list[dict[str, str]]) -> dict[str, dict[str, list[dict[str, str]]]]:
    grouped: dict[str, dict[str, list[dict[str, str]]]] = {}
    for row in rows:
        grouped.setdefault(row["scenario"], {}).setdefault(row["method"], []).append(row)
    for scenario in grouped:
        for method in grouped[scenario]:
            grouped[scenario][method].sort(key=lambda item: int(item["euler_steps"]))
    return grouped


def write_plot_files(path_label: str, rows: list[dict[str, str]], manifest: list[dict[str, str]]) -> None:
    grouped = grouped_step_rows(rows)
    source_path = str(local_source_path(f"step_sweep_{path_label}"))
    path_text = "20,000" if path_label == "20k" else "60,000"
    for scenario, _, slug in SCENARIO_ORDER:
        for method in ("benchmark", "hybrid"):
            output_rows: list[dict[str, float | int | str]] = []
            for row in grouped[scenario][method]:
                price = float(row["price_direct"])
                se = float(row["se_direct"])
                reference = float(row["reference_direct_price"])
                rel = rel_error(price, reference)
                rel_low, rel_high = rel_error_ci_bounds(price, se, reference)
                output_rows.append(
                    {
                        "euler_steps": int(row["euler_steps"]),
                        "rel_error_pct": f"{100.0 * rel:.6f}",
                        "yerr_minus_pct": f"{100.0 * (rel - rel_low):.6f}",
                        "yerr_plus_pct": f"{100.0 * (rel_high - rel):.6f}",
                    }
                )
            local_output = PLOT_DATA_DIR / f"step_sweep_{path_label}_{slug}_{method}.csv"
            overleaf_output = OVERLEAF_DATA_DIR / f"step_sweep_{path_label}_{slug}_{method}.csv"
            write_csv_pair(
                local_output,
                overleaf_output,
                ["euler_steps", "rel_error_pct", "yerr_minus_pct", "yerr_plus_pct"],
                output_rows,
                manifest,
                source_path=source_path,
                study_type="step sweep",
                scenario_scope=scenario,
                settings=f"matched {path_text} paths; relative error plot data",
                notes=method,
            )


def write_step72_table(path_label: str, rows: list[dict[str, str]], manifest: list[dict[str, str]]) -> None:
    path_text = "20,000" if path_label == "20k" else "60,000"
    grouped = grouped_step_rows(rows)
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        rf"\caption{{Representative direct metrics at $72$ steps under the matched {path_text}-path comparison.}}",
        rf"\label{{tab:step-sweep-{path_label}-step72}}",
        r"\small",
        r"\setlength{\tabcolsep}{3pt}",
        r"\begin{tabularx}{\textwidth}{@{}ccc>{\centering\arraybackslash}Xcc>{\centering\arraybackslash}X@{}}",
        r"\toprule",
        r"& \multicolumn{3}{c}{LSMC} & \multicolumn{3}{c}{Hybrid LSMC--PDE} \\",
        r"\cmidrule(lr){2-4}\cmidrule(lr){5-7}",
        r"$K$ & Dir. err. & SE & Confidence interval & Dir. err. & SE & Confidence interval \\",
        r"\midrule",
    ]
    for scenario, strike, _ in SCENARIO_ORDER:
        benchmark_row = next(row for row in grouped[scenario]["benchmark"] if int(row["euler_steps"]) == 72)
        hybrid_row = next(row for row in grouped[scenario]["hybrid"] if int(row["euler_steps"]) == 72)
        benchmark_price = float(benchmark_row["price_direct"])
        benchmark_se = float(benchmark_row["se_direct"])
        hybrid_price = float(hybrid_row["price_direct"])
        hybrid_se = float(hybrid_row["se_direct"])
        benchmark_low, benchmark_high = ci_bounds(benchmark_price, benchmark_se)
        hybrid_low, hybrid_high = ci_bounds(hybrid_price, hybrid_se)
        lines.append(
            rf"{strike} & "
            rf"{100.0 * float(benchmark_row['rel_error_direct']):.3f}\% & "
            rf"{benchmark_se:.6f} & "
            rf"[{benchmark_low:.6f}, {benchmark_high:.6f}] & "
            rf"{100.0 * float(hybrid_row['rel_error_direct']):.3f}\% & "
            rf"{hybrid_se:.6f} & "
            rf"[{hybrid_low:.6f}, {hybrid_high:.6f}] \\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabularx}",
            r"\end{table}",
        ]
    )
    write_text_pair(
        LOCAL_TABLE_DIR / f"step_sweep_{path_label}_step72_table.tex",
        OVERLEAF_TABLE_DIR / f"step_sweep_{path_label}_step72_table.tex",
        "\n".join(lines) + "\n",
        manifest,
        source_path=str(local_source_path(f"step_sweep_{path_label}")),
        study_type="step sweep",
        scenario_scope="five-strike matched step sweep",
        settings=f"matched {path_text} paths at 72 steps",
        notes="representative step-72 metrics table",
    )


def write_manifest(manifest: list[dict[str, str]]) -> None:
    path = OUTPUT_DIR / "reused_step_sweep_manifest.csv"
    write_csv(path, MANIFEST_COLUMNS, manifest)


def main() -> None:
    ensure_dirs()
    manifest: list[dict[str, str]] = []
    local_sources = {key: ensure_local_source(key, manifest) for key in SOURCE_FILENAMES}
    benchmark_main_rows = load_csv_rows(local_sources["benchmark_main"])
    benchmark_tail_rows = load_csv_rows(local_sources["benchmark_tail"])
    lookup = benchmark_lookup(benchmark_main_rows, benchmark_tail_rows)
    write_benchmark_reference_csv(lookup, manifest)
    write_benchmark_table(lookup, manifest)
    for path_label in ("20k", "60k"):
        rows = load_csv_rows(local_sources[f"step_sweep_{path_label}"])
        write_plot_files(path_label, rows, manifest)
        write_step72_table(path_label, rows, manifest)
    write_manifest(manifest)
    print("Reused step-sweep manuscript assets prepared.")
    print(f"Manifest: {OUTPUT_DIR / 'reused_step_sweep_manifest.csv'}")


if __name__ == "__main__":
    main()
