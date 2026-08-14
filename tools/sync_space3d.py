#!/usr/bin/env python3
"""Sync tools/space_frame_3d.js into Burner_boom_load_calculator.html (3D block)."""
from pathlib import Path

ROOT = Path('/workspace')
HTML = ROOT / 'Burner_boom_load_calculator.html'
SRC = ROOT / 'tools' / 'space_frame_3d.js'

START = '  // ---- 3D space frame (PDF topology) ----'
# HTML-only wrappers (computeSpaceFrame, renderMemberTable) must stay between END marker and 2D block.
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
i1 = html.index(END)
HTML.write_text(html[:i0] + START + '\n\n' + body + '\n\n' + html[i1:])
print('Synced 3D block into', HTML)
