/* Upstream Calculations App — core modules */
'use strict';

const STORAGE_KEYS = {
  theme: 'uc_theme',
  unitSystem: 'uc_unit_system',
  favorites: 'uc_favorites',
  history: 'uc_history',
  wellContext: 'uc_well_context',
};

const UNIT_FAMILIES = {
  pressure: { base: 'psi', field: 'psi', si: 'kPa', metric: 'bar', units: { psi: 1, kPa: 6.894757, bar: 0.06894757, MPa: 0.006894757, atm: 0.068046 } },
  length: { base: 'ft', field: 'ft', si: 'm', metric: 'm', units: { ft: 1, m: 0.3048, in: 12, mm: 304.8 } },
  diameter: { base: 'in', field: 'in', si: 'in', metric: 'in', units: { in: 1, mm: 25.4 } },
  volume: { base: 'bbl', field: 'bbl', si: 'm3', metric: 'm3', units: { bbl: 1, m3: 0.158987295, ft3: 5.614583, gal_us: 42 } },
  volume_gal: { base: 'gal', field: 'gal', si: 'L', metric: 'L', units: { gal: 1, L: 3.78541, bbl: 42 } },
  rate_liquid: { base: 'bbl_d', field: 'bbl_d', si: 'm3_d', metric: 'm3_d', units: { bbl_d: 1, m3_d: 0.158987295, gpm: 0.0291667, L_min: 4.41632, stb_d: 1 } },
  rate_gpm: { base: 'gpm', field: 'gpm', si: 'L_min', metric: 'L_min', units: { gpm: 1, L_min: 3.78541 } },
  rate_gas: { base: 'MMSCFD', field: 'MMSCFD', si: 'sm3_d', metric: 'sm3_d', units: { MMSCFD: 1, MSCFD: 1000, SCFD: 1e6, sm3_d: 28316.8466 } },
  density: { base: 'ppg', field: 'ppg', si: 'kg_m3', metric: 'kg_m3', units: { ppg: 1, sg: 1 / 8.345404, kg_m3: 119.826427, lb_ft3: 7.48052 } },
  density_gcc: { base: 'g_cc', field: 'g_cc', si: 'g_cc', metric: 'g_cc', units: { g_cc: 1, kg_m3: 0.001 } },
  density_lbft3: { base: 'lb_ft3', field: 'lb_ft3', si: 'kg_m3', metric: 'kg_m3', units: { lb_ft3: 1, kg_m3: 0.06242796 } },
  gradient: { base: 'psi_ft', field: 'psi_ft', si: 'kPa_m', metric: 'bar_m', units: { psi_ft: 1, kPa_m: 22.6206, bar_m: 0.226206 } },
  viscosity: { base: 'cP', field: 'cP', si: 'cP', si2: 'Pa_s', metric: 'cP', units: { cP: 1, Pa_s: 0.001 } },
  perm: { base: 'mD', field: 'mD', si: 'mD', metric: 'mD', units: { mD: 1 } },
  force: { base: 'lbf', field: 'lbf', si: 'kN', metric: 'kN', units: { lbf: 1, kN: 0.00444822 } },
  power_hp: { base: 'hp', field: 'hp', si: 'kW', metric: 'kW', units: { hp: 1, kW: 0.7457 } },
  area_in2: { base: 'in2', field: 'in2', si: 'in2', metric: 'in2', units: { in2: 1, cm2: 0.155 } },
  area: { base: 'in2', field: 'in2', si: 'cm2', metric: 'cm2', units: { in2: 1, cm2: 0.155, ft2: 144 } },
  modulus: { base: 'psi_mod', field: 'psi_mod', si: 'GPa', metric: 'GPa', units: { psi_mod: 1, GPa: 145037.7377 } },
  compressibility: { base: 'psi_inv', field: 'psi_inv', si: 'kPa_inv', metric: 'bar_inv', units: { psi_inv: 1, kPa_inv: 6.894757, bar_inv: 0.06894757 } },
  time_hr: { base: 'hr', field: 'hr', si: 'hr', metric: 'hr', units: { hr: 1, min: 1 / 60, sec: 1 / 3600, day: 24 } },
  temp_R: { base: 'R', field: 'R', si: 'K', metric: 'K', units: { R: 1, K: 1.8, F: 1, C: 1.8 } },
  temperature_delta: { base: 'F', field: 'F', si: 'C', metric: 'C', units: { F: 1, C: 1.8, K: 1.8 } },
  thermal_exp: { base: 'per_F', field: 'per_F', si: 'per_C', metric: 'per_C', units: { per_F: 1, per_C: 1.8 } },
  fraction: { base: 'frac', field: 'frac', si: 'frac', metric: 'frac', units: { frac: 1, pct: 0.01 } },
  percent: { base: 'pct', field: 'pct', si: 'pct', metric: 'pct', units: { pct: 1, frac: 100 } },
  dimensionless: { base: '—', field: '—', si: '—', metric: '—', units: { '—': 1 } },
  spf: { base: 'spf', field: 'spf', si: 'spm', metric: 'spm', units: { spf: 1, spm: 1 / 0.3048 } },
  pi: { base: 'bpd_psi', field: 'bpd_psi', si: 'm3d_kPa', metric: 'm3d_kPa', units: { bpd_psi: 1 } },
  ii: { base: 'bpd_psi', field: 'bpd_psi', si: 'm3d_kPa', metric: 'm3d_kPa', units: { bpd_psi: 1 } },
  deliverability_c: { base: 'c', field: 'c', si: 'c', metric: 'c', units: { c: 1 } },
  slope_psi: { base: 'psi_cycle', field: 'psi_cycle', si: 'kPa_cycle', metric: 'bar_cycle', units: { psi_cycle: 1, kPa_cycle: 6.894757, bar_cycle: 0.06894757 } },
  rb_stb: { base: 'rb_stb', field: 'rb_stb', si: 'rm3_sm3', metric: 'rm3_sm3', units: { rb_stb: 1 } },
  rcf_scf: { base: 'rcf_scf', field: 'rcf_scf', si: 'rcf_scf', metric: 'rcf_scf', units: { rcf_scf: 1 } },
  vol_per_length: { base: 'bbl_ft', field: 'bbl_ft', si: 'm3_m', metric: 'm3_m', units: { bbl_ft: 1, m3_m: 0.521611 } },
  vol_per_length_gal: { base: 'gal_ft', field: 'gal_ft', si: 'L_m', metric: 'L_m', units: { gal_ft: 1, L_m: 12.419 } },
  vol_per_sack: { base: 'gal_sk', field: 'gal_sk', si: 'L_sk', metric: 'L_sk', units: { gal_sk: 1, L_sk: 3.78541 } },
  pump_output: { base: 'bbl_stk', field: 'bbl_stk', si: 'm3_stk', metric: 'm3_stk', units: { bbl_stk: 1, m3_stk: 0.158987295 } },
  velocity: { base: 'ft_min', field: 'ft_min', si: 'm_min', metric: 'm_min', units: { ft_min: 1, m_min: 0.3048 } },
  velocity_fps: { base: 'ft_s', field: 'ft_s', si: 'm_s', metric: 'm_s', units: { ft_s: 1, m_s: 0.3048 } },
  rop: { base: 'ft_hr', field: 'ft_hr', si: 'm_hr', metric: 'm_hr', units: { ft_hr: 1, m_hr: 0.3048 } },
  ton_mile: { base: 'ton_mi', field: 'ton_mi', si: 'ton_mi', metric: 'ton_mi', units: { ton_mi: 1 } },
  spm: { base: 'spm', field: 'spm', si: 'spm', metric: 'spm', units: { spm: 1 } },
  strokes: { base: 'stk', field: 'stk', si: 'stk', metric: 'stk', units: { stk: 1 } },
  sacks: { base: 'sx', field: 'sx', si: 'sx', metric: 'sx', units: { sx: 1 } },
  yield_vol: { base: 'ft3_sk', field: 'ft3_sk', si: 'm3_sk', metric: 'm3_sk', units: { ft3_sk: 1, m3_sk: 0.0283168 } },
  count: { base: 'n', field: 'n', si: 'n', metric: 'n', units: { n: 1 } },
  length_in: { base: 'in', field: 'in', si: 'mm', metric: 'mm', units: { in: 1, mm: 25.4 } },
  resistivity: { base: 'ohm_m', field: 'ohm_m', si: 'ohm_m', metric: 'ohm_m', units: { ohm_m: 1 } },
  sg: { base: 'sg', field: 'sg', si: 'sg', metric: 'sg', units: { sg: 1 } },
  api: { base: 'API', field: 'API', si: 'API', metric: 'API', units: { API: 1 } },
  gor: { base: 'scf_stb', field: 'scf_stb', si: 'sm3_sm3', metric: 'sm3_sm3', units: { scf_stb: 1 } },
  mw: { base: 'g_mol', field: 'g_mol', si: 'g_mol', metric: 'g_mol', units: { g_mol: 1 } },
  conc: { base: 'lb_gal', field: 'lb_gal', si: 'kg_L', metric: 'kg_L', units: { lb_gal: 1, kg_L: 0.119826 } },
  mass: { base: 'lb', field: 'lb', si: 'kg', metric: 'kg', units: { lb: 1, kg: 0.453592 } },
};

