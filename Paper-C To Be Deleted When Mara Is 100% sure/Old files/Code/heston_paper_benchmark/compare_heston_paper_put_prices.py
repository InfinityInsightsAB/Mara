from pathlib import Path
import html
import re
import subprocess
import sys


this_folder = Path(__file__).resolve().parent
graph_path = this_folder / "compare_heston_paper_put_prices.svg"
monte_carlo_file = this_folder / "run_heston_paper_lsmc_put.py"
hybrid_file = this_folder / "run_heston_paper_hybrid_put.py"

fd_reference = 1.4507
paper_lsmc_direct = 1.4494
paper_lsmc_low = 1.4487
paper_hybrid_direct = 1.4530
paper_hybrid_low = 1.4529
paper_grid_label = "N_S^(2) = 2^9"


def run_script(script_path):
    completed = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(this_folder),
    )
    return completed.stdout


def parse_number(output, label):
    match = re.search(rf"^{re.escape(label)}\s*([0-9.+-]+)$", output, re.MULTILINE)
    if match is None:
        raise ValueError(f"Could not find '{label}' in script output.")
    return float(match.group(1))


def parse_integer(output, label):
    match = re.search(rf"^{re.escape(label)}\s*(\d+)$", output, re.MULTILINE)
    if match is None:
        raise ValueError(f"Could not find '{label}' in script output.")
    return int(match.group(1))


def parse_text(output, label):
    match = re.search(rf"^{re.escape(label)}\s*(.+)$", output, re.MULTILINE)
    if match is None:
        raise ValueError(f"Could not find '{label}' in script output.")
    return match.group(1).strip()


