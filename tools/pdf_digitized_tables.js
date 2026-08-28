#!/usr/bin/env node
'use strict';
/** Digitized PDF member unity tables — node tools/pdf_digitized_tables.js */
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

/** Screening digitization of CT-12-4536 member unity table (60 ft scaled model baseline). */
const PDF_DIGITIZED_DEFAULT = {
  kind: 'burnerBoomPdfDigitized',
  doc: 'CT-12-4536 / SESAM 90 ft — digitized member unity (60 ft screening baseline)',
  note: 'Replace via Import PDF tables JSON when certified PDF extracts are available.',
  cases: [
    {
      id: 'op_res',
      label: 'Operating · Heave+Resultant',
      members: [
        { id: 'D10_S', util_pct: 62.0, tolPct: 15 },
        { id: 'Bm119_17', util_pct: 40.5, tolPct: 25 },
        { id: 'Guy56', N_kN: 155.5, tolPct: 35 },
        { id: 'D12_S', util_pct: 61.9, tolPct: 15 },
        { id: 'X6', util_pct: 61.0, tolPct: 15 },
      ],
    },
    {
      id: 'acc_heel',
      label: 'Accidental · Static heel',
      members: [
        { id: 'Bm119_17', util_pct: 9.0, tolPct: 40 },
        { id: 'D10_S', util_pct: 52.9, tolPct: 20 },
        { id: 'D12_S', util_pct: 52.9, tolPct: 20 },
      ],
    },
    {
      id: 'sv_res',
      label: 'Survival · Heave+Resultant',
      members: [
        { id: 'Bm119_17', util_pct: 9.4, tolPct: 30 },
        { id: 'Bm119_12', util_pct: 10.9, tolPct: 30 },
        { id: 'D10_S', util_pct: 58.1, tolPct: 20 },
        { id: 'D12_S', util_pct: 58.1, tolPct: 20 },
      ],
    },
  ],
};

const COMBOS = {
  op_res: { id: 'op_res', condition: 'operating', loadFactor: 1, sfZ: 3.25, sfY: 0.29, sfX: 0.03, windX: 0.99, windY: 0.10, supports: ['turntable', 'kingpost', 'windstay', 'guys'] },
  acc_heel: { id: 'acc_heel', condition: 'accidental', loadFactor: 1, sfZ: 1.00, sfY: 0.10, sfX: 0.08, windX: 0.50, windY: 0.08, supports: ['turntable', 'kingpost'] },
  sv_res: { id: 'sv_res', condition: 'survival', loadFactor: 1, sfZ: 2.50, sfY: 0.25, sfX: 0.03, windX: 0.99, windY: 0.10, supports: ['turntable', 'boomrest'] },
};

function memberMetricFromCore(core, memberId, ref){
  const row = core.unity.rows.find(m => m.id === memberId);
  if(!row) return null;
  if(ref.N_kN != null) return Math.abs(row.N) / 1000;
  return row.util * 100;
}

function compareMemberMetric(actual, ref){
  if(actual == null || !Number.isFinite(actual)) {
    return { actual, ref: ref.util_pct ?? ref.N_kN, deltaPct: null, pass: false, status: 'MISSING' };
  }
  const target = ref.util_pct != null ? ref.util_pct : ref.N_kN;
  const deltaPct = target !== 0 ? ((actual - target) / target) * 100 : 0;
  const pass = Math.abs(deltaPct) <= (ref.tolPct || 25);
  return { actual, ref: target, deltaPct, pass, status: pass ? 'OK' : 'DRIFT' };
}

function buildDigitizedReport(tables, inp = REFERENCE_INPUTS){
  const rows = [];
  let allPass = true;
  for(const bc of tables.cases){
    const combo = COMBOS[bc.id];
    if(!combo) continue;
    const core = sf.computeSpaceFrameCore(inp, combo);
    const metrics = bc.members.map(ref => {
      const actual = memberMetricFromCore(core, ref.id, ref);
      const cmp = compareMemberMetric(actual, ref);
      if(!cmp.pass) allPass = false;
      return { ...ref, ...cmp, label: ref.id };
    });
    rows.push({ id: bc.id, label: bc.label, pass: metrics.every(m => m.pass), metrics });
  }
  return { rows, allPass, doc: tables.doc };
}

function mergeDigitizedCases(baseCases, overrideCases){
  if(!overrideCases?.length) return baseCases;
  const byId = Object.fromEntries(baseCases.map(c => [c.id, c]));
  for(const oc of overrideCases){
    if(!oc?.id || !byId[oc.id]) continue;
    const mergedMembers = [...byId[oc.id].members];
    for(const om of oc.members || []){
      const idx = mergedMembers.findIndex(m => m.id === om.id);
      if(idx >= 0) mergedMembers[idx] = { ...mergedMembers[idx], ...om };
      else mergedMembers.push(om);
    }
    byId[oc.id] = { ...byId[oc.id], ...oc, members: mergedMembers };
  }
  return baseCases.map(c => byId[c.id]);
}

function mergeDigitizedTables(base, override){
  if(!override) return base;
  return {
    ...base,
    doc: override.doc || base.doc,
    note: override.note || base.note,
    cases: mergeDigitizedCases(JSON.parse(JSON.stringify(base.cases)), override.cases),
  };
}

module.exports = {
  PDF_DIGITIZED_DEFAULT,
  REFERENCE_INPUTS,
  COMBOS,
  buildDigitizedReport,
  mergeDigitizedTables,
  compareMemberMetric,
  memberMetricFromCore,
};

if (require.main === module) {
  const report = buildDigitizedReport(PDF_DIGITIZED_DEFAULT);
  let failed = 0;
  for(const c of report.rows){
    console.log(`\n${c.label} — ${c.pass ? 'PASS' : 'FAIL'}`);
    for(const m of c.metrics){
      const actual = m.util_pct != null ? `${m.actual.toFixed(1)}%` : `${m.actual.toFixed(1)} kN`;
      const ref = m.util_pct != null ? `${m.ref}%` : `${m.ref} kN`;
      const delta = m.deltaPct != null ? ` (${m.deltaPct >= 0 ? '+' : ''}${m.deltaPct.toFixed(1)}%)` : '';
      console.log(`  ${m.pass ? 'OK' : 'DRIFT'} ${m.id}: ${actual} ref ${ref}${delta}`);
      if(!m.pass) failed++;
    }
  }
  if(failed) {
    console.error(`\n${failed} digitized member check(s) failed.`);
    process.exit(1);
  }
  console.log('\nAll digitized PDF member table checks passed.');
}
