#!/usr/bin/env python3
"""Patch Burner_boom_load_calculator.html with v3 matrix analysis."""
from pathlib import Path

HTML = Path("/workspace/Burner_boom_load_calculator.html")
text = HTML.read_text()

# --- CSS ---
css_insert = """
  .matrix-table { width: 100%; border-collapse: collapse; font-size: 11.5px; margin-top: 8px; }
  .matrix-table th, .matrix-table td { padding: 6px 7px; border-bottom: 1px solid var(--gridline); text-align: left; }
  .matrix-table td.n { text-align: right; font-variant-numeric: tabular-nums; }
  .matrix-table tr.gov { background: rgba(0,180,216,0.08); font-weight: 600; }
  .matrix-table tr.fail td { color: var(--critical); }
  .badge-sm { display: inline-block; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 999px; background: var(--accent-dim); color: var(--series-1); }
"""

if ".matrix-table" not in text:
    text = text.replace(
        "  .footnote {",
        css_insert + "\n  .footnote {",
        1,
    )

# --- Toolbar analysis mode ---
toolbar_patch = """    <label for="analysisMode">Analysis</label>
    <select id="analysisMode" aria-label="Analysis mode">
      <option value="simple">Simple cantilever</option>
      <option value="matrix" selected>Matrix envelope (SESAM-style)</option>
    </select>
    <span class="sep"></span>
    <label for="loadCase">Quick case</label>"""

text = text.replace(
    """    <span class="sep"></span>
    <label for="loadCase">Load case</label>""",
    toolbar_patch,
    1,
)

# --- Multi-support card before base reaction summary ---
support_card = """    <div class="card">
      <h2>Multi-support boundary conditions <span class="badge-sm">Matrix mode</span></h2>
      <p class="hint" style="margin-top:-6px;">Simplified static reactions — turntable (base), kingpost, wind stay, boom rest, crane lift. Inspired by 90 ft SESAM report; not a 3D frame solver.</p>
      <div class="grid">
        <div class="field"><label><input type="checkbox" id="kingpostEnabled" checked style="width:auto;margin-right:6px;">Kingpost vertical support (operating / accidental)</label></div>
        <div class="field"><label>Kingpost position from base</label><input type="number" id="kingpostPos_m" value="9.28" step="0.1" min="0"><span class="hint">m — PDF ref ≈ 9.28 m from deck</span></div>
        <div class="field"><label>Kingpost rated vertical capacity</label><input type="number" id="kingpostRated_kN" value="80" step="1" min="0"><span class="hint">kN</span></div>
        <div class="field"><label><input type="checkbox" id="windStayEnabled" checked style="width:auto;margin-right:6px;">Wind-stay lateral support (operating)</label></div>
        <div class="field"><label>Wind-stay position from base</label><input type="number" id="windStayPos_m" value="7.5" step="0.1" min="0"><span class="hint">m</span></div>
        <div class="field"><label>Wind-stay rated lateral capacity</label><input type="number" id="windStayRated_kN" value="25" step="1" min="0"><span class="hint">kN</span></div>
        <div class="field"><label><input type="checkbox" id="boomRestEnabled" checked style="width:auto;margin-right:6px;">Boom rest vertical support (survival)</label></div>
        <div class="field"><label>Boom rest position from base</label><input type="number" id="boomRestPos_m" value="8.19" step="0.1" min="0"><span class="hint">m</span></div>
        <div class="field"><label>Boom rest rated capacity</label><input type="number" id="boomRestRated_kN" value="60" step="1" min="0"><span class="hint">kN</span></div>
        <div class="field"><label>Accidental dry-weight factor</label><input type="number" id="accidentalDryFactor" value="0.85" step="0.01" min="0.5" max="1"><span class="hint">Empty pipe fraction of operating weight</span></div>
        <div class="field"><label>Lifting load factor</label><input type="number" id="liftingLoadFactor" value="2" step="0.1" min="1"><span class="hint">× total weight (PDF lifting = 2)</span></div>
      </div>
    </div>

    <div class="card">
      <h2>Guyline screening <span class="badge-sm">Windward effective</span></h2>
      <div class="grid">
        <div class="field"><label><input type="checkbox" id="guysEnabled" checked style="width:auto;margin-right:6px;">Include guyline tension check</label></div>
        <div class="field"><label>Effective guylines (windward)</label><input type="number" id="nGuysEffective" value="1" step="1" min="1" max="8"><span class="hint">Leeward guys slack — PDF uses windward only</span></div>
        <div class="field"><label>Guy attachment position</label><input type="number" id="guyAttachPos_m" value="9.28" step="0.1" min="0"><span class="hint">m from turntable / base</span></div>
        <div class="field"><label>Effective guy length</label><input type="number" id="guyLength_m" value="12" step="0.1" min="1"><span class="hint">m — anchor to attachment (straight-line)</span></div>
        <div class="field"><label>Guy angle from horizontal</label><input type="number" id="guyAngle_deg" value="35" step="1" min="5" max="85"><span class="hint">degrees</span></div>
        <div class="field"><label>Allowable tension per guy</label><input type="number" id="guyAllow_kN" value="50" step="1" min="0"><span class="hint">kN</span></div>
      </div>
    </div>

"""

