# Blower Scaling Calculator

Interactive scaling tool replicating the Foxconn blower scaling spreadsheet. Enter the base fan's geometry, RPM, sound level, and peak operating point, then specify a target diameter / height / RPM — the calculator outputs the scaled fan's tip speed, sound level, peak pressure and flow, and overlays both P-Q curves on a single chart.

!!! note "Where the formulas come from"
    The scaling laws encoded below were derived numerically from the
    Foxconn spreadsheet (`data/foxconn-blower-scaling/foxconn_blowerScaling.numbers`)
    by fitting the ratios between the documented base and scaled curves.
    They are not the textbook fan affinity laws — the spreadsheet appears
    to use empirical relations. Use the **Show formulas** toggle below the
    chart to inspect what's being computed and override if your blower
    family uses different scaling.

<style>
  .bt-card {
    border: 1px solid var(--md-default-fg-color--lightest);
    padding: 1rem 1.25rem;
    border-radius: 4px;
    background: transparent;
  }
  .bt-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 1rem;
    margin: 1.5rem 0;
  }
  .bt-card h3 {
    margin: 0 0 0.75rem;
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--md-default-fg-color--lighter);
    border: 0;
    padding: 0;
  }
  .bt-card label {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.45rem;
    font-size: 0.85rem;
  }
  .bt-card label span {
    color: var(--md-default-fg-color--light);
  }
  .bt-card input[type="number"] {
    width: 8rem;
    padding: 0.35rem 0.5rem;
    font-family: "JetBrains Mono", ui-monospace, monospace;
    font-size: 0.85rem;
    border: 1px solid var(--md-default-fg-color--lightest);
    border-radius: 2px;
    background: var(--md-default-bg-color);
    color: var(--md-default-fg-color);
  }
  .bt-card input[type="number"]:focus {
    outline: none;
    border-color: var(--md-default-fg-color);
  }
  .bt-card.bt-results table {
    width: 100%;
    border: 0;
    margin: 0;
  }
  .bt-card.bt-results td {
    padding: 0.3rem 0;
    border: 0;
    font-size: 0.85rem;
  }
  .bt-card.bt-results td:last-child {
    text-align: right;
    font-family: "JetBrains Mono", ui-monospace, monospace;
    font-weight: 600;
  }
  #bt-chart {
    height: 460px;
    margin: 1rem 0 0.5rem;
  }
  .bt-actions {
    display: flex;
    gap: 0.5rem;
    margin-top: 0.5rem;
  }
  .bt-actions button {
    padding: 0.35rem 0.75rem;
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 700;
    background: transparent;
    color: var(--md-default-fg-color);
    border: 1px solid var(--md-default-fg-color);
    border-radius: 2px;
    cursor: pointer;
  }
  .bt-actions button:hover {
    background: var(--md-default-fg-color);
    color: var(--md-default-bg-color);
  }
</style>

<div class="bt-grid">
  <div class="bt-card">
    <h3>Base fan</h3>
    <label><span>Diameter (mm)</span><input type="number" id="bt-d1" value="60.5" step="0.1"></label>
    <label><span>Height (mm)</span><input type="number" id="bt-h1" value="32" step="0.1"></label>
    <label><span>RPM</span><input type="number" id="bt-n1" value="4050" step="50"></label>
    <label><span>SPL (dBA)</span><input type="number" id="bt-spl1" value="51.4" step="0.1"></label>
    <label><span>Peak P (Pa)</span><input type="number" id="bt-p1max" value="154.28" step="0.1"></label>
    <label><span>Peak Q (CFM)</span><input type="number" id="bt-q1max" value="15.2" step="0.1"></label>
  </div>

  <div class="bt-card">
    <h3>Scaled fan</h3>
    <label><span>Diameter (mm)</span><input type="number" id="bt-d2" value="50" step="0.1"></label>
    <label><span>Height (mm)</span><input type="number" id="bt-h2" value="20" step="0.1"></label>
    <label><span>RPM</span><input type="number" id="bt-n2" value="8000" step="50"></label>
    <div class="bt-actions">
      <button id="bt-reset">Reset</button>
    </div>
  </div>

  <div class="bt-card bt-results">
    <h3>Results</h3>
    <table>
      <tr><td>Base tip speed</td><td><span id="bt-tip1">—</span> m/s</td></tr>
      <tr><td>Scaled tip speed</td><td><span id="bt-tip2">—</span> m/s</td></tr>
      <tr><td>Scaled SPL</td><td><span id="bt-spl2">—</span> dBA</td></tr>
      <tr><td>ΔSPL</td><td><span id="bt-dspl">—</span> dBA</td></tr>
      <tr><td>Scaled peak P</td><td><span id="bt-p2max">—</span> Pa</td></tr>
      <tr><td>Scaled peak Q</td><td><span id="bt-q2max">—</span> CFM</td></tr>
      <tr><td>Q scale factor</td><td><span id="bt-qscale">—</span></td></tr>
      <tr><td>P scale factor</td><td><span id="bt-pscale">—</span></td></tr>
    </table>
  </div>
