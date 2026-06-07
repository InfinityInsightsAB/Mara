from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parents[1]
OVERLEAF_DIR = PROJECT_ROOT / "Working Files" / "Manuscript Overleaf"
SOURCE_DIR = ROOT / "reference_values" / "path_sweep"
OUTPUT_DIR = ROOT / "outputs"
PLOT_DATA_DIR = OUTPUT_DIR / "plot_data"
LOCAL_TABLE_DIR = ROOT / "tables"
OVERLEAF_DATA_DIR = OVERLEAF_DIR / "data" / "numerical"
OVERLEAF_TABLE_DIR = OVERLEAF_DIR / "tables" / "numerical"
MANIFEST_PATH = OUTPUT_DIR / "reused_path_sweep_manifest.csv"

SCENARIO_ORDER = [
    ("K=70", "70", "k70"),
    ("K=80", "80", "k80"),
    ("K=90", "90", "k90"),
    ("K=100", "100", "k100"),
    ("K=110", "110", "k110"),
]

STEP_VALUES = [48, 60]
PATH_GRID = [250, 1000, 5000, 10000, 20000, 40000, 60000]

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
    for path in (OUTPUT_DIR, PLOT_DATA_DIR, LOCAL_TABLE_DIR, OVERLEAF_DATA_DIR, OVERLEAF_TABLE_DIR):
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


def source_csv_path(scenario_slug: str, euler_steps: int) -> Path:
    stem = f"bgk_r00_t1_nex12_path_sweep_{scenario_slug}_steps{euler_steps}_direct_ref1200_paths1200000_table"
    return SOURCE_DIR / f"{stem}.csv"


def source_meta_path(scenario_slug: str, euler_steps: int) -> Path:
    stem = f"bgk_r00_t1_nex12_path_sweep_{scenario_slug}_steps{euler_steps}_direct_ref1200_paths1200000_table"
    return SOURCE_DIR / f"{stem}.json"


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_meta(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def format_paths(value: int) -> str:
    return f"{value:,}"


def ci_bounds(value: float, se: float) -> tuple[float, float]:
    half_width = 1.96 * se
    return value - half_width, value + half_width


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, float | int | str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


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
            "checksum_source": str(MANIFEST_PATH),
        }
    )


def write_csv_pair(
    local_path: Path,
    overleaf_path: Path,
    fieldnames: list[str],
    rows: list[dict[str, float | int | str]],
    manifest: list[dict[str, str]],
    *,
    source_path: str,
    scenario_scope: str,
    settings: str,
    notes: str,
) -> None:
    write_csv(local_path, fieldnames, rows)
    shutil.copy2(local_path, overleaf_path)
    record_manifest(
        manifest,
        kind="derived_asset",
        study_type="path sweep",
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
        study_type="path sweep",
        reuse_mode="rebased",
        source_path=local_path,
        destination_path=overleaf_path,
        scenario_scope=scenario_scope,
        settings=settings,
        notes=f"overleaf export for {notes}",
    )


def write_text_pair(
    local_path: Path,
    overleaf_path: Path,
    text: str,
    manifest: list[dict[str, str]],
    *,
    source_path: str,
    scenario_scope: str,
    settings: str,
    notes: str,
) -> None:
    write_text(local_path, text)
    shutil.copy2(local_path, overleaf_path)
    record_manifest(
        manifest,
        kind="derived_asset",
        study_type="path sweep",
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
        study_type="path sweep",
        reuse_mode="rebased",
        source_path=local_path,
        destination_path=overleaf_path,
        scenario_scope=scenario_scope,
        settings=settings,
        notes=f"overleaf export for {notes}",
    )


