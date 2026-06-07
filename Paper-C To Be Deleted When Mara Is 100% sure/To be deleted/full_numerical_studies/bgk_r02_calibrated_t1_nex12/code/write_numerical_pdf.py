from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


RUN_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = RUN_ROOT.parents[2]
CONFIG_PATH = RUN_ROOT / "config" / "rerun_config.json"
RESULTS_DIR = RUN_ROOT / "results"
REFERENCE_DIR = RESULTS_DIR / "reference_values"
PATH_REFERENCE_DIR = REFERENCE_DIR / "path_sweep"
TABLE_DIR = RUN_ROOT / "tables"
FIGURE_DIR = RUN_ROOT / "figures"
TEX_DIR = RUN_ROOT / "tex"


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def finite(value: Any) -> float:
    return float(value)


def rel_range(rows: list[dict[str, str]], method: str) -> str:
    values = [100.0 * finite(row["rel_error_direct"]) for row in rows if row["method"] == method]
    return f"{min(values):.3f}\\%--{max(values):.3f}\\%"


def table_input(case_id: str, stem: str) -> str:
    return rf"\input{{../tables/{case_id}_{stem}}}"


def figure_input(case_id: str, stem: str, label: str, caption: str) -> str:
    return "\n".join(
        [
            r"\begin{figure}[htbp]",
            r"\centering",
            rf"\includegraphics[width=0.96\textwidth]{{../figures/{case_id}_{stem}.pdf}}",
            rf"\caption{{{caption}}}",
            rf"\label{{{label}}}",
            r"\end{figure}",
        ]
    )


def ensure_springer_class() -> None:
    TEX_DIR.mkdir(parents=True, exist_ok=True)
    source_root = PROJECT_ROOT / "Working Files" / "Manuscript Overleaf"
    for filename in ("sn-jnl.cls", "cuted.sty", "appendix.sty", "threeparttable.sty", "wrapfig.sty"):
        source = source_root / filename
        if not source.exists():
            raise FileNotFoundError(source)
        shutil.copy2(source, TEX_DIR / filename)