</div>

<div id="bt-chart"></div>

<details>
<summary><strong>Formulas used</strong></summary>

The calculator applies the following transformations to map the base fan onto the scaled fan. Subscript 1 is base, subscript 2 is scaled. `D` is wheel diameter (mm), `H` is wheel height (mm), `N` is rotational speed (RPM).

- **Tip speed:** `U_tip = π · D · N / 60` (with D in metres).
- **Sound pressure level:** `ΔSPL = 50 · log₁₀(N₂/N₁) + 70 · log₁₀(D₂/D₁)`, so `SPL₂ = SPL₁ + ΔSPL`.
- **Flow scale factor:** `Q₂ / Q₁ = (N₂/N₁) · (D₂/D₁)³ · (H₂/H₁)`.
- **Pressure scale factor:** `P₂ / P₁ = (N₂/N₁) · (D₂/D₁)²`.

The P-Q curve of the scaled fan is generated by applying these scale factors point-by-point to the base curve.

The Q and P scale factors are derived empirically from the Foxconn spreadsheet — they differ from the textbook affinity laws (`Q ∝ N·D³` and `P ∝ N²·D²`) which assume geometric similarity. The spreadsheet's separate `D` and `H` scaling treats wheel diameter and wheel height as independent parameters, so the formulas above are not dimensionally clean but match the spreadsheet's outputs exactly.

</details>