def draw_svg(summary):
    width = 1180
    height = 760
    left = 120
    right = 1020
    top = 210
    bottom = 560
    chart_height = bottom - top

    values = [
        summary["lsmc_direct"],
        summary["lsmc_low"],
        summary["hybrid_direct"],
        summary["hybrid_low"],
        fd_reference,
        paper_lsmc_direct,
        paper_lsmc_low,
        paper_hybrid_direct,
        paper_hybrid_low,
    ]
    min_value = min(values)
    max_value = max(values)
    span = max(max_value - min_value, 0.01)
    y_min = min_value - 0.35 * span
    y_max = max_value + 0.55 * span

    def y_of(value):
        return bottom - (value - y_min) / (y_max - y_min) * chart_height

    bars = [
        ("LSMC direct", summary["lsmc_direct"], "#1f5aa6", 150),
        ("LSMC low", summary["lsmc_low"], "#4f46e5", 360),
        ("Hybrid direct", summary["hybrid_direct"], "#d97706", 570),
        ("Hybrid low", summary["hybrid_low"], "#6b7280", 780),
    ]

    ticks = []
    for i in range(6):
        value = y_min + (y_max - y_min) * i / 5.0
        ticks.append((value, y_of(value)))

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f6f7fb"/>',
        '<rect x="36" y="30" width="1108" height="700" rx="24" fill="#ffffff" stroke="#d7dce5"/>',
        '<text x="70" y="86" font-family="Segoe UI, Arial, sans-serif" font-size="30" font-weight="700" fill="#0f172a">Paper-Parameter Bermudan Put Comparison</text>',
        f'<text x="70" y="116" font-family="Segoe UI, Arial, sans-serif" font-size="15" fill="#475569">{html.escape(summary["model"])} setup with the article parameters and published targets</text>',
        f'<text x="70" y="138" font-family="Segoe UI, Arial, sans-serif" font-size="14" fill="#64748b">Spot: {summary["spot"]:.2f}   Strike: {summary["strike"]:.2f}   Maturity: {summary["maturity"]:.2f}   Exercise dates: {summary["exercise_dates"]}   Euler steps: {summary["euler_steps"]}</text>',
        f'<text x="70" y="160" font-family="Segoe UI, Arial, sans-serif" font-size="14" fill="#64748b">LSMC paths: {summary["lsmc_paths"]:,}   Hybrid vol paths: {summary["hybrid_paths"]:,}   Grid: {summary["asset_grid_points"]} points   {html.escape(paper_grid_label)}</text>',
        '<text x="70" y="182" font-family="Segoe UI, Arial, sans-serif" font-size="14" fill="#64748b">The green line is the finite-difference benchmark from the paper.</text>',
        '<rect x="745" y="84" width="345" height="126" rx="16" fill="#f8fafc" stroke="#d7dce5"/>',
        '<text x="767" y="110" font-family="Segoe UI, Arial, sans-serif" font-size="13" font-weight="700" fill="#334155">Published article targets</text>',
        f'<text x="767" y="134" font-family="Segoe UI, Arial, sans-serif" font-size="13" fill="#475569">Finite difference: {fd_reference:.4f}</text>',
        f'<text x="767" y="156" font-family="Segoe UI, Arial, sans-serif" font-size="13" fill="#475569">LSMC direct / low: {paper_lsmc_direct:.4f} / {paper_lsmc_low:.4f}</text>',
        f'<text x="767" y="178" font-family="Segoe UI, Arial, sans-serif" font-size="13" fill="#475569">Hybrid direct / low: {paper_hybrid_direct:.4f} / {paper_hybrid_low:.4f}</text>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="#334155" stroke-width="1.5"/>',
        f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="#334155" stroke-width="1.5"/>',
    ]

    for value, y in ticks:
        lines.append(f'<line x1="{left}" y1="{y:.2f}" x2="{right}" y2="{y:.2f}" stroke="#e2e8f0" stroke-width="1"/>')
        lines.append(f'<text x="{left - 14}" y="{y + 5:.2f}" text-anchor="end" font-family="Segoe UI, Arial, sans-serif" font-size="12" fill="#64748b">{value:.4f}</text>')

    ref_y = y_of(fd_reference)
    lines.append(f'<line x1="{left}" y1="{ref_y:.2f}" x2="{right}" y2="{ref_y:.2f}" stroke="#16a34a" stroke-width="2" stroke-dasharray="7 6" opacity="0.9"/>')
    lines.append(f'<text x="{right - 6}" y="{ref_y - 8:.2f}" text-anchor="end" font-family="Segoe UI, Arial, sans-serif" font-size="12" fill="#16a34a">Finite-difference reference {fd_reference:.4f}</text>')

    bar_width = 120
    published_map = {
        "LSMC direct": paper_lsmc_direct,
        "LSMC low": paper_lsmc_low,
        "Hybrid direct": paper_hybrid_direct,
        "Hybrid low": paper_hybrid_low,
    }
    for label, value, color, x in bars:
        y = y_of(value)
        zero_y = y_of(y_min)
        lines.append(f'<rect x="{x}" y="{y:.2f}" width="{bar_width}" height="{zero_y - y:.2f}" rx="12" fill="{color}" opacity="0.94"/>')
        lines.append(f'<text x="{x + bar_width / 2:.2f}" y="{y - 14:.2f}" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="15" font-weight="700" fill="#0f172a">{value:.6f}</text>')
        lines.append(f'<text x="{x + bar_width / 2:.2f}" y="{bottom + 30}" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="14" fill="#334155">{html.escape(label)}</text>')
        pub_y = y_of(published_map[label])
        lines.append(f'<line x1="{x + 12}" y1="{pub_y:.2f}" x2="{x + bar_width - 12}" y2="{pub_y:.2f}" stroke="#111827" stroke-width="2"/>')
        lines.append(f'<text x="{x + bar_width / 2:.2f}" y="{pub_y - 8:.2f}" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="11" fill="#111827">paper {published_map[label]:.4f}</text>')

    lines.append('<text x="70" y="610" font-family="Segoe UI, Arial, sans-serif" font-size="14" fill="#334155">This package uses the paper parameters and compares your run to the article targets, but it is still a standalone reimplementation.</text>')
    lines.append('</svg>')
    graph_path.write_text("\n".join(lines), encoding="utf-8")


mc_output = run_script(monte_carlo_file)
hybrid_output = run_script(hybrid_file)

summary = {
    "model": parse_text(mc_output, "Model:"),
    "option_type": parse_text(mc_output, "Option type:"),
    "spot": parse_number(mc_output, "Spot:"),
    "strike": parse_number(mc_output, "Strike:"),
    "maturity": parse_number(mc_output, "Maturity:"),
    "lsmc_paths": parse_integer(mc_output, "Paths:"),
    "exercise_dates": parse_integer(mc_output, "Exercise dates:"),
    "euler_steps": parse_integer(mc_output, "Euler steps:"),
    "basis_degree": parse_integer(mc_output, "Basis degree:"),
    "lsmc_direct": parse_number(mc_output, "LSMC direct price:"),
    "lsmc_direct_error": parse_number(mc_output, "LSMC direct error:"),
    "lsmc_low": parse_number(mc_output, "LSMC low price:"),
    "lsmc_low_error": parse_number(mc_output, "LSMC low error:"),
    "hybrid_model": parse_text(hybrid_output, "Model:"),
    "hybrid_option_type": parse_text(hybrid_output, "Option type:"),
    "hybrid_spot": parse_number(hybrid_output, "Spot:"),
    "hybrid_strike": parse_number(hybrid_output, "Strike:"),
    "hybrid_maturity": parse_number(hybrid_output, "Maturity:"),
    "hybrid_paths": parse_integer(hybrid_output, "Paths:"),
    "hybrid_exercise_dates": parse_integer(hybrid_output, "Exercise dates:"),
    "hybrid_euler_steps": parse_integer(hybrid_output, "Euler steps:"),
    "hybrid_basis_degree": parse_integer(hybrid_output, "Basis degree:"),
    "asset_grid_points": parse_integer(hybrid_output, "Asset grid points:"),
    "hybrid_direct": parse_number(hybrid_output, "Hybrid direct price:"),
    "hybrid_direct_error": parse_number(hybrid_output, "Hybrid direct error:"),
    "hybrid_low": parse_number(hybrid_output, "Hybrid low price:"),
    "hybrid_low_error": parse_number(hybrid_output, "Hybrid low error:"),
}

