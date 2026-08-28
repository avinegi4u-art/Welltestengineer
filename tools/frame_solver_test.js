// Standalone test for 2D plane frame solver (run: node tools/frame_solver_test.js)
'use strict';

function matZero(n) { return Array.from({ length: n }, () => new Float64Array(n)); }
function vecZero(n) { return new Float64Array(n); }

function addToK(K, i, j, v) { K[i][j] += v; }

function beamLocalStiff(E, A, I, L) {
  const EA = E * A, EI = E * I, L2 = L * L, L3 = L2 * L;
  return [
    [EA / L, 0, 0, -EA / L, 0, 0],
    [0, 12 * EI / L3, 6 * EI / L2, 0, -12 * EI / L3, 6 * EI / L2],
    [0, 6 * EI / L2, 4 * EI / L, 0, -6 * EI / L2, 2 * EI / L],
    [-EA / L, 0, 0, EA / L, 0, 0],
    [0, -12 * EI / L3, -6 * EI / L2, 0, 12 * EI / L3, -6 * EI / L2],
    [0, 6 * EI / L2, 2 * EI / L, 0, -6 * EI / L2, 4 * EI / L],
  ];
}

function rot2(c, s) {
  return [[c, s, 0], [-s, c, 0], [0, 0, 1]];
}

function mul33(A, B) {
  const R = [[0, 0, 0], [0, 0, 0], [0, 0, 0]];
  for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) for (let k = 0; k < 3; k++) R[i][j] += A[i][k] * B[k][j];
  return R;
}

function transformBeamK(kL, c, s) {
  const T = [[c, s, 0, 0, 0, 0], [-s, c, 0, 0, 0, 0], [0, 0, 1, 0, 0, 0], [0, 0, 0, c, s, 0], [0, 0, 0, -s, c, 0], [0, 0, 0, 0, 0, 1]];
  const TT = Array.from({ length: 6 }, (_, i) => T.map(r => r[i]));
  const tmp = Array.from({ length: 6 }, () => new Array(6).fill(0));
  for (let i = 0; i < 6; i++) for (let j = 0; j < 6; j++) for (let k = 0; k < 6; k++) tmp[i][j] += TT[i][k] * kL[k][j];
  const kg = Array.from({ length: 6 }, () => new Array(6).fill(0));
  for (let i = 0; i < 6; i++) for (let j = 0; j < 6; j++) for (let k = 0; k < 6; k++) kg[i][j] += tmp[i][k] * T[k][j];
  return kg;
}

function trussGlobalK(E, A, L, c, s) {
  const k = E * A / L;
  const cx = c * c, cs = c * s, ss = s * s;
  return [
    [k * cx, k * cs, 0, -k * cx, -k * cs, 0],
    [k * cs, k * ss, 0, -k * cs, -k * ss, 0],
    [0, 0, 0, 0, 0, 0],
    [-k * cx, -k * cs, 0, k * cx, k * cs, 0],
    [-k * cs, -k * ss, 0, k * cs, k * ss, 0],
    [0, 0, 0, 0, 0, 0],
  ];
}

function assembleBeam(K, F, n0, n1, E, A, I, x0, z0, x1, z1, qx, qz) {
  const dx = x1 - x0, dz = z1 - z0, L = Math.hypot(dx, dz);
  if (L < 1e-9) return;
  const c = dx / L, s = dz / L;
  const kG = transformBeamK(beamLocalStiff(E, A, I, L), c, s);
  const map = [3 * n0, 3 * n0 + 1, 3 * n0 + 2, 3 * n1, 3 * n1 + 1, 3 * n1 + 2];
  for (let a = 0; a < 6; a++) for (let b = 0; b < 6; b++) addToK(K, map[a], map[b], kG[a][b]);
  // Fixed-end forces for global UDL (qx, qz) on inclined member -> equivalent nodal loads
  const qn = -qx * s + qz * c; // normal to member in local y
  const qt = qx * c + qz * s;  // tangential
  const V0 = qn * L / 2, M0 = qn * L * L / 12, V1 = qn * L / 2, M1 = -qn * L * L / 12;
  const N0 = qt * L / 2, N1 = qt * L / 2;
  const feL = [N0, V0, M0, N1, V1, M1];
  const T = [[c, s, 0, 0, 0, 0], [-s, c, 0, 0, 0, 0], [0, 0, 1, 0, 0, 0], [0, 0, 0, c, s, 0], [0, 0, 0, -s, c, 0], [0, 0, 0, 0, 0, 1]];
  for (let a = 0; a < 6; a++) {
    let fg = 0;
    for (let b = 0; b < 6; b++) fg += T[a][b] * feL[b];
    F[map[a]] += fg;
  }
}