def grouped_rows(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {"benchmark": [], "hybrid": []}
    for row in rows:
        grouped[row["method"]].append(row)
    for method in grouped:
        grouped[method].sort(key=lambda item: int(item["paths"]))
    return grouped


def record_source_inputs(manifest: list[dict[str, str]]) -> None:
    for euler_steps in STEP_VALUES:
        for display_label, _, scenario_slug in SCENARIO_ORDER:
            csv_path = source_csv_path(scenario_slug, euler_steps)
            meta = load_meta(source_meta_path(scenario_slug, euler_steps))
            source_paths = list(meta["source_paths"]) if meta["source_paths"] else []
            if meta["computed_paths"]:
                source_paths.extend(meta["benchmark_source_paths"])
                source_paths.extend([meta["benchmark_script"], meta["hybrid_script"]])
            notes_parts = [f"reuse mode: {meta['reuse_mode']}"]
            if meta["reused_paths"]:
                notes_parts.append(
                    "reused paths: " + ", ".join(format_paths(int(value)) for value in meta["reused_paths"])
                )
            if meta["computed_paths"]:
                notes_parts.append(
                    "computed paths: " + ", ".join(format_paths(int(value)) for value in meta["computed_paths"])
                )
            record_manifest(
                manifest,
                kind="local_reference_input",
                study_type="path sweep",
                reuse_mode=str(meta["reuse_mode"]),
                source_path=";".join(sorted(set(str(path) for path in source_paths))),
                destination_path=csv_path,
                scenario_scope=f"{display_label}, {euler_steps} steps",
                settings=f"{euler_steps} steps; paths 250 to 60,000; direct path sweep",
                notes="; ".join(notes_parts),
            )


def write_plot_files(manifest: list[dict[str, str]]) -> None:
    for euler_steps in STEP_VALUES:
        for display_label, _, scenario_slug in SCENARIO_ORDER:
            rows = load_rows(source_csv_path(scenario_slug, euler_steps))
            grouped = grouped_rows(rows)
            for method in ("benchmark", "hybrid"):
                output_rows: list[dict[str, float | int | str]] = []
                for row in grouped[method]:
                    if int(row["paths"]) not in PATH_GRID:
                        continue
                    rel = 100.0 * float(row["rel_error_direct"])
                    rel_low = 100.0 * float(row["rel_ci_lower_direct"])
                    rel_high = 100.0 * float(row["rel_ci_upper_direct"])
                    output_rows.append(
                        {
                            "paths": int(row["paths"]),
                            "rel_error_pct": f"{rel:.6f}",
                            "yerr_minus_pct": f"{(rel - rel_low):.6f}",
                            "yerr_plus_pct": f"{(rel_high - rel):.6f}",
                        }
                    )
                local_output = PLOT_DATA_DIR / f"path_sweep_steps{euler_steps}_{scenario_slug}_{method}.csv"
                overleaf_output = OVERLEAF_DATA_DIR / f"path_sweep_steps{euler_steps}_{scenario_slug}_{method}.csv"
                write_csv_pair(
                    local_output,
                    overleaf_output,
                    ["paths", "rel_error_pct", "yerr_minus_pct", "yerr_plus_pct"],
                    output_rows,
                    manifest,
                    source_path=str(source_csv_path(scenario_slug, euler_steps)),
                    scenario_scope=f"{display_label}, {euler_steps} steps",
                    settings=f"{euler_steps} steps; paths 250,1000,5000,10000,20000,40000,60000; relative error plot data",
                    notes=method,
                )


def write_path20k_table(euler_steps: int, manifest: list[dict[str, str]]) -> None:
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        rf"\caption{{Representative direct metrics at $20{{,}}000$ paths under the fixed {euler_steps}-step path sweep.}}",
        rf"\label{{tab:path-sweep-{euler_steps}-path20k}}",
        r"\small",
        r"\setlength{\tabcolsep}{3pt}",
        r"\begin{tabularx}{\textwidth}{@{}ccc>{\centering\arraybackslash}Xcc>{\centering\arraybackslash}X@{}}",
        r"\toprule",
        r"& \multicolumn{3}{c}{LSMC} & \multicolumn{3}{c}{Hybrid LSMC--PDE} \\",
        r"\cmidrule(lr){2-4}\cmidrule(lr){5-7}",
        r"$K$ & Dir. err. & SE & Confidence interval & Dir. err. & SE & Confidence interval \\",
        r"\midrule",
    ]
    source_paths: list[str] = []
    for _, strike, scenario_slug in SCENARIO_ORDER:
        source_path = source_csv_path(scenario_slug, euler_steps)
        source_paths.append(str(source_path))
        rows = load_rows(source_path)
        benchmark_row = next(row for row in rows if int(row["paths"]) == 20000 and row["method"] == "benchmark")
        hybrid_row = next(row for row in rows if int(row["paths"]) == 20000 and row["method"] == "hybrid")
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
    lines.extend([r"\bottomrule", r"\end{tabularx}", r"\end{table}"])
    write_text_pair(
        LOCAL_TABLE_DIR / f"path_sweep_steps{euler_steps}_path20k_table.tex",
        OVERLEAF_TABLE_DIR / f"path_sweep_steps{euler_steps}_path20k_table.tex",
        "\n".join(lines) + "\n",
        manifest,
        source_path=";".join(source_paths),
        scenario_scope=f"five-strike path sweep, {euler_steps} steps",
        settings=f"{euler_steps} steps; representative 20,000-path comparison",
        notes="representative path-20k metrics table",
    )


def write_manifest(manifest: list[dict[str, str]]) -> None:
    write_csv(MANIFEST_PATH, MANIFEST_COLUMNS, manifest)


def main() -> None:
    ensure_dirs()
    manifest: list[dict[str, str]] = []
    record_source_inputs(manifest)
    write_plot_files(manifest)
    for euler_steps in STEP_VALUES:
        write_path20k_table(euler_steps, manifest)
    write_manifest(manifest)
    print("Path-sweep manuscript assets prepared.")
    print(f"Manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
