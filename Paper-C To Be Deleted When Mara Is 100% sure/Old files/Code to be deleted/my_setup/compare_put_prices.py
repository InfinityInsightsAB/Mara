from pathlib import Path
import html
import re
import subprocess
import sys


THIS_FOLDER = Path(__file__).resolve().parent
GRAPH_PATH = THIS_FOLDER / "compare_put_prices.svg"
MONTE_CARLO_FILE = THIS_FOLDER / "run_monte_carlo_put.py"
HYBRID_FILE = THIS_FOLDER / "run_hybrid_put.py"
DIRECT_TARGET = 0.02


def run_script(script_path):
    completed = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(THIS_FOLDER),
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


def relative_error(value, reference):
    scale = max(abs(reference), 1e-12)
    return abs(value - reference) / scale


def format_percent(value):
    return f"{100.0 * value:.2f}%"


def draw_svg(summary):
    width = 1220
    height = 780
    left = 120
    right = 1080
    top = 205
    bottom = 590
    chart_height = bottom - top
    label_y = bottom + 36
    title_font = "Segoe UI, Arial, sans-serif"

    points = [
        ("LSMC direct", summary["lsmc_direct"], summary["lsmc_direct_error"], "#1d4ed8", 190),
        ("LSMC low", summary["lsmc_low"], summary["lsmc_low_error"], "#4f46e5", 405),
        ("Hybrid direct", summary["hybrid_direct"], summary["hybrid_direct_error"], "#d97706", 670),
        ("Hybrid low", summary["hybrid_low"], summary["hybrid_low_error"], "#6b7280", 885),
    ]

    max_error = max(point[2] for point in points)
    min_value = min(point[1] - 2.5 * point[2] for point in points)
    max_value = max(point[1] + 2.5 * point[2] for point in points)
    span = max(max_value - min_value, max_error * 8.0, 0.2)
    y_min = min_value - 0.18 * span
    y_max = max_value + 0.22 * span

    def y_of(value):
        return bottom - (value - y_min) / (y_max - y_min) * chart_height

    ticks = []
    for i in range(6):
        value = y_min + (y_max - y_min) * i / 5.0
        ticks.append((value, y_of(value)))

    pass_fill = "#166534" if summary["direct_target_met"] else "#991b1b"
    pass_text = "PASS" if summary["direct_target_met"] else "MISS"

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#eff3f8"/>',
        '<rect x="34" y="28" width="1152" height="724" rx="28" fill="#ffffff" stroke="#d8dee9"/>',
        f'<text x="70" y="88" font-family="{title_font}" font-size="31" font-weight="700" fill="#0f172a">gDMR Bermudan Put Comparison</text>',
        f'<text x="70" y="118" font-family="{title_font}" font-size="15" fill="#475569">Article-style standalone comparison for the generalized Gatheral double mean-reverting model</text>',
        f'<text x="70" y="142" font-family="{title_font}" font-size="14" fill="#64748b">Spot: {summary["spot"]:.2f}   Strike: {summary["strike"]:.2f}   Maturity: {summary["maturity"]:.2f}   Exercise dates: {summary["exercise_dates"]}   Euler steps: {summary["euler_steps"]}</text>',
        f'<text x="70" y="164" font-family="{title_font}" font-size="14" fill="#64748b">LSMC paths: {summary["lsmc_paths"]:,}   Hybrid paths: {summary["hybrid_paths"]:,}   Hybrid low paths: {summary["hybrid_low_paths"]:,}</text>',
        f'<text x="70" y="186" font-family="{title_font}" font-size="14" fill="#64748b">Asset grid: {summary["asset_grid_points"]} points   Range factors: {summary["asset_low_factor"]:.2f} to {summary["asset_high_factor"]:.2f}   Hermite nodes: {summary["hermite_nodes"]}</text>',
        '<rect x="780" y="80" width="334" height="134" rx="18" fill="#f8fafc" stroke="#d8dee9"/>',
        f'<text x="804" y="110" font-family="{title_font}" font-size="14" font-weight="700" fill="#334155">Reference summary</text>',
        f'<text x="804" y="136" font-family="{title_font}" font-size="13" fill="#475569">Reference = LSMC direct = {summary["lsmc_direct"]:.6f}</text>',
        f'<text x="804" y="160" font-family="{title_font}" font-size="13" fill="#475569">Hybrid direct relative error = {format_percent(summary["hybrid_direct_rel"])}</text>',
        f'<text x="804" y="184" font-family="{title_font}" font-size="13" fill="#475569">Hybrid low relative error = {format_percent(summary["hybrid_low_rel_vs_direct"])}</text>',
        f'<rect x="1010" y="146" width="78" height="28" rx="14" fill="{pass_fill}" opacity="0.92"/>',
        f'<text x="1049" y="165" text-anchor="middle" font-family="{title_font}" font-size="12" font-weight="700" fill="#ffffff">{pass_text} 2.00%</text>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="#334155" stroke-width="1.5"/>',
        f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="#334155" stroke-width="1.5"/>',
    ]

    for value, y in ticks:
        lines.append(f'<line x1="{left}" y1="{y:.2f}" x2="{right}" y2="{y:.2f}" stroke="#e2e8f0" stroke-width="1"/>')
        lines.append(f'<text x="{left - 14}" y="{y + 5:.2f}" text-anchor="end" font-family="{title_font}" font-size="12" fill="#64748b">{value:.4f}</text>')

    ref_y = y_of(summary["lsmc_direct"])
    lines.append(f'<line x1="{left}" y1="{ref_y:.2f}" x2="{right}" y2="{ref_y:.2f}" stroke="#16a34a" stroke-width="2" stroke-dasharray="8 6" opacity="0.95"/>')
    lines.append(f'<text x="{right - 8}" y="{ref_y - 10:.2f}" text-anchor="end" font-family="{title_font}" font-size="12" fill="#166534">LSMC direct reference</text>')

    for label, value, error, color, x in points:
        y = y_of(value)
        y_top = y_of(value + error)
        y_bottom = y_of(value - error)
        lines.append(f'<line x1="{x}" y1="{y_top:.2f}" x2="{x}" y2="{y_bottom:.2f}" stroke="{color}" stroke-width="3"/>')
        lines.append(f'<line x1="{x - 12}" y1="{y_top:.2f}" x2="{x + 12}" y2="{y_top:.2f}" stroke="{color}" stroke-width="3"/>')
        lines.append(f'<line x1="{x - 12}" y1="{y_bottom:.2f}" x2="{x + 12}" y2="{y_bottom:.2f}" stroke="{color}" stroke-width="3"/>')
        lines.append(f'<circle cx="{x}" cy="{y:.2f}" r="11" fill="{color}" stroke="#ffffff" stroke-width="4"/>')
        lines.append(f'<text x="{x}" y="{y - 18:.2f}" text-anchor="middle" font-family="{title_font}" font-size="15" font-weight="700" fill="#0f172a">{value:.6f}</text>')
        lines.append(f'<text x="{x}" y="{y + 34:.2f}" text-anchor="middle" font-family="{title_font}" font-size="12" fill="#64748b">SE {error:.6f}</text>')
        lines.append(f'<text x="{x}" y="{label_y}" text-anchor="middle" font-family="{title_font}" font-size="14" fill="#334155">{html.escape(label)}</text>')

    lines.append(f'<text x="70" y="650" font-family="{title_font}" font-size="14" fill="#334155">Hybrid direct vs LSMC direct: {format_percent(summary["hybrid_direct_rel"])}   Hybrid low vs LSMC direct: {format_percent(summary["hybrid_low_rel_vs_direct"])}</text>')
    lines.append(f'<text x="70" y="674" font-family="{title_font}" font-size="14" fill="#334155">Hybrid low vs LSMC low: {format_percent(summary["hybrid_low_rel_vs_lsmc_low"])}   LSMC low vs LSMC direct: {format_percent(summary["lsmc_low_rel_vs_direct"])}</text>')
    lines.append('<text x="70" y="698" font-family="Segoe UI, Arial, sans-serif" font-size="14" fill="#475569">Error bars show one standard error for each estimator. The dashed line is the LSMC direct reference used for relative errors.</text>')
    lines.append('</svg>')
    GRAPH_PATH.write_text("\n".join(lines), encoding="utf-8")


