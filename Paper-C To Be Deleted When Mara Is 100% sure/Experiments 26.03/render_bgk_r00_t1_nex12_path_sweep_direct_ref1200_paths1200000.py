#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
REFERENCE_TABLE = THIS_DIR / "bgk_r00_t1_nex12_benchmark_steps1200_paths1200000_table.csv"
CI_Z = 1.96

SCENARIOS = {
    "atm": {
        "label": "ATM",
        "slug": "atm",
        "path_sweep_table": THIS_DIR / "bgk_r00_t1_nex12_path_sweep_atm_steps48_table.csv",
    },
    "otm": {
        "label": "OTM put",
        "slug": "otm",
        "path_sweep_table": THIS_DIR / "bgk_r00_t1_nex12_path_sweep_otm_steps48_table.csv",
    },
}

CSV_COLUMNS = [
    "paths",
    "method",
    "runtime_seconds",
    "price_direct",
    "se_direct",
    "reference_direct_price",
    "rel_error_direct",
    "rel_ci_lower_direct",
    "rel_ci_upper_direct",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebase a saved 48-step ATM or OTM direct path sweep to the 1200-step, 1.2M-path benchmark reference."
    )
    parser.add_argument(
        "--scenario",
        choices=sorted(SCENARIOS),
        required=True,
        help="Scenario slug to render.",
    )
    return parser.parse_args()


def rel_error(value: float, reference: float) -> float:
    scale = abs(reference)
    if scale <= 1e-16:
        return 0.0 if abs(value) <= 1e-16 else float("inf")
    return abs(value - reference) / scale


def ci_bounds(value: float, se: float) -> tuple[float, float]:
    half_width = CI_Z * se
    return value - half_width, value + half_width


def rel_error_ci_bounds(value: float, se: float, reference: float) -> tuple[float, float]:
    low_value, high_value = ci_bounds(value, se)
    endpoint_errors = (
        rel_error(low_value, reference),
        rel_error(high_value, reference),
    )
    if low_value <= reference <= high_value:
        return 0.0, max(endpoint_errors)
    return min(endpoint_errors), max(endpoint_errors)


def format_pct(value: float) -> str:
    return f"{100.0 * value:.3f}%"


def format_paths(value: int) -> str:
    return f"{value:,}"


def output_paths(scenario_slug: str) -> dict[str, Path]:
    stem = f"bgk_r00_t1_nex12_path_sweep_{scenario_slug}_steps48_direct_ref1200_paths1200000"
    return {
        "summary": THIS_DIR / f"{stem}_summary.md",
        "table": THIS_DIR / f"{stem}_table.csv",
        "figure": THIS_DIR / f"{stem}_relative_error_with_ci.svg",
    }


def load_reference(scenario_label: str) -> dict[str, float]:
    with REFERENCE_TABLE.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row["scenario"] == scenario_label:
                return {
                    "benchmark_direct_price": float(row["benchmark_direct_price"]),
                    "benchmark_direct_error": float(row["benchmark_direct_error"]),
                }
    raise RuntimeError(f"Could not find {scenario_label!r} reference row in {REFERENCE_TABLE.name}")


def load_rows(path_sweep_table: Path, reference_direct_price: float) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    with path_sweep_table.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            price_direct = float(row["price_direct"])
            se_direct = float(row["se_direct"])
            rel_ci_lower, rel_ci_upper = rel_error_ci_bounds(price_direct, se_direct, reference_direct_price)
            rows.append(
                {
                    "paths": int(row["paths"]),
                    "method": row["method"],
                    "runtime_seconds": float(row["runtime_seconds"]),
                    "price_direct": price_direct,
                    "se_direct": se_direct,
                    "reference_direct_price": reference_direct_price,
                    "rel_error_direct": rel_error(price_direct, reference_direct_price),
                    "rel_ci_lower_direct": rel_ci_lower,
                    "rel_ci_upper_direct": rel_ci_upper,
                }
            )
    rows.sort(key=lambda item: (int(item["paths"]), str(item["method"])))
    return rows


