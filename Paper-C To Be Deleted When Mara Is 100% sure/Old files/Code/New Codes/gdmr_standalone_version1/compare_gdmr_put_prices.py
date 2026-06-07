import os
import re
import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt


THIS_DIR = Path(__file__).resolve().parent
BENCHMARK_SCRIPT = THIS_DIR / "run_gdmr_benchmark_put.py"
HYBRID_SCRIPT = THIS_DIR / "run_gdmr_hybrid_put.py"
OUTPUT_SVG = THIS_DIR / "compare_gdmr_put_prices.svg"
OUTPUT_MD = THIS_DIR / "gdmr_compare_summary.md"


BENCHMARK_PATTERNS = {
    "lsmc_direct_price": r"LSMC direct price:\s*([0-9eE+\-.]+)",
    "lsmc_direct_error": r"LSMC direct error:\s*([0-9eE+\-.]+)",
    "lsmc_low_price": r"LSMC low price:\s*([0-9eE+\-.]+)",
    "lsmc_low_error": r"LSMC low error:\s*([0-9eE+\-.]+)",
}

HYBRID_PATTERNS = {
    "hybrid_direct_price": r"Hybrid direct price:\s*([0-9eE+\-.]+)",
    "hybrid_direct_error": r"Hybrid direct error:\s*([0-9eE+\-.]+)",
    "hybrid_low_price": r"Hybrid low price:\s*([0-9eE+\-.]+)",
    "hybrid_low_error": r"Hybrid low error:\s*([0-9eE+\-.]+)",
}



def parse_numbers(text: str, patterns: dict[str, str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if not match:
            raise RuntimeError(f"Could not parse '{key}' from output:\n{text}")
        out[key] = float(match.group(1))
    return out



def rel_error(value: float, reference: float) -> float:
    if abs(reference) <= 1e-16:
        return 0.0 if abs(value) <= 1e-16 else float("inf")
    return abs(value - reference) / abs(reference)



def run_script(path: Path, patterns: dict[str, str]) -> tuple[str, dict[str, float]]:
    completed = subprocess.run(
        [sys.executable, str(path)],
        cwd=str(THIS_DIR),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=True,
    )
    stdout = completed.stdout.strip()
    return stdout, parse_numbers(stdout, patterns)



def save_plot(values: dict[str, float]) -> None:
    labels = [
        "LSMC direct",
        "LSMC low",
        "Hybrid direct",
        "Hybrid low",
    ]
    estimates = [
        values["lsmc_direct_price"],
        values["lsmc_low_price"],
        values["hybrid_direct_price"],
        values["hybrid_low_price"],
    ]
    errors = [
        values["lsmc_direct_error"],
        values["lsmc_low_error"],
        values["hybrid_direct_error"],
        values["hybrid_low_error"],
    ]
    xs = list(range(len(labels)))

    plt.figure(figsize=(9, 5.5))
    plt.errorbar(xs, estimates, yerr=errors, fmt="o", capsize=5)
    plt.axhline(values["lsmc_direct_price"], linewidth=1.5, linestyle="--")
    plt.xticks(xs, labels, rotation=15)
    plt.ylabel("Bermudan put estimate")
    plt.title("gDMR Bermudan put: LSMC benchmark vs hybrid LSMC-PDE")
    plt.tight_layout()
    plt.savefig(OUTPUT_SVG, format="svg")
    plt.close()



def save_markdown(values: dict[str, float], benchmark_stdout: str, hybrid_stdout: str) -> None:
    hybrid_direct_vs_lsmc_direct = rel_error(values["hybrid_direct_price"], values["lsmc_direct_price"])
    hybrid_low_vs_lsmc_direct = rel_error(values["hybrid_low_price"], values["lsmc_direct_price"])
    hybrid_low_vs_lsmc_low = rel_error(values["hybrid_low_price"], values["lsmc_low_price"])

    text = f"""# gDMR comparison summary

## Headline numbers

- LSMC direct = `{values['lsmc_direct_price']:.6f}`
- LSMC low = `{values['lsmc_low_price']:.6f}`
- Hybrid direct = `{values['hybrid_direct_price']:.6f}`
- Hybrid low = `{values['hybrid_low_price']:.6f}`
- Hybrid direct relative error vs LSMC direct = `{100.0 * hybrid_direct_vs_lsmc_direct:.2f}%`
- Hybrid low relative error vs LSMC direct = `{100.0 * hybrid_low_vs_lsmc_direct:.2f}%`
- Hybrid low relative error vs LSMC low = `{100.0 * hybrid_low_vs_lsmc_low:.2f}%`

## Standard errors

- LSMC direct error = `{values['lsmc_direct_error']:.6f}`
- LSMC low error = `{values['lsmc_low_error']:.6f}`
- Hybrid direct error = `{values['hybrid_direct_error']:.6f}`
- Hybrid low error = `{values['hybrid_low_error']:.6f}`

## Raw benchmark output

```text
{benchmark_stdout}
```

## Raw hybrid output

```text
{hybrid_stdout}
```
"""
    OUTPUT_MD.write_text(text, encoding="utf-8")



def main() -> None:
    benchmark_stdout, benchmark_values = run_script(BENCHMARK_SCRIPT, BENCHMARK_PATTERNS)
    hybrid_stdout, hybrid_values = run_script(HYBRID_SCRIPT, HYBRID_PATTERNS)
    values = {**benchmark_values, **hybrid_values}

    hybrid_direct_vs_lsmc_direct = rel_error(values["hybrid_direct_price"], values["lsmc_direct_price"])
    hybrid_low_vs_lsmc_direct = rel_error(values["hybrid_low_price"], values["lsmc_direct_price"])
    hybrid_low_vs_lsmc_low = rel_error(values["hybrid_low_price"], values["lsmc_low_price"])

    save_plot(values)
    save_markdown(values, benchmark_stdout, hybrid_stdout)

    print("gDMR Bermudan put comparison")
    print(f"Benchmark script:     {BENCHMARK_SCRIPT.name}")
    print(f"Hybrid script:        {HYBRID_SCRIPT.name}")
    print(f"LSMC direct:          {values['lsmc_direct_price']:.6f} ± {values['lsmc_direct_error']:.6f}")
    print(f"LSMC low:             {values['lsmc_low_price']:.6f} ± {values['lsmc_low_error']:.6f}")
    print(f"Hybrid direct:        {values['hybrid_direct_price']:.6f} ± {values['hybrid_direct_error']:.6f}")
    print(f"Hybrid low:           {values['hybrid_low_price']:.6f} ± {values['hybrid_low_error']:.6f}")
    print(f"Hybrid direct relerr vs LSMC direct: {100.0 * hybrid_direct_vs_lsmc_direct:.2f}%")
    print(f"Hybrid low relerr vs LSMC direct:    {100.0 * hybrid_low_vs_lsmc_direct:.2f}%")
    print(f"Hybrid low relerr vs LSMC low:       {100.0 * hybrid_low_vs_lsmc_low:.2f}%")
    print(f"Saved plot:           {OUTPUT_SVG.name}")
    print(f"Saved summary:        {OUTPUT_MD.name}")


if __name__ == "__main__":
    main()