if summary["model"] != summary["hybrid_model"]:
    raise ValueError("The model label is not the same in the two standalone scripts.")
if summary["option_type"] != summary["hybrid_option_type"]:
    raise ValueError("The option type is not the same in the two standalone scripts.")
if abs(summary["spot"] - summary["hybrid_spot"]) > 1e-12:
    raise ValueError("The spot value is not the same in the two standalone scripts.")
if abs(summary["strike"] - summary["hybrid_strike"]) > 1e-12:
    raise ValueError("The strike value is not the same in the two standalone scripts.")
if abs(summary["maturity"] - summary["hybrid_maturity"]) > 1e-12:
    raise ValueError("The maturity is not the same in the two standalone scripts.")
if summary["exercise_dates"] != summary["hybrid_exercise_dates"]:
    raise ValueError("The Bermudan exercise dates are not the same in the two standalone scripts.")
if summary["euler_steps"] != summary["hybrid_euler_steps"]:
    raise ValueError("The Euler step counts are not the same in the two standalone scripts.")

draw_svg(summary)

our_errors = {
    "lsmc_direct": abs(summary["lsmc_direct"] - fd_reference),
    "lsmc_low": abs(summary["lsmc_low"] - fd_reference),
    "hybrid_direct": abs(summary["hybrid_direct"] - fd_reference),
    "hybrid_low": abs(summary["hybrid_low"] - fd_reference),
}

published_deltas = {
    "lsmc_direct": summary["lsmc_direct"] - paper_lsmc_direct,
    "lsmc_low": summary["lsmc_low"] - paper_lsmc_low,
    "hybrid_direct": summary["hybrid_direct"] - paper_hybrid_direct,
    "hybrid_low": summary["hybrid_low"] - paper_hybrid_low,
}

print("Comparison of Bermudan put prices under the paper parameters")
print(f"Model:                     {summary['model']}")
print(f"Option type:               {summary['option_type']}")
print(f"Spot:                      {summary['spot']:.2f}")
print(f"Strike:                    {summary['strike']:.2f}")
print(f"Maturity:                  {summary['maturity']:.2f}")
print(f"LSMC paths:                {summary['lsmc_paths']}")
print(f"Hybrid volatility paths:   {summary['hybrid_paths']}")
print(f"Exercise dates:            {summary['exercise_dates']}")
print(f"Euler steps:               {summary['euler_steps']}")
print(f"Finite-difference ref.:    {fd_reference:.4f}")
print(f"Paper LSMC direct / low:   {paper_lsmc_direct:.4f} / {paper_lsmc_low:.4f}")
print(f"Paper hybrid direct / low: {paper_hybrid_direct:.4f} / {paper_hybrid_low:.4f}")
print(f"Run LSMC direct / low:     {summary['lsmc_direct']:.6f} / {summary['lsmc_low']:.6f}")
print(f"Run hybrid direct / low:   {summary['hybrid_direct']:.6f} / {summary['hybrid_low']:.6f}")
print(f"|Run LSMC direct - FD|:    {our_errors['lsmc_direct']:.6f}")
print(f"|Run LSMC low - FD|:       {our_errors['lsmc_low']:.6f}")
print(f"|Run hybrid direct - FD|:  {our_errors['hybrid_direct']:.6f}")
print(f"|Run hybrid low - FD|:     {our_errors['hybrid_low']:.6f}")
print(f"Run - paper LSMC direct:   {published_deltas['lsmc_direct']:+.6f}")
print(f"Run - paper LSMC low:      {published_deltas['lsmc_low']:+.6f}")
print(f"Run - paper hybrid direct: {published_deltas['hybrid_direct']:+.6f}")
print(f"Run - paper hybrid low:    {published_deltas['hybrid_low']:+.6f}")
print("Result:                    Parameters are paper-faithful; the published article values above are the true comparison targets.")
print(f"Graph saved to:            {graph_path}")
