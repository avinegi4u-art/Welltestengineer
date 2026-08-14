#!/usr/bin/env python3
"""Embed 3D space frame solver into Burner_boom_load_calculator.html (v5)."""
from pathlib import Path

ROOT = Path('/workspace')
HTML = ROOT / 'Burner_boom_load_calculator.html'
SRC = (ROOT / 'tools/space_frame_3d.js').read_text()

# Strip node exports / self-test
lines = []
skip = False
for line in SRC.splitlines():
    if line.startswith('module.exports') or line.startswith("if (require.main"):
        break
    if line.startswith('#!/') or line.startswith("'use strict") or line.startswith('// Self-test'):
        continue
    lines.append(line)
BODY = '\n'.join(lines)

WRAPPER = r'''
  function computeSpaceFrame(inp, combo){
    try {
      const core = computeSpaceFrameCore(inp, combo);
      const Lmm = inp.L_m * 1000;
      const utilStress = core.unity.worst.util;
      const sigmaEq = core.unity.worst.sigma || 0;
      const allow = core.allow;
      const actualSF = core.actualSF;
      const Mres = core.Mbase;
      const Vres = core.Vres;
      const N_d = core.Nax;
      const defLimit = Lmm / inp.defLimitDenom;
      const dRes = core.dRes;
      const Rbolt = inp.bcd_mm / 2;
      const boltTension_kN = inp.nBolts > 0 ? ((2 * Mres / (inp.nBolts * Rbolt)) + (N_d / inp.nBolts)) / 1000 : 0;
      const boltUtil = inp.boltAllow_kN > 0 ? boltTension_kN / inp.boltAllow_kN * 100 : 0;
      const sigmaBend = core.Z > 0 ? Mres / core.Z : 0;
      const sigmaAxial = core.A > 0 ? N_d / core.A : 0;
      const tau = core.A > 0 ? 2 * Vres / core.A : 0;
      const n = 21, xs = [], Mg = [], Mw = [], Mr = [], defl = [];
      for (let i = 0; i < n; i++) {
        const x = Lmm * i / (n - 1);
        xs.push(x);
        const rem = Lmm - x;
        Mg.push(Mres * rem / Lmm);
        Mw.push(0);
        Mr.push(Mres * rem / Lmm);
        defl.push(dRes * (x / Lmm));
      }
      const pass = core.pass && boltUtil <= 100;
      return {
        A: core.A, I: core.I, Z: core.Z, OD: core.OD, ID: core.OD - 2 * core.t, L: Lmm, theta: inp.angle_deg * Math.PI / 180,
        wSelf: 0, wAdded: 0, wGravity: 0, Ptip: 0, Pextra: 0, xp: 0,
        Mgrav_d: Mres, Vgrav_d: Vres, N_d, Mwind: 0, Vwind: 0, Mres, Vres,
        sigmaBend, sigmaAxial: sigmaAxial, sigmaCombined: sigmaBend + sigmaAxial, tau, sigmaEq,
        allow, actualSF, dVert: dRes, dWind: 0, dRes, defLimit, boltTension_kN, boltUtil, R: Rbolt,
        xs, Mg, Mw, Mr, defl, predictedTestDefl: dRes, testLoad_kg: inp.swl_kg * inp.testFactor,
        Dt: core.t > 0 ? core.OD / core.t : 0, Pcr: 0, bucklingSF: Infinity, bucklingPass: true, t: core.t,
        comboLabel: combo ? combo.label : null, supports: core.supportsOut, utilStress, pass,
        Fx_total: Vres, Fz_total: N_d, Fy_ax: N_d,
        space3d: true, frameNodes: core.model.nodes.length, frameMembers: core.model.elements.length,
        memberRows: core.unity.rows, worstMember: core.unity.worst, bm119Count: core.model.elements.filter(e => e.id.startsWith('Bm119')).length
      };
    } catch (_e) {
      return computeFrame({ ...inp, analysisMode: 'frame' }, combo);
    }
  }

  function renderMemberTable(envelope){
    const el = $('memberTable');
    if(!el || !envelope?.governing?.r?.memberRows) return;
    const rows = envelope.governing.r.memberRows
      .filter(m => m.id.startsWith('Bm119') || m.truss)
      .sort((a,b) => b.util - a.util)
      .slice(0, 20);
    let html = '<thead><tr><th>Member</th><th>Section</th><th>Util.</th><th>N (kN)</th><th>Status</th></tr></thead><tbody>';
    for(const m of rows){
      const gov = m.id === envelope.governing.r.worstMember?.id;
      html += `<tr class="${gov?'gov ':''}${m.pass?'':'fail'}"><td>${m.id}${gov?' ★':''}</td><td>${m.sn||'—'}</td><td class="n">${fmt(m.util*100,0)}%</td><td class="n">${fmt((m.N||0)/1000,1)}</td><td>${m.pass?'OK':'FAIL'}</td></tr>`;
    }
    html += '</tbody>';
    el.innerHTML = html;
  }
'''

