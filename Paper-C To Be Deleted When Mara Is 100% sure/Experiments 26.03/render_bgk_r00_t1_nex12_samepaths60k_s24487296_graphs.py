#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
DEFAULT_PATHS = 60000

SCENARIO_ORDER = ["ITM put", "ATM", "OTM put", "K=80 put", "K=70 put"]
STEP_COUNTS = [24, 48, 72, 96]
METHODS = [
    ("benchmark", "#1d4ed8", "LSMC"),
    ("hybrid", "#d97706", "Hybrid LSMC-PDE"),
]

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render the combined same-path sweep graphs for a chosen matched path count."
    )
    parser.add_argument("--paths", type=int, default=DEFAULT_PATHS)
    return parser.parse_args()


def paths_tag(path_count: int) -> str:
    if path_count % 1000 == 0:
        return f"{path_count // 1000}k"
    return str(path_count)


def stem(path_count: int) -> str:
    return f"bgk_r00_t1_nex12_step_sweep_all_ref1200_direct_samepaths{paths_tag(path_count)}_s24487296"


def input_table(path_count: int) -> Path:
    return THIS_DIR / f"{stem(path_count)}_table.csv"


def metrics_for(path_count: int) -> list[dict[str, object]]:
    stem_name = stem(path_count)
    return [
        {
            "key": "rel_error_direct",
            "filename": f"{stem_name}_relative_error.svg",
            "title": "Equal-path sweep: Direct relative error",
            "subtitle": f"Same {path_count:,} direct paths for LSMC and Hybrid; values shown as percentages against the fixed 1200-step references.",
            "y_label": "Direct relative error (%)",
            "formatter": lambda value: f"{value:.2f}%",
            "transform": lambda value: 100.0 * value,
            "log_scale": False,
        },
        {
            "key": "se_direct",
            "filename": f"{stem_name}_se.svg",
            "title": "Equal-path sweep: Standard error",
            "subtitle": "Direct-estimator standard errors under matched path budgets.",
            "y_label": "Direct standard error",
            "formatter": lambda value: f"{value:.3f}",
            "transform": lambda value: value,
            "log_scale": False,
        },
        {
            "key": "ci_width_direct",
            "filename": f"{stem_name}_ci_width.svg",
            "title": "Equal-path sweep: 95% CI width",
            "subtitle": "Width of the direct-estimator 95% confidence interval: 2 x 1.96 x SE.",
            "y_label": "95% CI width",
            "formatter": lambda value: f"{value:.3f}",
            "transform": lambda value: value,
            "log_scale": False,
        },
        {
            "key": "runtime_seconds",
            "filename": f"{stem_name}_runtime.svg",
            "title": "Equal-path sweep: Runtime",
            "subtitle": "Wall-clock runtime by step count. The vertical axis uses a log scale so both methods remain visible.",
            "y_label": "Runtime (seconds, log scale)",
            "formatter": lambda value: f"{value:.2f} s" if value < 10 else f"{value:.0f} s",
            "transform": lambda value: value,
            "log_scale": True,
        },
    ]


def load_rows(path_count: int) -> dict[str, dict[str, dict[int, dict[str, float | str]]]]:
    rows: dict[str, dict[str, dict[int, dict[str, float | str]]]] = {
        scenario: {} for scenario in SCENARIO_ORDER
    }
    with input_table(path_count).open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            scenario = row["scenario"]
            method = row["method"]
            step = int(row["euler_steps"])
            rows.setdefault(scenario, {}).setdefault(method, {})[step] = row
    return rows


