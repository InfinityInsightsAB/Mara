import runpy
from pathlib import Path


if __name__ == "__main__":
    target = Path(__file__).with_name("run_gdmr_benchmark_put.py")
    runpy.run_path(str(target), run_name="__main__")
