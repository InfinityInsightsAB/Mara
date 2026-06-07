import importlib.util
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
BENCHMARK_SCRIPT = THIS_DIR / "run_gdmr_benchmark_put.py"
HYBRID_SCRIPT = THIS_DIR / "run_gdmr_hybrid_put.py"


def rel_error(value: float, reference: float) -> float:
    if abs(reference) <= 1e-16:
        return 0.0 if abs(value) <= 1e-16 else float("inf")
    return abs(value - reference) / abs(reference)


def gap_pct(low: float, direct: float) -> float:
    if abs(direct) <= 1e-16:
        return float("inf")
    return (low - direct) / direct


def load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path.name}.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    benchmark_module = load_module(BENCHMARK_SCRIPT, "gdmr_benchmark_put")
    hybrid_module = load_module(HYBRID_SCRIPT, "gdmr_hybrid_put")

    benchmark = benchmark_module.benchmark_prices()
    hybrid = hybrid_module.hybrid_prices()

    direct_rel = rel_error(hybrid["hybrid_direct_price"], benchmark["lsmc_direct_price"])
    low_rel = rel_error(hybrid["hybrid_low_price"], benchmark["lsmc_low_price"])
    benchmark_gap = gap_pct(benchmark["lsmc_low_price"], benchmark["lsmc_direct_price"])
    hybrid_gap = gap_pct(hybrid["hybrid_low_price"], hybrid["hybrid_direct_price"])

    print("gDMR Bermudan put: benchmark LSMC vs Farahany-style FST hybrid")
    print("==============================================================")
    print(f"Benchmark script: {BENCHMARK_SCRIPT.name}")
    print(f"Hybrid script:    {HYBRID_SCRIPT.name}")
    print()
    print("Benchmark LSMC")
    print(f"  direct price: {benchmark['lsmc_direct_price']:.6f} +/- {benchmark['lsmc_direct_error']:.6f}")
    print(f"  low price:    {benchmark['lsmc_low_price']:.6f} +/- {benchmark['lsmc_low_error']:.6f}")
    print()
    print("FST hybrid")
    print(f"  direct price: {hybrid['hybrid_direct_price']:.6f} +/- {hybrid['hybrid_direct_error']:.6f}")
    print(f"  low price:    {hybrid['hybrid_low_price']:.6f} +/- {hybrid['hybrid_low_error']:.6f}")
    print()
    print("Headline comparison")
    print(f"  Hybrid direct relerr vs benchmark direct: {100.0 * direct_rel:.3f}%")
    print(f"  Hybrid low relerr vs benchmark low:       {100.0 * low_rel:.3f}%")
    print(f"  Benchmark direct-low gap:                 {100.0 * benchmark_gap:+.3f}%")
    print(f"  Hybrid direct-low gap:                    {100.0 * hybrid_gap:+.3f}%")
