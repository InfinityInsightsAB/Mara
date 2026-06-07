#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
SUMMARY_PATH = THIS_DIR / "Summary.md"

FAMILIES = [
    {
        "title": "BGK `r=0.03`, `T=1`",
        "summary_label": "This family uses the BGK model block with `GDMR_R=0.03` and `GDMR_MATURITY=1.0`.",
        "results_table": THIS_DIR / "bgk_r03_comparison_table.csv",
    },
    {
        "title": "BGK `r=0`, `T=2`",
        "summary_label": "This family uses the BGK model block with `GDMR_R=0.0` and `GDMR_MATURITY=2.0`.",
        "results_table": THIS_DIR / "bgk_r00_t2_comparison_table.csv",
    },
    {
        "title": "BGK `r=0`, `T=1`, `delta1=delta2=0.5`",
        "summary_label": "This family uses the BGK model block with `GDMR_R=0.0`, `GDMR_MATURITY=1.0`, and equal deltas `GDMR_DELTA1=GDMR_DELTA2=0.5`.",
        "results_table": THIS_DIR / "bgk_r00_t1_delta05_comparison_table.csv",
    },
]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def format_price_row(row: dict[str, str]) -> str:
    return (
        f"| {row['scenario']} | `{float(row['S0']):.0f}` | `{float(row['K']):.0f}` | `{float(row['T']):.0f}` | "
        f"`{float(row['benchmark_direct_price']):.6f}` | `{float(row['benchmark_direct_error']):.6f}` | "
        f"`{float(row['benchmark_low_price']):.6f}` | `{float(row['benchmark_low_error']):.6f}` | "
        f"`{float(row['hybrid_direct_price']):.6f}` | `{float(row['hybrid_direct_error']):.6f}` | "
        f"`{float(row['hybrid_low_price']):.6f}` | `{float(row['hybrid_low_error']):.6f}` | "
        f"`{100.0 * float(row['hybrid_direct_rel_error']):.3f}%` | "
        f"`{100.0 * float(row['hybrid_low_rel_error']):.3f}%` | "
        f"`{100.0 * float(row['benchmark_direct_low_gap']):+.3f}%` | "
        f"`{100.0 * float(row['hybrid_direct_low_gap']):+.3f}%` |"
    )


def build_table(rows: list[dict[str, str]]) -> str:
    header = [
        "| Scenario | `S0` | `K` | `T` | Benchmark direct | Benchmark direct SE | Benchmark low | Benchmark low SE | Hybrid direct | Hybrid direct SE | Hybrid low | Hybrid low SE | Hybrid direct rel. err. | Hybrid low rel. err. | Benchmark direct-low gap | Hybrid direct-low gap |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    return "\n".join(header + [format_price_row(row) for row in rows])


def build_notes(rows: list[dict[str, str]]) -> list[str]:
    notes: list[str] = []
    for row in rows:
        notes.append(
            "- {scenario}: hybrid direct rel. err. `{direct:.3f}%`, hybrid low rel. err. `{low:.3f}%`, "
            "benchmark direct-low gap `{bg:+.3f}%`, hybrid direct-low gap `{hy:+.3f}%`.".format(
                scenario=row["scenario"],
                direct=100.0 * float(row["hybrid_direct_rel_error"]),
                low=100.0 * float(row["hybrid_low_rel_error"]),
                bg=100.0 * float(row["benchmark_direct_low_gap"]),
                hy=100.0 * float(row["hybrid_direct_low_gap"]),
            )
        )
    return notes


def build_family_section(family: dict[str, object]) -> str:
    result_rows = read_rows(family["results_table"])
    lines = [
        f"## {family['title']}",
        "",
        str(family["summary_label"]),
        "",
        "### Results",
        "",
        build_table(result_rows),
        "",
        "Observations:",
    ]
    lines.extend(build_notes(result_rows))
    lines.extend(
        [
            "",
            "Files used:",
            f"- `{Path(family['results_table']).name}`",
            "",
        ]
    )
    return "\n".join(lines)


def build_summary() -> str:
    sections = [
        "# Summary",
        "",
        "This file summarizes the main experiment results currently stored in `Final Code/More Experiments`.",
        "Smoke runs are kept as validation artifacts in the folder, but they are intentionally omitted from this summary.",
        "",
        "Operational artifacts such as runner scripts, `_scratch`, and inaccessible `tmp...` directories are intentionally excluded.",
        "",
    ]
    for family in FAMILIES:
        sections.append(build_family_section(family))
    return "\n".join(sections).rstrip() + "\n"


def main() -> None:
    SUMMARY_PATH.write_text(build_summary(), encoding="utf-8")
    print(f"Summary saved to: {SUMMARY_PATH.name}")


if __name__ == "__main__":
    main()
