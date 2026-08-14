#!/usr/bin/env node
'use strict';
/** 60 ft burner boom — Sprint A regression (node tools/space_frame_regression.js) */
const sf = require('./space_frame_3d.js');

const INP_60FT = {
  L_m: sf.PDF_L_DESIGN_M,
  OD_mm: 219.1,
  t_mm: 8.18,
  Fy_MPa: 241,
  SF: 1.67,
  angle_deg: 0,
  addedW_kgpm: 15,
  tipLoad_kg: 80,
  extraLoad_kg: 30,
  extraPos_m: 9.144,
  windSpeed_ms: 40,
  rhoAir: 1.225,
  windExposure: 1,
  Cd: 1.2,
  DAF: 1.15,
  accidentalDryFactor: 0.85,
  accidentalHeel_deg: 5,
  liftingLoadFactor: 2,
  boomRestEnabled: true,
  guysEnabled: true,
  windStayEnabled: true,
  boomRestPos_m: 5.46,
  kingpostRated_kN: 80,
  windStayRated_kN: 25,
  guyAllow_kN: 50,
  nGuysEffective: 1,
  ratedMoment_kNm: 60,
  ratedLoad_kN: 30,
};

const MATRIX_COMBOS = [
  { id: 'op_roll', condition: 'operating', loadFactor: 1, sfZ: 2.40, sfY: 0.18, sfX: 0.04, windX: 0.63, windY: 0.08, supports: ['turntable', 'kingpost', 'windstay', 'guys'] },
  { id: 'op_pitch', condition: 'operating', loadFactor: 1, sfZ: 2.10, sfY: 0.22, sfX: 0.05, windX: 0.48, windY: 0.10, supports: ['turntable', 'kingpost', 'windstay', 'guys'] },
  { id: 'op_res', condition: 'operating', loadFactor: 1, sfZ: 3.25, sfY: 0.29, sfX: 0.03, windX: 0.99, windY: 0.10, supports: ['turntable', 'kingpost', 'windstay', 'guys'] },
  { id: 'sv_roll', condition: 'survival', loadFactor: 1, sfZ: 2.00, sfY: 0.15, sfX: 0.04, windX: 0.77, windY: 0.10, supports: ['turntable', 'boomrest'] },
  { id: 'sv_pitch', condition: 'survival', loadFactor: 1, sfZ: 1.80, sfY: 0.18, sfX: 0.05, windX: 0.60, windY: 0.10, supports: ['turntable', 'boomrest'] },
  { id: 'sv_res', condition: 'survival', loadFactor: 1, sfZ: 2.50, sfY: 0.25, sfX: 0.03, windX: 0.99, windY: 0.10, supports: ['turntable', 'boomrest'] },
  { id: 'acc_heel', condition: 'accidental', loadFactor: 1, sfZ: 1.00, sfY: 0.10, sfX: 0.08, windX: 0.50, windY: 0.08, supports: ['turntable', 'kingpost'] },
  { id: 'lift', condition: 'lifting', sfZ: 1, sfY: 0, sfX: 0, windX: 0, windY: 0, loadFactor: 2, supports: ['lifting'] },
];

let failed = 0;
function assert(cond, msg) {
  if (!cond) {
    console.error('FAIL:', msg);
    failed++;
  } else {
    console.log('OK:', msg);
  }
}

const model = sf.buildModel(INP_60FT.L_m, INP_60FT);
assert(Math.abs(model.sc - 1) < 0.001, '60 ft model scale sc ≈ 1');
assert(Math.abs(model.dy - sf.PDF_DY_M) < 0.001, 'bay spacing = 1.016 m');
assert(Math.abs(model.nodes[model.nk(18, 0)].y - INP_60FT.L_m) < 0.001, 'tip at 18.288 m');

for (const combo of MATRIX_COMBOS) {
  try {
    const core = sf.computeSpaceFrameCore(INP_60FT, combo);
    assert(Number.isFinite(core.unity.worst.util), `${combo.id} finite util`);
    assert(core.unity.worst.id.startsWith('Bm119'), `${combo.id} worst is Bm119`);
  } catch (e) {
    assert(false, `${combo.id} solves: ${e.message}`);
  }
}

const opRes = sf.computeSpaceFrameCore(INP_60FT, MATRIX_COMBOS[2]);
const util = opRes.unity.worst.util * 100;
assert(util >= 25 && util <= 55, `op_res Bm119 util ${util.toFixed(0)}% in 25–55% band`);
assert(opRes.dRes >= 900 && opRes.dRes <= 2200, `op_res tip deflection ${opRes.dRes.toFixed(0)} mm in 900–2200 band`);
assert(opRes.governing && opRes.governing.util >= 0.4, 'governing member tracked');
assert(opRes.governing.id === 'D10_S', 'op_res governing member D10_S brace');

const { loads, swFactor, frameWeightN } = sf.computeSpaceFrameLoads(INP_60FT, MATRIX_COMBOS[2], model);
assert(Math.abs(swFactor - sf.PDF_SW_FACTOR) < 0.001, 'PDF 1.27 SW factor applied');
assert(frameWeightN > 5000 && frameWeightN < 80000, `frame self-weight ${(frameWeightN / 1000).toFixed(1)} kN plausible`);

const guy = opRes.members.find(m => m.id === 'Guy56');
assert(guy && guy.N > 1000, 'Guy56 axial from 3D solve');

const modelGuys = sf.buildModel(INP_60FT.L_m, { ...INP_60FT, nGuysEffective: 3 });
assert(modelGuys.elements.some(e => e.id === 'GuySp5'), 'Sp5 guy when nGuysEffective >= 2');
assert(modelGuys.elements.some(e => e.id === 'GuySp6'), 'Sp6 guy when nGuysEffective >= 3');
assert(modelGuys.nodes.filter(n => n.tag && n.tag.startsWith('Sp')).length >= 5, 'Sp anchors grow with extra guys');

const braceRow = opRes.unity.rows.find(m => /^[DVX]\d/.test(m.id));
assert(braceRow && braceRow.util >= 0 && braceRow.util < 2, 'bracing unity plausible (<200%)');

const pdf = require('./pdf_benchmarks.js');
const cal = pdf.runPdfCalibration(INP_60FT);
assert(cal.every(c => c.pass), 'PDF calibration cases within tolerance bands');
assert(cal[0].metrics.find(m => m.key === 'bm119_id').pass, 'op_res governing chord Bm119_17');

if (failed) {
  console.error(`\n${failed} regression failure(s)`);
  process.exit(1);
}
console.log('\nAll regression checks passed (Sprint A + PDF calibration).');