mc_output = run_script(MONTE_CARLO_FILE)
hybrid_output = run_script(HYBRID_FILE)

summary = {
    "model": parse_text(mc_output, "Model:"),
    "option_type": parse_text(mc_output, "Option type:"),
    "spot": parse_number(mc_output, "Spot:"),
    "strike": parse_number(mc_output, "Strike:"),
    "maturity": parse_number(mc_output, "Maturity:"),
    "lsmc_paths": parse_integer(mc_output, "Paths:"),
    "exercise_dates": parse_integer(mc_output, "Exercise dates:"),
    "euler_steps": parse_integer(mc_output, "Euler steps:"),
    "internal_steps": parse_number(mc_output, "Internal steps:"),
    "lsmc_basis_size": parse_integer(mc_output, "Basis size:"),
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
    "hybrid_low_paths": parse_integer(hybrid_output, "Low paths:"),
    "hybrid_exercise_dates": parse_integer(hybrid_output, "Exercise dates:"),
    "hybrid_euler_steps": parse_integer(hybrid_output, "Euler steps:"),
    "hybrid_internal_steps": parse_number(hybrid_output, "Internal steps:"),
    "asset_grid_points": parse_integer(hybrid_output, "Asset grid points:"),
    "asset_low_factor": parse_number(hybrid_output, "Asset low factor:"),
    "asset_high_factor": parse_number(hybrid_output, "Asset high factor:"),
    "hermite_nodes": parse_integer(hybrid_output, "Hermite nodes:"),
    "hybrid_basis_size": parse_integer(hybrid_output, "Vol basis size:"),
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
if abs(summary["internal_steps"] - summary["hybrid_internal_steps"]) > 1e-12:
    raise ValueError("The internal step counts are not the same in the two standalone scripts.")

summary["hybrid_direct_rel"] = relative_error(summary["hybrid_direct"], summary["lsmc_direct"])
summary["hybrid_low_rel_vs_direct"] = relative_error(summary["hybrid_low"], summary["lsmc_direct"])
summary["hybrid_low_rel_vs_lsmc_low"] = relative_error(summary["hybrid_low"], summary["lsmc_low"])
summary["lsmc_low_rel_vs_direct"] = relative_error(summary["lsmc_low"], summary["lsmc_direct"])
summary["direct_target_met"] = summary["hybrid_direct_rel"] <= DIRECT_TARGET

draw_svg(summary)

print("Comparison of Bermudan put prices")
print(f"Model:                         {summary['model']}")
print(f"Option type:                   {summary['option_type']}")
print(f"Spot:                          {summary['spot']:.2f}")
print(f"Strike:                        {summary['strike']:.2f}")
print(f"Maturity:                      {summary['maturity']:.2f}")
print(f"LSMC paths:                    {summary['lsmc_paths']}")
print(f"Hybrid volatility paths:       {summary['hybrid_paths']}")
print(f"Hybrid low paths:              {summary['hybrid_low_paths']}")
print(f"Exercise dates:                {summary['exercise_dates']}")
print(f"Euler steps:                   {summary['euler_steps']}")
print(f"LSMC direct price/error:       {summary['lsmc_direct']:.6f} / {summary['lsmc_direct_error']:.6f}")
print(f"LSMC low price/error:          {summary['lsmc_low']:.6f} / {summary['lsmc_low_error']:.6f}")
print(f"Hybrid direct price/error:     {summary['hybrid_direct']:.6f} / {summary['hybrid_direct_error']:.6f}")
print(f"Hybrid low price/error:        {summary['hybrid_low']:.6f} / {summary['hybrid_low_error']:.6f}")
print(f"Hybrid direct rel. error:      {format_percent(summary['hybrid_direct_rel'])}")
print(f"Hybrid low rel. vs LSMC dir.:  {format_percent(summary['hybrid_low_rel_vs_direct'])}")
print(f"Hybrid low rel. vs LSMC low:   {format_percent(summary['hybrid_low_rel_vs_lsmc_low'])}")
print(f"LSMC low rel. vs LSMC direct:  {format_percent(summary['lsmc_low_rel_vs_direct'])}")
print(f"2% direct target met:          {'yes' if summary['direct_target_met'] else 'no'}")
print("Result:                        LSMC direct is the headline reference for this standalone gDMR comparison.")
print(f"Graph saved to:                {GRAPH_PATH}")