if "kingpostEnabled" not in text:
    text = text.replace(
        """    <div class="card">
      <h2>Base reaction summary</h2>
      <table class="report" id="reactionTable"></table>
    </div>""",
        support_card + """    <div class="card">
      <h2>Base reaction summary</h2>
      <table class="report" id="reactionTable"></table>
    </div>""",
        1,
    )

# --- Matrix results card ---
matrix_results = """    <div class="card" id="matrixResultsCard">
      <h2>Load combination matrix <span class="badge-sm">Operating · Survival · Accidental · Lifting</span></h2>
      <p class="hint" style="margin-top:-6px;">Runs 8 SESAM-style combinations with 3-direction dynamic scale factors (X ⊥ boom, Y ∥ boom, Z vertical). Governing row drives header status.</p>
      <div style="overflow-x:auto;"><table class="matrix-table" id="matrixTable"></table></div>
    </div>

"""

if "matrixTable" not in text:
    text = text.replace(
        """    <div class="card">
      <h2>Quality checks</h2>
      <div class="qc-list" id="qcList" role="list"></div>
    </div>""",
        matrix_results + """    <div class="card">
      <h2>Quality checks</h2>
      <div class="qc-list" id="qcList" role="list"></div>
    </div>""",
        1,
    )

# --- Replace APP_VERSION and add MATRIX + new compute ---
old_compute_start = "  function compute(inp){"
old_compute_end = "      xs,Mg,Mw,Mr,defl, predictedTestDefl, testLoad_kg, Dt, Pcr, bucklingSF, bucklingPass, t};\n  }"

