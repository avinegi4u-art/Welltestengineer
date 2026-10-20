#!/usr/bin/env python3
"""Sync tools/space_frame_3d.js into Burner_boom_load_calculator.html (3D block).

Preserves HTML-only wrappers (computeSpaceFrame, renderMemberTable, PDF benchmarks)
between the synced module and the 2D plane-frame block.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / 'Burner_boom_load_calculator.html'
SRC = ROOT / 'tools' / 'space_frame_3d.js'

START = '  // ---- 3D space frame (PDF topology) ----'
WRAPPER_START = '  function computeSpaceFrame(inp, combo){'
END = '  // ---- 2D plane frame solver'

lines = []
for line in SRC.read_text().splitlines():
    if line.startswith('module.exports') or line.startswith('if (require.main'):
        break
    if line.startswith('#!/') or line.startswith("'use strict") or line.startswith('// Self-test'):
        continue
    lines.append(line)

body = '\n'.join(lines)
html = HTML.read_text()
i0 = html.index(START)
i1 = html.index(WRAPPER_START, i0)
i2 = html.index(END, i1)
wrappers = html[i1:i2]
HTML.write_text(html[:i0] + START + '\n\n' + body + '\n\n' + wrappers + html[i2:])
print('Synced 3D block into', HTML)