def render_svg(
    rows: dict[str, dict[str, dict[int, dict[str, float | str]]]],
    metric: dict[str, object],
    path_count: int,
) -> None:
    width = 1440
    height = 1120
    font = "Segoe UI, Arial, sans-serif"
    outer_left = 48
    outer_top = 170
    outer_right = width - 48
    outer_bottom = height - 42
    gutter_x = 32
    gutter_y = 28
    cols = 2
    panel_width = (outer_right - outer_left - gutter_x) / cols
    panel_height = 270

    def panel_rect(index: int) -> tuple[float, float, float, float]:
        row = index // cols
        col = index % cols
        x = outer_left + col * (panel_width + gutter_x)
        y = outer_top + row * (panel_height + gutter_y)
        return x, y, panel_width, panel_height

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f3efe7"/>',
        '<rect x="20" y="20" width="1400" height="1080" rx="28" fill="#fffdf9" stroke="#ddd4c6"/>',
        f'<text x="56" y="78" font-family="{font}" font-size="31" font-weight="700" fill="#17202a">{metric["title"]}</text>',
        f'<text x="56" y="108" font-family="{font}" font-size="15" fill="#475569">{metric["subtitle"]}</text>',
        f'<text x="56" y="132" font-family="{font}" font-size="13" fill="#64748b">Strikes: 110, 100, 90, 80, 70. Euler steps: 24, 48, 72, 96. Both methods use {path_count:,} direct paths.</text>',
    ]

    legend_y = 146
    for legend_index, (_, color, label) in enumerate(METHODS):
        x0 = 900 + 180 * legend_index
        lines.append(f'<line x1="{x0}" y1="{legend_y}" x2="{x0 + 32}" y2="{legend_y}" stroke="{color}" stroke-width="4"/>')
        lines.append(f'<circle cx="{x0 + 16}" cy="{legend_y}" r="5.5" fill="{color}" stroke="#fffdf9" stroke-width="2"/>')
        lines.append(f'<text x="{x0 + 42}" y="{legend_y + 5}" font-family="{font}" font-size="14" fill="#334155">{label}</text>')

    for panel_index, scenario in enumerate(SCENARIO_ORDER):
        x, y, w, h = panel_rect(panel_index)
        lines.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="20" fill="#fffaf0" stroke="#e5dccd"/>')
        lines.append(f'<text x="{x + 18:.1f}" y="{y + 28:.1f}" font-family="{font}" font-size="18" font-weight="700" fill="#17202a">{scenario}</text>')

        chart_left = x + 68
        chart_right = x + w - 28
        chart_top = y + 48
        chart_bottom = y + h - 44
        chart_width = chart_right - chart_left
        chart_height = chart_bottom - chart_top

        values = []
        for method_key, _, _ in METHODS:
            for step in STEP_COUNTS:
                raw = rows[scenario][method_key][step]
                value = float(raw[metric["key"]])  # type: ignore[index]
                values.append(metric["transform"](value))  # type: ignore[index]

        if metric["log_scale"]:
            min_value = max(min(values), 1e-6)
            max_value = max(values)
            log_min = math.floor(math.log10(min_value))
            log_max = math.ceil(math.log10(max_value))

            def y_of(value: float) -> float:
                clipped = max(value, 10 ** log_min)
                if log_max == log_min:
                    return chart_bottom - chart_height / 2.0
                return chart_bottom - (math.log10(clipped) - log_min) / (log_max - log_min) * chart_height

            tick_values = [10 ** exponent for exponent in range(log_min, log_max + 1)]
            for tick in tick_values:
                y_tick = y_of(tick)
                lines.append(f'<line x1="{chart_left:.1f}" y1="{y_tick:.1f}" x2="{chart_right:.1f}" y2="{y_tick:.1f}" stroke="#ece5d8" stroke-width="1"/>')
                tick_label = metric["formatter"](tick)  # type: ignore[index]
                lines.append(f'<text x="{chart_left - 10:.1f}" y="{y_tick + 5:.1f}" text-anchor="end" font-family="{font}" font-size="11" fill="#64748b">{tick_label}</text>')
        else:
            y_min = 0.0
            y_max = max(values) * 1.12 if max(values) > 0 else 1.0

            def y_of(value: float) -> float:
                return chart_bottom - (value - y_min) / (y_max - y_min) * chart_height

            for tick_index in range(6):
                tick = y_min + (y_max - y_min) * tick_index / 5.0
                y_tick = y_of(tick)
                lines.append(f'<line x1="{chart_left:.1f}" y1="{y_tick:.1f}" x2="{chart_right:.1f}" y2="{y_tick:.1f}" stroke="#ece5d8" stroke-width="1"/>')
                tick_label = metric["formatter"](tick)  # type: ignore[index]
                lines.append(f'<text x="{chart_left - 10:.1f}" y="{y_tick + 5:.1f}" text-anchor="end" font-family="{font}" font-size="11" fill="#64748b">{tick_label}</text>')

        def x_of(step: int) -> float:
            return chart_left + (step - STEP_COUNTS[0]) / (STEP_COUNTS[-1] - STEP_COUNTS[0]) * chart_width

        lines.append(f'<line x1="{chart_left:.1f}" y1="{chart_top:.1f}" x2="{chart_left:.1f}" y2="{chart_bottom:.1f}" stroke="#334155" stroke-width="1.5"/>')
        lines.append(f'<line x1="{chart_left:.1f}" y1="{chart_bottom:.1f}" x2="{chart_right:.1f}" y2="{chart_bottom:.1f}" stroke="#334155" stroke-width="1.5"/>')

        for step in STEP_COUNTS:
            x_tick = x_of(step)
            lines.append(f'<line x1="{x_tick:.1f}" y1="{chart_top:.1f}" x2="{x_tick:.1f}" y2="{chart_bottom:.1f}" stroke="#f3eee4" stroke-width="1"/>')
            lines.append(f'<text x="{x_tick:.1f}" y="{chart_bottom + 22:.1f}" text-anchor="middle" font-family="{font}" font-size="11" fill="#64748b">{step}</text>')

        if panel_index % cols == 0:
            lines.append(
                f'<text x="{chart_left - 52:.1f}" y="{chart_top + chart_height / 2:.1f}" transform="rotate(-90 {chart_left - 52:.1f} {chart_top + chart_height / 2:.1f})" font-family="{font}" font-size="12" fill="#475569">{metric["y_label"]}</text>'
            )
        if panel_index >= 4:
            lines.append(f'<text x="{(chart_left + chart_right) / 2:.1f}" y="{chart_bottom + 40:.1f}" text-anchor="middle" font-family="{font}" font-size="12" fill="#475569">Euler steps</text>')

        for method_key, color, _ in METHODS:
            polyline = []
            for step in STEP_COUNTS:
                raw = rows[scenario][method_key][step]
                value = metric["transform"](float(raw[metric["key"]]))  # type: ignore[index]
                polyline.append(f"{x_of(step):.1f},{y_of(value):.1f}")
            lines.append(
                f'<polyline fill="none" stroke="{color}" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" points="{" ".join(polyline)}"/>'
            )
            for step in STEP_COUNTS:
                raw = rows[scenario][method_key][step]
                value = metric["transform"](float(raw[metric["key"]]))  # type: ignore[index]
                lines.append(f'<circle cx="{x_of(step):.1f}" cy="{y_of(value):.1f}" r="5.3" fill="{color}" stroke="#fffdf9" stroke-width="2"/>')

    note_x, note_y, note_w, note_h = panel_rect(5)
    lines.append(f'<rect x="{note_x:.1f}" y="{note_y:.1f}" width="{note_w:.1f}" height="{note_h:.1f}" rx="20" fill="#f7f1e4" stroke="#e5dccd"/>')
    lines.append(f'<text x="{note_x + 20:.1f}" y="{note_y + 34:.1f}" font-family="{font}" font-size="18" font-weight="700" fill="#17202a">Reading note</text>')
    notes = [
        "Hybrid is most favorable in the middle of the step grid.",
        "48 to 72 steps is the strongest region in the combined study.",
        "SE and CI width stay much smaller for Hybrid at the same paths.",
        "Runtime still strongly favors LSMC.",
    ]
    for index, note in enumerate(notes):
        lines.append(f'<text x="{note_x + 20:.1f}" y="{note_y + 72 + 28 * index:.1f}" font-family="{font}" font-size="14" fill="#475569">{note}</text>')

    lines.append("</svg>")
    (THIS_DIR / metric["filename"]).write_text("\n".join(lines), encoding="utf-8")  # type: ignore[index]


def main() -> None:
    args = parse_args()
    rows = load_rows(args.paths)
    for metric in metrics_for(args.paths):
        render_svg(rows, metric, args.paths)
    print(f"Combined same-path graphs rendered for {args.paths} paths.")


if __name__ == "__main__":
    main()