const OUTPUT_LABELS = {
  pressure: 'Pressure', gradient: 'Gradient', density: 'Density', volume: 'Volume', vol_per_length: 'Capacity',
  pump_output: 'Pump output', velocity: 'Velocity', velocity_fps: 'Velocity', force: 'Force', power_hp: 'HHP',
  length: 'Length', perm: 'Permeability', pi: 'PI', percent: 'Percent', fraction: 'Porosity/Saturation',
  dimensionless: 'Value', api: 'API', gor: 'GOR', time_hr: 'Time', rate_liquid: 'Rate', rate_gas: 'Gas rate',
  ii: 'Injectivity index', rcf_scf: 'Bg', rb_stb: 'Bo', strokes: 'Strokes', spm: 'SPM', rop: 'ROP',
  ton_mile: 'Ton-mile', spf: 'SPF', sacks: 'Sacks', volume_gal: 'Volume (gal)', conc: 'Concentration',
};

const UnitConv = {
  getPreferredUnit(family, system) {
    const f = UNIT_FAMILIES[family] || UNIT_FAMILIES.dimensionless;
    if (system === 'si') return f.si || f.base;
    if (system === 'metric') return f.metric || f.base;
    return f.field || f.base;
  },
  toBase(val, unit, family) {
    const f = UNIT_FAMILIES[family];
    if (!f || !f.units[unit]) return val;
    return val / f.units[unit];
  },
  fromBase(val, unit, family) {
    const f = UNIT_FAMILIES[family];
    if (!f || !f.units[unit]) return val;
    return val * f.units[unit];
  },
  convert(val, fromU, toU, family) {
    return this.fromBase(this.toBase(val, fromU, family), toU, family);
  },
};

const Store = {
  get(k, def) {
    try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : def; } catch { return def; }
  },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} },
};

function calcKey(seg, name) { return `${seg}|${name}`; }

