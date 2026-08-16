#!/usr/bin/env node
'use strict';
/** Physics-fidelity checks — node tools/space_frame_physics.js */
const sf = require('./space_frame_3d.js');

const INP = {
  L_m: sf.PDF_L_DESIGN_M, OD_mm: 219.1, t_mm: 8.18, Fy_MPa: 241, SF: 1.67,
  angle_deg: 0, addedW_kgpm: 15, tipLoad_kg: 80, extraLoad_kg: 30, extraPos_m: 9.144,
  windSpeed_ms: 40, rhoAir: 1.225, windExposure: 1, Cd: 1.2, DAF: 1.15,
  accidentalDryFactor: 0.85, accidentalHeel_deg: 5, liftingLoadFactor: 2,
  boomRestEnabled: true, guysEnabled: true, windStayEnabled: true,
  boomRestPos_m: 5.46, kingpostPos_m: 6.19, kingpostRated_kN: 80,
  windStayRated_kN: 25, guyAllow_kN: 50, nGuysEffective: 1,
  ratedMoment_kNm: 60, ratedLoad_kN: 30, vesselPeriod_s: 8, dampingZeta: 0.02,
};

const OP = {
  id: 'op_res', condition: 'operating', loadFactor: 1,
  sfZ: 3.25, sfY: 0.29, sfX: 0.03, windX: 0.99, windY: 0.10,
  supports: ['turntable', 'kingpost', 'windstay', 'guys'],
};

let failed = 0;
function assert(cond, msg) {
  if (!cond) { console.error('FAIL:', msg); failed++; }
  else console.log('OK:', msg);
}

const linear = sf.computeSpaceFrameCore(INP, OP);
const guy40 = linear.members.find(m => m.id === 'Guy40');
assert(guy40 && guy40.N < -1000, `linear Guy40 is in compression (${(guy40.N / 1000).toFixed(1)} kN) — ropes cannot do this`);

const phy = sf.computeSpaceFrameCore({ ...INP, physicsFidelity: true }, OP);
assert(phy.physics, 'physics payload present');
assert(phy.physics.slackGuys.includes('Guy40'), 'physics marks Guy40 slack');
assert(phy.physics.slackGuys.includes('GuyLat35'), 'physics marks GuyLat35 slack');
const g56 = phy.members.find(m => m.id === 'Guy56');
assert(g56 && g56.Nsigned > 0, `Guy56 remains in tension (${(g56.Nsigned / 1000).toFixed(1)} kN)`);
assert(phy.members.filter(m => m.truss && m.Nsigned < -5).length === 0, 'no rope left in compression');
const slackRow = phy.unity.rows.find(m => m.id === 'Guy40');
assert(slackRow && slackRow.slack && slackRow.N === 0, 'Guy40 unity row is SLACK with zero force');
assert(phy.unity.rows.some(m => m.id === 'GuyLat35' && m.slack), 'GuyLat35 appears as SLACK in unity table');
assert(phy.dRes > 800 && phy.dRes < 2500, `physics tip disp ${phy.dRes.toFixed(0)} mm in 800–2500 band`);
assert(phy.physics.iters >= 2 && phy.physics.iters <= 10, `tension-only / P-Δ converged in ${phy.physics.iters} iters`);
assert(phy.physics.rayleigh.Tn > 0.3 && phy.physics.rayleigh.Tn < 5, `Rayleigh Tn ${phy.physics.rayleigh.Tn.toFixed(2)} s plausible for 60 ft guyed boom`);
assert(phy.physics.dafPhysics >= 1 && phy.physics.dafPhysics <= 1.3, `SDOF DAF ${phy.physics.dafPhysics.toFixed(3)} vs 8 s heave`);
assert(phy.physics.pipeLocal.governs === 'yield', '8 in Sch 40 local buckling does not govern (yield first)');
assert(phy.physics.chordBuckling.sf > 5, `braced-chord Euler SF ${phy.physics.chordBuckling.sf.toFixed(0)} >> 1 (not a K=2 cantilever)`);
assert(Math.abs(linear.dRes - 1567) < 30, 'linear screening path unchanged');

if (failed) {
  console.error(`\n${failed} physics check(s) failed`);
  process.exit(1);
}
console.log('\nAll physics-fidelity checks passed.');