new_js_block = r'''  const APP_VERSION = '3.0.0';

  const MATRIX_COMBOS = [
    { id:'op_roll', label:'Operating · Heave+Roll', condition:'operating', sfZ:2.40, sfY:0.18, sfX:0.04, windX:0.63, windY:0.08, loadFactor:1, supports:['turntable','kingpost','windstay','guys'] },
    { id:'op_pitch', label:'Operating · Heave+Pitch', condition:'operating', sfZ:2.10, sfY:0.22, sfX:0.05, windX:0.48, windY:0.10, loadFactor:1, supports:['turntable','kingpost','windstay','guys'] },
    { id:'op_res', label:'Operating · Heave+Resultant', condition:'operating', sfZ:3.25, sfY:0.29, sfX:0.03, windX:0.99, windY:0.10, loadFactor:1, supports:['turntable','kingpost','windstay','guys'] },
    { id:'sv_roll', label:'Survival · Heave+Roll', condition:'survival', sfZ:2.00, sfY:0.15, sfX:0.04, windX:0.77, windY:0.10, loadFactor:1, supports:['turntable','boomrest'] },
    { id:'sv_pitch', label:'Survival · Heave+Pitch', condition:'survival', sfZ:1.80, sfY:0.18, sfX:0.05, windX:0.60, windY:0.10, loadFactor:1, supports:['turntable','boomrest'] },
    { id:'sv_res', label:'Survival · Heave+Resultant', condition:'survival', sfZ:2.50, sfY:0.25, sfX:0.03, windX:0.99, windY:0.10, loadFactor:1, supports:['turntable','boomrest'] },
    { id:'acc_heel', label:'Accidental · Static heel', condition:'accidental', sfZ:1.00, sfY:0.10, sfX:0.08, windX:0.50, windY:0.08, loadFactor:1, supports:['turntable','kingpost'] },
    { id:'lift', label:'Lifting · Crane guylines', condition:'lifting', sfZ:1.00, sfY:0.00, sfX:0.00, windX:0, windY:0, loadFactor:2, supports:['lifting'] },
  ];

  function compute(inp, combo){
    const g = 9.81;
    const rhoSteel = 7.85e-6;
    const E = inp.E_MPa;
    const L = inp.L_m*1000;
    const OD = inp.OD_mm, t = Math.min(inp.t_mm, inp.OD_mm/2 - 0.01);
    const ID = OD - 2*t;
    const A = Math.PI/4*(OD*OD - ID*ID);
    const I = Math.PI/64*(Math.pow(OD,4)-Math.pow(ID,4));
    const Z = I/(OD/2);
    const theta = inp.angle_deg*Math.PI/180;
    const cosT = Math.cos(theta), sinT = Math.sin(theta);

    const wSelf = A*rhoSteel*g;
    const wAdded = (inp.addedW_kgpm*g)/1000;
    const wGravity = wSelf + wAdded;
    const Ptip = inp.tipLoad_kg*g;
    const Pextra = inp.extraLoad_kg*g;
    const xp = Math.min(inp.extraPos_m*1000, L);

    const useMatrix = combo && inp.analysisMode === 'matrix';
    const lf = useMatrix ? combo.loadFactor : 1;
    let wMult = lf;
    if(useMatrix && combo.condition === 'accidental') wMult *= inp.accidentalDryFactor;

    const sfZ = useMatrix ? combo.sfZ : 1;
    const sfY = useMatrix ? combo.sfY : 1;
    const sfX = useMatrix ? combo.sfX : 1;
    const windMultX = useMatrix ? combo.windX : 1;
    const windMultY = useMatrix ? combo.windY : 1;
    const daf = inp.DAF;

    let windSpeed = inp.windSpeed_ms;
    if(useMatrix && combo.condition === 'survival') windSpeed *= 1.15;
    if(useMatrix && combo.condition === 'lifting') windSpeed = 0;
    if(!useMatrix && $('loadCase')?.value === 'storm') windSpeed = inp.windSpeed_ms;

    const wVert0 = wGravity*cosT;
    const PtipZ0 = Ptip*cosT;
    const PextraZ0 = Pextra*cosT;
    const wAx0 = wGravity*sinT;

    const wZ = wVert0 * wMult * daf * sfZ;
    const PtipZ = PtipZ0 * wMult * daf * sfZ;
    const PextraZ = PextraZ0 * wMult * daf * sfZ;
    const Fy_ax = wAx0 * L * wMult * daf * sfY + (Ptip*sinT + Pextra*sinT) * wMult * daf * sfY;

    const Fz_total = wZ*L + PtipZ + PextraZ;
    const Mz = wZ*L*L/2 + PtipZ*L + PextraZ*xp;

    const q_Pa = 0.5*inp.rhoAir*windSpeed*windSpeed*inp.windExposure;
    const wWind = q_Pa*inp.Cd*(OD/1000)/1000;
    const FwindX = wWind*L*windMultX;
    const FwindY = wWind*L*windMultY;
    const Fxd = Fz_total * sfX / Math.max(sfZ, 1e-9);
    const Fx_total = Fxd + FwindX;

    const Mx = Fx_total * L / 2;
    let Mres = Math.sqrt(Mz*Mz + Mx*Mx);
    const Vz = wZ*L + PtipZ + PextraZ;
    const Vres = Math.sqrt(Fx_total*Fx_total + Vz*Vz);
    const N_d = Fy_ax + FwindY;

    const supports = { turntable:{M_kNm:Mres/1e6,V_kN:Vres/1000,N_kN:N_d/1000}, kingpost:{R_kN:0,ok:true}, windstay:{R_kN:0,ok:true}, boomrest:{R_kN:0,ok:true}, guys:{T_kN:0,util:0,ok:true} };

    const active = s => useMatrix && combo.supports.includes(s);
    const kpOn = active('kingpost') && inp.kingpostEnabled;
    const wsOn = active('windstay') && inp.windStayEnabled;
    const brOn = active('boomrest') && inp.boomRestEnabled;
    const guysOn = active('guys') && inp.guysEnabled;

    if(kpOn){
      const a = Math.min(inp.kingpostPos_m*1000, L*0.99);
      supports.kingpost.R_kN = Fz_total * (L - a) / L / 1000;
      const Mz_tt = Math.max(0, Mz - supports.kingpost.R_kN*1000*a);
      Mres = Math.sqrt(Mz_tt*Mz_tt + Mx*Mx);
      supports.turntable.M_kNm = Mres/1e6;
      supports.kingpost.ok = supports.kingpost.R_kN <= inp.kingpostRated_kN;
    }
    if(wsOn){
      supports.windstay.R_kN = Math.min(Fx_total/1000, inp.windStayRated_kN);
      const Fx_rem = Math.max(0, Fx_total/1000 - supports.windstay.R_kN);
      supports.windstay.ok = supports.windstay.R_kN <= inp.windStayRated_kN;
      if(guysOn && inp.nGuysEffective > 0){
        const ang = inp.guyAngle_deg*Math.PI/180;
        const T = Math.sin(ang) > 0.01 ? (Fx_rem*1000/inp.nGuysEffective)/Math.sin(ang) : 0;
        supports.guys.T_kN = T/1000;
        supports.guys.util = inp.guyAllow_kN > 0 ? (T/1000)/inp.guyAllow_kN*100 : 0;
        supports.guys.ok = supports.guys.util <= 100;
      }
    } else if(guysOn && inp.nGuysEffective > 0){
      const ang = inp.guyAngle_deg*Math.PI/180;
      const T = Math.sin(ang) > 0.01 ? (Fx_total/inp.nGuysEffective)/Math.sin(ang) : 0;
      supports.guys.T_kN = T/1000;
      supports.guys.util = inp.guyAllow_kN > 0 ? supports.guys.T_kN/inp.guyAllow_kN*100 : 0;
      supports.guys.ok = supports.guys.util <= 100;
    }
    if(brOn){
      const a = Math.min(inp.boomRestPos_m*1000, L*0.99);
      supports.boomrest.R_kN = Fz_total * (L - a) / L / 1000;
      const Mz_tt = Math.max(0, Mz - supports.boomrest.R_kN*1000*a);
      Mres = Math.sqrt(Mz_tt*Mz_tt + Mx*Mx);
      supports.turntable.M_kNm = Mres/1e6;
      supports.boomrest.ok = supports.boomrest.R_kN <= inp.boomRestRated_kN;
    }
    if(active('lifting')){
      Mres = Mz * 0.85;
      supports.turntable.M_kNm = Mres/1e6;
    }

    const sigmaBend = Z>0 ? Mres/Z : 0;
    const sigmaAxial = A>0 ? N_d/A : 0;
    const sigmaCombined = sigmaBend + sigmaAxial;
    const tau = A>0 ? 2*Vres/A : 0;
    const sigmaEq = Math.sqrt(sigmaCombined*sigmaCombined + 3*tau*tau);
    const allow = inp.Fy_MPa/inp.SF;
    const actualSF = sigmaEq>0 ? inp.Fy_MPa/sigmaEq : Infinity;

    const dUdl = I>0 ? wZ*Math.pow(L,4)/(8*E*I) : 0;
    const dTip = I>0 ? PtipZ*Math.pow(L,3)/(3*E*I) : 0;
    const dExtra = (I>0 && inp.extraLoad_kg>0) ? PextraZ*xp*xp*(3*L-xp)/(6*E*I) : 0;
    const dVert = dUdl+dTip+dExtra;
    const dWind = I>0 ? wWind*windMultX*Math.pow(L,4)/(8*E*I) : 0;
    const dRes = Math.sqrt(dVert*dVert + dWind*dWind);
    const defLimit = L/inp.defLimitDenom;

    const Dt = t > 0 ? OD/t : 0;
    const Kbuck = 2.0;
    const Pcr = I>0 && L>0 ? (Math.PI*Math.PI*E*I)/Math.pow(Kbuck*L,2) : 0;
    const bucklingSF = N_d>0 ? Pcr/N_d : Infinity;
    const bucklingPass = N_d <= 0 || bucklingSF >= inp.SF;

    const Rbolt = inp.bcd_mm/2;
    const boltTension_kN = inp.nBolts>0 ? ((2*Mres/(inp.nBolts*Rbolt)) + (N_d/inp.nBolts))/1000 : 0;
    const boltUtil = inp.boltAllow_kN>0 ? boltTension_kN/inp.boltAllow_kN*100 : 0;

    const n = 21;
    const xs=[], Mg=[], Mw=[], Mr=[], defl=[];
    for(let i=0;i<n;i++){
      const x = L*i/(n-1);
      const rem = L-x;
      const mg = wZ*rem*rem/2 + PtipZ*rem + (x<=xp?PextraZ*(xp-x):0);
      const mw = wWind*windMultX*rem*rem/2;
      xs.push(x); Mg.push(mg); Mw.push(mw); Mr.push(Math.sqrt(mg*mg+mw*mw));
      let dv = I>0 ? wZ*(Math.pow(x,4)-4*L*Math.pow(x,3)+6*L*L*x*x)/(24*E*I) : 0;
      dv += I>0 ? PtipZ*( x<=L ? (x*x*(3*L-x))/(6*E*I) : 0) : 0;
      if(inp.extraLoad_kg>0 && I>0){
        if(x<=xp) dv += PextraZ*x*x*(3*xp-x)/(6*E*I);
        else dv += PextraZ*xp*xp*(3*x-xp)/(6*E*I);
      }
      const dw = I>0 ? wWind*windMultX*(Math.pow(x,4)-4*L*Math.pow(x,3)+6*L*L*x*x)/(24*E*I) : 0;
      defl.push(Math.sqrt(dv*dv+dw*dw));
    }

    const testLoadFactor = inp.testFactor;
    const dUdl_t = I>0 ? wVert0*testLoadFactor*Math.pow(L,4)/(8*E*I) : 0;
    const dTip_t = I>0 ? PtipZ0*testLoadFactor*Math.pow(L,3)/(3*E*I) : 0;
    const dExtra_t = (I>0 && inp.extraLoad_kg>0) ? PextraZ0*testLoadFactor*xp*xp*(3*L-xp)/(6*E*I) : 0;
    const predictedTestDefl = dUdl_t+dTip_t+dExtra_t;
    const testLoad_kg = inp.swl_kg*testLoadFactor;

    const utilStress = allow>0 ? sigmaEq/allow : 0;
    const pass = actualSF >= inp.SF && bucklingPass && boltUtil <= 100
      && supports.kingpost.ok && supports.windstay.ok && supports.boomrest.ok && supports.guys.ok
      && supports.turntable.M_kNm <= inp.ratedMoment_kNm
      && Math.sqrt(supports.turntable.V_kN**2+supports.turntable.N_kN**2) <= inp.ratedLoad_kN;

    return {A,I,Z,OD,ID,L,theta,wSelf,wAdded,wGravity,Ptip,Pextra,xp,
      Mgrav_d:Mz,Vgrav_d:Vz,N_d,Mwind:Mw[0],Vwind:FwindX,Mres,Vres,sigmaBend,sigmaAxial,sigmaCombined,tau,sigmaEq,
      allow,actualSF,dVert,dWind,dRes,defLimit, boltTension_kN, boltUtil, R:Rbolt,
      xs,Mg,Mw,Mr,defl, predictedTestDefl, testLoad_kg, Dt, Pcr, bucklingSF, bucklingPass, t,
      comboLabel: combo?combo.label:null, supports, utilStress, pass, Fx_total, Fz_total, Fy_ax};
  }

  function computeEnvelope(inp){
    const rows = MATRIX_COMBOS.map(c=>{
      const r = compute({...inp, analysisMode:'matrix'}, c);
      return { combo:c, r };
    });
    let gov = rows[0];
    for(const row of rows){
      if(row.r.utilStress > gov.r.utilStress) gov = row;
    }
    return { rows, governing: gov };
  }

  function renderMatrixTable(envelope){
    const el = $('matrixTable');
    if(!el) return;
    let html = '<thead><tr><th>Combination</th><th>σ util.</th><th>SF</th><th>M base</th><th>Guy T</th><th>Status</th></tr></thead><tbody>';
    for(const {combo, r} of envelope.rows){
      const gov = combo.id === envelope.governing.combo.id;
      const cls = (gov?'gov ':'') + (r.pass?'':'fail');
      html += `<tr class="${cls}"><td>${combo.label}${gov?' ★':''}</td><td class="n">${fmt(r.utilStress*100,0)}%</td><td class="n">${fmt(r.actualSF,2)}</td><td class="n">${fmt(r.Mres/1e6,1)}</td><td class="n">${r.supports.guys.T_kN>0?fmt(r.supports.guys.T_kN,1):'—'}</td><td>${r.pass?'OK':'FAIL'}</td></tr>`;
    }
    html += '</tbody>';
    el.innerHTML = html;
  }'''