def write_csv(output_table: Path, rows: list[dict[str, float | str]]) -> None:
    with output_table.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in CSV_COLUMNS})


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def render_figure(
    output_figure: Path,
    scenario_label: str,
    rows: list[dict[str, float | str]],
    reference: dict[str, float],
) -> None:
    width = 1260
    height = 760
    font = "Segoe UI, Arial, sans-serif"
    left = 115
    right = 1150
    top = 230
    bottom = 590
    chart_width = right - left
    chart_height = bottom - top
    legend_y = 190

    y_max = max(0.005, max(float(row["rel_ci_upper_direct"]) for row in rows) * 1.15)
    path_values = [int(row["paths"]) for row in rows]
    log_min = math.log10(min(path_values))
    log_max = math.log10(max(path_values))

    def x_of(paths: float) -> float:
        if log_max == log_min:
            return left + chart_width / 2.0
        return left + (math.log10(paths) - log_min) / (log_max - log_min) * chart_width

    def y_of(value: float) -> float:
        return bottom - value / y_max * chart_height

    method_styles = [
        ("benchmark", "#1d4ed8", "LSMC benchmark"),
        ("hybrid", "#d97706", "Hybrid LSMC-PDE"),
    ]

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f3efe7"/>',
        '<rect x="30" y="28" width="1200" height="704" rx="28" fill="#fffdf9" stroke="#ddd4c6"/>',
        f'<text x="72" y="88" font-family="{font}" font-size="31" font-weight="700" fill="#17202a">{scenario_label}: Direct relative error vs path count</text>',
        f'<text x="72" y="118" font-family="{font}" font-size="15" fill="#475569">Fixed reference is the 12-date, 1200-step, 1,200,000-path benchmark direct value from {REFERENCE_TABLE.name}.</text>',
        f'<text x="72" y="146" font-family="{font}" font-size="14" fill="#64748b">This reuses the saved {scenario_label} 48-step path sweep and recomputes direct relative errors against the updated benchmark reference.</text>',
        f'<text x="72" y="174" font-family="{font}" font-size="14" fill="#64748b">Benchmark direct reference: {reference["benchmark_direct_price"]:.6f} with SE {reference["benchmark_direct_error"]:.6f}. Path count varies on a log scale.</text>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="#334155" stroke-width="1.6"/>',
        f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="#334155" stroke-width="1.6"/>',
    ]

    y_ticks = [y_max * index / 5.0 for index in range(6)]
    for tick in y_ticks:
        y = y_of(tick)
        lines.append(f'<line x1="{left}" y1="{y:.2f}" x2="{right}" y2="{y:.2f}" stroke="#ece5d8" stroke-width="1"/>')
        lines.append(
            f'<text x="{left - 12}" y="{y + 5:.2f}" text-anchor="end" font-family="{font}" font-size="12" fill="#64748b">{100.0 * tick:.2f}%</text>'
        )

    for paths in path_values:
        x = x_of(float(paths))
        lines.append(f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{bottom}" stroke="#f3eee4" stroke-width="1"/>')
        lines.append(
            f'<text x="{x:.2f}" y="{bottom + 24}" text-anchor="end" transform="rotate(-35 {x:.2f} {bottom + 24})" font-family="{font}" font-size="11" fill="#64748b">{format_paths(paths)}</text>'
        )

    lines.append(
        f'<text x="{left - 78}" y="{top + chart_height / 2:.2f}" transform="rotate(-90 {left - 78} {top + chart_height / 2:.2f})" font-family="{font}" font-size="13" fill="#475569">Relative error</text>'
    )
    lines.append(
        f'<text x="{(left + right) / 2:.2f}" y="{bottom + 52}" text-anchor="middle" font-family="{font}" font-size="13" fill="#475569">Number of paths (log scale)</text>'
    )

    for legend_index, (method_key, color, label) in enumerate(method_styles):
        x0 = 72 + 330 * legend_index
        lines.append(f'<line x1="{x0}" y1="{legend_y}" x2="{x0 + 34}" y2="{legend_y}" stroke="{color}" stroke-width="4"/>')
        lines.append(f'<circle cx="{x0 + 17}" cy="{legend_y}" r="5.5" fill="{color}" stroke="#fffdf9" stroke-width="2"/>')
        lines.append(f'<text x="{x0 + 46}" y="{legend_y + 5}" font-family="{font}" font-size="14" fill="#334155">{label}</text>')

        method_rows = [row for row in rows if row["method"] == method_key]
        polyline = []
        for row in method_rows:
            polyline.append(f"{x_of(float(row['paths'])):.2f},{y_of(float(row['rel_error_direct'])):.2f}")
        lines.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" points="{" ".join(polyline)}"/>'
        )
        for row in method_rows:
            x = x_of(float(row["paths"]))
            y = y_of(float(row["rel_error_direct"]))
            y_low = y_of(float(row["rel_ci_lower_direct"]))
            y_high = y_of(float(row["rel_ci_upper_direct"]))
            lines.append(
                f'<line x1="{x:.2f}" y1="{y_high:.2f}" x2="{x:.2f}" y2="{y_low:.2f}" stroke="{color}" stroke-width="2.0" opacity="0.82"/>'
            )
            lines.append(
                f'<line x1="{x - 6:.2f}" y1="{y_high:.2f}" x2="{x + 6:.2f}" y2="{y_high:.2f}" stroke="{color}" stroke-width="2.0" opacity="0.82"/>'
            )
            lines.append(
                f'<line x1="{x - 6:.2f}" y1="{y_low:.2f}" x2="{x + 6:.2f}" y2="{y_low:.2f}" stroke="{color}" stroke-width="2.0" opacity="0.82"/>'
            )
            lines.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5.8" fill="{color}" stroke="#fffdf9" stroke-width="2"/>'
            )

    lines.append("</svg>")
    output_figure.write_text("\n".join(lines), encoding="utf-8")


