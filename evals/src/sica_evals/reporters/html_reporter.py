"""Standalone HTML report with inline CSS + tiny vanilla JS sort.

No external CDN dependencies — the file opens in a browser offline.
"""

from __future__ import annotations

import html
import json

from jinja2 import Template

from sica_evals.schemas import HarnessReport

# Gate thresholds — kept in sync with markdown_reporter.
FACTUAL_ACCURACY_GATE = 0.85
CRITICAL_OMISSIONS_GATE = 5

_TEMPLATE = Template(
    """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>SICA evals — run {{ report.run_id[:8] }}</title>
<style>
  :root { color-scheme: light dark; }
  body { font-family: -apple-system, BlinkMacSystemFont, Segoe UI, system-ui, sans-serif;
         margin: 0; padding: 24px; max-width: 1100px; margin-inline: auto; line-height: 1.5; }
  h1 { font-size: 1.5rem; margin-bottom: 0.25rem; }
  h2 { font-size: 1.15rem; margin-top: 2rem; border-bottom: 1px solid #ddd; padding-bottom: 0.25rem; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 0.85rem; font-weight: 600; }
  .badge-pass { background: #d1fae5; color: #065f46; }
  .badge-fail { background: #fee2e2; color: #991b1b; }
  .badge-warn { background: #fef3c7; color: #92400e; }
  table { border-collapse: collapse; width: 100%; margin-top: 0.5rem; font-size: 0.92rem; }
  th, td { border: 1px solid #e5e7eb; padding: 6px 10px; text-align: left; vertical-align: top; }
  th { background: #f9fafb; cursor: pointer; user-select: none; }
  th.sorted-asc::after { content: " ▲"; }
  th.sorted-desc::after { content: " ▼"; }
  tr:nth-child(even) td { background: #fafafa; }
  details { margin-top: 0.5rem; }
  summary { cursor: pointer; font-weight: 600; }
  code { background: #f3f4f6; padding: 0 4px; border-radius: 3px; font-size: 0.85rem; }
  .finding { margin-left: 1rem; }
  .meta { color: #6b7280; font-size: 0.85rem; }
  @media (prefers-color-scheme: dark) {
    body { background: #0b0f15; color: #e5e7eb; }
    table th { background: #111827; }
    table td { background: #0f1622; }
    tr:nth-child(even) td { background: #131c2c; }
    code { background: #1f2937; color: #e5e7eb; }
    .badge-pass { background: #064e3b; color: #d1fae5; }
    .badge-fail { background: #7f1d1d; color: #fee2e2; }
    .badge-warn { background: #78350f; color: #fef3c7; }
    h2 { border-color: #1f2937; }
    th, td { border-color: #1f2937; }
  }
</style>
</head>
<body>
  <h1>Reporte de evaluación — <code>{{ report.run_id[:8] }}</code></h1>
  <p class="meta">
    {{ report.timestamp.isoformat() }} · cases: {{ report.cases_total }}
    (ok: {{ report.cases_succeeded }}, error: {{ report.cases_failed }})
  </p>
  <p>
    Gate R0:
    {% if gate_pass %}<span class="badge badge-pass">PASS</span>
    {% else %}<span class="badge badge-fail">FAIL</span>{% endif %}
    <span class="meta">— umbral factual ≥ {{ factual_gate }}, omisiones críticas ≤ {{ omissions_gate }}</span>
  </p>

  <h2>Métricas agregadas</h2>
  <table>
    <thead><tr><th>Métrica</th><th>Valor</th></tr></thead>
    <tbody>
    {% for k, v in agg_rows %}
      <tr><td>{{ k }}</td><td>{{ v }}</td></tr>
    {% endfor %}
    </tbody>
  </table>

  <h2>Resultados por caso</h2>
  <table id="cases-table">
    <thead>
      <tr>
        <th data-col="0">case_id</th>
        <th data-col="1" data-numeric="1">factual_accuracy</th>
        <th data-col="2" data-numeric="1">critical_omissions</th>
        <th data-col="3" data-numeric="1">hallucinations</th>
        <th data-col="4" data-numeric="1">calib_error</th>
        <th data-col="5" data-numeric="1">latency_s</th>
        <th data-col="6">estado</th>
      </tr>
    </thead>
    <tbody>
    {% for r in report.per_case_results %}
      <tr>
        <td>{{ r.case_id }}</td>
        <td>{{ "%.4f"|format(r.factual_accuracy) }}</td>
        <td>{{ r.critical_omissions }}</td>
        <td>{{ r.hallucinations }}</td>
        <td>{{ "%.4f"|format(r.confidence_calibration_error) }}</td>
        <td>{{ "%.2f"|format(r.latency_seconds) }}</td>
        <td>
          {% if r.error %}<span class="badge badge-fail">error</span>
          {% elif r.hallucinations > 0 %}<span class="badge badge-warn">hallu</span>
          {% elif r.critical_omissions > 0 %}<span class="badge badge-warn">omits</span>
          {% else %}<span class="badge badge-pass">ok</span>{% endif %}
        </td>
      </tr>
    {% endfor %}
    </tbody>
  </table>

  <h2>Hallazgos críticos</h2>
  {% set findings_present = false %}
  {% for r in report.per_case_results %}
    {% if r.error or r.critical_omissions > 0 or r.hallucinations > 0 %}
      {% set findings_present = true %}
      <details open>
        <summary>{{ r.case_id }}{% if r.error %} — error{% endif %}</summary>
        {% if r.error %}
          <p>{{ r.error|e }}</p>
        {% endif %}
        {% if r.critical_omissions > 0 %}
          <p class="finding">⚠️ {{ r.critical_omissions }} omisión(es) crítica(s):</p>
          <ul>
          {% for fc in r.field_comparisons if fc.weight >= 2.0 and fc.match_type == 'missing' %}
            <li><code>{{ fc.field_name }}</code> — esperado: <code>{{ fc.expected_value|tojson }}</code></li>
          {% endfor %}
          </ul>
        {% endif %}
        {% if r.hallucinations > 0 %}
          <p class="finding">🚨 {{ r.hallucinations }} alucinación(es):</p>
          <ul>
          {% for desc in r.hallucination_descriptions %}
            <li>{{ desc|e }}</li>
          {% endfor %}
          </ul>
        {% endif %}
      </details>
    {% endif %}
  {% endfor %}
  {% if not findings_present %}
    <p class="meta"><em>(ningún hallazgo crítico — todos los casos limpios)</em></p>
  {% endif %}

  <h2>Metadatos del run</h2>
  <table>
    <thead><tr><th>Clave</th><th>Valor</th></tr></thead>
    <tbody>
    {% for k, v in meta_rows %}
      <tr><td>{{ k }}</td><td><code>{{ v|e }}</code></td></tr>
    {% endfor %}
    </tbody>
  </table>

  <p class="meta" style="margin-top: 2rem;">
    <em>Generado por sica-evals harness · raw JSON disponible en el archivo .json hermano.</em>
  </p>

<script>
(function() {
  // Tiny tablesort: click any th to sort that column. Numeric columns are
  // detected via data-numeric="1". Click toggles asc/desc.
  document.querySelectorAll('table#cases-table th').forEach(function(th) {
    th.addEventListener('click', function() {
      var col = parseInt(th.dataset.col, 10);
      var numeric = th.dataset.numeric === '1';
      var tbody = th.closest('table').querySelector('tbody');
      var rows = Array.from(tbody.querySelectorAll('tr'));
      var asc = !th.classList.contains('sorted-asc');
      th.parentNode.querySelectorAll('th').forEach(function(t) {
        t.classList.remove('sorted-asc'); t.classList.remove('sorted-desc');
      });
      th.classList.add(asc ? 'sorted-asc' : 'sorted-desc');
      rows.sort(function(a, b) {
        var av = a.children[col].innerText.trim();
        var bv = b.children[col].innerText.trim();
        if (numeric) { av = parseFloat(av) || 0; bv = parseFloat(bv) || 0; return asc ? av - bv : bv - av; }
        return asc ? av.localeCompare(bv) : bv.localeCompare(av);
      });
      rows.forEach(function(r) { tbody.appendChild(r); });
    });
  });
})();
</script>
</body>
</html>
"""
)


def render_html(report: HarnessReport) -> str:
    """Render the report to a self-contained HTML string."""
    gate_pass = (
        report.aggregate_metrics.get("factual_accuracy_mean", 0.0) >= FACTUAL_ACCURACY_GATE
        and report.aggregate_metrics.get("critical_omissions_total", 0.0)
        <= CRITICAL_OMISSIONS_GATE
    )
    agg_rows = [
        (k, f"{v:.4f}" if isinstance(v, float) else str(v))
        for k, v in sorted(report.aggregate_metrics.items())
    ]
    meta_rows = []
    for k, v in sorted(report.metadata.items()):
        meta_rows.append((k, json.dumps(v) if not isinstance(v, str) else v))

    # Jinja2 escapes by default via the |e filter we use explicitly where needed.
    rendered: str = _TEMPLATE.render(
        report=report,
        gate_pass=gate_pass,
        factual_gate=FACTUAL_ACCURACY_GATE,
        omissions_gate=CRITICAL_OMISSIONS_GATE,
        agg_rows=agg_rows,
        meta_rows=meta_rows,
        # html.escape kept available if a future template needs it
        _esc=html.escape,
    )
    return rendered