def write_tex() -> Path:
    config = load_config()
    case_id = config["case_id"]
    benchmark_csv = REFERENCE_DIR / f"{case_id}_benchmark_steps1200_paths1200000_table.csv"
    step20 = read_rows(REFERENCE_DIR / f"{case_id}_step_sweep_all_ref1200_direct_samepaths20k_s24487296_table.csv")
    step60 = read_rows(REFERENCE_DIR / f"{case_id}_step_sweep_all_ref1200_direct_samepaths60k_s24487296_table.csv")
    path48 = read_rows(PATH_REFERENCE_DIR / f"{case_id}_path_sweep_k100_steps48_direct_ref1200_paths1200000_table.csv")
    path60 = read_rows(PATH_REFERENCE_DIR / f"{case_id}_path_sweep_k100_steps60_direct_ref1200_paths1200000_table.csv")
    benchmark_rows = read_rows(benchmark_csv)

    benchmark_min = min(finite(row["benchmark_direct_price"]) for row in benchmark_rows)
    benchmark_max = max(finite(row["benchmark_direct_price"]) for row in benchmark_rows)
    title = "Standalone numerical study for the calibrated gDMR parameter set with positive rate"
    tex_path = TEX_DIR / f"main_numerical_study_{case_id}.tex"
    content = rf"""
\documentclass[pdflatex,sn-mathphys-num]{{sn-jnl}}

\usepackage{{graphicx}}
\usepackage{{amsmath,amssymb,amsfonts}}
\usepackage{{booktabs}}
\usepackage{{tabularx}}
\usepackage{{hyperref}}
\hypersetup{{hypertexnames=false}}

\raggedbottom

\begin{{document}}

\title[{title}]{{{title}}}

\author[1]{{\fnm{{Mara Kalicanin}} \sur{{Dimitrov}}}}
\author[1]{{\fnm{{Ying}} \sur{{Ni}}}}
\affil[1]{{\orgdiv{{Department of Business and Mathematics}}, \orgname{{M\"{{a}}lardalen University}}, \orgaddress{{\postcode{{721~23}}, \city{{V\"{{a}}ster{{\aa}}s}}, \country{{Sweden}}}}}}

\maketitle

\section{{Numerical studies}}

This standalone document repeats the manuscript numerical-study design for the calibrated gDMR parameter set reported in Table~\ref{{tab:{case_id}-experimental-setting}}, using the positive risk-free rate \(r=0.02\). The option is a Bermudan put with twelve exercise dates, maturity \(T=1\), and strikes \(K=70,80,90,100,110\). The direct plain LSMC estimator is compared with the Hybrid LSMC--PDE estimator. All prices, standard errors, confidence intervals, and relative errors are computed from the direct estimators, and benchmark-relative errors use the plain LSMC references in Table~\ref{{tab:{case_id}-benchmark-references}}.

{table_input(case_id, "experimental_setting_table")}

The benchmark references are obtained with \(1200\) Euler time steps and \(1,200,000\) direct paths. Across the five strikes, the benchmark direct prices range from {benchmark_min:.6f} to {benchmark_max:.6f}. These values define the reference scale used in the step-sweep and path-sweep experiments below.

{table_input(case_id, "benchmark_reference_table")}

\subsection{{Fixed path budget, varying number of Euler time steps}}

The first experiment keeps the direct path budget fixed and varies the number of Euler time steps. The two path budgets are \(20,000\) and \(60,000\), and both methods are evaluated at \(24\), \(48\), \(72\), and \(96\) steps. This isolates how the time discretization affects the direct Bermudan estimator away from the benchmark regime.

For \(20,000\) paths, the LSMC relative-error range over the full step-sweep grid is {rel_range(step20, "benchmark")}, while the Hybrid LSMC--PDE range is {rel_range(step20, "hybrid")}. Figure~\ref{{fig:{case_id}-step20k}} shows the strike-wise relative-error profiles, and Table~\ref{{tab:{case_id}-step72-20k}} reports the representative \(72\)-step values.

{figure_input(case_id, "step_sweep_20k_direct_relative_error", f"fig:{case_id}-step20k", r"Relative errors for the matched \(20{,}000\)-path step-sweep experiment. Error bars are induced by the \(95\%\) confidence intervals of the direct estimators.")}

{table_input(case_id, "step_sweep_20k_step72_table")}

For \(60,000\) paths, the same design gives an LSMC relative-error range of {rel_range(step60, "benchmark")} and a Hybrid LSMC--PDE range of {rel_range(step60, "hybrid")}. Figure~\ref{{fig:{case_id}-step60k}} and Table~\ref{{tab:{case_id}-step72-60k}} give the corresponding graphical and tabular summaries.

{figure_input(case_id, "step_sweep_60k_direct_relative_error", f"fig:{case_id}-step60k", r"Relative errors for the matched \(60{,}000\)-path step-sweep experiment. Error bars are induced by the \(95\%\) confidence intervals of the direct estimators.")}

{table_input(case_id, "step_sweep_60k_step72_table")}

\subsection{{Fixed number of Euler time steps, varying path counts}}

The second experiment fixes the number of Euler time steps and varies the direct path budget. The reported path grid is \(250\), \(1000\), \(5000\), \(10000\), \(20000\), \(40000\), and \(60000\). The two discretization levels are \(48\) and \(60\) steps.

At \(48\) steps for the at-the-money strike, the LSMC relative-error range over all path counts is {rel_range(path48, "benchmark")}, while the Hybrid LSMC--PDE range is {rel_range(path48, "hybrid")}. Figure~\ref{{fig:{case_id}-path48}} reports the full strike-wise path sweep, and Table~\ref{{tab:{case_id}-path48-path20k}} reports the \(20,000\)-path representative values.

{figure_input(case_id, "path_sweep_steps48_direct_relative_error", f"fig:{case_id}-path48", r"Relative errors for the fixed \(48\)-step path-sweep experiment. Error bars are induced by the \(95\%\) confidence intervals of the direct estimators.")}

{table_input(case_id, "path_sweep_steps48_path20k_table")}

At \(60\) steps for the at-the-money strike, the corresponding LSMC range is {rel_range(path60, "benchmark")}, and the Hybrid LSMC--PDE range is {rel_range(path60, "hybrid")}. Figure~\ref{{fig:{case_id}-path60}} and Table~\ref{{tab:{case_id}-path60-path20k}} provide the companion summaries.

{figure_input(case_id, "path_sweep_steps60_direct_relative_error", f"fig:{case_id}-path60", r"Relative errors for the fixed \(60\)-step path-sweep experiment. Error bars are induced by the \(95\%\) confidence intervals of the direct estimators.")}

{table_input(case_id, "path_sweep_steps60_path20k_table")}

The two experiment families provide a direct check of the pricing behavior under the calibrated positive-rate parameter set. The tables should be read together with the confidence intervals, since both methods retain finite Monte Carlo variability at the moderate path budgets used in the sweeps. The appendix-style tables below list the underlying prices used to form the figures and representative summaries.

\clearpage
\appendix
{table_input(case_id, "appendix_price_tables")}

\end{{document}}
"""
    tex_path.write_text(content.strip() + "\n", encoding="utf-8")
    return tex_path


def run_pdflatex(tex_path: Path) -> None:
    for index in range(2):
        completed = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
            cwd=str(TEX_DIR),
            capture_output=True,
            text=True,
            check=False,
        )
        (TEX_DIR / f"{tex_path.stem}_pdflatex{index + 1}.log.txt").write_text(
            completed.stdout + "\n\nSTDERR:\n" + completed.stderr,
            encoding="utf-8",
        )
        if completed.returncode != 0:
            raise RuntimeError(f"pdflatex failed for {tex_path}. See {tex_path.stem}_pdflatex{index + 1}.log.txt")


def main() -> None:
    ensure_springer_class()
    tex_path = write_tex()
    run_pdflatex(tex_path)
    print(f"[pdf] wrote {tex_path.with_suffix('.pdf')}")


if __name__ == "__main__":
    main()