# Replace APP_VERSION line and compute function
text = text.replace("  const APP_VERSION = '2.0.0';", new_js_block.split('  const MATRIX_COMBOS')[0].strip(), 1)

start = text.find("  function compute(inp){")
end = text.find("  function renderQC(issues){")
if start == -1 or end == -1:
    raise SystemExit('compute block not found')

text = text[:start] + new_js_block + "\n\n  " + text[end:]

# Extend getInputs - find closing of getInputs return
getinputs_snip = """      measDefl_mm: valMetric('measDefl_mm', v => v / CONV.mm_in),
      measSet_mm: valMetric('measSet_mm', v => v / CONV.mm_in),
    };
  }"""

getinputs_new = """      measDefl_mm: valMetric('measDefl_mm', v => v / CONV.mm_in),
      measSet_mm: valMetric('measSet_mm', v => v / CONV.mm_in),
      analysisMode: ($('analysisMode')?.value)||'matrix',
      kingpostEnabled: !!$('kingpostEnabled')?.checked,
      kingpostPos_m: valMetric('kingpostPos_m', v => v / CONV.m_ft) || 0,
      kingpostRated_kN: valMetric('kingpostRated_kN', v => v / CONV.kn_kip) || 0,
      windStayEnabled: !!$('windStayEnabled')?.checked,
      windStayPos_m: valMetric('windStayPos_m', v => v / CONV.m_ft) || 0,
      windStayRated_kN: valMetric('windStayRated_kN', v => v / CONV.kn_kip) || 0,
      boomRestEnabled: !!$('boomRestEnabled')?.checked,
      boomRestPos_m: valMetric('boomRestPos_m', v => v / CONV.m_ft) || 0,
      boomRestRated_kN: valMetric('boomRestRated_kN', v => v / CONV.kn_kip) || 0,
      accidentalDryFactor: parseFloat($('accidentalDryFactor')?.value)||0.85,
      liftingLoadFactor: parseFloat($('liftingLoadFactor')?.value)||2,
      guysEnabled: !!$('guysEnabled')?.checked,
      nGuysEffective: parseFloat($('nGuysEffective')?.value)||1,
      guyAttachPos_m: valMetric('guyAttachPos_m', v => v / CONV.m_ft) || 0,
      guyLength_m: valMetric('guyLength_m', v => v / CONV.m_ft) || 0,
      guyAngle_deg: parseFloat($('guyAngle_deg')?.value)||35,
      guyAllow_kN: valMetric('guyAllow_kN', v => v / CONV.kn_kip) || 0,
    };
  }"""

