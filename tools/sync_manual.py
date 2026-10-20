#!/usr/bin/env python3
"""Sync embedded Tab 6 manual from Burner_boom_load_calculator.html to standalone manual file."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / 'Burner_boom_load_calculator.html'
MANUAL = ROOT / 'Burner_boom_load_calculator_user_manual.html'

html = HTML.read_text()
start = html.index('<section class="panel" id="panel-manual">')
end = html.index('</section>', start) + len('</section>')
panel = html[start:end]

inner_match = re.search(r'<div class="card manual-doc">\s*(.*)\s*</div>\s*</section>', panel, re.S)
if not inner_match:
    raise SystemExit('Could not extract manual-doc inner HTML')
inner = inner_match.group(1)

standalone_head = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Burner Boom Load Calculator v5.2 — User Manual</title>
  <style>
    :root { --ink:#0f172a; --muted:#475569; --accent:#007ea8; --accent-2:#00b4d8; --border:#cbd5e1; --bg:#fff; }
    * { box-sizing:border-box; }
    body { margin:0; font-family:"Segoe UI",Inter,system-ui,sans-serif; font-size:10.5pt; line-height:1.55; color:var(--ink); background:#eef2f6; }
    .page { width:min(210mm,calc(100% - 2rem)); margin:1.25rem auto 2rem; background:var(--bg); box-shadow:0 8px 30px rgba(0,0,0,.12); padding:18mm 16mm; }
    h1,h2,h3 { color:var(--accent); }
    h2 { font-size:1.2rem; border-bottom:2px solid var(--accent); padding-bottom:.25rem; margin-top:1.6rem; }
    table { width:100%; border-collapse:collapse; margin:.75rem 0; font-size:10pt; }
    th,td { border:1px solid var(--border); padding:.45rem .55rem; text-align:left; vertical-align:top; }
    th { background:#f1f5f9; }
    .toc { border:1px solid var(--border); border-radius:10px; padding:1rem; background:#fafbfc; }
    .callout { border-left:4px solid var(--accent-2); background:#ecfeff; padding:.65rem .85rem; margin:.75rem 0; }
    .callout.warn { border-color:#f59e0b; background:#fff7ed; }
    .status-grid { display:grid; gap:.65rem; }
    .pass,.warn,.fail { padding:.55rem .75rem; border-radius:8px; font-size:10pt; }
    .pass { background:#ecfdf5; border:1px solid #6ee7b7; }
    .warn { background:#fff7ed; border:1px solid #fdba74; }
    .fail { background:#fef2f2; border:1px solid #fca5a5; }
    footer { margin-top:2rem; font-size:9pt; color:var(--muted); }
    @media print { body { background:#fff; } .page { box-shadow:none; width:auto; margin:0; } .no-print { display:none !important; } }
  </style>
</head>
<body>
<div class="page manual-doc">
'''

standalone_tail = '''
</div>
</body>
</html>
'''

MANUAL.write_text(standalone_head + inner + standalone_tail)
print('Wrote', MANUAL)
