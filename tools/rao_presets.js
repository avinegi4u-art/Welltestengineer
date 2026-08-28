#!/usr/bin/env node
'use strict';
/** Ship-specific RAO / matrix scale presets — node tools/rao_presets.js */

const RAO_PRESETS = {
  default: { name: 'Default SESAM screening', sfMult: 1 },
  conservative: { name: 'Conservative (+15%)', sfMult: 1.15 },
  soft_rao: { name: 'Soft RAO vessel', sfMult: 0.92, sfYMult: 1.1 },
  stiff_rao: { name: 'Stiff RAO vessel', sfMult: 1.12, sfYMult: 0.95 },
};

const MATRIX_COMBO_SCALES = {
  op_roll: { sfZ: 2.40, sfY: 0.18, sfX: 0.04 },
  op_pitch: { sfZ: 2.10, sfY: 0.22, sfX: 0.05 },
  op_res: { sfZ: 3.25, sfY: 0.29, sfX: 0.03 },
  sv_roll: { sfZ: 2.00, sfY: 0.15, sfX: 0.04 },
  sv_pitch: { sfZ: 1.80, sfY: 0.18, sfX: 0.05 },
  sv_res: { sfZ: 2.50, sfY: 0.25, sfX: 0.03 },
  acc_heel: { sfZ: 1.00, sfY: 0.10, sfX: 0.08 },
  lift: { sfZ: 1.00, sfY: 0.00, sfX: 0.00 },
};

const RAO_DEFAULT = {
  doc: 'SESAM screening defaults — not ship-specific RAO calibration',
  combos: MATRIX_COMBO_SCALES,
  presets: RAO_PRESETS,
};

function mergeRaoOverride(base, override) {
  if (!override) return base;
  const combos = { ...base.combos };
  for (const [id, scales] of Object.entries(override.combos || {})) {
    if (!scales || typeof scales !== 'object') continue;
    combos[id] = { ...(combos[id] || {}), ...scales };
  }
  return {
    doc: override.doc || base.doc,
    combos,
    presets: { ...base.presets, ...(override.presets || {}) },
  };
}

function applyRaoScale(combo, presetKey = 'default', override = null) {
  const merged = mergeRaoOverride(RAO_DEFAULT, override);
  const base = merged.combos[combo.id] || {};
  let sfZ = combo.sfZ;
  let sfY = combo.sfY;
  let sfX = combo.sfX;
  if (base.sfZ != null) sfZ = base.sfZ;
  if (base.sfY != null) sfY = base.sfY;
  if (base.sfX != null) sfX = base.sfX;
  const p = merged.presets[presetKey] || merged.presets.default || RAO_PRESETS.default;
  const m = p.sfMult ?? 1;
  const my = p.sfYMult ?? m;
  if (m === 1 && my === 1) return { ...combo, sfZ, sfY, sfX };
  return { ...combo, sfZ: sfZ * m, sfY: sfY * my, sfX: sfX * m };
}

function validateRaoImport(data) {
  if (!data || typeof data !== 'object') throw new Error('invalid RAO JSON');
  if (data.combos && typeof data.combos !== 'object') throw new Error('combos must be an object');
  return true;
}

module.exports = {
  RAO_PRESETS,
  MATRIX_COMBO_SCALES,
  RAO_DEFAULT,
  mergeRaoOverride,
  applyRaoScale,
  validateRaoImport,
};

if (require.main === module) {
  const sampleOverride = {
    doc: 'Example vessel — RAO screening factors',
    combos: {
      op_res: { sfZ: 3.5, sfY: 0.32, sfX: 0.04 },
      sv_res: { sfZ: 2.8, sfY: 0.28, sfX: 0.03 },
    },
  };
  const combo = {
    id: 'op_res',
    sfZ: 3.25,
    sfY: 0.29,
    sfX: 0.03,
    supports: ['turntable', 'kingpost', 'windstay', 'guys'],
  };
  const scaled = applyRaoScale(combo, 'conservative', sampleOverride);
  if (Math.abs(scaled.sfZ - 3.5 * 1.15) > 1e-9) {
    console.error('FAIL: RAO override + preset scaling');
    process.exit(1);
  }
  console.log('OK: RAO override replaces combo scales then applies preset multiplier');
  console.log('  op_res sfZ', scaled.sfZ.toFixed(3), '(3.5 × 1.15)');
  console.log('\nAll RAO preset checks passed.');
}