text = text.replace(getinputs_snip, getinputs_new, 1)

# Extend UNIT_FIELDS for new metric fields
unit_snip = """    { id: 'measSet_mm', metric: 'mm', us: 'in', toUs: v => v * CONV.mm_in, toMetric: v => v / CONV.mm_in }
  ];"""
unit_new = """    { id: 'measSet_mm', metric: 'mm', us: 'in', toUs: v => v * CONV.mm_in, toMetric: v => v / CONV.mm_in },
    { id: 'kingpostPos_m', metric: 'm', us: 'ft', toUs: v => v * CONV.m_ft, toMetric: v => v / CONV.m_ft },
    { id: 'windStayPos_m', metric: 'm', us: 'ft', toUs: v => v * CONV.m_ft, toMetric: v => v / CONV.m_ft },
    { id: 'boomRestPos_m', metric: 'm', us: 'ft', toUs: v => v * CONV.m_ft, toMetric: v => v / CONV.m_ft },
    { id: 'guyAttachPos_m', metric: 'm', us: 'ft', toUs: v => v * CONV.m_ft, toMetric: v => v / CONV.m_ft },
    { id: 'guyLength_m', metric: 'm', us: 'ft', toUs: v => v * CONV.m_ft, toMetric: v => v / CONV.m_ft },
    { id: 'kingpostRated_kN', metric: 'kN', us: 'kip', toUs: v => v * CONV.kn_kip, toMetric: v => v / CONV.kn_kip },
    { id: 'windStayRated_kN', metric: 'kN', us: 'kip', toUs: v => v * CONV.kn_kip, toMetric: v => v / CONV.kn_kip },
    { id: 'boomRestRated_kN', metric: 'kN', us: 'kip', toUs: v => v * CONV.kn_kip, toMetric: v => v / CONV.kn_kip },
    { id: 'guyAllow_kN', metric: 'kN', us: 'kip', toUs: v => v * CONV.kn_kip, toMetric: v => v / CONV.kn_kip }
  ];"""
