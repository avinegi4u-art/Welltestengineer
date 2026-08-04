/**
 * welltest-pta-engine.js
 * Port of welltest-pta 0.1.0 (MIT) — V8.1 event detector + vSH04 deconvolution.
 * Adapted for DST Pressure Transient Analyzer Pro (browser, no dependencies).
 */
(function (global) {
  "use strict";

  const DEFAULT_CFG = {
    sgWindow: 0,
    sgPolyorder: 3,
    sgMinWindow: 15,
    sgMaxWindow: 301,
    hampelWindow: 0,
    hampelSigma: 3.0,
    pResOverride: 0,
    pResStablePct: 20,
    pResMinPts: 30,
    spikePercentile: 95,
    spikeMinGapPts: 0,
    minZonePts: 10,
    minPtaDpPsi: 15,
    minPtaDurationHr: 0.1,
    mergeGapMaxPts: 0,
    tailTrimEnabled: true,
    tailTrimMinDurHr: 4,
    tailTrimMinPlateauFrac: 0.4,
    tailTrimDevNSigma: 8,
    tailTrimMinTailDurHr: 0.3
  };

  function median(arr) {
    const a = arr.filter(Number.isFinite).slice().sort((x, y) => x - y);
    if (!a.length) return NaN;
    const m = Math.floor(a.length / 2);
    return a.length % 2 ? a[m] : (a[m - 1] + a[m]) / 2;
  }

  function percentile(arr, p) {
    const a = arr.filter(Number.isFinite).slice().sort((x, y) => x - y);
    if (!a.length) return NaN;
    const idx = (p / 100) * (a.length - 1);
    const lo = Math.floor(idx);
    const hi = Math.ceil(idx);
    if (lo === hi) return a[lo];
    return a[lo] + (a[hi] - a[lo]) * (idx - lo);
  }

  function odd(w, mn = 5) {
    w = Math.max(w, mn);
    return w % 2 === 0 ? w + 1 : w;
  }

  function contiguous(mask) {
    const regions = [];
    let inR = false;
    let start = 0;
    for (let i = 0; i < mask.length; i += 1) {
      if (mask[i] && !inR) {
        start = i;
        inR = true;
      } else if (!mask[i] && inR) {
        regions.push([start, i]);
        inR = false;
      }
    }
    if (inR) regions.push([start, mask.length]);
    return regions;
  }

  function rle(labels) {
    const groups = [];
    if (!labels.length) return groups;
    let cur = labels[0];
    let start = 0;
    for (let i = 1; i < labels.length; i += 1) {
      if (labels[i] !== cur) {
        groups.push([start, i, cur]);
        cur = labels[i];
        start = i;
      }
    }
    groups.push([start, labels.length, cur]);
    return groups;
  }

  function sgCoeffs(windowSize, polyOrder, deriv = 0, delta = 1) {
    const half = (windowSize - 1) / 2;
    const rows = windowSize;
    const cols = polyOrder + 1;
    const A = Array.from({length: rows}, (_, i) => {
      const x = i - half;
      const row = [];
      for (let p = 0; p < cols; p += 1) row.push(Math.pow(x, p));
      return row;
    });
    const pinv = pseudoInverse(A);
    const row = pinv[deriv] || pinv[0];
    const fact = Math.pow(delta, -deriv);
    for (let i = 0; i < row.length; i += 1) row[i] *= fact;
    return row;
  }

  function pseudoInverse(matrix) {
    const m = matrix.length;
    const n = matrix[0].length;
    const ata = Array.from({length: n}, () => Array(n).fill(0));
    for (let i = 0; i < n; i += 1) {
      for (let j = 0; j < n; j += 1) {
        let s = 0;
        for (let k = 0; k < m; k += 1) s += matrix[k][i] * matrix[k][j];
        ata[i][j] = s;
      }
    }
    return invertMatrix(ata).map(row => {
      const out = Array(m).fill(0);
      for (let j = 0; j < m; j += 1) {
        for (let i = 0; i < n; i += 1) out[j] += row[i] * matrix[j][i];
      }
      return out;
    });
  }

  function invertMatrix(m) {
    const n = m.length;
    const aug = m.map((row, i) => [...row, ...Array.from({length: n}, (_, j) => (i === j ? 1 : 0))]);
    for (let col = 0; col < n; col += 1) {
      let pivot = col;
      for (let row = col + 1; row < n; row += 1) {
        if (Math.abs(aug[row][col]) > Math.abs(aug[pivot][col])) pivot = row;
      }
      [aug[col], aug[pivot]] = [aug[pivot], aug[col]];
      const div = aug[col][col] || 1e-12;
      for (let j = 0; j < 2 * n; j += 1) aug[col][j] /= div;
      for (let row = 0; row < n; row += 1) {
        if (row === col) continue;
        const factor = aug[row][col];
        for (let j = 0; j < 2 * n; j += 1) aug[row][j] -= factor * aug[col][j];
      }
    }
    return aug.map(row => row.slice(n));
  }

  function savgolFilter(series, windowSize, polyOrder, deriv = 0, delta = 1) {
    const n = series.length;
    if (n < 3) return series.slice();
    const w = odd(Math.min(windowSize, n - 1), polyOrder + 2);
    const half = (w - 1) / 2;
    const coeffs = sgCoeffs(w, polyOrder, deriv, delta);
    const out = new Array(n);
    for (let i = 0; i < n; i += 1) {
      let sum = 0;
      for (let j = 0; j < w; j += 1) {
        const idx = Math.min(Math.max(i - half + j, 0), n - 1);
        sum += coeffs[j] * series[idx];
      }
      out[i] = sum;
    }
    return out;
  }

  function hampelFilter(series, window, nSigmas = 3) {
    const n = series.length;
    if (!n) return series.slice();
    window = Math.max(3, window);
    if (window % 2 === 0) window += 1;
    const half = Math.floor(window / 2);
    const out = series.slice();
    for (let i = 0; i < n; i += 1) {
      const start = Math.max(0, i - half);
      const end = Math.min(n, i + half + 1);
      const slice = series.slice(start, end);
      const med = median(slice);
      const mad = median(slice.map(v => Math.abs(v - med))) || 1e-9;
      const stdMad = 1.4826 * mad;
      if (Math.abs(series[i] - med) > nSigmas * stdMad) out[i] = med;
    }
    return out;
  }

  class EventDetector {
    constructor(cfg = {}) {
      this.cfg = {...DEFAULT_CFG, ...cfg};
      this.sgWindow = 21;
      this.pRes = 0;
      this.spikeThr = 100;
      this.noiseFloor = 1;
    }

    detect(rows) {
      if (!rows || rows.length < 20) throw new Error(`Too few data points (${rows?.length || 0})`);
      const df = this.computeDerivatives(rows);
      this.pRes = this.detectPres(df);
      const {mask: validMask, ptaStart, ptaEnd} = this.maskEdges(df, this.pRes);
      const boundaries = this.detectSpikeBoundaries(df, ptaStart, ptaEnd);
      let labels = this.classifyZones(df, boundaries, ptaStart, ptaEnd, validMask);
      labels = this.absorbPauses(labels, df);
      labels = this.mergeSameType(labels, df);
      labels = this.absorbTinyGaps(labels, df);
      labels = this.mergeSameType(labels, df);
      labels = this.validate(labels, df);
      labels = this.trimEdges(labels, df);
      labels = this.trimBuildupTails(labels, df);
      labels = this.mergeSameType(labels, df);
      labels = this.absorbTinyGaps(labels, df);
      labels = this.mergeSameType(labels, df);
      return {
        labels,
        pReservoir: this.pRes,
        noiseFloor: this.noiseFloor,
        pSmooth: df.pSmooth,
        dpdt: df.dpdt,
        elapsedHr: df.elapsedHr
      };
    }

    computeDerivatives(rows) {
      const cfg = this.cfg;
      const n = rows.length;
      const t0 = rows[0].timeMs;
      const hours = rows.map(r => (r.timeMs - t0) / 3600000);
      const diffs = hours.slice(1).map((h, i) => h - hours[i]);
      const mdt = Math.max(median(diffs) || 1e-3, 1e-6);

      const pRaw = rows.map(r => r.bhp);
      let hw = cfg.hampelWindow;
      if (!hw) {
        hw = Math.max(Math.floor(180 / (mdt * 3600)), Math.floor(n * 0.005), 5);
        hw = Math.min(hw, 51);
      }
      const pClean = hampelFilter(pRaw, hw, cfg.hampelSigma);

      let sgW = cfg.sgWindow;
      if (!sgW) {
        sgW = Math.max(Math.floor(n * 0.005), Math.max(Math.floor(3 / 60 / mdt), 15), cfg.sgMinWindow);
        sgW = Math.min(sgW, cfg.sgMaxWindow, n - 1);
      }
      this.sgWindow = odd(sgW);
      const wf = odd(Math.min(this.sgWindow, n - 1), cfg.sgPolyorder + 2);
      const pSmooth = savgolFilter(pClean, wf, cfg.sgPolyorder, 0, mdt);
      const dpdt = savgolFilter(pClean, wf, cfg.sgPolyorder, 1, mdt);

      const residuals = pRaw.map((p, i) => p - pSmooth[i]);
      this.noiseFloor = Math.max(percentile(residuals.map(Math.abs), 75), 0.5);

      return {elapsedHr: hours, pSmooth, dpdt, mdt};
    }

    detectPres(df) {
      const cfg = this.cfg;
      if (cfg.pResOverride > 0) return cfg.pResOverride;
      const p = df.pSmooth;
      const dpdt = df.dpdt.map(Math.abs);
      const dpf = dpdt.filter(Number.isFinite);
      if (dpf.length < 10) return Math.max(...p);

      const thr = Math.max(percentile(dpf, cfg.pResStablePct), 0.5);
      const stable = dpdt.map(v => v < thr);
      if (stable.filter(Boolean).length < cfg.pResMinPts) return percentile(p, 95);

      const regions = contiguous(stable).filter(([s, e]) => e - s >= cfg.pResMinPts);
      if (!regions.length) return percentile(p.filter((_, i) => stable[i]), 95);

      let bestM = -Infinity;
      let best = null;
      for (const [s, e] of regions) {
        const slice = p.slice(s, e);
        const m = slice.reduce((a, b) => a + b, 0) / slice.length;
        if (m > bestM) {
          bestM = m;
          best = [s, e];
        }
      }
      return bestM;
    }

    maskEdges(df, P_res) {
      const p = df.pSmooth;
      const n = p.length;
      const cfg = this.cfg;
      const approach = P_res * (P_res < 100 ? 0.7 : 0.85);
      const confirm = Math.max(Math.floor(cfg.pResMinPts / 3), 5);

      let ptaStart = 0;
      for (let i = 0; i < n; i += 1) {
        if (p[i] >= approach) {
          const slice = p.slice(i, Math.min(i + confirm, n));
          const mean = slice.reduce((a, b) => a + b, 0) / slice.length;
          if (mean >= approach * 0.95) {
            ptaStart = Math.max(0, i - confirm);
            break;
          }
        }
      }

      let ptaEnd = n - 1;
      let lastAt = -1;
      for (let i = n - 1; i >= 0; i -= 1) {
        if (p[i] >= approach) {
          lastAt = i;
          break;
        }
      }
      if (lastAt > ptaStart) {
        const ext = Math.min(confirm * 3, n - 1 - lastAt);
        ptaEnd = lastAt + ext;
        const crash = P_res * 0.5;
        for (let j = lastAt; j <= Math.min(ptaEnd, n - 1); j += 1) {
          if (p[j] < crash) {
            ptaEnd = Math.max(lastAt, j - 1);
            break;
          }
        }
        ptaEnd = Math.min(ptaEnd, n - 1);
      }

      const mask = new Array(n).fill(false);
      for (let i = ptaStart; i <= ptaEnd; i += 1) mask[i] = true;
      return {mask, ptaStart, ptaEnd};
    }

    detectSpikeBoundaries(df, ptaStart, ptaEnd) {
      const cfg = this.cfg;
      const dpdt = df.dpdt;
      const p = df.pSmooth;
      const n = dpdt.length;
      const ptaDpdt = dpdt.slice(ptaStart, ptaEnd + 1).map(Math.abs).filter(Number.isFinite);
      const spikeBounds = [];
      if (ptaDpdt.length > 10) {
        this.spikeThr = Math.max(percentile(ptaDpdt, cfg.spikePercentile), 5, this.noiseFloor * 5);
        const absDpdt = dpdt.map(Math.abs);
        const isSpike = absDpdt.map((v, i) => i >= ptaStart && i <= ptaEnd && v > this.spikeThr);
        let minGap = cfg.spikeMinGapPts || Math.max(Math.floor(n * 0.005), 10);
        let inSpike = false;
        let lastBnd = ptaStart;
        for (let i = ptaStart; i <= ptaEnd; i += 1) {
          if (isSpike[i] && !inSpike) {
            if (i - lastBnd >= minGap) {
              spikeBounds.push(i);
              lastBnd = i;
            }
            inSpike = true;
          } else if (!isSpike[i] && inSpike) inSpike = false;
        }
      }

      const tpBounds = [];
      const ptaP = p.slice(ptaStart, ptaEnd + 1);
      const ptaN = ptaP.length;
      if (ptaN > 50) {
        let tpWin = odd(Math.max(Math.floor(ptaN * 0.05), 15));
        tpWin = Math.min(tpWin, ptaN - 1);
        let pHeavy;
        try {
          pHeavy = savgolFilter(ptaP, tpWin, 2);
        } catch (_) {
          pHeavy = ptaP;
        }
        const dpHeavy = pHeavy.slice(1).map((v, i) => v - pHeavy[i]);
        const signs = dpHeavy.map(v => Math.sign(v));
        for (let sc = 0; sc < signs.length - 1; sc += 1) {
          if (signs[sc] === signs[sc + 1] || signs[sc] === 0 || signs[sc + 1] === 0) continue;
          const tpIdx = sc + 1 + ptaStart;
          if (tpIdx <= ptaStart + 20 || tpIdx >= ptaEnd - 20) continue;
          const localP = p[tpIdx];
          const windowSize = Math.max(50, Math.floor(ptaN * 0.05));
          const leftP = p.slice(Math.max(0, tpIdx - windowSize), tpIdx);
          const rightP = p.slice(tpIdx + 1, Math.min(n, tpIdx + windowSize));
          if (leftP.length < 5 || rightP.length < 5) continue;
          const pRange = Math.max(...ptaP) - Math.min(...ptaP);
          const minProm = Math.max(pRange * 0.03, this.noiseFloor * 10, 10);
          if (Math.min(...leftP) > localP + minProm && Math.min(...rightP) > localP + minProm) tpBounds.push(tpIdx);
          else if (Math.max(...leftP) < localP - minProm && Math.max(...rightP) < localP - minProm) tpBounds.push(tpIdx);
        }
      }

      const allBounds = [...new Set([...spikeBounds, ...tpBounds])].sort((a, b) => a - b);
      const validated = [];
      const checkWindow = Math.max(Math.floor(0.01 * n), 10);
      for (const b of allBounds) {
        const preStart = Math.max(ptaStart, b - checkWindow);
        const postEnd = Math.min(ptaEnd, b + checkWindow);
        const pBefore = median(p.slice(preStart, b));
        const pAfter = median(p.slice(b, postEnd));
        if (Math.abs(pBefore - pAfter) > this.noiseFloor * 5) validated.push(b);
      }
      return validated;
    }

    classifyZones(df, boundaries, ptaStart, ptaEnd, validMask) {
      const cfg = this.cfg;
      const p = df.pSmooth;
      const hours = df.elapsedHr;
      const n = p.length;
      const labels = new Array(n).fill("non_pta");
      const zoneEdges = [...new Set([ptaStart, ...boundaries, ptaEnd + 1])].sort((a, b) => a - b);
      const zones = [];
      for (let i = 0; i < zoneEdges.length - 1; i += 1) {
        const zs = zoneEdges[i];
        const ze = zoneEdges[i + 1];
        if (ze - zs >= 2) zones.push([zs, ze]);
      }

      for (const [zs, ze] of zones) {
        const zeSafe = Math.min(ze - 1, n - 1);
        const pStart = median(p.slice(zs, Math.min(zs + 5, ze)));
        const pEnd = median(p.slice(Math.max(zs, ze - 5), ze));
        const netDp = pEnd - pStart;
        const dur = hours[zeSafe] - hours[zs];
        const absDp = Math.abs(netDp);
        let label;
        if (!validMask[zs]) label = "non_pta";
        else if (absDp < Math.max(cfg.minPtaDpPsi, this.noiseFloor * 5) || dur < cfg.minPtaDurationHr) label = "pause";
        else if (netDp < 0) label = "drawdown";
        else label = "buildup";
        for (let i = zs; i < ze; i += 1) labels[i] = label;
      }
      return labels;
    }

    absorbPauses(labels, df) {
      let refined = labels.slice();
      const p = df.pSmooth;
      let changed = true;
      while (changed) {
        changed = false;
        const groups = rle(refined);
        for (let i = 0; i < groups.length; i += 1) {
          const [s, e, l] = groups[i];
          if (l !== "pause") continue;
          const left = i > 0 ? groups[i - 1][2] : "non_pta";
          const right = i < groups.length - 1 ? groups[i + 1][2] : "non_pta";
          if (left === right && (left === "drawdown" || left === "buildup")) {
            for (let j = s; j < e; j += 1) refined[j] = left;
            changed = true;
            break;
          } else if ((left === "drawdown" || left === "buildup") && (right === "drawdown" || right === "buildup")) {
            const netDp = p[Math.min(e - 1, p.length - 1)] - p[s];
            const fill = netDp < 0 ? "drawdown" : "buildup";
            for (let j = s; j < e; j += 1) refined[j] = fill;
            changed = true;
            break;
          } else if (left === "drawdown" || left === "buildup") {
            for (let j = s; j < e; j += 1) refined[j] = left;
            changed = true;
            break;
          } else if (right === "drawdown" || right === "buildup") {
            for (let j = s; j < e; j += 1) refined[j] = right;
            changed = true;
            break;
          } else {
            for (let j = s; j < e; j += 1) refined[j] = "non_pta";
            changed = true;
            break;
          }
        }
      }
      return refined.map(l => (l === "pause" ? "non_pta" : l));
    }

    mergeSameType(labels, df) {
      const p = df.pSmooth;
      const hours = df.elapsedHr;
      let refined = labels.slice();
      let changed = true;
      while (changed) {
        changed = false;
        const groups = rle(refined);
        if (groups.length < 3) break;
        for (let i = 0; i < groups.length - 1; i += 1) {
          const [s1, e1, l1] = groups[i];
          const [s2, e2, l2] = groups[i + 1];
          if (l1 === l2 && ["drawdown", "buildup", "non_pta"].includes(l1)) {
            for (let j = s1; j < e2; j += 1) refined[j] = l1;
            changed = true;
            break;
          }
        }
        if (changed) continue;
        for (let i = 0; i < groups.length - 2; i += 1) {
          const [s1, e1, l1] = groups[i];
          const [s2, e2, l2] = groups[i + 1];
          const [s3, e3, l3] = groups[i + 2];
          if (!(["drawdown", "buildup"].includes(l1) && l1 === l3 && l2 !== l1)) continue;
          const es2 = Math.min(e2 - 1, p.length - 1);
          const midDp = Math.abs(p[es2] - p[s2]);
          const midDur = hours[es2] - hours[s2];
          const totalDp = Math.abs(p[Math.min(e3 - 1, p.length - 1)] - p[s1]);
          if (midDp < Math.max(totalDp * 0.2, this.noiseFloor * 10) && midDur < 0.5) {
            for (let j = s1; j < e3; j += 1) refined[j] = l1;
            changed = true;
            break;
          }
        }
      }
      return refined;
    }

    absorbTinyGaps(labels, df) {
      const refined = labels.slice();
      const groups = rle(refined);
      const n = df.pSmooth.length;
      for (let i = 0; i < groups.length; i += 1) {
        const [s, e, l] = groups[i];
        if (l !== "non_pta" || i === 0 || i === groups.length - 1) continue;
        const pts = e - s;
        const left = groups[i - 1][2];
        const right = groups[i + 1][2];
        if (!["drawdown", "buildup"].includes(left) || !["drawdown", "buildup"].includes(right)) continue;
        const thr = Math.max(20, Math.floor(n * 0.004));
        if (pts > thr) continue;
        const fill = left === right ? left : (pts < 10 ? left : left);
        for (let j = s; j < e; j += 1) refined[j] = fill;
      }
      return refined;
    }

    trimBuildupTails(labels, df) {
      const cfg = this.cfg;
      if (!cfg.tailTrimEnabled) return labels.slice();
      const refined = labels.slice();
      const p = df.pSmooth;
      const hours = df.elapsedHr;
      const n = p.length;
      const platTol = Math.max(this.noiseFloor * 4, 3);
      const tailThrPsi = Math.max(this.noiseFloor * cfg.tailTrimDevNSigma, 5);

      for (const [s, e, l] of rle(refined)) {
        if (l !== "buildup") continue;
        const zoneN = e - s;
        const es = Math.min(e - 1, n - 1);
        const zoneDur = hours[es] - hours[s];
        if (zoneDur < cfg.tailTrimMinDurHr || zoneN < 200) continue;
        const zoneP = p.slice(s, e);
        if (Math.max(...zoneP) - Math.min(...zoneP) < platTol * 4) continue;

        const nBins = Math.max(60, Math.floor(Math.sqrt(zoneN)));
        const hist = new Array(nBins).fill(0);
        const pMin = Math.min(...zoneP);
        const pMax = Math.max(...zoneP);
        const binW = (pMax - pMin) / nBins || 1;
        zoneP.forEach(v => {
          const idx = Math.min(nBins - 1, Math.floor((v - pMin) / binW));
          hist[idx] += 1;
        });
        let modeIdx = 0;
        hist.forEach((c, i) => { if (c > hist[modeIdx]) modeIdx = i; });
        const pPlateau = pMin + (modeIdx + 0.5) * binW;

        const onPlateau = zoneP.map(v => Math.abs(v - pPlateau) < platTol);
        const lateHalf = onPlateau.slice(Math.floor(zoneN / 2));
        const lateHalfCov = lateHalf.filter(Boolean).length / lateHalf.length;
        if (lateHalfCov < 0.3) continue;

        let lastPlLoc = -1;
        onPlateau.forEach((v, i) => { if (v) lastPlLoc = i; });
        if (lastPlLoc < 0) continue;
        const lastPlGlobal = s + lastPlLoc + 1;
        const plateauFrac = (lastPlGlobal - s) / zoneN;
        if (plateauFrac < cfg.tailTrimMinPlateauFrac) continue;

        const tailN = e - lastPlGlobal;
        const tailDur = lastPlGlobal < e ? hours[es] - hours[lastPlGlobal] : 0;
        if (tailN < 30 || tailDur < cfg.tailTrimMinTailDurHr) continue;

        const tailP = zoneP.slice(lastPlLoc + 1);
        const tailDev = Math.max(...tailP.map(v => Math.abs(v - pPlateau)));
        if (tailDev <= tailThrPsi) continue;
        for (let j = lastPlGlobal; j < e; j += 1) refined[j] = "non_pta";
      }
      return refined;
    }

    validate(labels, df) {
      const cfg = this.cfg;
      const refined = labels.slice();
      const p = df.pSmooth;
      const hours = df.elapsedHr;
      for (const [s, e, l] of rle(refined)) {
        if (!["drawdown", "buildup"].includes(l)) continue;
        const es = Math.min(e - 1, p.length - 1);
        const dur = hours[es] - hours[s];
        const dp = p[es] - p[s];
        if (dur < cfg.minPtaDurationHr || Math.abs(dp) < Math.max(cfg.minPtaDpPsi, this.noiseFloor * 5)) {
          for (let j = s; j < e; j += 1) refined[j] = "non_pta";
          continue;
        }
        if (l === "drawdown" && dp > cfg.minPtaDpPsi) {
          for (let j = s; j < e; j += 1) refined[j] = "buildup";
        } else if (l === "buildup" && dp < -cfg.minPtaDpPsi) {
          for (let j = s; j < e; j += 1) refined[j] = "drawdown";
        }
      }
      return refined;
    }

    trimEdges(labels, df) {
      const refined = labels.slice();
      const p = df.pSmooth;
      let changed = true;
      while (changed) {
        changed = false;
        const groups = rle(refined);
        const pta = groups.map((g, i) => [i, ...g]).filter(([, , , l]) => l === "drawdown" || l === "buildup");
        if (!pta.length) break;
        const [li, ls, le, ll] = pta[pta.length - 1];
        if (ll === "drawdown") {
          const after = groups.slice(li + 1).every(([, , l]) => l === "non_pta");
          if (after || li === groups.length - 1) {
            for (let j = ls; j < le; j += 1) refined[j] = "non_pta";
            changed = true;
            continue;
          }
        }
        const [fi, fs, fe, fl] = pta[0];
        if (fl === "buildup" && pta.length >= 2 && pta[1][3] === "buildup" && p[fs] > this.pRes * 0.8) {
          for (let j = fs; j < fe; j += 1) refined[j] = "non_pta";
          changed = true;
        }
      }
      return refined;
    }
  }

  function countPtaEvents(labels) {
    const groups = rle(labels).filter(([, , l]) => l === "drawdown" || l === "buildup");
    const nDd = groups.filter(([, , l]) => l === "drawdown").length;
    const nBu = groups.filter(([, , l]) => l === "buildup").length;
    return {nDd, nBu, groups};
  }

  function jaccardPtaMask(refLabels, altLabels) {
    const refPta = refLabels.map(l => l === "drawdown" || l === "buildup");
    const altPta = altLabels.map(l => l === "drawdown" || l === "buildup");
    const n = Math.min(refPta.length, altPta.length);
    let inter = 0;
    let union = 0;
    for (let i = 0; i < n; i += 1) {
      if (refPta[i] && altPta[i]) inter += 1;
      if (refPta[i] || altPta[i]) union += 1;
    }
    return union > 0 ? inter / union : 0;
  }

  function crossValidateDetector(rows, cfg = {}, opts = {}) {
    const nBootstrap = opts.nBootstrap || 6;
    const downsampleFrac = opts.downsampleFrac || 0.85;
    const perturbation = opts.perturbation || 0.2;
    const baseCfg = {...DEFAULT_CFG, ...cfg};
    const refDet = new EventDetector(baseCfg);
    const ref = refDet.detect(rows);
    const {nDd: refNDd, nBu: refNBu} = countPtaEvents(ref.labels);

    const nDds = [];
    const nBus = [];
    const jaccards = [];
    const n = rows.length;
    const keepN = Math.max(Math.floor(n * downsampleFrac), 100);

    for (let b = 0; b < nBootstrap; b += 1) {
      const idx = [];
      const used = new Set();
      while (idx.length < keepN) {
        const r = Math.floor(Math.random() * n);
        if (!used.has(r)) {
          used.add(r);
          idx.push(r);
        }
      }
      idx.sort((a, b) => a - b);
      const sub = idx.map(i => rows[i]);
      try {
        const det = new EventDetector(baseCfg);
        const ann = det.detect(sub);
        const {nDd, nBu} = countPtaEvents(ann.labels);
        nDds.push(nDd);
        nBus.push(nBu);
        jaccards.push(jaccardPtaMask(ref.labels, ann.labels));
      } catch (_) { /* skip failed replica */ }
    }

    const bsStd = (nDds.length ? Math.sqrt(((nDds.reduce((a, v) => a + v, 0) / nDds.length) - refNDd) ** 2) : 0)
      + (nBus.length ? Math.sqrt(((nBus.reduce((a, v) => a + v, 0) / nBus.length) - refNBu) ** 2) : 0);
    const ddStd = nDds.length ? std(nDds) : 0;
    const buStd = nBus.length ? std(nBus) : 0;
    const bsPen = ddStd + buStd;
    const bsScore = Math.max(0, 1 - bsPen / Math.max(refNDd + refNBu, 1));
    const jMean = jaccards.length ? jaccards.reduce((a, b) => a + b, 0) / jaccards.length : 0;

    const sens = {};
    const params = {
      hampelSigma: baseCfg.hampelSigma,
      spikePercentile: baseCfg.spikePercentile,
      minPtaDpPsi: baseCfg.minPtaDpPsi,
      tailTrimDevNSigma: baseCfg.tailTrimDevNSigma
    };
    let sensTotal = 0;
    for (const [name, val] of Object.entries(params)) {
      let maxDd = 0;
      let maxBu = 0;
      for (const sign of [-1, 1]) {
        const newVal = val * (1 + sign * perturbation);
        const perturbed = {...baseCfg, [name]: newVal};
        try {
          const det = new EventDetector(perturbed);
          const ann = det.detect(rows);
          const {nDd, nBu} = countPtaEvents(ann.labels);
          maxDd = Math.max(maxDd, Math.abs(nDd - refNDd));
          maxBu = Math.max(maxBu, Math.abs(nBu - refNBu));
        } catch (_) { /* skip */ }
      }
      sens[name] = {deltaNDd: maxDd, deltaNBu: maxBu};
      sensTotal += maxDd + maxBu;
    }
    const sensScore = Math.max(0, 1 - sensTotal / Math.max(2 * (refNDd + refNBu) * Object.keys(sens).length, 1));
    const overall = Math.min(100, Math.max(0, 100 * (0.4 * bsScore + 0.4 * jMean + 0.2 * sensScore)));
    let grade;
    if (overall >= 80) grade = "HIGHLY ROBUST";
    else if (overall >= 60) grade = "REASONABLE";
    else if (overall >= 40) grade = "MARGINAL";
    else grade = "UNSTABLE";

    return {
      overallScore: overall,
      grade,
      refNDd,
      refNBu,
      bootstrapNDdStd: ddStd,
      bootstrapNBuStd: buStd,
      edgeJaccardMean: jMean,
      sensitivity: sens,
      detection: ref
    };
  }

  function std(arr) {
    if (arr.length < 2) return 0;
    const m = arr.reduce((a, b) => a + b, 0) / arr.length;
    return Math.sqrt(arr.reduce((s, v) => s + (v - m) ** 2, 0) / (arr.length - 1));
  }

  function labelsToSegments(labels) {
    return rle(labels)
      .filter(([, , l]) => l === "drawdown" || l === "buildup")
      .map(([startIndex, endIndex, eventType]) => ({startIndex, endIndex: endIndex - 1, eventType}));
  }

  function detectEvents(rows, cfg = {}, runCv = false) {
    const det = new EventDetector({...DEFAULT_CFG, ...cfg});
    const detection = det.detect(rows);
    const segments = labelsToSegments(detection.labels);
    let cv = null;
    if (runCv && rows.length >= 100) {
      try {
        cv = crossValidateDetector(rows, cfg, {nBootstrap: 6});
      } catch (_) { /* CV optional */ }
    }
    return {detection, segments, cv};
  }

  /* ── vSH04 deconvolution ── */

  function geomspace(tMin, tMax, n) {
    const logMin = Math.log10(tMin);
    const logMax = Math.log10(tMax);
    return Array.from({length: n}, (_, i) => Math.pow(10, logMin + (logMax - logMin) * i / (n - 1)));
  }

  function puFromZ(z, sigma) {
    const dpdlnt = z.map(v => Math.exp(v));
    const dsigma = sigma.map((s, i) => i === 0 ? sigma[1] - sigma[0] : s - sigma[i - 1]);
    const pu = [];
    let cum = 0;
    for (let i = 0; i < z.length; i += 1) {
      cum += dpdlnt[i] * dsigma[i];
      pu.push(cum);
    }
    return {pu, dpdlnt};
  }

  function secondDifferenceOperator(n) {
    const D = Array.from({length: n - 2}, () => Array(n).fill(0));
    for (let i = 0; i < n - 2; i += 1) {
      D[i][i] = 1;
      D[i][i + 1] = -2;
      D[i][i + 2] = 1;
    }
    return D;
  }

  function matVec(D, v) {
    return D.map(row => row.reduce((s, c, j) => s + c * v[j], 0));
  }

  function convolveWithRates(tObs, rateT, rateDq, tResp, pu) {
    const deltaP = new Array(tObs.length).fill(0);
    const logResp = tResp.map(Math.log);
    for (let k = 0; k < rateT.length; k += 1) {
      const tauK = rateT[k];
      const dqK = rateDq[k];
      if (!dqK) continue;
      for (let j = 0; j < tObs.length; j += 1) {
        const dtK = tObs[j] - tauK;
        if (dtK <= 0) continue;
        const clipped = Math.min(Math.max(dtK, tResp[0]), tResp[tResp.length - 1]);
        const logDt = Math.log(clipped);
        let puInterp = pu[0];
        for (let i = 0; i < logResp.length - 1; i += 1) {
          if (logDt >= logResp[i] && logDt <= logResp[i + 1]) {
            const t = (logDt - logResp[i]) / (logResp[i + 1] - logResp[i]);
            puInterp = pu[i] + t * (pu[i + 1] - pu[i]);
            break;
          }
          if (logDt > logResp[logResp.length - 1]) puInterp = pu[pu.length - 1];
        }
        deltaP[j] += dqK * puInterp;
      }
    }
    return deltaP;
  }

  function leastSquaresLM(residualFn, x0, maxIter = 150) {
    let x = x0.slice();
    let lambda = 1e-3;
    let prevCost = Infinity;
    const eps = 1e-7;
    const n = x.length;

    for (let iter = 0; iter < maxIter; iter += 1) {
      const r = residualFn(x);
      const cost = r.reduce((s, v) => s + v * v, 0);
      if (Math.abs(prevCost - cost) < 1e-9 * (prevCost + 1)) {
        return {x, converged: true, iterations: iter + 1, residualNorm: Math.sqrt(cost)};
      }
      prevCost = cost;

      const J = [];
      for (let i = 0; i < r.length; i += 1) {
        const row = [];
        for (let j = 0; j < n; j += 1) {
          const xp = x.slice();
          xp[j] += eps;
          const rp = residualFn(xp);
          row.push((rp[i] - r[i]) / eps);
        }
        J.push(row);
      }

      const JTJ = Array.from({length: n}, () => Array(n).fill(0));
      const JTr = Array(n).fill(0);
      for (let i = 0; i < n; i += 1) {
        for (let j = 0; j < n; j += 1) {
          let s = 0;
          for (let k = 0; k < r.length; k += 1) s += J[k][i] * J[k][j];
          JTJ[i][j] = s;
        }
        let s = 0;
        for (let k = 0; k < r.length; k += 1) s += J[k][i] * r[k];
        JTr[i] = s;
      }
      for (let i = 0; i < n; i += 1) JTJ[i][i] += lambda;

      let delta;
      try {
        delta = solveLinear(JTJ, JTr.map(v => -v));
      } catch (_) {
        lambda *= 10;
        continue;
      }

      const xNew = x.map((v, i) => v + delta[i]);
      const rNew = residualFn(xNew);
      const costNew = rNew.reduce((s, v) => s + v * v, 0);
      if (costNew < cost) {
        x = xNew;
        lambda = Math.max(lambda / 3, 1e-12);
      } else {
        lambda *= 10;
      }
    }
    const rFinal = residualFn(x);
    const costFinal = rFinal.reduce((s, v) => s + v * v, 0);
    return {x, converged: false, iterations: maxIter, residualNorm: Math.sqrt(costFinal)};
  }

  function solveLinear(A, b) {
    const n = A.length;
    const aug = A.map((row, i) => [...row, b[i]]);
    for (let col = 0; col < n; col += 1) {
      let pivot = col;
      for (let row = col + 1; row < n; row += 1) {
        if (Math.abs(aug[row][col]) > Math.abs(aug[pivot][col])) pivot = row;
      }
      [aug[col], aug[pivot]] = [aug[pivot], aug[col]];
      const div = aug[col][col] || 1e-12;
      for (let j = 0; j <= n; j += 1) aug[col][j] /= div;
      for (let row = 0; row < n; row += 1) {
        if (row === col) continue;
        const factor = aug[row][col];
        for (let j = 0; j <= n; j += 1) aug[row][j] -= factor * aug[col][j];
      }
    }
    return aug.map(row => row[n]);
  }

  function buildRateHistoryFromPeriods(periods, defaultQ = 0) {
    const rows = [];
    let lastQ = 0;
    for (const period of periods) {
      const startHr = period.startHr ?? 0;
      const isShutin = period.type === "shut-in" || period.eventType === "buildup" || period.autoType === "shut-in";
      const isFlow = ["flow", "cleanup", "restart"].includes(period.type)
        || period.eventType === "drawdown"
        || ["flow", "cleanup", "restart"].includes(period.autoType);
      if (isShutin) {
        const dq = 0 - lastQ;
        if (dq !== 0) rows.push({tHr: startHr, q: 0, dq});
        lastQ = 0;
        continue;
      }
      if (!isFlow) continue;
      const q = Number.isFinite(period.avgRate) && period.avgRate > 0 ? period.avgRate : defaultQ;
      const dq = q - lastQ;
      if (dq !== 0) rows.push({tHr: startHr, q, dq});
      lastQ = q;
    }
    if (!rows.length) rows.push({tHr: 0, q: 0, dq: 0});
    return rows;
  }

  function deconvolveVsh04({
    rows,
    periods,
    defaultQ = 850,
    nu = 0.01,
    nResponseNodes = 50,
    tResponseMin = 1e-3,
    tResponseMax = null,
    fitPInitial = true
  }) {
    const t0 = rows[0]?.timeMs || 0;
    const ptaPeriods = periods.filter(p => ["shut-in", "flow", "cleanup", "restart"].includes(p.type) || p.eventType === "drawdown" || p.eventType === "buildup");
    if (!ptaPeriods.length) return null;

    const tObs = [];
    const pObs = [];
    for (const period of ptaPeriods) {
      for (const row of period.rows || rows.slice(period.startIndex, period.endIndex + 1)) {
        tObs.push((row.timeMs - t0) / 3600000);
        pObs.push(row.bhp);
      }
    }
    const order = tObs.map((t, i) => i).sort((a, b) => tObs[a] - tObs[b]);
    let tSorted = order.map(i => tObs[i]);
    let pSorted = order.map(i => pObs[i]);
    const maxObs = 350;
    if (tSorted.length > maxObs) {
      const step = Math.ceil(tSorted.length / maxObs);
      const tSub = [];
      const pSub = [];
      for (let i = 0; i < tSorted.length; i += step) {
        tSub.push(tSorted[i]);
        pSub.push(pSorted[i]);
      }
      tSorted = tSub;
      pSorted = pSub;
    }

    const ratePeriods = periods.map(p => ({
      ...p,
      startHr: (p.start?.timeMs - t0) / 3600000,
      eventType: p.eventType || (p.type === "shut-in" ? "buildup" : "drawdown")
    }));
    const rateHist = buildRateHistoryFromPeriods(ratePeriods, defaultQ);
    const rateT = rateHist.map(r => r.tHr);
    const rateDq = rateHist.map(r => r.dq);

    const tMax = tResponseMax || Math.max(...tSorted);
    const tResp = geomspace(tResponseMin, tMax, nResponseNodes);
    const sigma = tResp.map(Math.log);
    const D = secondDifferenceOperator(nResponseNodes);
    const sqrtNu = Math.sqrt(nu);

    const pIGuess = percentile(pSorted, 95);
    const typicalDp = Math.max(pIGuess - Math.min(...pSorted), 50);
    const typicalQ = Math.max(...rateDq.map(Math.abs).filter(v => v > 0), 1);
    const puGuess = typicalDp / typicalQ;
    const z0Const = Math.log(Math.max(puGuess / (sigma[sigma.length - 1] - sigma[0] + 1e-9), 1e-6));
    const z0 = new Array(nResponseNodes).fill(z0Const);

    function residuals(params) {
      const z = fitPInitial ? params.slice(0, -1) : params;
      const pI = fitPInitial ? params[params.length - 1] : pIGuess;
      const {pu} = puFromZ(z, sigma);
      const deltaPPred = convolveWithRates(tSorted, rateT, rateDq, tResp, pu);
      const pModel = deltaPPred.map(dp => pI - dp);
      const rData = pSorted.map((p, i) => p - pModel[i]);
      const rReg = matVec(D, z).map(v => sqrtNu * v);
      return [...rData, ...rReg];
    }

    const x0 = fitPInitial ? [...z0, pIGuess] : z0.slice();
    const sol = leastSquaresLM(residuals, x0, 80);
    const zSol = fitPInitial ? sol.x.slice(0, -1) : sol.x;
    const pISol = fitPInitial ? sol.x[sol.x.length - 1] : pIGuess;
    const {pu: puSol, dpdlnt: dpuDlntSol} = puFromZ(zSol, sigma);
    const deltaPPred = convolveWithRates(tSorted, rateT, rateDq, tResp, puSol);
    const pFit = deltaPPred.map(dp => pISol - dp);

    return {
      method: "vSH04",
      t: tResp,
      pu: puSol,
      dpuDlnt: dpuDlntSol,
      pInitial: pISol,
      nu,
      converged: sol.converged,
      iterations: sol.iterations,
      residualNorm: sol.residualNorm,
      fitPressure: pFit,
      obsPressure: pSorted,
      obsTime: tSorted,
      rateHistory: rateHist,
      summary: [
        `vSH04 encoded deconvolution (von Schroeter–Hollaender–Gringarten 2004): ν=${nu}, ${nResponseNodes} log-spaced nodes.`,
        `Solver: ${sol.converged ? "converged" : "stopped"} in ${sol.iterations} iterations; ||r|| = ${sol.residualNorm.toFixed(2)} psi; pᵢ = ${pISol.toFixed(1)} psi.`,
        `Merges ${ptaPeriods.length} PTA period(s) into a single unit-rate response — extends radius of investigation beyond any individual buildup.`,
        `Rate steps: ${rateHist.length}. Compare vSH04 log-log derivative with raw/superposition curves before reporting.`
      ].join("\n\n")
    };
  }

  global.WelltestPtaEngine = {
    EventDetector,
    detectEvents,
    crossValidateDetector,
    deconvolveVsh04,
    labelsToSegments,
    DEFAULT_CFG
  };
})(typeof window !== "undefined" ? window : globalThis);
