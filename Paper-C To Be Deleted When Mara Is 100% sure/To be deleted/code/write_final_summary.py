from __future__ import annotations

import csv
import math
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
SUMMARY = ROOT / "summary"
TEX = SUMMARY / "delta05_diagnostic_summary.tex"


def rows(name: str) -> list[dict[str, str]]:
    path = RESULTS / name
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def f(value: Any, digits: int = 3) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return ""


def pct(value: Any, digits: int = 1) -> str:
    try:
        return f"{100.0 * float(value):.{digits}f}%"
    except Exception:
        return ""


def esc(value: Any) -> str:
    text = str(value)
    return (
        text.replace("\\", "\\textbackslash{}")
        .replace("_", "\\_")
        .replace("&", "\\&")
        .replace("%", "\\%")
    )


def table(headers: list[str], body: list[list[Any]], align: str | None = None) -> str:
    align = align or ("l" * len(headers))
    lines = [f"\\begin{{tabular}}{{{align}}}", "\\toprule"]
    lines.append(" & ".join(headers) + r" \\")
    lines.append("\\midrule")
    for row in body:
        lines.append(" & ".join(esc(v) for v in row) + r" \\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    return "\n".join(lines)


def by_key(data: list[dict[str, str]], **conds: str) -> list[dict[str, str]]:
    out = data
    for key, value in conds.items():
        out = [row for row in out if row.get(key) == value]
    return out


def first(data: list[dict[str, str]], **conds: str) -> dict[str, str] | None:
    subset = by_key(data, **conds)
    return subset[0] if subset else None


def price(data: list[dict[str, str]], **conds: str) -> float | None:
    row = first(data, **conds)
    if row is None:
        return None
    return float(row["price_direct"])


def lsmc_table() -> str:
    data = rows("lsmc_convergence.csv")
    body: list[list[Any]] = []
    for paths in ["60000", "600000"]:
        for m in ["48", "96", "240", "600", "1200"]:
            row = first(data, K="100", paths=paths, euler_steps=m, seed="2026")
            if row:
                body.append([m, paths, f(row["price_direct"]), f(row["se_direct"]), f(row["price_low"]), f(row["direct_low_gap"], 4)])
    for k in ["70", "110"]:
        for m in ["48", "1200"]:
            row = first(data, K=k, paths="60000", euler_steps=m, seed="2026")
            if row:
                body.append([f"K={k}, M={m}", "60000", f(row["price_direct"]), f(row["se_direct"]), f(row["price_low"]), f(row["direct_low_gap"], 4)])
    return table(["Case/M", "N", "Direct", "SE", "Low", "Gap"], body, "llllll")


def targeted_figure5_table() -> tuple[str, float, float, float | None]:
    data = rows("lsmc_m100_n500k_figure5_benchmark.csv")
    body: list[list[Any]] = []
    rel_errors: list[float] = []
    atm_price: float | None = None
    for row in sorted(data, key=lambda item: float(item["K"])):
        rel = float(row["rel_error_direct"])
        rel_errors.append(rel)
        if row["K"] == "100":
            atm_price = float(row["price_direct"])
        body.append(
            [
                row["K"],
                f(row["price_direct"]),
                f(row["se_direct"]),
                f(row["benchmark_direct_price"]),
                f(100.0 * rel, 2) + "%",
                f(row["price_low"]),
                f(row["direct_low_gap"], 4),
            ]
        )
    if not body:
        return table(["K", "Direct", "SE", "Figure 5 ref.", "Rel. error", "Low", "Gap"], body, "lllllll"), math.nan, math.nan, None
    return (
        table(["K", "Direct", "SE", "Figure 5 ref.", "Rel. error", "Low", "Gap"], body, "lllllll"),
        min(rel_errors),
        max(rel_errors),
        atm_price,
    )


def fresh_m500_table() -> tuple[str, float | None, float | None, float | None, float | None]:
    data = rows("lsmc_m500_n1200k_benchmark_compare.csv")
    body: list[list[Any]] = []
    k90_rel: float | None = None
    k100_rel: float | None = None
    k90_bench: float | None = None
    k100_bench: float | None = None
    for row in sorted(data, key=lambda item: float(item["K"])):
        rel = float(row["rel_error_m100_vs_m500"])
        if row["K"] == "90":
            k90_rel = rel
            k90_bench = float(row["benchmark_price_direct"])
        if row["K"] == "100":
            k100_rel = rel
            k100_bench = float(row["benchmark_price_direct"])
        diff = float(row["comparison_price_direct"]) - float(row["benchmark_price_direct"])
        body.append(
            [
                row["K"],
                f(row["comparison_price_direct"]),
                f(row["comparison_se_direct"]),
                f(row["benchmark_price_direct"]),
                f(row["benchmark_se_direct"]),
                f(diff),
                f(100.0 * rel, 2) + "%",
            ]
        )
    return table(["K", "M=100 price", "SE", "M=500 bench.", "SE", "Diff.", "Rel. diff."], body, "lllllll"), k90_rel, k100_rel, k90_bench, k100_bench


def policy_table() -> tuple[str, float]:
    data = rows("policy_diagnostic.csv")
    body: list[list[Any]] = []
    max_diff = 0.0
    for k in ["70", "100", "110"]:
        for m in ["48", "1200"]:
            all_row = first(data, K=k, euler_steps=m, paths="60000", policy="all_paths")
            itm_row = first(data, K=k, euler_steps=m, paths="60000", policy="itm_only")
            if all_row and itm_row:
                diff = float(itm_row["price_direct"]) - float(all_row["price_direct"])
                max_diff = max(max_diff, abs(diff))
                body.append([k, m, f(all_row["price_direct"]), f(itm_row["price_direct"]), f(diff), f(all_row["se_direct"])])
    return table(["K", "M", "All-path", "ITM-only", "Diff.", "SE"], body, "llllll"), max_diff


def euler_table() -> tuple[str, float, float]:
    data = sorted(rows("euler_boundary.csv"), key=lambda row: int(row["euler_steps"]))
    body: list[list[Any]] = []
    eur48 = math.nan
    eur1200 = math.nan
    for row in data:
        m = row["euler_steps"]
        if m == "48":
            eur48 = float(row["european_put_k100"])
        if m == "1200":
            eur1200 = float(row["european_put_k100"])
        body.append(
            [
                m,
                pct(row["neg_raw_v_rate"], 1),
                pct(row["zero_v_rate"], 1),
                pct(row["neg_raw_vp_rate"], 1),
                pct(row["zero_vp_rate"], 1),
                f(row["european_put_k100"]),
                f(row["se_put_k100"]),
            ]
        )
    return table(["M", "neg v", "zero v", "neg v'", "zero v'", "Eur K=100", "SE"], body, "lllllll"), eur48, eur1200


def hybrid_table() -> tuple[str, float, float]:
    data = rows("hybrid_sensitivity.csv")
    body: list[list[Any]] = []
    ranges: list[float] = []
    for m in ["48", "96", "240"]:
        subset = by_key(data, K="100", euler_steps=m, paths="20000")
        if subset:
            prices = [float(row["price_direct"]) for row in subset]
            ranges.append(max(prices) - min(prices))
            default = first(subset, grid_label="default") or subset[0]
            body.append([f"K=100, M={m}", "20000", f(default["price_direct"]), f(default["se_direct"]), f(min(prices)), f(max(prices)), f(max(prices) - min(prices))])
    for k in ["70", "110"]:
        for m in ["48", "96"]:
            row = first(data, K=k, euler_steps=m, paths="20000", grid_label="default")
            if row:
                body.append([f"K={k}, M={m}", "20000", f(row["price_direct"]), f(row["se_direct"]), "-", "-", "-"])
    row48 = first(data, K="100", euler_steps="48", paths="60000", grid_label="default")
    row96 = first(data, K="100", euler_steps="96", paths="60000", grid_label="default")
    if row48:
        body.append(["K=100, M=48", "60000", f(row48["price_direct"]), f(row48["se_direct"]), "-", "-", "-"])
    if row96:
        body.append(["K=100, M=96", "60000", f(row96["price_direct"]), f(row96["se_direct"]), "-", "-", "-"])
    max_range = max(ranges) if ranges else math.nan
    m48 = float(row48["price_direct"]) if row48 else math.nan
    m96 = float(row96["price_direct"]) if row96 else math.nan
    return table(["Case", "N", "Default", "SE", "Min grid", "Max grid", "Range"], body, "lllllll"), max_range, abs(m48 - m96)


def parity_sentence() -> str:
    row = first(rows("parity.csv"), study="parity")
    if not row:
        return "The sandbox parity row is missing."
    return (
        f"The sandbox value for K=100, M=48, N=60,000 is {f(row['price_direct'], 12)}, "
        f"and the manuscript CSV value is {f(row['manuscript_price_direct'], 12)}; "
        f"the absolute difference is {f(row['abs_price_difference_from_manuscript'], 12)}."
    )


def write() -> None:
    SUMMARY.mkdir(parents=True, exist_ok=True)
    lsmc = rows("lsmc_convergence.csv")
    k100_m48 = price(lsmc, K="100", euler_steps="48", paths="60000", seed="2026")
    k100_m1200 = price(lsmc, K="100", euler_steps="1200", paths="60000", seed="2026")
    k100_m48_600k = price(lsmc, K="100", euler_steps="48", paths="600000", seed="2026")
    lsmc_drift = abs(k100_m48 - k100_m1200) if k100_m48 is not None and k100_m1200 is not None else math.nan
    path_shift = abs(k100_m48 - k100_m48_600k) if k100_m48 is not None and k100_m48_600k is not None else math.nan
    policy, max_policy = policy_table()
    euler, eur48, eur1200 = euler_table()
    hybrid, max_grid_range, hybrid_m_shift = hybrid_table()
    targeted, targeted_min_rel, targeted_max_rel, targeted_atm = targeted_figure5_table()
    fresh_m500, k90_m500_rel, k100_m500_rel, k90_m500_bench, k100_m500_bench = fresh_m500_table()
    targeted_sentence = ""
    if targeted_atm is not None and math.isfinite(targeted_min_rel) and math.isfinite(targeted_max_rel):
        targeted_sentence = (
            f" The targeted Figure 5 benchmark check at M=100 and N=500,000 gives K=100 price {targeted_atm:.3f}; "
            f"across strikes its relative errors remain between {100.0 * targeted_min_rel:.2f}% and {100.0 * targeted_max_rel:.2f}%."
        )
    fresh_sentence = ""
    if k90_m500_rel is not None and k100_m500_rel is not None and k90_m500_bench is not None and k100_m500_bench is not None:
        fresh_sentence = (
            f" Against fresh M=500, N=1,200,000 benchmarks, the same M=100 prices have relative errors {100.0 * k90_m500_rel:.2f}% for K=90 and {100.0 * k100_m500_rel:.2f}% for K=100 "
            f"(fresh benchmarks {k90_m500_bench:.3f} and {k100_m500_bench:.3f})."
        )
    conclusion = (
        f"The diagnostics do not support a stale benchmark or wrong-parameter explanation. {parity_sentence()} "
        f"For K=100, plain LSMC changes by {lsmc_drift:.3f} between M=48 and M=1200 at N=60,000, while increasing paths at M=48 from 60,000 to 600,000 changes the price by {path_shift:.3f}. "
        + targeted_sentence
        + fresh_sentence
        + " "
        f"The all-path versus ITM-only policy effect is at most {max_policy:.3f}. "
        f"The forward European K=100 diagnostic moves from {eur48:.3f} at M=48 to {eur1200:.3f} at M=1200, before any Bermudan regression. "
        f"Hybrid grid changes are small by comparison, with maximum K=100 grid range {max_grid_range:.3f}; the default Hybrid K=100 price changes by {hybrid_m_shift:.3f} from M=48 to M=96 at N=60,000. "
        "The dominant source is therefore Euler time-discretization/full-truncation bias in the square-root variance case."
    )
    tex = r"""\documentclass{article}
\usepackage[margin=0.8in]{geometry}
\usepackage{booktabs}
\usepackage{array}
\begin{document}
\section*{Delta 0.5 diagnostic summary}
\textbf{Case.} $r=0.02$, $\delta_1=\delta_2=0.5$, $T=1$, $N_{\mathrm{ex}}=12$, $v_0=0.114$, $v'_0=0.110$. All outputs are under \texttt{D:/Mara PhD/Paper-C/To be deleted}.

\paragraph{Conclusion.}
""" + conclusion + r"""

\paragraph{LSMC step and path convergence.}
Low denotes the independent validation estimator reported by the copied LSMC engine; Gap is $|\mathrm{direct}-\mathrm{low}|/|\mathrm{direct}|$.

""" + lsmc_table() + r"""

\paragraph{Targeted Figure 5 benchmark check.}
The benchmark values are the direct LSMC references used for Figure 5 of \texttt{main\_springer.pdf}: $M_{\mathrm{ref}}=1200$ and $N_{\mathrm{ref}}=1{,}200{,}000$. The new run uses plain LSMC with $M=100$ and $N=500{,}000$.

""" + targeted + r"""

\paragraph{Fresh M=500 benchmark check.}
This compares the targeted $M=100$, $N=500{,}000$ plain LSMC prices against new plain LSMC benchmarks generated in this sandbox with $M=500$ and $N=1{,}200{,}000$ for $K=90$ and $K=100$.

""" + fresh_m500 + r"""

\paragraph{All-path versus ITM-only policy.}

""" + policy + r"""

\paragraph{Forward Euler boundary diagnostic.}
This is a terminal European put diagnostic, so it does not use Bermudan regression.

""" + euler + r"""

\paragraph{Hybrid-PDE sensitivity.}
For K=100 and N=20,000, Min grid and Max grid are the range across default, expanded, wide, and q995 grids. Other rows report the default grid.

""" + hybrid + r"""

\paragraph{Recommendation.}
Do not treat the large relative errors as a path-count failure or a benchmark-file mismatch. If this parameter case remains in the manuscript, it should be framed as a stress test showing sensitivity of the square-root case to the Euler time step, or rerun with a finer-step design and a discretization scheme better suited to the boundary.

\end{document}
"""
    TEX.write_text(tex, encoding="utf-8")


def compile_pdf() -> None:
    try:
        subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", TEX.name],
            cwd=str(SUMMARY),
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return


if __name__ == "__main__":
    write()
    compile_pdf()
