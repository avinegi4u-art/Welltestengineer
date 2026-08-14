#!/usr/bin/env node
'use strict';
/** PDF / SESAM calibration benchmarks — node tools/pdf_benchmarks.js */
const sf = require('./space_frame_3d.js');

const REFERENCE_INPUTS = {
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
  kingpostPos_m: 6.19,
  windStayPos_m: 5.18,
  guyAttachPos_m: 6.19,
  kingpostRated_kN: 80,
  windStayRated_kN: 25,
  guyAllow_kN: 50,
  nGuysEffective: 1,
  ratedMoment_kNm: 60,
  ratedLoad_kN: 30,
};

const PDF_BENCHMARKS = {
  doc: 'CT-12-4536 / SESAM 90 ft report — 60 ft scaled screening calibration',
  note: 'Reference values from calibrated 3D model; tolerances are screening bands not certified PDF extracts.',
  cases: [
    {
      id: 'op_res',
      label: 'Operating · Heave+Resultant',
      combo: { id: 'op_res', condition: 'operating', loadFactor: 1, sfZ: 3.25, sfY: 0.29, sfX: 0.03, windX: 0.99, windY: 0.10, supports: ['turntable', 'kingpost', 'windstay', 'guys'] },
      metrics: [
        { key: 'bm119_util_pct', label: 'Bm119 unity', ref: 40.5, tolPct: 25 },
        { key: 'bm119_id', label: 'Governing chord', ref: 'Bm119_17', kind: 'string' },
        { key: 'governing_util_pct', label: 'Governing member util.', ref: 62.0, tolPct: 20 },
        { key: 'governing_id', label: 'Governing member', ref: 'D10_S', kind: 'string' },
        { key: 'tip_defl_mm', label: 'Tip deflection', ref: 1567, tolPct: 20 },
        { key: 'Mbase_kNm', label: 'Turntable moment', ref: 3.67, tolPct: 30 },
        { key: 'frame_sw_kN', label: 'Frame self-weight', ref: 79.3, tolPct: 15 },
        { key: 'guy56_kN', label: 'Guy56 axial', ref: 155.5, tolPct: 35 },
      ],
    },
    {
      id: 'acc_heel',
      label: 'Accidental · Static heel',
      combo: { id: 'acc_heel', condition: 'accidental', loadFactor: 1, sfZ: 1.00, sfY: 0.10, sfX: 0.08, windX: 0.50, windY: 0.08, supports: ['turntable', 'kingpost'] },
      metrics: [
        { key: 'bm119_util_pct', label: 'Bm119 unity', ref: 9.0, tolPct: 40 },
        { key: 'tip_defl_mm', label: 'Tip deflection', ref: 421, tolPct: 35 },
        { key: 'Mbase_kNm', label: 'Turntable moment', ref: 0.90, tolPct: 40 },
        { key: 'frame_sw_kN', label: 'Frame self-weight', ref: 22.6, tolPct: 25 },
      ],
    },
    {
      id: 'sv_res',
      label: 'Survival · Heave+Resultant',
      combo: { id: 'sv_res', condition: 'survival', loadFactor: 1, sfZ: 2.50, sfY: 0.25, sfX: 0.03, windX: 0.99, windY: 0.10, supports: ['turntable', 'boomrest'] },
      metrics: [
        { key: 'bm119_util_pct', label: 'Bm119 unity', ref: 10.9, tolPct: 30 },
        { key: 'tip_defl_mm', label: 'Tip deflection', ref: 1133, tolPct: 25 },
        { key: 'Mbase_kNm', label: 'Turntable moment', ref: 1.87, tolPct: 30 },
      ],
    },
  ],
};

function extractMetric(key, core) {
  const guy56 = core.members.find(m => m.id === 'Guy56');
  switch (key) {
    case 'bm119_util_pct': return core.unity.worst.util * 100;
    case 'bm119_id': return core.unity.worst.id;
    case 'governing_util_pct': return core.governing.util * 100;
    case 'governing_id': return core.governing.id;
    case 'tip_defl_mm': return core.dRes;
    case 'Mbase_kNm': return core.Mbase / 1e6;
    case 'frame_sw_kN': return core.frameWeightN / 1000;
    case 'guy56_kN': return guy56 ? Math.abs(guy56.N) / 1000 : null;
    case 'kingpost_kN': return core.supportsOut.kingpost.R_kN;
    case 'windstay_kN': return core.supportsOut.windstay.R_kN;
    default: return null;
  }
}

function compareMetric(actual, metric) {
  if (metric.kind === 'string') {
    const pass = String(actual) === String(metric.ref);
    return { actual, ref: metric.ref, deltaPct: null, pass, status: pass ? 'OK' : 'DRIFT' };
  }
  if (actual == null || !Number.isFinite(actual)) {
    return { actual, ref: metric.ref, deltaPct: null, pass: false, status: 'MISSING' };
  }
  const ref = metric.ref;
  const deltaPct = ref !== 0 ? ((actual - ref) / ref) * 100 : 0;
  const pass = Math.abs(deltaPct) <= (metric.tolPct || 25);
  return { actual, ref, deltaPct, pass, status: pass ? 'OK' : 'DRIFT' };
}

function runPdfCalibration(inp = REFERENCE_INPUTS) {
  return PDF_BENCHMARKS.cases.map(bCase => {
    const core = sf.computeSpaceFrameCore(inp, bCase.combo);
    const metrics = bCase.metrics.map(m => {
      const actual = extractMetric(m.key, core);
      const cmp = compareMetric(actual, m);
      return { ...m, ...cmp };
    });
    const pass = metrics.every(m => m.pass);
    return { id: bCase.id, label: bCase.label, pass, metrics, governing: core.governing };
  });
}

module.exports = { PDF_BENCHMARKS, REFERENCE_INPUTS, extractMetric, compareMetric, runPdfCalibration };

if (require.main === module) {
  const results = runPdfCalibration();
  let failed = 0;
  for (const row of results) {
    console.log('\n' + row.label + (row.pass ? ' — PASS' : ' — DRIFT'));
    for (const m of row.metrics) {
      const delta = m.deltaPct != null ? ` (${m.deltaPct >= 0 ? '+' : ''}${m.deltaPct.toFixed(1)}%)` : '';
      const val = m.kind === 'string' ? m.actual : Number(m.actual).toFixed(m.key.includes('mm') ? 0 : 1);
      console.log(' ', m.status, m.label + ':', val, 'ref', m.ref + delta);
      if (!m.pass) failed++;
    }
  }
  if (failed) process.exit(1);
  console.log('\nAll PDF calibration checks passed.');
}