function assembleTruss(K, n0, n1, E, A, x0, z0, x1, z1) {
  const dx = x1 - x0, dz = z1 - z0, L = Math.hypot(dx, dz);
  if (L < 1e-9) return;
  const c = dx / L, s = dz / L;
  const kG = trussGlobalK(E, A, L, c, s);
  const map = [3 * n0, 3 * n0 + 1, 3 * n0 + 2, 3 * n1, 3 * n1 + 1, 3 * n1 + 2];
  for (let a = 0; a < 6; a++) for (let b = 0; b < 6; b++) addToK(K, map[a], map[b], kG[a][b]);
}

function solveFrame(nodes, elements, supports, pointLoads) {
  const n = nodes.length;
  const ndof = 3 * n;
  const K = matZero(ndof);
  const F = vecZero(ndof);
  for (const pl of pointLoads) {
    F[3 * pl.node + 0] += pl.fx || 0;
    F[3 * pl.node + 1] += pl.fz || 0;
    F[3 * pl.node + 2] += pl.my || 0;
  }
  for (const el of elements) {
    const p0 = nodes[el.i], p1 = nodes[el.j];
    if (el.type === 'beam') assembleBeam(K, F, el.i, el.j, el.E, el.A, el.I, p0.x, p0.z, p1.x, p1.z, el.qx || 0, el.qz || 0);
    else assembleTruss(K, el.i, el.j, el.E, el.A, p0.x, p0.z, p1.x, p1.z);
  }
  const fixed = new Set();
  for (const s of supports) {
    if (s.ux) fixed.add(3 * s.node);
    if (s.uz) fixed.add(3 * s.node + 1);
    if (s.ry) fixed.add(3 * s.node + 2);
  }
  const free = [];
  for (let i = 0; i < ndof; i++) if (!fixed.has(i)) free.push(i);
  const nf = free.length;
  const Kff = matZero(nf);
  const Ff = vecZero(nf);
  for (let a = 0; a < nf; a++) {
    Ff[a] = F[free[a]];
    for (let b = 0; b < nf; b++) Kff[a][b] = K[free[a]][free[b]];
  }
  const u = vecZero(ndof);
  const uf = gaussSolve(Kff, Ff);
  for (let a = 0; a < nf; a++) u[free[a]] = uf[a];
  const R = vecZero(ndof);
  for (let i = 0; i < ndof; i++) {
    let sum = 0;
    for (let j = 0; j < ndof; j++) sum += K[i][j] * u[j];
    R[i] = sum - F[i];
  }
  return { u, R, ndof };
}

function gaussSolve(A, b) {
  const n = b.length;
  const M = A.map((row, i) => [...row, b[i]]);
  for (let col = 0; col < n; col++) {
    let piv = col;
    for (let r = col + 1; r < n; r++) if (Math.abs(M[r][col]) > Math.abs(M[piv][col])) piv = r;
    [M[col], M[piv]] = [M[piv], M[col]];
    const d = M[col][col];
    if (Math.abs(d) < 1e-12) throw new Error('Singular stiffness matrix');
    for (let j = col; j <= n; j++) M[col][j] /= d;
    for (let r = 0; r < n; r++) {
      if (r === col) continue;
      const f = M[r][col];
      for (let j = col; j <= n; j++) M[r][j] -= f * M[col][j];
    }
  }
  return M.map(row => row[n]);
}

// Cantilever test: horizontal beam L=10000, E=200000, A=3000, I=1e7, UDL wz=-0.01 N/mm
const L = 10000, E = 200000, A = 3000, I = 1e7, wz = -0.01;
const nodes = [{ x: 0, z: 0 }, { x: L, z: 0 }];
const elements = [{ type: 'beam', i: 0, j: 1, E, A, I, qx: 0, qz: wz }];
const supports = [{ node: 0, ux: true, uz: true, ry: true }];
const { u, R } = solveFrame(nodes, elements, supports, []);
const Mbase = R[2]; // moment reaction at base
const Mtheory = -wz * L * L / 2;
const dTip = u[3 * 1 + 1];
const dTheory = -wz * Math.pow(L, 4) / (8 * E * I);
console.log('Cantilever M base:', Mbase.toFixed(0), 'theory', Mtheory.toFixed(0), 'err%', ((Mbase - Mtheory) / Mtheory * 100).toFixed(2));
console.log('Cantilever tip defl:', dTip.toFixed(2), 'theory', dTheory.toFixed(2), 'err%', ((dTip - dTheory) / dTheory * 100).toFixed(2));