def build_summary(
    scenario_label: str,
    output_figure: Path,
    output_table: Path,
    rows: list[dict[str, float | str]],
    reference: dict[str, float],
) -> str:
    table_rows = []
    for row in rows:
        table_rows.append(
            [
                f"`{int(row['paths']):,}`",
                f"`{row['method']}`",
                f"`{float(row['price_direct']):.6f}`",
                f"`{float(row['se_direct']):.6f}`",
                f"`{format_pct(float(row['rel_error_direct']))}`",
                f"`{float(row['runtime_seconds']):.2f} s`",
            ]
        )

    return "\n".join(
        [
            f"# BGK 12-date {scenario_label} Direct Path Sweep Rebased to the 1200-step Benchmark",
            "",
            f"This note reuses the saved {scenario_label} path sweep with Euler steps fixed at `48` and recomputes only the direct relative error.",
            "The updated reference is the benchmark-only run with `GDMR_EULER_STEPS=1200`, `GDMR_LSMC_PATHS=1200000`, and `GDMR_LSMC_LOW_PATHS=1200000`.",
            "",
            f"- Scenario: `{scenario_label}`",
            f"- Fixed benchmark direct reference: `{reference['benchmark_direct_price']:.6f}`",
            f"- Fixed benchmark direct reference SE: `{reference['benchmark_direct_error']:.6f}`",
            "- Euler steps in the path sweep: `48`",
            "- Path counts tested: `250, 500, 1000, 2000, 5000, 10000, 20000, 40000, 60000`",
            "",
            markdown_table(
                [
                    "Paths",
                    "Method",
                    "Direct price",
                    "Direct SE",
                    "Direct rel. error",
                    "Runtime",
                ],
                table_rows,
            ),
            "",
            f"![{scenario_label} direct relative error rebased to 1200-step benchmark]({output_figure})",
            "",
            f"Saved CSV: `{output_table.name}`",
        ]
    )


def main() -> None:
    args = parse_args()
    scenario = SCENARIOS[args.scenario]
    outputs = output_paths(scenario["slug"])
    reference = load_reference(scenario["label"])
    rows = load_rows(scenario["path_sweep_table"], reference["benchmark_direct_price"])
    write_csv(outputs["table"], rows)
    render_figure(outputs["figure"], scenario["label"], rows, reference)
    outputs["summary"].write_text(
        build_summary(scenario["label"], outputs["figure"], outputs["table"], rows, reference),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