function highlightText(text, term) {
  if (!term) return escapeHtml(text);
  const re = new RegExp(`(${term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
  return escapeHtml(text).replace(re, '<mark class="hl">$1</mark>');
}

function escapeHtml(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function fmtNum(n, digits = 4) {
  if (!Number.isFinite(n)) return '—';
  const a = Math.abs(n);
  if (a !== 0 && (a < 1e-4 || a >= 1e7)) return n.toExponential(digits);
  return n.toLocaleString(undefined, { maximumFractionDigits: digits });
}

function getWellContext() {
  return Store.get(STORAGE_KEYS.wellContext, {
    wellName: '', field: '', operator: '', testDate: '', reservoir: '', engineer: '',
  });
}

function saveWellContext(ctx) { Store.set(STORAGE_KEYS.wellContext, ctx); }

function logHistory(entry) {
  const ctx = getWellContext();
  const hist = Store.get(STORAGE_KEYS.history, []);
  hist.unshift({
    ...entry,
    well: ctx.wellName || '—',
    field: ctx.field || '—',
    ts: new Date().toISOString(),
  });
  Store.set(STORAGE_KEYS.history, hist.slice(0, 20));
  renderHistory();
}

function getFavorites() { return Store.get(STORAGE_KEYS.favorites, []); }
function toggleFavorite(key) {
  const fav = getFavorites();
  const i = fav.indexOf(key);
  if (i >= 0) fav.splice(i, 1); else fav.push(key);
  Store.set(STORAGE_KEYS.favorites, fav);
  return fav.includes(key);
}

function buildComputeFn(computeStr) {
  try { return new Function('v', computeStr); } catch { return () => NaN; }
}

const computeCache = {};
function getCompute(key, spec) {
  if (!computeCache[key]) computeCache[key] = buildComputeFn(spec.compute);
  return computeCache[key];
}

function runCalcEngine(key, spec, rawVals, unitSelections, unitSystem) {
  const baseVals = {};
  spec.inputs.forEach(([id, , family], i) => {
    const u = unitSelections[id] || UnitConv.getPreferredUnit(family, unitSystem);
    baseVals[id] = UnitConv.toBase(parseFloat(rawVals[id]), u, family);
  });
  const fn = getCompute(key, spec);
  const resultBase = fn(baseVals);
  const [outFamily] = spec.out;
  const outUnit = UnitConv.getPreferredUnit(outFamily, unitSystem);
  const result = UnitConv.fromBase(resultBase, outUnit, outFamily);
  return { result, resultBase, outUnit, outFamily: spec.out[0], outLabel: spec.out[1] || OUTPUT_LABELS[spec.out[0]] || 'Result' };
}

function createUnitField(id, label, family, unitSystem, ariaPrefix, inputKey) {
  const wrap = document.createElement('div');
  wrap.className = 'field';
  const row = document.createElement('div');
  row.className = 'field-row';
  const inp = document.createElement('input');
  inp.type = 'number';
  inp.step = 'any';
  inp.id = id;
  inp.dataset.key = inputKey || id;
  inp.dataset.family = family;
  inp.setAttribute('aria-label', `${ariaPrefix} ${label}`);
  const sel = document.createElement('select');
  sel.className = 'unit-sel';
  sel.dataset.key = inputKey || id;
  sel.dataset.family = family;
  sel.setAttribute('aria-label', `${label} unit`);
  const fam = UNIT_FAMILIES[family] || UNIT_FAMILIES.dimensionless;
  Object.keys(fam.units).forEach(u => {
    const o = document.createElement('option');
    o.value = u; o.textContent = u; sel.appendChild(o);
  });
  sel.value = UnitConv.getPreferredUnit(family, unitSystem);
  sel.addEventListener('change', () => {
    const v = parseFloat(inp.value);
    if (Number.isNaN(v)) return;
    const prev = sel.dataset.prevUnit || sel.value;
    const converted = UnitConv.convert(v, prev, sel.value, family);
    inp.value = fmtNum(converted, 6);
    sel.dataset.prevUnit = sel.value;
  });
  sel.dataset.prevUnit = sel.value;
  const lbl = document.createElement('label');
  lbl.htmlFor = id;
  lbl.textContent = label;
  row.appendChild(inp);
  row.appendChild(sel);
  wrap.appendChild(lbl);
  wrap.appendChild(row);
  return wrap;
}

/* ---- Charts (inline SVG) ---- */
const Charts = {
  pad: { t: 30, r: 20, b: 50, l: 60 },
  svg(w, h) {
    const el = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    el.setAttribute('viewBox', `0 0 ${w} ${h}`);
    el.setAttribute('width', w);
    el.setAttribute('height', h);
    el.setAttribute('role', 'img');
    return el;
  },
  line(svg, x1, y1, x2, y2, stroke, sw = 2) {
    const l = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    l.setAttribute('x1', x1); l.setAttribute('y1', y1); l.setAttribute('x2', x2); l.setAttribute('y2', y2);
    l.setAttribute('stroke', stroke); l.setAttribute('stroke-width', sw);
    svg.appendChild(l);
  },
  text(svg, x, y, txt, anchor = 'middle', size = 11) {
    const t = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    t.setAttribute('x', x); t.setAttribute('y', y); t.setAttribute('text-anchor', anchor);
    t.setAttribute('fill', 'currentColor'); t.setAttribute('font-size', size);
    t.textContent = txt;
    svg.appendChild(t);
  },
  horner(container, tp, points, params) {
    container.innerHTML = '';
    const W = 560, H = 320, p = this.pad;
    const svg = this.svg(W, H);
    const data = points.filter(pt => pt.dt > 0).map(pt => ({
      x: Math.log10((tp + pt.dt) / pt.dt),
      y: pt.pwf,
      dt: pt.dt,
    })).sort((a, b) => a.x - b.x);
    if (data.length < 2) {
      container.textContent = 'Enter at least 2 valid Δt / Pwf points.';
      return null;
    }
    const xs = data.map(d => d.x), ys = data.map(d => d.y);
    const xmin = Math.min(...xs), xmax = Math.max(...xs);
    const ymin = Math.min(...ys), ymax = Math.max(...ys);
    const xR = xmax - xmin || 1, yR = ymax - ymin || 1;
    const tx = x => p.l + ((x - xmin) / xR) * (W - p.l - p.r);
    const ty = y => p.t + (1 - (y - ymin) / yR) * (H - p.t - p.b);
    this.line(svg, p.l, H - p.b, W - p.r, H - p.b, 'var(--color-border)');
    this.line(svg, p.l, p.t, p.l, H - p.b, 'var(--color-border)');
    data.forEach(d => {
      const c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      c.setAttribute('cx', tx(d.x)); c.setAttribute('cy', ty(d.y)); c.setAttribute('r', 4);
      c.setAttribute('fill', 'var(--color-primary)');
      svg.appendChild(c);
    });
    const n = data.length;
    let sx = 0, sy = 0, sxy = 0, sxx = 0;
    data.forEach(d => { sx += d.x; sy += d.y; sxy += d.x * d.y; sxx += d.x * d.x; });
    const slope = (n * sxy - sx * sy) / (n * sxx - sx * sx);
    const intercept = (sy - slope * sx) / n;
    this.line(svg, tx(xmin), ty(slope * xmin + intercept), tx(xmax), ty(slope * xmax + intercept), 'var(--color-error)', 2);
    this.text(svg, W / 2, H - 8, 'log₁₀[(tp+Δt)/Δt]');
    this.text(svg, 14, H / 2, 'Pwf', 'middle');
    container.appendChild(svg);
    const q = params.q || 0, mu = params.mu || 1, b = params.b || 1, h = params.h || 1;
    const rw = params.rw || 0.25, phi = params.phi || 0.2, ct = params.ct || 1e-5;
    const m = Math.abs(slope);
    const k = m > 0 ? (162.6 * q * b * mu) / (m * h) : NaN;
    const t1hr = Math.log10((tp + 1) / 1);
    const p1hr = slope * t1hr + intercept;
    const pStar = p1hr + m * Math.log10((tp + 1) / tp);
    const skin = Number.isFinite(k) ? 1.151 * ((pStar - params.pi) / m - Math.log10(k / (phi * mu * ct * rw * rw)) + 3.23) : NaN;
    return { slope: m, k, skin, intercept, p1hr };
  },
  decline(container, type, qi, Di, b, tMax) {
    container.innerHTML = '';
    const W = 560, H = 280, p = this.pad;
    const svg = this.svg(W, H);
    const steps = 80;
    const ts = [], qs = [], nps = [];
    let np = 0, dt = tMax / steps;
    for (let i = 0; i <= steps; i++) {
      const t = i * dt;
      let q;
      if (type === 'exp') q = qi * Math.exp(-Di * t);
      else if (type === 'harm') q = qi / (1 + Di * t);
      else q = qi / Math.pow(1 + b * Di * t, 1 / b);
      if (i > 0) np += ((qs[i - 1] ?? qi) + q) / 2 * dt;
      ts.push(t); qs.push(q); nps.push(np);
    }
    const qmax = Math.max(...qs), npmax = Math.max(...nps, 1);
    const tx = t => p.l + (t / tMax) * (W - p.l - p.r);
    const tyQ = q => p.t + (1 - q / qmax) * (H * 0.45 - p.t);
    const tyN = n => H * 0.55 + (1 - n / npmax) * (H - p.b - H * 0.55);
    qs.forEach((q, i) => {
      if (i === 0) return;
      this.line(svg, tx(ts[i - 1]), tyQ(qs[i - 1]), tx(ts[i]), tyQ(q), '#01696f', 2);
      this.line(svg, tx(ts[i - 1]), tyN(nps[i - 1]), tx(ts[i]), tyN(nps[i]), '#964219', 2);
    });
    this.text(svg, W / 2, H - 6, 'Time');
    this.text(svg, W / 2, 16, `${type} decline — blue: q(t), orange: Np(t)`);
    container.appendChild(svg);
  },
  nodal(container, iprType, pr, qmax, pi, vlpPoints) {
    container.innerHTML = '';
    const W = 560, H = 320, p = this.pad;
    const svg = this.svg(W, H);
    const ipr = [];
    const n = 40;
    for (let i = 0; i <= n; i++) {
      const q = (qmax || pr * pi) * i / n;
      let pwf;
      if (iprType === 'vogel') pwf = pr - (pr / (qmax || 1)) * (q + 0.2 * Math.sqrt(qmax * q));
      else pwf = pr - q / pi;
      ipr.push({ q, pwf });
    }
    const all = [...ipr, ...vlpPoints];
    const qMax = Math.max(...all.map(d => d.q), 1);
    const pMin = Math.min(...all.map(d => d.pwf), 0);
    const pMax = Math.max(...all.map(d => d.pwf), pr);
    const tx = q => p.l + (q / qMax) * (W - p.l - p.r);
    const ty = pwf => p.t + (1 - (pwf - pMin) / (pMax - pMin || 1)) * (H - p.t - p.b);
    for (let i = 1; i < ipr.length; i++)
      this.line(svg, tx(ipr[i - 1].q), ty(ipr[i - 1].pwf), tx(ipr[i].q), ty(ipr[i].pwf), '#01696f', 2);
    for (let i = 1; i < vlpPoints.length; i++)
      this.line(svg, tx(vlpPoints[i - 1].q), ty(vlpPoints[i - 1].pwf), tx(vlpPoints[i].q), ty(vlpPoints[i].pwf), '#964219', 2);
    let match = null, best = Infinity;
    ipr.forEach(a => vlpPoints.forEach(b => {
      const d = Math.hypot(a.q - b.q, a.pwf - b.pwf);
      if (d < best) { best = d; match = { q: (a.q + b.q) / 2, pwf: (a.pwf + b.pwf) / 2 }; }
    }));
    if (match) {
      const c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      c.setAttribute('cx', tx(match.q)); c.setAttribute('cy', ty(match.pwf)); c.setAttribute('r', 6);
      c.setAttribute('fill', 'var(--color-error)'); svg.appendChild(c);
    }
    this.text(svg, W / 2, H - 8, 'Rate');
    this.text(svg, 14, H / 2, 'Pwf', 'middle');
    container.appendChild(svg);
    return match;
  },
};

/* ---- Quick calcs ---- */
function buildQuickDefs() {
  return {
    hydrostatic_pressure: {
      label: 'Hydrostatic pressure', inputs: [['mw', 'Mud weight', 'density'], ['tvd', 'TVD', 'length']],
      fn: v => 0.052 * v.mw * v.tvd, outFamily: 'pressure', outLabel: 'Pressure',
    },
    kill_mud_weight: {
      label: 'Kill mud weight', inputs: [['omw', 'Original MW', 'density'], ['sidpp', 'SIDPP', 'pressure'], ['tvd', 'TVD', 'length']],
      fn: v => v.omw + v.sidpp / (0.052 * v.tvd), outFamily: 'density', outLabel: 'Kill MW',
    },
    annular_volume: {
      label: 'Annular volume', inputs: [['dh', 'Hole ID', 'diameter'], ['dp', 'Pipe OD', 'diameter'], ['len', 'Length', 'length']],
      fn: v => ((v.dh ** 2 - v.dp ** 2) / 1029.4) * v.len, outFamily: 'volume', outLabel: 'Volume',
    },
    pump_output: {
      label: 'Pump output', inputs: [['liner', 'Liner ID', 'diameter'], ['stroke', 'Stroke', 'length']],
      fn: v => (v.liner ** 2 * v.stroke) / 1029.4, outFamily: 'pump_output', outLabel: 'Pump output',
    },
    oil_PI: {
      label: 'Oil productivity index', inputs: [['q', 'Rate', 'rate_liquid'], ['pr', 'Pr', 'pressure'], ['pwf', 'Pwf', 'pressure']],
      fn: v => v.q / (v.pr - v.pwf), outFamily: 'pi', outLabel: 'PI',
    },
    radius_investigation: {
      label: 'Radius of investigation', inputs: [['k', 'Permeability', 'perm'], ['t', 'Time', 'time_hr'], ['phi', 'Porosity', 'fraction'], ['mu', 'Viscosity', 'viscosity'], ['ct', 'Total compressibility', 'compressibility']],
      fn: v => Math.sqrt(0.000264 * v.k * v.t / (v.phi * v.mu * v.ct)), outFamily: 'length', outLabel: 'ri',
    },
    skin_buildup: {
      label: 'Skin from buildup intercept', inputs: [['pstar', 'P*', 'pressure'], ['pi', 'Pi', 'pressure'], ['m', 'Slope m', 'slope_psi'], ['k', 'k', 'perm'], ['phi', 'Porosity', 'fraction'], ['mu', 'Viscosity', 'viscosity'], ['ct', 'ct', 'compressibility'], ['rw', 'rw', 'length']],
      fn: v => 1.151 * ((v.pstar - v.pi) / v.m - Math.log10(v.k / (v.phi * v.mu * v.ct * v.rw ** 2)) + 3.23), outFamily: 'dimensionless', outLabel: 'Skin',
    },
    wellbore_storage: {
      label: 'Wellbore storage coefficient C', inputs: [['q', 'Rate', 'rate_liquid'], ['dt', 'Δt early', 'time_hr'], ['dp', 'ΔP early', 'pressure']],
      fn: v => (v.q * v.dt) / (24 * v.dp), outFamily: 'dimensionless', outLabel: 'C (bbl/psi approx)',
    },
    choke_critical_gas: {
      label: 'Choke critical flow (gas — Gilbert)', inputs: [['d', 'Choke ID', 'diameter'], ['p1', 'Upstream P', 'pressure'], ['p2', 'Downstream P', 'pressure'], ['t', 'Temp R', 'temp_R'], ['gamma', 'Gas gravity', 'sg']],
      fn: v => {
        const crit = v.p2 / v.p1 <= 0.55;
        if (!crit) return NaN;
        return 879 * (v.d ** 2) * v.p1 / Math.sqrt(v.gamma * v.t);
      },
      outFamily: 'rate_gas', outLabel: 'Critical rate (MMSCFD approx)',
    },
    ecd: {
      label: 'ECD', inputs: [['mw', 'MW', 'density'], ['loss', 'Annular loss', 'pressure'], ['tvd', 'TVD', 'length']],
      fn: v => v.mw + v.loss / (0.052 * v.tvd), outFamily: 'density', outLabel: 'ECD',
    },
    burst_collapse_sf: {
      label: 'Burst / Collapse safety factor', inputs: [['rating', 'Rating', 'pressure'], ['load', 'Applied load', 'pressure']],
      fn: v => v.rating / v.load, outFamily: 'dimensionless', outLabel: 'Safety factor',
    },
    gas_fvf: {
      label: 'Gas FVF (Bg)', inputs: [['p', 'Pressure', 'pressure'], ['t', 'Temp R', 'temp_R'], ['z', 'Z-factor', 'dimensionless']],
      fn: v => 0.02827 * v.z * v.t / v.p, outFamily: 'rcf_scf', outLabel: 'Bg',
    },
    api_gravity: {
      label: 'API gravity from SG', inputs: [['sg', 'SG @60°F', 'sg']],
      fn: v => 141.5 / v.sg - 131.5, outFamily: 'api', outLabel: 'API',
    },
    water_cut: {
      label: 'Water cut', inputs: [['qw', 'Water rate', 'rate_liquid'], ['ql', 'Total liquid', 'rate_liquid']],
      fn: v => 100 * v.qw / v.ql, outFamily: 'percent', outLabel: 'Water cut %',
    },
    gor_calc: {
      label: 'GOR', inputs: [['qg', 'Gas rate', 'rate_gas'], ['qo', 'Oil rate', 'rate_liquid']],
      fn: v => v.qg / v.qo, outFamily: 'gor', outLabel: 'GOR',
    },
  };
}

function registerPWA() {
  const manifest = {
    name: 'Upstream Calculations App',
    short_name: 'Upstream Calc',
    description: 'Oil & gas upstream engineering calculator for DST, CT, wireline',
    start_url: '.',
    display: 'standalone',
    background_color: '#f7f6f2',
    theme_color: '#01696f',
    icons: [{ src: 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128"><rect fill="%2301696f" width="128" height="128" rx="24"/><text x="50%" y="54%" fill="white" font-size="48" font-family="sans-serif" text-anchor="middle" dominant-baseline="middle">UC</text></svg>'), sizes: '128x128', type: 'image/svg+xml' }],
  };
  document.getElementById('appManifest').href = 'data:application/manifest+json,' + encodeURIComponent(JSON.stringify(manifest));
  if (!('serviceWorker' in navigator)) return;
  const sw = `
    self.addEventListener('install', e => { self.skipWaiting(); e.waitUntil(caches.open('uc-v1').then(c => c.addAll([self.location.href]))); });
    self.addEventListener('activate', e => { e.waitUntil(self.clients.claim()); });
    self.addEventListener('fetch', e => { e.respondWith(caches.match(e.request).then(r => r || fetch(e.request))); });
  `;
  const blob = new Blob([sw], { type: 'application/javascript' });
  navigator.serviceWorker.register(URL.createObjectURL(blob)).catch(() => {});
}

function exportHistoryCSV() {
  const hist = Store.get(STORAGE_KEYS.history, []);
  const ctx = getWellContext();
  const rows = [['Timestamp', 'Well', 'Field', 'Operator', 'Engineer', 'Calculation', 'Formula', 'Inputs', 'Result', 'Units']];
  hist.forEach(h => rows.push([h.ts, h.well, h.field, ctx.operator, ctx.engineer, h.name, h.formula, h.inputs, h.result, h.unit]));
  const csv = rows.map(r => r.map(c => `"${String(c ?? '').replace(/"/g, '""')}"`).join(',')).join('\n');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
  a.download = `upstream-calc-log-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
}

function generateReport() {
  const hist = Store.get(STORAGE_KEYS.history, []);
  const ctx = getWellContext();
  const el = document.getElementById('reportPreview');
  el.innerHTML = `
    <div class="card" style="margin-top:1rem">
      <h2>Upstream Calculations Report</h2>
      <p><strong>Well:</strong> ${escapeHtml(ctx.wellName || '—')} &nbsp; <strong>Field:</strong> ${escapeHtml(ctx.field || '—')}<br>
      <strong>Operator:</strong> ${escapeHtml(ctx.operator || '—')} &nbsp; <strong>Engineer:</strong> ${escapeHtml(ctx.engineer || '—')}<br>
      <strong>Reservoir:</strong> ${escapeHtml(ctx.reservoir || '—')} &nbsp; <strong>Test Date:</strong> ${escapeHtml(ctx.testDate || '—')}<br>
      <strong>Generated:</strong> ${new Date().toLocaleString()}</p>
      <table><thead><tr><th>Time</th><th>Calculation</th><th>Inputs</th><th>Result</th></tr></thead>
      <tbody>${hist.map(h => `<tr><td>${escapeHtml(h.ts)}</td><td>${escapeHtml(h.name)}</td><td>${escapeHtml(h.inputs)}</td><td><strong>${escapeHtml(h.result)} ${escapeHtml(h.unit || '')}</strong></td></tr>`).join('') || '<tr><td colspan="4">No calculations in session.</td></tr>'}
      </tbody></table>
    </div>`;
  window.print();
}

function renderHistory() {
  const panel = document.getElementById('historyList');
  if (!panel) return;
  const hist = Store.get(STORAGE_KEYS.history, []);
  panel.innerHTML = hist.length ? hist.map(h => `
    <div class="history-item">
      <time>${escapeHtml(new Date(h.ts).toLocaleString())}</time>
      <div><strong>${escapeHtml(h.well)}</strong> — ${escapeHtml(h.name)}</div>
      <div class="muted tiny">${escapeHtml(h.inputs)}</div>
      <div class="res">${escapeHtml(h.result)} ${escapeHtml(h.unit || '')}</div>
    </div>`).join('') : '<p class="muted">No calculations yet.</p>';
}

/* App init — called from inline bootstrap with calcData + calcRegistry */
function initUpstreamApp(calcData, calcRegistry) {
  const quickDefs = buildQuickDefs();
  let unitSystem = Store.get(STORAGE_KEYS.unitSystem, 'field');
  let activeSegment = 'All';
  let searchTerm = '';

  const els = {
    nav: document.getElementById('nav'),
    library: document.getElementById('library'),
    search: document.getElementById('search'),
    segCount: document.getElementById('segCount'),
    calcCount: document.getElementById('calcCount'),
    themeBtn: document.getElementById('themeBtn'),
    unitSystemSel: document.getElementById('unitSystemSel'),
    quickCalc: document.getElementById('quickCalc'),
    quickFields: document.getElementById('quickFields'),
    calcResult: document.getElementById('calcResult'),
    sidebar: document.getElementById('sidebar'),
    historyPanel: document.getElementById('historyPanel'),
    overlay: document.getElementById('overlay'),
    menuBtn: document.getElementById('menuBtn'),
    histBtn: document.getElementById('histBtn'),
  };

  const segmentNames = Object.keys(calcData);
  els.segCount.textContent = segmentNames.length;
  els.calcCount.textContent = segmentNames.reduce((a, k) => a + calcData[k].length, 0);

  const themes = ['light', 'dark', 'contrast'];
  let themeIdx = themes.indexOf(Store.get(STORAGE_KEYS.theme, 'light'));
  if (themeIdx < 0) themeIdx = 0;
  document.documentElement.setAttribute('data-theme', themes[themeIdx]);

  function applyUnitSystem() {
    Store.set(STORAGE_KEYS.unitSystem, unitSystem);
    document.querySelectorAll('.unit-sel').forEach(sel => {
      const fam = UNIT_FAMILIES[sel.closest('.field')?.querySelector('input')?.dataset.family];
      if (fam) sel.value = UnitConv.getPreferredUnit(sel.closest('.field').querySelector('input').dataset.family, unitSystem);
    });
  }

  function renderNav(active = 'All') {
    els.nav.innerHTML = '';
    const fav = getFavorites();
    if (fav.length) {
      const fb = document.createElement('button');
      fb.textContent = `⭐ Favorites (${fav.length})`;
      fb.className = active === 'Favorites' ? 'active' : '';
      fb.onclick = () => renderLibrary('Favorites', searchTerm);
      els.nav.appendChild(fb);
    }
    const allBtn = document.createElement('button');
    allBtn.textContent = 'All segments';
    allBtn.className = active === 'All' ? 'active' : '';
    allBtn.onclick = () => renderLibrary('All', searchTerm);
    els.nav.appendChild(allBtn);
    segmentNames.forEach(name => {
      const b = document.createElement('button');
      b.textContent = `${name} (${calcData[name].length})`;
      b.className = active === name ? 'active' : '';
      b.onclick = () => renderLibrary(name, searchTerm);
      els.nav.appendChild(b);
    });
  }

  function renderInteractiveCalc(seg, name, formula, spec) {
    const key = calcKey(seg, name);
    const div = document.createElement('div');
    div.className = 'calc';
    div.dataset.key = key;
    const isFav = getFavorites().includes(key);
    div.innerHTML = `<h4><button type="button" class="star-btn ${isFav ? 'on' : ''}" aria-label="Toggle favorite" data-fav="${escapeHtml(key)}">${isFav ? '★' : '☆'}</button>${escapeHtml(name)}</h4>`;
    const inputsWrap = document.createElement('div');
    inputsWrap.className = 'calc-inputs';
    const unitSelections = {};
    spec.inputs.forEach(([id, lbl, family]) => {
      inputsWrap.appendChild(createUnitField(`calc-${key.replace(/\|/g, '-')}-${id}`, lbl, family, unitSystem, name, id));
      unitSelections[id] = UnitConv.getPreferredUnit(family, unitSystem);
    });
    div.appendChild(inputsWrap);
    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'toggle-formula';
    toggle.textContent = 'Show derivation / formula';
    const fp = document.createElement('div');
    fp.className = 'formula-panel';
    fp.innerHTML = `<div class="eq-block mono">${escapeHtml(spec.formula || formula)}</div><ul class="assump-list">${(spec.assumptions || []).map(a => `<li>${escapeHtml(a)}</li>`).join('')}</ul><p class="muted tiny">${escapeHtml(spec.notes || '')}</p>`;
    toggle.onclick = () => { fp.classList.toggle('open'); toggle.textContent = fp.classList.contains('open') ? 'Hide derivation / formula' : 'Show derivation / formula'; };
    div.appendChild(toggle);
    div.appendChild(fp);
    const resBox = document.createElement('div');
    resBox.className = 'result-box';
    resBox.textContent = 'Result: —';
    div.appendChild(resBox);

    function recalc() {
      const raw = {};
      spec.inputs.forEach(([id]) => {
      const inp = div.querySelector(`input[data-key="${id}"]`);
      const sel = div.querySelector(`select[data-key="${id}"]`);
        if (inp) { raw[id] = inp.value; unitSelections[id] = sel?.value; }
      });
      try {
        const out = runCalcEngine(key, spec, raw, unitSelections, unitSystem);
        resBox.textContent = `Result: ${fmtNum(out.result)} ${out.outUnit} (${out.outLabel})`;
        const inputStr = spec.inputs.map(([id, lbl]) => `${lbl}=${raw[id]}`).join('; ');
        logHistory({ segment: seg, name, formula: spec.formula || formula, inputs: inputStr, result: fmtNum(out.result), unit: out.outUnit });
      } catch { resBox.textContent = 'Result: Error — check inputs'; }
    }
    div.querySelectorAll('input, select').forEach(el => el.addEventListener('input', recalc));
    div.querySelector('.star-btn').onclick = e => {
      const on = toggleFavorite(key);
      e.target.textContent = on ? '★' : '☆';
      e.target.classList.toggle('on', on);
      renderNav(activeSegment);
    };

    if (seg === 'Well Testing & DST' && name === 'Permeability from build-up') {
      div.appendChild(buildHornerSection());
    }
    if (seg === 'Production' && name === 'Productivity decline') {
      div.appendChild(buildDeclineSection());
    }
    if ((seg === 'Production' && name === 'Oil PI') || (seg === 'Completion' && name === 'Nodal inflow/outflow match')) {
      div.appendChild(buildNodalSection());
    }
    return div;
  }

  function buildHornerSection() {
    const box = document.createElement('div');
    box.className = 'chart-box';
    box.innerHTML = `<h4>Horner plot generator</h4>
      <div class="calc-inputs">
        <div class="field"><label>tp (hr)</label><input type="number" id="horner-tp" step="any" value="10" aria-label="Flow time tp"></div>
        <div class="field"><label>q (stb/d)</label><input type="number" id="horner-q" step="any" value="1000" aria-label="Rate"></div>
        <div class="field"><label>μ (cP)</label><input type="number" id="horner-mu" step="any" value="1" aria-label="Viscosity"></div>
        <div class="field"><label>B (rb/stb)</label><input type="number" id="horner-b" step="any" value="1.2" aria-label="FVF"></div>
        <div class="field"><label>h (ft)</label><input type="number" id="horner-h" step="any" value="50" aria-label="Net pay"></div>
        <div class="field"><label>Pi (psi)</label><input type="number" id="horner-pi" step="any" value="5000" aria-label="Initial pressure"></div>
      </div>
      <div class="field"><label>Pwf data (Δt hr, Pwf psi — one pair per line)</label><textarea id="horner-data" rows="5" aria-label="Horner pressure data" style="width:100%;padding:.75rem;border-radius:10px;border:1px solid var(--color-border)">0.01,4800\n0.05,4850\n0.1,4900\n0.5,4950\n1,4980\n5,5020\n10,5040</textarea></div>
      <button type="button" class="btn primary no-print" id="hornerPlotBtn">Plot Horner</button>
      <div id="hornerChart"></div><div id="hornerResults" class="footer-note"></div>`;
    box.querySelector('#hornerPlotBtn').onclick = () => {
      const tp = parseFloat(box.querySelector('#horner-tp').value);
      const lines = box.querySelector('#horner-data').value.trim().split('\n');
      const points = lines.map(l => { const [dt, pwf] = l.split(/[,\s]+/).map(Number); return { dt, pwf }; }).filter(p => p.dt > 0 && Number.isFinite(p.pwf));
      const params = {
        q: parseFloat(box.querySelector('#horner-q').value),
        mu: parseFloat(box.querySelector('#horner-mu').value),
        b: parseFloat(box.querySelector('#horner-b').value),
        h: parseFloat(box.querySelector('#horner-h').value),
        pi: parseFloat(box.querySelector('#horner-pi').value),
        rw: 0.25, phi: 0.2, ct: 1e-5,
      };
      const r = Charts.horner(box.querySelector('#hornerChart'), tp, points, params);
      if (r) box.querySelector('#hornerResults').innerHTML = `<strong>Slope m:</strong> ${fmtNum(r.slope)} psi/cycle &nbsp; <strong>k:</strong> ${fmtNum(r.k)} mD &nbsp; <strong>Skin:</strong> ${fmtNum(r.skin)}`;
    };
    return box;
  }

  function buildDeclineSection() {
    const box = document.createElement('div');
    box.className = 'chart-box';
    box.innerHTML = `<h4>Decline curve plotter</h4>
      <div class="calc-inputs">
        <div class="field"><label>Model</label><select id="decl-type" aria-label="Decline type"><option value="exp">Exponential</option><option value="hyper">Hyperbolic</option><option value="harm">Harmonic</option></select></div>
        <div class="field"><label>qi</label><input type="number" id="decl-qi" value="1000" aria-label="Initial rate"></div>
        <div class="field"><label>Di (1/day)</label><input type="number" id="decl-di" value="0.001" step="any" aria-label="Decline constant"></div>
        <div class="field"><label>b</label><input type="number" id="decl-b" value="0.5" step="any" aria-label="b factor"></div>
        <div class="field"><label>t max (days)</label><input type="number" id="decl-tmax" value="3650" aria-label="Max time"></div>
      </div>
      <button type="button" class="btn primary" id="declPlotBtn">Plot decline</button><div id="declChart"></div>`;
    box.querySelector('#declPlotBtn').onclick = () => {
      Charts.decline(box.querySelector('#declChart'), box.querySelector('#decl-type').value,
        parseFloat(box.querySelector('#decl-qi').value), parseFloat(box.querySelector('#decl-di').value),
        parseFloat(box.querySelector('#decl-b').value), parseFloat(box.querySelector('#decl-tmax').value));
    };
    return box;
  }

  function buildNodalSection() {
    const box = document.createElement('div');
    box.className = 'chart-box';
    box.innerHTML = `<h4>Nodal analysis / IPR + tubing curve</h4>
      <div class="calc-inputs">
        <div class="field"><label>IPR type</label><select id="nod-ipr" aria-label="IPR type"><option value="vogel">Vogel</option><option value="linear">Linear (PI)</option></select></div>
        <div class="field"><label>Pr (psi)</label><input type="number" id="nod-pr" value="4000" aria-label="Reservoir pressure"></div>
        <div class="field"><label>qmax or PI</label><input type="number" id="nod-qmax" value="3000" aria-label="qmax or PI"></div>
      </div>
      <div class="field"><label>VLP points (q, Pwf — one per line)</label><textarea id="nod-vlp" rows="4" aria-label="VLP data" style="width:100%;padding:.75rem;border-radius:10px;border:1px solid var(--color-border)">0,4000\n500,3500\n1000,2800\n1500,2000\n2000,1200\n2500,500</textarea></div>
      <button type="button" class="btn primary" id="nodPlotBtn">Plot nodal</button><div id="nodChart"></div><div id="nodMatch" class="footer-note"></div>`;
    box.querySelector('#nodPlotBtn').onclick = () => {
      const vlp = box.querySelector('#nod-vlp').value.trim().split('\n').map(l => { const [q, pwf] = l.split(/[,\s]+/).map(Number); return { q, pwf }; }).filter(p => Number.isFinite(p.q));
      const iprType = box.querySelector('#nod-ipr').value;
      const pr = parseFloat(box.querySelector('#nod-pr').value);
      const qmax = parseFloat(box.querySelector('#nod-qmax').value);
      const match = Charts.nodal(box.querySelector('#nodChart'), iprType, pr, iprType === 'vogel' ? qmax : null, iprType === 'linear' ? qmax : 1, vlp);
      box.querySelector('#nodMatch').innerHTML = match ? `<strong>Intersection:</strong> q ≈ ${fmtNum(match.q)} stb/d, Pwf ≈ ${fmtNum(match.pwf)} psi` : 'No intersection found — adjust curves.';
    };
    return box;
  }

  function renderLibrary(segment = 'All', term = '') {
    activeSegment = segment;
    searchTerm = term.toLowerCase();
    renderNav(segment);
    els.library.innerHTML = '';
    let names = segment === 'All' ? segmentNames : segment === 'Favorites' ? segmentNames : [segment];
    const fav = getFavorites();
    names.forEach(name => {
      let rows = calcData[name];
      if (segment === 'Favorites') rows = rows.filter(r => fav.includes(calcKey(name, r[0])));
      rows = rows.filter(r => !term || (name + ' ' + r[0] + ' ' + r[1] + ' ' + r[2].join(' ')).toLowerCase().includes(term));
      if (!rows.length) return;
      const section = document.createElement('section');
      section.className = 'card';
      section.innerHTML = `<div class="section-title"><div><h3 style="margin:0">${highlightText(name, term)}</h3><div class="muted">${rows.length} calculations</div></div></div>`;
      const tableWrap = document.createElement('div');
      tableWrap.className = 'table-wrap';
      const table = document.createElement('table');
      table.innerHTML = '<thead><tr><th>Calculation</th><th>Formula / method</th><th>Primary inputs</th><th>Notes / Caution</th><th></th></tr></thead>';
      const tbody = document.createElement('tbody');
      rows.forEach(r => {
        const key = calcKey(name, r[0]);
        const spec = calcRegistry[key];
        const isFav = fav.includes(key);
        const tr = document.createElement('tr');
        tr.innerHTML = `<td><button type="button" class="star-btn ${isFav ? 'on' : ''}" data-fav="${escapeHtml(key)}" aria-label="Favorite">${isFav ? '★' : '☆'}</button> <strong>${highlightText(r[0], term)}</strong></td>
          <td><code>${highlightText(r[1], term)}</code></td>
          <td>${r[2].map(x => `<span class="pill">${highlightText(x, term)}</span>`).join(' ')}</td>
          <td class="muted tiny">${escapeHtml(spec?.notes || '')}</td>
          <td><button type="button" class="btn expand-btn" data-expand="${escapeHtml(key)}" aria-label="Expand">▸</button></td>`;
        tbody.appendChild(tr);
        const tr2 = document.createElement('tr');
        tr2.className = 'expand-row';
        tr2.style.display = 'none';
        tr2.dataset.expandRow = key;
        const td = document.createElement('td');
        td.colSpan = 5;
        td.appendChild(renderInteractiveCalc(name, r[0], r[1], spec));
        tr2.appendChild(td);
        tbody.appendChild(tr2);
      });
      table.appendChild(tbody);
      tableWrap.appendChild(table);
      section.appendChild(tableWrap);
      els.library.appendChild(section);
    });
    els.library.querySelectorAll('.expand-btn').forEach(btn => {
      btn.onclick = () => {
        const row = els.library.querySelector(`tr[data-expand-row="${btn.dataset.expand}"]`);
        const open = row.style.display !== 'none';
        row.style.display = open ? 'none' : 'table-row';
        btn.textContent = open ? '▸' : '▾';
      };
    });
    els.library.querySelectorAll('.star-btn[data-fav]').forEach(btn => {
      btn.onclick = () => {
        const on = toggleFavorite(btn.dataset.fav);
        btn.textContent = on ? '★' : '☆';
        btn.classList.toggle('on', on);
        if (activeSegment === 'Favorites') renderLibrary('Favorites', searchTerm);
        else renderNav(activeSegment);
      };
    });
    if (!els.library.children.length) {
      els.library.innerHTML = '<div class="card"><h3>No matches</h3><p class="muted">Try pressure, buildup, choke, ECD, or annulus.</p></div>';
    }
  }

  /* Converter */
  const converterFamilies = {
    pressure: UNIT_FAMILIES.pressure.units,
    length: UNIT_FAMILIES.length.units,
    volume: UNIT_FAMILIES.volume.units,
    rate_liquid: UNIT_FAMILIES.rate_liquid.units,
    density: UNIT_FAMILIES.density.units,
    gradient: UNIT_FAMILIES.gradient.units,
    temperature: null,
    force: UNIT_FAMILIES.force.units,
    power: UNIT_FAMILIES.power_hp.units,
    gas_rate: UNIT_FAMILIES.rate_gas.units,
  };
  const familySel = document.getElementById('family');
  const fromUnit = document.getElementById('fromUnit');
  const toUnit = document.getElementById('toUnit');
  const fromValue = document.getElementById('fromValue');
  const convResult = document.getElementById('convResult');
  Object.keys(converterFamilies).forEach(k => {
    const o = document.createElement('option'); o.value = k; o.textContent = k.replace('_', ' '); familySel.appendChild(o);
  });
  function fillUnits() {
    const fam = familySel.value;
    fromUnit.innerHTML = ''; toUnit.innerHTML = '';
    const units = fam === 'temperature' ? ['C', 'F', 'K'] : Object.keys(converterFamilies[fam]);
    units.forEach((u, i) => {
      const a = document.createElement('option'); a.value = u; a.textContent = u; fromUnit.appendChild(a);
      const b = document.createElement('option'); b.value = u; b.textContent = u; toUnit.appendChild(b);
      if (i === 1) toUnit.value = u;
    });
    convert();
  }
  function convert() {
    const fam = familySel.value; const v = parseFloat(fromValue.value);
    if (Number.isNaN(v)) { convResult.textContent = 'Enter a number'; return; }
    let result;
    if (fam === 'temperature') {
      const f = fromUnit.value, t = toUnit.value;
      let c = f === 'C' ? v : (f === 'F' ? (v - 32) * 5 / 9 : v - 273.15);
      result = t === 'C' ? c : (t === 'F' ? (c * 9 / 5 + 32) : c + 273.15);
    } else {
      const base = v / converterFamilies[fam][fromUnit.value];
      result = base * converterFamilies[fam][toUnit.value];
    }
    convResult.textContent = `${fmtNum(result)} ${toUnit.value}`;
  }
  familySel.onchange = fillUnits; fromUnit.onchange = convert; toUnit.onchange = convert; fromValue.oninput = convert; fillUnits();

  /* Quick calc */
  Object.entries(quickDefs).forEach(([k, d]) => {
    const o = document.createElement('option'); o.value = k; o.textContent = d.label; els.quickCalc.appendChild(o);
  });
  function fillQuickFields() {
    const d = quickDefs[els.quickCalc.value];
    els.quickFields.innerHTML = '';
    d.inputs.forEach(([id, lbl, family]) => els.quickFields.appendChild(createUnitField(`quick-${id}`, lbl, family, unitSystem, d.label, id)));
    els.calcResult.textContent = '—';
  }
  els.quickCalc.onchange = fillQuickFields; fillQuickFields();
  document.getElementById('runCalc').onclick = () => {
    const d = quickDefs[els.quickCalc.value];
    const raw = {}; const us = {}; let ok = true;
    d.inputs.forEach(([id, , family]) => {
      const inp = document.getElementById(`quick-${id}`);
      const sel = inp?.closest('.field-row')?.querySelector('select');
      const n = parseFloat(inp?.value);
      if (Number.isNaN(n)) ok = false;
      else { us[id] = sel?.value; raw[id] = UnitConv.toBase(n, us[id], family); }
    });
    if (!ok) { els.calcResult.textContent = 'Enter all inputs'; return; }
    const resultBase = d.fn(raw);
    const outU = UnitConv.getPreferredUnit(d.outFamily, unitSystem);
    const result = UnitConv.fromBase(resultBase, outU, d.outFamily);
    els.calcResult.textContent = `${fmtNum(result)} ${outU}`;
    logHistory({ name: d.label, formula: d.label, inputs: d.inputs.map(([id, lbl]) => lbl).join(', '), result: fmtNum(result), unit: outU });
  };
  document.getElementById('resetCalc').onclick = fillQuickFields;

  els.search.addEventListener('input', () => renderLibrary(activeSegment, els.search.value.trim().toLowerCase()));

  els.themeBtn.onclick = () => {
    themeIdx = (themeIdx + 1) % themes.length;
    document.documentElement.setAttribute('data-theme', themes[themeIdx]);
    Store.set(STORAGE_KEYS.theme, themes[themeIdx]);
    els.themeBtn.textContent = `Theme: ${themes[themeIdx]}`;
  };
  els.themeBtn.textContent = `Theme: ${themes[themeIdx]}`;

  els.unitSystemSel.value = unitSystem;
  els.unitSystemSel.onchange = () => { unitSystem = els.unitSystemSel.value; applyUnitSystem(); fillQuickFields(); };

  els.menuBtn.onclick = () => { els.sidebar.classList.toggle('open'); els.overlay.classList.toggle('open'); };
  els.histBtn.onclick = () => { els.historyPanel.classList.toggle('open'); els.overlay.classList.toggle('open'); };
  els.overlay.onclick = () => { els.sidebar.classList.remove('open'); els.historyPanel.classList.remove('open'); els.overlay.classList.remove('open'); };

  document.getElementById('exportCsvBtn').onclick = exportHistoryCSV;
  document.getElementById('reportBtn').onclick = generateReport;

  renderHistory();
  renderLibrary();
  registerPWA();
}