<script src="https://cdn.plot.ly/plotly-2.27.1.min.js"></script>
<script>
(function () {
  const baseCurve = [
    [0, 154.28],
    [2, 144.33],
    [4, 129.40],
    [6, 109.49],
    [8, 92.07],
    [10, 72.16],
    [12, 49.77],
    [14, 24.88],
    [15.2, 0]
  ];

  const defaults = {
    'bt-d1': 60.5, 'bt-h1': 32, 'bt-n1': 4050, 'bt-spl1': 51.4,
    'bt-p1max': 154.28, 'bt-q1max': 15.2,
    'bt-d2': 50, 'bt-h2': 20, 'bt-n2': 8000
  };

  const $ = id => document.getElementById(id);
  const num = id => parseFloat($(id).value);

  function compute () {
    const D1 = num('bt-d1'), H1 = num('bt-h1'), N1 = num('bt-n1');
    const SPL1 = num('bt-spl1'), P1max = num('bt-p1max'), Q1max = num('bt-q1max');
    const D2 = num('bt-d2'), H2 = num('bt-h2'), N2 = num('bt-n2');

    const Nr = N2 / N1, Dr = D2 / D1, Hr = H2 / H1;
    const tip1 = Math.PI * (D1 / 1000) * N1 / 60;
    const tip2 = Math.PI * (D2 / 1000) * N2 / 60;
    const dSPL = 50 * Math.log10(Nr) + 70 * Math.log10(Dr);
    const SPL2 = SPL1 + dSPL;
    const Qscale = Nr * Math.pow(Dr, 3) * Hr;
    const Pscale = Nr * Math.pow(Dr, 2);

    $('bt-tip1').textContent = tip1.toFixed(2);
    $('bt-tip2').textContent = tip2.toFixed(2);
    $('bt-spl2').textContent = SPL2.toFixed(2);
    $('bt-dspl').textContent = (dSPL >= 0 ? '+' : '') + dSPL.toFixed(2);
    $('bt-p2max').textContent = (P1max * Pscale).toFixed(2);
    $('bt-q2max').textContent = (Q1max * Qscale).toFixed(2);
    $('bt-qscale').textContent = Qscale.toFixed(4);
    $('bt-pscale').textContent = Pscale.toFixed(4);

    // Scale the embedded base curve by the user-entered Q1max / P1max so the
    // shape lines up if the user overrides the defaults.
    const Qnorm = Q1max / 15.2;
    const Pnorm = P1max / 154.28;
    const baseX = baseCurve.map(r => r[0] * Qnorm);
    const baseY = baseCurve.map(r => r[1] * Pnorm);
    const scaledX = baseX.map(q => q * Qscale);
    const scaledY = baseY.map(p => p * Pscale);

    const dark = document.documentElement.getAttribute('data-md-color-scheme') === 'slate';
    const fg = dark ? '#ffffff' : '#000000';
    const grid = dark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)';

    Plotly.react('bt-chart', [
      {
        x: baseX, y: baseY,
        mode: 'lines+markers', name: 'Base fan',
        line: { color: fg, width: 2 },
        marker: { color: fg, size: 6 }
      },
      {
        x: scaledX, y: scaledY,
        mode: 'lines+markers', name: 'Scaled fan',
        line: { color: fg, width: 2, dash: 'dash' },
        marker: { color: fg, size: 6, symbol: 'square' }
      }
    ], {
      xaxis: { title: 'Flow (CFM)', gridcolor: grid, zerolinecolor: grid, color: fg },
      yaxis: { title: 'Static pressure (Pa)', gridcolor: grid, zerolinecolor: grid, color: fg },
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      margin: { t: 20, r: 20, b: 60, l: 70 },
      legend: { x: 0.7, y: 0.95, bgcolor: 'rgba(0,0,0,0)' },
      font: { family: 'Inter, system-ui, sans-serif', color: fg }
    }, { displayModeBar: false, responsive: true });
  }

  document.querySelectorAll('.bt-card input').forEach(i => i.addEventListener('input', compute));
  $('bt-reset').addEventListener('click', () => {
    Object.keys(defaults).forEach(k => { $(k).value = defaults[k]; });
    compute();
  });

  // Re-render when user toggles dark/light mode.
  const observer = new MutationObserver(() => compute());
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-md-color-scheme'] });

  if (typeof Plotly === 'undefined') {
    document.addEventListener('DOMContentLoaded', () => setTimeout(compute, 100));
  } else {
    compute();
  }
})();
</script>

## Source data

The original Apple Numbers spreadsheet and per-table CSV exports live in the repository at [`data/foxconn-blower-scaling/`](https://github.com/Mengero/AICFD/tree/main/data/foxconn-blower-scaling). The key tables are:

| File | What's in it |
|---|---|
| `foxconn_blowerScaling.numbers` | Original Apple Numbers source. |
| `table_1.csv` | Base and scaled fan parameters (diameter, height, RPM, SPL, tip speed). |
| `base_fan.csv` | Base fan P-Q curve at 4050 RPM. |
| `scaled_fan.csv` | Scaled fan P-Q curve at 8000 RPM. |
| `system_impedance.csv` / `system_impedance-1.csv` | Two system-impedance curves overlaid on the fan curves to find operating points. |
| `system_impedance_steps.csv` | Computed impedance coefficients `k = 0.001 · inH₂O / CFM²`. |

To rebuild the CSV exports from the original `.numbers` file:

```bash
pip install numbers-parser
python -c "
from numbers_parser import Document
import csv, os
doc = Document('data/foxconn-blower-scaling/foxconn_blowerScaling.numbers')
for sheet in doc.sheets:
    for t in sheet.tables:
        with open(f'data/foxconn-blower-scaling/{t.name.lower().replace(chr(32),chr(95))}.csv','w',newline='') as f:
            w = csv.writer(f)
            for r in t.rows():
                w.writerow([c.value if c.value is not None else '' for c in r])
"
```