text = text.replace(unit_snip, unit_new, 1)

# Update recalc to use envelope
recalc_snip = """    const r = compute(inp);

    $('t_mm').classList.toggle('invalid', inp.t_mm >= inp.OD_mm/2);"""

recalc_new = """    let envelope = null;
    let r;
    if(inp.analysisMode === 'matrix'){
      envelope = computeEnvelope(inp);
      r = envelope.governing.r;
      renderMatrixTable(envelope);
      $('matrixResultsCard').style.display = '';
    } else {
      r = compute(inp, null);
      if($('matrixResultsCard')) $('matrixResultsCard').style.display = 'none';
    }

    $('t_mm').classList.toggle('invalid', inp.t_mm >= inp.OD_mm/2);"""

text = text.replace(recalc_snip, recalc_new, 1)

# Extend reaction table with support reactions
reaction_snip = """      <tr><th>Bolt utilization</th><td class="v">${fmt(r.boltUtil,1)}% of allowable ${uForce_kN(inp.boltAllow_kN)}</td></tr>
    `;"""

reaction_new = """      <tr><th>Bolt utilization</th><td class="v">${fmt(r.boltUtil,1)}% of allowable ${uForce_kN(inp.boltAllow_kN)}</td></tr>
      ${inp.analysisMode==='matrix' && r.supports ? `
      <tr><th colspan="2" style="padding-top:10px;color:var(--series-1)">Multi-support reactions (${r.comboLabel||'governing'})</th></tr>
      <tr><th>Kingpost vertical</th><td class="v">${uForce_kN(r.supports.kingpost.R_kN)} ${r.supports.kingpost.ok?'OK':'EXCEEDED'}</td></tr>
      <tr><th>Wind-stay lateral</th><td class="v">${uForce_kN(r.supports.windstay.R_kN)} ${r.supports.windstay.ok?'OK':'EXCEEDED'}</td></tr>
      <tr><th>Boom rest vertical</th><td class="v">${uForce_kN(r.supports.boomrest.R_kN)} ${r.supports.boomrest.ok?'OK':'EXCEEDED'}</td></tr>
      <tr><th>Guyline tension (ea.)</th><td class="v">${r.supports.guys.T_kN>0?uForce_kN(r.supports.guys.T_kN)+' · '+fmt(r.supports.guys.util,0)+'%': '—'}</td></tr>
      <tr><th>3-direction forces (X/Y/Z)</th><td class="v">${uForce_kN(r.Fx_total/1000)} / ${uForce_kN(r.Fy_ax/1000)} / ${uForce_kN(r.Fz_total/1000)}</td></tr>
      ` : ''}
    `;"""

