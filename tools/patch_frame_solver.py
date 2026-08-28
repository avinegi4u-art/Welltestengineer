#!/usr/bin/env python3
from pathlib import Path

ROOT = Path('/workspace')
HTML = ROOT / 'Burner_boom_load_calculator.html'
BLOCK = (ROOT / 'tools/frame_solver_block.js').read_text()

text = HTML.read_text()

if 'function computeFrame(' in text:
    print('Frame solver already present')
    exit(0)

marker = '  const MATRIX_COMBOS = ['
if marker not in text:
    raise SystemExit('MATRIX_COMBOS marker not found')

text = text.replace(marker, BLOCK + '\n' + marker, 1)

text = text.replace(
    "  function computeEnvelope(inp){\n    const rows = MATRIX_COMBOS.map(c=>{\n      const r = compute({...inp, analysisMode:'matrix'}, c);\n      return { combo:c, r };\n    });",
    "  function computeEnvelope(inp){\n    const useFrame = inp.analysisMode === 'frame';\n    const fn = useFrame ? computeFrame : compute;\n    const mode = useFrame ? 'frame' : 'matrix';\n    const rows = MATRIX_COMBOS.map(c=>{\n      const r = fn({...inp, analysisMode: mode}, c);\n      return { combo:c, r };\n    });",
    1,
)

text = text.replace(
    "    if(inp.analysisMode === 'matrix'){\n      envelope = computeEnvelope(inp);\n      r = envelope.governing.r;\n      renderMatrixTable(envelope);\n      $('matrixResultsCard').style.display = '';\n    } else {",
    "    if(inp.analysisMode === 'matrix' || inp.analysisMode === 'frame'){\n      envelope = computeEnvelope(inp);\n      r = envelope.governing.r;\n      renderMatrixTable(envelope);\n      $('matrixResultsCard').style.display = '';\n      if($('frameInfo')) $('frameInfo').style.display = inp.analysisMode === 'frame' ? '' : 'none';\n    } else {",
    1,
)

text = text.replace(
    "    const supportFail = inp.analysisMode==='matrix' && r.supports && (!r.supports.kingpost.ok || !r.supports.windstay.ok || !r.supports.boomrest.ok || !r.supports.guys.ok);",
    "    const supportFail = (inp.analysisMode==='matrix'||inp.analysisMode==='frame') && r.supports && (!r.supports.kingpost.ok || !r.supports.windstay.ok || !r.supports.boomrest.ok || !r.supports.guys.ok);",
    1,
)

text = text.replace(
    "      ${inp.analysisMode==='matrix' && r.supports ? `",
    "      ${(inp.analysisMode==='matrix'||inp.analysisMode==='frame') && r.supports ? `",
    1,
)

text = text.replace(
    "      <option value=\"matrix\" selected>Matrix envelope (SESAM-style)</option>\n    </select>",
    "      <option value=\"matrix\">Matrix envelope (1D screening)</option>\n      <option value=\"frame\" selected>Frame solver + matrix (2D FEA)</option>\n    </select>",
    1,
)

text = text.replace(
    "    $('analysisMode').value = 'matrix';",
    "    $('analysisMode').value = 'frame';",
    1,
)

text = text.replace(
    "<title>Burner Boom Load Analysis v3</title>",
    "<title>Burner Boom Load Analysis v4</title>",
    1,
)

text = text.replace(
    "<p class=\"meta\">v3.0 · Matrix + cantilever structural check · AISC/API-style ASD · ASCE 7 wind</p>",
    "<p class=\"meta\">v4.0 · 2D frame FEA + matrix envelope · AISC/API-style ASD · ASCE 7 wind</p>",
    1,
)

text = text.replace(
    "  const STORAGE_KEY = 'burnerBoomCalc_v3';\n  const APP_VERSION = '3.0.0';",
    "  const STORAGE_KEY = 'burnerBoomCalc_v4';\n  const APP_VERSION = '4.0.0';",
    1,
)

text = text.replace(
    "      <p class=\"hint\" style=\"margin-top:-6px;\">Runs 8 SESAM-style combinations with 3-direction dynamic scale factors (X ⊥ boom, Y ∥ boom, Z vertical). Governing row drives header status.</p>\n      <div style=\"overflow-x:auto;\"><table class=\"matrix-table\" id=\"matrixTable\"></table></div>",
    "      <p class=\"hint\" style=\"margin-top:-6px;\">Runs 8 SESAM-style combinations with 3-direction dynamic scale factors (X ⊥ boom, Y ∥ boom, Z vertical). Governing row drives header status.</p>\n      <p class=\"hint\" id=\"frameInfo\" style=\"display:none;margin-top:6px;color:var(--series-1);\"><strong>Frame solver active:</strong> 2D plane-frame direct stiffness (12 boom segments + truss guys/stays). Reactions from solved displacements — closer to SESAM than 1D screening.</p>\n      <div style=\"overflow-x:auto;\"><table class=\"matrix-table\" id=\"matrixTable\"></table></div>",
    1,
)

text = text.replace(
    "      <h2>Multi-support boundary conditions <span class=\"badge-sm\">Matrix mode</span></h2>",
    "      <h2>Multi-support boundary conditions <span class=\"badge-sm\">Matrix / Frame</span></h2>",
    1,
)

text = text.replace(
    "      <p class=\"hint\" style=\"margin-top:-6px;\">Simplified static reactions — turntable (base), kingpost, wind stay, boom rest, crane lift. Inspired by 90 ft SESAM report; not a 3D frame solver.</p>",
    "      <p class=\"hint\" style=\"margin-top:-6px;\">Turntable (base), kingpost, wind stay, boom rest, crane lift. In <strong>Frame solver</strong> mode these are enforced as DOF constraints + truss links; in <strong>Matrix (1D)</strong> mode as static reaction screening.</p>",
    1,
)

HTML.write_text(text)
print('Patched', HTML)