MARKER = '  // ---- 2D plane frame solver'
html = HTML.read_text()
if 'function computeSpaceFrame(' in html:
    print('Already embedded')
    exit(0)

html = html.replace(MARKER, '  // ---- 3D space frame (PDF topology) ----\n' + BODY + WRAPPER + '\n\n' + MARKER, 1)

html = html.replace(
    "  function computeEnvelope(inp){\n    const useFrame = inp.analysisMode === 'frame';\n    const fn = useFrame ? computeFrame : compute;\n    const mode = useFrame ? 'frame' : 'matrix';",
    "  function computeEnvelope(inp){\n    const useSpace = inp.analysisMode === 'space3d';\n    const useFrame = inp.analysisMode === 'frame';\n    const fn = useSpace ? computeSpaceFrame : (useFrame ? computeFrame : compute);\n    const mode = useSpace ? 'space3d' : (useFrame ? 'frame' : 'matrix');",
    1,
)

html = html.replace(
    "    if(inp.analysisMode === 'matrix' || inp.analysisMode === 'frame'){",
    "    if(inp.analysisMode === 'matrix' || inp.analysisMode === 'frame' || inp.analysisMode === 'space3d'){",
    1,
)

html = html.replace(
    "      if($('frameInfo')) $('frameInfo').style.display = inp.analysisMode === 'frame' ? '' : 'none';",
    "      if($('frameInfo')) $('frameInfo').style.display = inp.analysisMode === 'frame' ? '' : 'none';\n      if($('space3dInfo')) $('space3dInfo').style.display = inp.analysisMode === 'space3d' ? '' : 'none';\n      if($('memberResultsCard')) $('memberResultsCard').style.display = inp.analysisMode === 'space3d' ? '' : 'none';\n      if(inp.analysisMode === 'space3d' && envelope) renderMemberTable(envelope);",
    1,
)

html = html.replace(
    "    const supportFail = (inp.analysisMode==='matrix'||inp.analysisMode==='frame') && r.supports",
    "    const supportFail = (inp.analysisMode==='matrix'||inp.analysisMode==='frame'||inp.analysisMode==='space3d') && r.supports",
    1,
)

html = html.replace(
    "      ${(inp.analysisMode==='matrix'||inp.analysisMode==='frame') && r.supports ? `",
    "      ${(inp.analysisMode==='matrix'||inp.analysisMode==='frame'||inp.analysisMode==='space3d') && r.supports ? `",
    1,
)

html = html.replace(
    "      <option value=\"frame\" selected>Frame solver + matrix (2D FEA)</option>\n    </select>",
    "      <option value=\"frame\">Frame solver + matrix (2D FEA)</option>\n      <option value=\"space3d\" selected>3D space frame (PDF topology)</option>\n    </select>",
    1,
)

html = html.replace(
    "    $('analysisMode').value = 'frame';",
    "    $('analysisMode').value = 'space3d';",
    1,
)

html = html.replace(
    "<title>Burner Boom Load Analysis v4</title>",
    "<title>Burner Boom Load Analysis v5</title>",
    1,
)

html = html.replace(
    "<p class=\"meta\">v4.0 · 2D frame FEA + matrix envelope · AISC/API-style ASD · ASCE 7 wind</p>",
    "<p class=\"meta\">v5.0 · 3D PDF space frame · Bm119 + rope sections · matrix envelope</p>",
    1,
)

html = html.replace(
    "  const STORAGE_KEY = 'burnerBoomCalc_v4';\n  const APP_VERSION = '4.0.0';",
    "  const STORAGE_KEY = 'burnerBoomCalc_v5';\n  const APP_VERSION = '5.0.0';",
    1,
)

html = html.replace(
    "      <div style=\"overflow-x:auto;\"><table class=\"matrix-table\" id=\"matrixTable\"></table></div>\n    </div>\n\n    <div class=\"card\">\n      <h2>Quality checks</h2>",
    "      <div style=\"overflow-x:auto;\"><table class=\"matrix-table\" id=\"matrixTable\"></table></div>\n      <p class=\"hint\" id=\"space3dInfo\" style=\"display:none;margin-top:8px;color:var(--series-1);\"><strong>3D space frame active:</strong> 18-bay braced boom (+X ⊥ boom, +Y along boom, +Z up) · box_90/75 chords · Bm119 top chords · Rope_pipe effective areas · Sp1–Sp10 supports from CT-12-4536 PDF.</p>\n    </div>\n\n    <div class=\"card\" id=\"memberResultsCard\" style=\"display:none;\">\n      <h2>Member unity checks <span class=\"badge-sm\">Bm119 · ropes · PDF sections</span></h2>\n      <p class=\"hint\" style=\"margin-top:-6px;\">Top 20 members by utilization. Bm119 chord segments use tributary bending from 3D base reactions; rope/truss axial from solved 3D model.</p>\n      <div style=\"overflow-x:auto;\"><table class=\"matrix-table\" id=\"memberTable\"></table></div>\n    </div>\n\n    <div class=\"card\">\n      <h2>Quality checks</h2>",
    1,
)

HTML.write_text(html)
print('Patched', HTML)