text = text.replace(reaction_snip, reaction_new, 1)

# primary fail includes support checks in matrix mode
primary_snip = """    const primaryFail = !stressOk || !momentOk || !boltOk || !loadOk || !r.bucklingPass || issues.some(i=>i.level==='bad');"""
primary_new = """    const supportFail = inp.analysisMode==='matrix' && r.supports && (!r.supports.kingpost.ok || !r.supports.windstay.ok || !r.supports.boomrest.ok || !r.supports.guys.ok);
    const primaryFail = !stressOk || !momentOk || !boltOk || !loadOk || !r.bucklingPass || supportFail || issues.some(i=>i.level==='bad');"""
text = text.replace(primary_snip, primary_new, 1)

# Update meta version in header
text = text.replace("v2.0 · Cantilever", "v3.0 · Matrix + cantilever", 1)
text = text.replace("Burner Boom Load Analysis &amp; Rig-Up Calculator v2", "Burner Boom Load Analysis v3", 1)

# DEFAULTS for lifting factor sync
text = text.replace(
    "    swl_kg: 110, testFactor: 1.5, permSetPct: 10\n  };",
    "    swl_kg: 110, testFactor: 1.5, permSetPct: 10,\n    kingpostPos_m: 9.28, kingpostRated_kN: 80, windStayPos_m: 7.5, windStayRated_kN: 25,\n    boomRestPos_m: 8.19, boomRestRated_kN: 60, guyAttachPos_m: 9.28, guyLength_m: 12, guyAllow_kN: 50\n  };",
    1,
)

apply_defaults_snip = """    $('loadCase').value = 'operating';
    $('visualOk').checked = false;"""
apply_defaults_new = """    $('loadCase').value = 'operating';
    $('analysisMode').value = 'matrix';
    if($('kingpostEnabled')) $('kingpostEnabled').checked = true;
    if($('windStayEnabled')) $('windStayEnabled').checked = true;
    if($('boomRestEnabled')) $('boomRestEnabled').checked = true;
    if($('guysEnabled')) $('guysEnabled').checked = true;
    $('visualOk').checked = false;"""
text = text.replace(apply_defaults_snip, apply_defaults_new, 1)

HTML.write_text(text)
print("Patched OK", len(text))
