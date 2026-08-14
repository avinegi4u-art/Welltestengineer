#!/usr/bin/env node
'use strict';
// Self-test for 3D space frame module — run: node tools/space_frame_3d.js

const PDF_L_DESIGN_M = 18.288; // 60 ft — native design baseline
const PDF_L_PDF90_M = 27.432;  // 90 ft SESAM drawing (geometry source)
const PDF_N_BAYS = 18;
const PDF_DY_M = PDF_L_DESIGN_M / PDF_N_BAYS;
const PDF_L_REF_M = PDF_L_DESIGN_M; // alias for embed scripts
const PDF_E = 200000, PDF_G = PDF_E / 2.6, PDF_E_ROPE = 150000;
const PDF_SW_FACTOR = 1.27; // SESAM structural dead-load multiplier on frame self-weight

function pdfGeomScale(Lm){ return Lm / PDF_L_PDF90_M; }

/** Deck anchor catalogue — CT-12-4536 90 ft PDF coordinates (scaled by gs at runtime). */
const PDF_ANCHORS_90 = [
  { tag: 'Sp1',  x: 0.35,  y: 2.20,  z: 8.50 },
  { tag: 'Sp2',  x: -0.35, y: 2.20,  z: 8.50 },
  { tag: 'Sp3',  x: 0.50,  y: 3.88,  z: 0.02 },
  { tag: 'Sp4',  x: -0.50, y: 9.28,  z: 9.00 },
  { tag: 'Sp5',  x: 0.42,  y: 4.80,  z: 7.20 },
  { tag: 'Sp6',  x: -0.42, y: 4.80,  z: 7.20 },
  { tag: 'Sp7',  x: 0.55,  y: 6.50,  z: 8.00 },
  { tag: 'Sp8',  x: -0.38, y: 5.28,  z: 6.36 },
  { tag: 'Sp9',  x: 0.48,  y: 11.00, z: 9.50 },
  { tag: 'Sp10', x: -0.48, y: 11.00, z: 9.50 },
];

const EXTRA_GUY_LINKS = [
  { id: 'GuySp5',  anchor: 'Sp5',  corner: 0, sn: 'Rope_pipe_30mm_eff', minGuys: 2 },
  { id: 'GuySp6',  anchor: 'Sp6',  corner: 1, sn: 'Rope_pipe_30mm_eff', minGuys: 3 },
  { id: 'GuySp7',  anchor: 'Sp7',  corner: 2, sn: 'Rope_pipe_35mm_eff', minGuys: 4 },
  { id: 'GuySp9',  anchor: 'Sp9',  corner: 2, sn: 'Rope_pipe_40mm_eff', minGuys: 5 },
  { id: 'GuySp10', anchor: 'Sp10', corner: 3, sn: 'Rope_pipe_40mm_eff', minGuys: 6 },
  { id: 'GuySp1',  anchor: 'Sp1',  corner: 0, sn: 'Rope_pipe_30mm_eff', minGuys: 7 },
  { id: 'GuySp2',  anchor: 'Sp2',  corner: 1, sn: 'Rope_pipe_30mm_eff', minGuys: 8 },
];

function memberCategory(id){
  if(id.startsWith('Bm119')) return 'chord';
  if(/^Guy|^Stay/.test(id)) return 'rope';
  if(/^[DVX]\d/.test(id)) return 'brace';
  if(/^Bm\d/.test(id)) return 'chord';
  return 'other';
}

function isUnityTableMember(m){
  const c = memberCategory(m.id);
  return (c === 'chord' && m.id.startsWith('Bm119')) || c === 'rope' || c === 'brace';
}

function dryFractionAtY(y, Lm, inp, useCombo, combo){
  if(!useCombo || combo.condition !== 'accidental') return 1;
  const dryTip = inp.accidentalDryFactor != null ? inp.accidentalDryFactor : 0.85;
  const t = Math.min(1, Math.max(0, y / Math.max(Lm, 1e-9)));
  return 1 - (1 - dryTip) * t;
}

function heelRad(inp, useCombo, combo){
  if(!useCombo || combo.condition !== 'accidental') return 0;
  return (inp.accidentalHeel_deg != null ? inp.accidentalHeel_deg : 5) * Math.PI / 180;
}

function applyHeelLoad(addLoad, node, W, heel){
  if(Math.abs(heel) < 1e-9) addLoad(node, 0, 0, -W);
  else addLoad(node, W * Math.sin(heel), 0, -W * Math.cos(heel));
}

const PDF_SECTIONS = {
  box_75x75x6:       { A: 1656,  Iy: 1.32e6,  Iz: 1.32e6,  J: 2.64e6,  Zy: 35200, Zz: 35200, E: PDF_E, truss: false },
  box_90x90x8:       { A: 2624,  Iy: 2.97e6,  Iz: 2.97e6,  J: 5.94e6,  Zy: 66000, Zz: 66000, E: PDF_E, truss: false },
  L_200x100x10:      { A: 2900,  Iy: 9.5e6,   Iz: 3.2e6,   J: 0.5e6,   Zy: 95000, Zz: 64000, E: PDF_E, truss: false },
  L75x75x8:          { A: 1700,  Iy: 0.85e6,  Iz: 0.85e6,  J: 0.3e6,   Zy: 23000, Zz: 23000, E: PDF_E, truss: false },
  Rope_pipe_30mm_eff:{ A: 456.17,E: PDF_E_ROPE, allow: 180, truss: true },
  Rope_pipe_35mm_eff:{ A: 621.48,E: PDF_E_ROPE, allow: 250, truss: true },
  Rope_pipe_40mm_eff:{ A: 815.34,E: PDF_E_ROPE, allow: 320, truss: true },
  Rope_pipe_56mm_eff:{ A: 1592.55,E: PDF_E_ROPE, allow: 500, truss: true },
};

function dirCos3(x0,y0,z0,x1,y1,z1){
  const dx=x1-x0, dy=y1-y0, dz=z1-z0, L=Math.hypot(dx,dy,dz)||1;
  const lx=dx/L, mx=dy/L, nx=dz/L;
  let rx=0, ry=0, rz=1;
  if(Math.abs(nx)>0.95){ rx=0; ry=1; rz=0; }
  else if(Math.abs(mx)>0.95){ rx=1; ry=0; rz=0; }
  else if(Math.abs(lx)>0.95){ rx=0; ry=1; rz=0; }
  let ly=ry*nx-rz*mx, my=rz*lx-rx*nx, ny=rx*mx-ry*lx;
  let len=Math.hypot(ly,my,ny)||1; ly/=len; my/=len; ny/=len;
  const lz=my*nx-ny*mx, mz=ny*lx-ly*nx, nz=ly*mx-my*lx;
  len=Math.hypot(lz,mz,nz)||1; return [lx,mx,nx, ly,my,ny, lz/len,mz/len,nz/len];
}

function beam3dLocalK(E,G,A,Iy,Iz,J,L){
  const EA=E*A/L, GJ=G*J/L, iz=E*Iz, iy=E*Iy, L2=L*L, L3=L2*L;
  const k=new Float64Array(144);
  const s=(a,b,v)=>{ k[a*12+b]=v; k[b*12+a]=v; };
  s(0,0,EA); s(0,6,-EA); s(6,6,EA);
  s(3,3,GJ); s(3,9,-GJ); s(9,9,GJ);
  const phiy=12*iz/L3, phiz=12*iy/L3;
  s(1,1,phiy); s(1,5,6*iz/L2); s(1,7,-phiy); s(1,11,6*iz/L2);
  s(5,5,4*iz/L); s(5,7,-6*iz/L2); s(5,11,2*iz/L);
  s(7,7,phiy); s(7,11,-6*iz/L2); s(11,11,4*iz/L);
  s(2,2,phiz); s(2,4,-6*iy/L2); s(2,8,-phiz); s(2,10,-6*iy/L2);
  s(4,4,4*iy/L); s(4,8,6*iy/L2); s(4,10,2*iy/L);
  s(8,8,phiz); s(8,10,6*iy/L2); s(10,10,4*iy/L);
  return k;
}

function matMul12(T, M){
  const R=new Float64Array(144);
  for(let i=0;i<12;i++) for(let j=0;j<12;j++){
    let s=0; for(let k=0;k<12;k++) s+=T[i*12+k]*M[k*12+j];
    R[i*12+j]=s;
  }
  return R;
}

function transpose12(M){
  const R=new Float64Array(144);
  for(let i=0;i<12;i++) for(let j=0;j<12;j++) R[i*12+j]=M[j*12+i];
  return R;
}

function transform12(kL,R){
  const T=new Float64Array(144);
  for(let b=0;b<4;b++) for(let i=0;i<3;i++) for(let j=0;j<3;j++) T[(b*3+i)*12+b*3+j]=R[i*3+j];
  return matMul12(transpose12(T), matMul12(T, kL));
}

function trussGlobalK(E,A,L,R){
  const EA=E*A/L, k=new Float64Array(144);
  const c=[R[0],R[1],R[2]];
  for(let a=0;a<3;a++) for(let b=0;b<3;b++){
    const v=EA*c[a]*c[b];
    k[a*12+b]+=v; k[(a+6)*12+b+6]+=v; k[a*12+b+6]-=v; k[(a+6)*12+b]-=v;
  }
  return k;
}

function gaussSolve(K,n,b){
  const m=new Float64Array(n*(n+1));
  for(let i=0;i<n;i++){ for(let j=0;j<n;j++) m[i*(n+1)+j]=K[i*n+j]; m[i*(n+1)+n]=b[i]; }
  for(let c=0;c<n;c++){
    let p=c; for(let r=c+1;r<n;r++) if(Math.abs(m[r*(n+1)+c])>Math.abs(m[p*(n+1)+c])) p=r;
    for(let j=0;j<=n;j++){ const t=m[c*(n+1)+j]; m[c*(n+1)+j]=m[p*(n+1)+j]; m[p*(n+1)+j]=t; }
    const d=m[c*(n+1)+c]; if(Math.abs(d)<1e-12) throw new Error('Singular');
    for(let j=c;j<=n;j++) m[c*(n+1)+j]/=d;
    for(let r=0;r<n;r++){ if(r===c) continue; const f=m[r*(n+1)+c]; for(let j=c;j<=n;j++) m[r*(n+1)+j]-=f*m[c*(n+1)+j]; }
  }
  const x=new Float64Array(n); for(let i=0;i<n;i++) x[i]=m[i*(n+1)+n]; return x;
}

function buildModel(Lm, inp = {}){
  const gs=pdfGeomScale(Lm), sc=Lm/PDF_L_DESIGN_M, dy=Lm/PDF_N_BAYS;
  const hw=0.45*gs, hh=0.375*gs;
  const nodes=[], nk=(si,c)=>si*4+c;
  for(let si=0;si<=PDF_N_BAYS;si++){
    const y=si*dy;
    [[-hw,-hh],[hw,-hh],[hw,hh],[-hw,hh]].forEach((p,c)=>nodes.push({x:p[0],y,z:p[1],si,c}));
  }
  const elements=[], add=(id,i,j,sn,tr)=>elements.push({id,i,j,sec:PDF_SECTIONS[sn],sn,tr});
  for(let si=0;si<PDF_N_BAYS;si++){
    for(let c=0;c<4;c++){
      add(c===2?`Bm119_${si}`:`Bm${100+si}_${c}`, nk(si,c), nk(si+1,c), c===2?'box_90x90x8':'box_75x75x6', false);
    }
    add(`V${si}_P`, nk(si,0), nk(si,3), 'box_75x75x6', false);
    add(`V${si}_S`, nk(si,1), nk(si,2), 'box_75x75x6', false);
    if(si%2===0){
      add(`D${si}_P`, nk(si,0), nk(si+1,3), 'L75x75x8', false);
      add(`D${si}_S`, nk(si,1), nk(si+1,2), 'L75x75x8', false);
    }
    if(si%3===0) add(`X${si}`, nk(si,0), nk(si,2), 'L_200x100x10', false);
  }
  const yKing=inp.guyAttachPos_m ?? inp.kingpostPos_m ?? 9.28*gs;
  const yStay=inp.windStayPos_m ?? 7.77*gs;
  const yBoomRest=inp.boomRestPos_m ?? 8.19*gs;
  const siG=Math.min(PDF_N_BAYS, Math.max(0, Math.round(yKing/dy)));
  const siW=Math.min(PDF_N_BAYS, Math.max(0, Math.round(yStay/dy)));
  const nGuys=Math.max(1, inp.nGuysEffective || 1);
  const neededAnchors=new Set(['Sp3','Sp4','Sp8']);
  for(const g of EXTRA_GUY_LINKS){
    if(nGuys >= g.minGuys) neededAnchors.add(g.anchor);
  }
  const anchorIdx={};
  for(const a of PDF_ANCHORS_90){
    if(!neededAnchors.has(a.tag)) continue;
    let y=a.y*gs, x=a.x*gs, z=a.z*gs;
    if(a.tag==='Sp4'){ y=yKing; x=-0.5*gs; z=9*gs; }
    if(a.tag==='Sp3'){ y=yStay*0.5; x=0.5*gs; z=0.02; }
    const idx=nodes.length;
    nodes.push({x,y,z,tag:a.tag});
    anchorIdx[a.tag]=idx;
  }
  add('Guy56', nk(siG,2), anchorIdx.Sp4, 'Rope_pipe_56mm_eff', true);
  add('Guy40', nk(siG,3), anchorIdx.Sp4, 'Rope_pipe_40mm_eff', true);
  add('GuyLat35', nk(siG,1), anchorIdx.Sp8, 'Rope_pipe_35mm_eff', true);
  add('Stay30', nk(siW,1), anchorIdx.Sp3, 'Rope_pipe_30mm_eff', true);
  for(const g of EXTRA_GUY_LINKS){
    if(nGuys >= g.minGuys && anchorIdx[g.anchor] != null){
      add(g.id, nk(siG, g.corner), anchorIdx[g.anchor], g.sn, true);
    }
  }
  return {nodes, elements, nk, sc, dy, gs, siG, siW, siBr:Math.round(yBoomRest/dy), anchorIdx};
}

function solve3d(model, loads, supports){
  const n=model.nodes.length, ndof=6*n;
  const K=new Float64Array(ndof*ndof), F=new Float64Array(ndof);
  const meta=[];
  for(const el of model.elements){
    const a=model.nodes[el.i], b=model.nodes[el.j];
    const R=dirCos3(a.x,a.y,a.z,b.x,b.y,b.z);
    const Lmm=Math.hypot(b.x-a.x,b.y-a.y,b.z-a.z)*1000;
    let kG;
    if(el.tr||el.sec.truss) kG=trussGlobalK(el.sec.E, el.sec.A, Lmm, R);
    else kG=transform12(beam3dLocalK(el.sec.E, PDF_G, el.sec.A, el.sec.Iy, el.sec.Iz, el.sec.J, Lmm), R);
    const map=[6*el.i,6*el.i+1,6*el.i+2,6*el.i+3,6*el.i+4,6*el.i+5,6*el.j,6*el.j+1,6*el.j+2,6*el.j+3,6*el.j+4,6*el.j+5];
    for(let r=0;r<12;r++) for(let c=0;c<12;c++) K[map[r]*ndof+map[c]]+=kG[r*12+c];
    meta.push({el,Lmm,R,map,kG});
  }
  for(const ld of loads){ F[6*ld.node+0]+=ld.fx||0; F[6*ld.node+1]+=ld.fy||0; F[6*ld.node+2]+=ld.fz||0; }
  const fixed=new Set();
  for(const s of supports){
    const dof=['ux','uy','uz','rx','ry','rz'];
    dof.forEach((d,i)=>{ if(s[d]) fixed.add(6*s.node+i); });
  }
  const free=[]; for(let i=0;i<ndof;i++) if(!fixed.has(i)) free.push(i);
  const nf=free.length, Kff=new Float64Array(nf*nf), Ff=new Float64Array(nf);
  for(let a=0;a<nf;a++){ Ff[a]=F[free[a]]; for(let b=0;b<nf;b++) Kff[a*nf+b]=K[free[a]*ndof+free[b]]; }
  const uf=gaussSolve(Kff,nf,Ff);
  const u=new Float64Array(ndof); for(let a=0;a<nf;a++) u[free[a]]=uf[a];
  const R=new Float64Array(ndof);
  for(let i=0;i<ndof;i++){ let s=0; for(let j=0;j<ndof;j++) s+=K[i*ndof+j]*u[j]; R[i]=s-F[i]; }
  return {u,R,meta,ndof};
}

function ropeAnchorNodes(model){
  const anchors=new Set();
  for(const el of model.elements){
    if(!el.tr) continue;
    for(const idx of [el.i, el.j]){
      const tag=model.nodes[idx].tag;
      if(tag && tag.startsWith('Sp')) anchors.add(idx);
    }
  }
  return anchors;
}

function buildSupports3d(model, combo, inp){
  const sup=[];
  const active=s=>combo && combo.supports.includes(s);
  for(const node of ropeAnchorNodes(model)){
    sup.push({node,ux:1,uy:1,uz:1,rx:1,ry:1,rz:1});
  }
  if(active('lifting')){
    const mid=model.nk(Math.floor(PDF_N_BAYS/2),2);
    sup.push({node:mid, ux:1, uy:1, uz:1, rx:1, ry:1, rz:1});
    return sup;
  }
  for(let c=0;c<4;c++) sup.push({node:c,ux:1,uy:1,uz:1,rx:1,ry:1,rz:1});
  if(active('boomrest') && inp.boomRestEnabled){
    const si=Math.min(PDF_N_BAYS, Math.max(0, Math.round(inp.boomRestPos_m/model.dy)));
    for(let c=0;c<4;c++) sup.push({node:model.nk(si,c), uz:1});
  }
  return sup;
}

function computeSpaceFrameLoads(inp, combo, model){
  const g=9.81, rhoSteel=7.85e-6;
  const swFactor=inp.structuralSwFactor!=null?inp.structuralSwFactor:PDF_SW_FACTOR;
  const OD=inp.OD_mm, t=Math.min(inp.t_mm, inp.OD_mm/2-0.01);
  const wAdded=(inp.addedW_kgpm*g)/1000;
  const useCombo=!!combo;
  const lf=useCombo?(combo.condition==='lifting'?inp.liftingLoadFactor:combo.loadFactor):1;
  let wMult=lf;
  const sfZ=useCombo?combo.sfZ:1, sfY=useCombo?combo.sfY:1, sfX=useCombo?combo.sfX:1;
  const heel=heelRad(inp, useCombo, combo);
  const windMultX=useCombo?combo.windX:1, windMultY=useCombo?combo.windY:1, daf=inp.DAF;
  let windSpeed=inp.windSpeed_ms;
  if(useCombo && combo.condition==='survival') windSpeed*=1.15;
  if(useCombo && combo.condition==='lifting') windSpeed=0;
  const theta=inp.angle_deg*Math.PI/180, cosT=Math.cos(theta), sinT=Math.sin(theta);
  const deadMult=cosT*wMult*daf*sfZ;
  const liveMult=deadMult;
  const q=0.5*inp.rhoAir*windSpeed*windSpeed*inp.windExposure;
  const wWind=q*inp.Cd*(OD/1000)/1000;
  const nodal=new Map();
  const addLoad=(node,fx,fy,fz)=>{
    let ld=nodal.get(node);
    if(!ld){ ld={fx:0,fy:0,fz:0}; nodal.set(node,ld); }
    ld.fx+=fx; ld.fy+=fy; ld.fz+=fz;
  };
  let frameWeightN=0;
  for(const el of model.elements){
    if(el.tr||el.sec.truss) continue;
    const a=model.nodes[el.i], b=model.nodes[el.j];
    const Lmm=Math.hypot(b.x-a.x,b.y-a.y,b.z-a.z)*1000;
    const yMid=(a.y+b.y)/2;
    const dry=dryFractionAtY(yMid, inp.L_m, inp, useCombo, combo);
    const W=rhoSteel*el.sec.A*Lmm*g*swFactor*deadMult*dry;
    frameWeightN+=W;
    applyHeelLoad(addLoad, el.i, W/2, heel);
    applyHeelLoad(addLoad, el.j, W/2, heel);
  }
  const wAddedLine=wAdded*swFactor*deadMult;
  for(let si=0;si<PDF_N_BAYS;si++){
    const yMid=(si+0.5)*model.dy;
    const dry=dryFractionAtY(yMid, inp.L_m, inp, useCombo, combo);
    const wBay=wAddedLine*dry*model.dy/4;
    for(let c=0;c<4;c++) applyHeelLoad(addLoad, model.nk(si,c), wBay, heel);
  }
  const dryTip=dryFractionAtY(inp.L_m, inp.L_m, inp, useCombo, combo);
  const Ptip=inp.tipLoad_kg*g*liveMult*dryTip;
  const Pextra=inp.extraLoad_kg*g*liveMult;
  const refVertical=frameWeightN+wAddedLine*inp.L_m;
  const fxDyn=useCombo?refVertical*sfX/Math.max(sfZ,1e-9)/inp.L_m:0;
  for(let si=0;si<PDF_N_BAYS;si++) for(let c=0;c<4;c++){
    addLoad(model.nk(si,c),(wWind*windMultX+fxDyn)*model.dy/4,0,0);
  }
  applyHeelLoad(addLoad, model.nk(PDF_N_BAYS,2), Ptip, heel);
  if(inp.extraLoad_kg>0){
    const si=Math.min(PDF_N_BAYS,Math.max(0,Math.round(inp.extraPos_m/model.dy)));
    const dryExtra=dryFractionAtY(inp.extraPos_m, inp.L_m, inp, useCombo, combo);
    applyHeelLoad(addLoad, model.nk(si,2), Pextra*dryExtra, heel);
  }
  if(useCombo && windMultY>0){
    const wy=wWind*inp.L_m*windMultY;
    addLoad(model.nk(PDF_N_BAYS,2),0,wy*sinT,-wy*cosT);
  }
  const loads=[];
  for(const [node,ld] of nodal) loads.push({node,...ld});
  const wZ=refVertical/inp.L_m/1000;
  const Fz_total=refVertical+Ptip+Pextra;
  return {loads,wZ,wWind,windMultX,Ptip,Pextra,sfZ,sfX,sfY,wMult,daf,Fz_total,frameWeightN,swFactor};
}

function memberEndForces(meta, u){
  const members=[];
  for(const m of meta){
    const ug=new Float64Array(12);
    for(let k=0;k<12;k++) ug[k]=u[m.map[k]];
    const sec=m.el.sec, R=m.R;
    if(m.el.tr||sec.truss){
      const du=(ug[6]-ug[0])*R[0]+(ug[7]-ug[1])*R[1]+(ug[8]-ug[2])*R[2];
      const N=sec.E*sec.A/m.Lmm*du;
      members.push({id:m.el.id,sn:m.el.sn,N,My:0,Mz:0,V:0,truss:true});
    } else {
      const fg=new Float64Array(12);
      for(let i=0;i<12;i++){ let s=0; for(let k=0;k<12;k++) s+=m.kG[i*12+k]*ug[k]; fg[i]=s; }
      const lx=R[0], mx=R[1], nx=R[2];
      const Ni=fg[0]*lx+fg[1]*mx+fg[2]*nx;
      const Nj=fg[6]*lx+fg[7]*mx+fg[8]*nx;
      const N=Math.max(Math.abs(Ni),Math.abs(Nj));
      const ul=new Float64Array(12);
      for(let block=0;block<4;block++){
        for(let i=0;i<3;i++){
          let s=0;
          for(let j=0;j<3;j++) s+=R[i*3+j]*ug[block*3+j];
          ul[block*3+i]=s;
        }
      }
      const kL=beam3dLocalK(sec.E,PDF_G,sec.A,sec.Iy,sec.Iz,sec.J,m.Lmm);
      const fl=new Float64Array(12);
      for(let i=0;i<12;i++){ let s=0; for(let k=0;k<12;k++) s+=kL[i*12+k]*ul[k]; fl[i]=s; }
      const MyA=Math.max(Math.abs(fl[4]),Math.abs(fl[10]));
      const MzA=Math.max(Math.abs(fl[5]),Math.abs(fl[11]));
      let My,Mz;
      if(Math.abs(R[1])>0.85){
        const Mb=MzA>0?Math.min(MyA,MzA):MyA;
        My=Mb; Mz=0;
      } else {
        My=MyA; Mz=MzA;
      }
      const Vy=Math.max(Math.hypot(fg[1],fg[2]),Math.hypot(fg[7],fg[8]));
      members.push({id:m.el.id,sn:m.el.sn,N,My,Mz,V:Vy,truss:false,solved:true});
    }
  }
  return members;
}

function memberUnityFromModel(members, model, Mbase, Nax, Fy, SF){
  const allow=Fy/SF;
  let worst={util:0,id:'Bm119_0',sn:'box_90x90x8',sigma:0,allow};
  let worstBrace={util:0,id:'—',sn:'',sigma:0,allow};
  const rows=members.map(m=>{
    const sec=PDF_SECTIONS[m.sn]||{};
    const cat=memberCategory(m.id);
    if(m.truss){
      const tAllow=(sec.allow||120)*1000;
      const util=Math.max(0,Math.abs(m.N))/tAllow;
      return {...m,cat,util,pass:util<=1,sigma:Math.max(0,Math.abs(m.N))/1000,allow:tAllow/1000,solved:true};
    }
    const A=sec.A||2624;
    const Zy=sec.Zy||66000, Zz=sec.Zz||Zy;
    let Nmem=Math.abs(m.N);
    let Mmem=0;
    if(m.id.startsWith('Bm119')){
      const si=parseInt(m.id.match(/^Bm119_(\d+)/)[1],10);
      const frac=(si+0.5)/PDF_N_BAYS;
      Mmem=Mbase*frac*frac;
    } else if(m.solved){
      Mmem=Math.min(Math.max(Math.abs(m.My),Math.abs(m.Mz)),Mbase*0.5);
    }
    const sa=Nmem/A;
    const sb=Mmem/Zy+(m.id.startsWith('Bm119')?0:Math.abs(m.Mz)/Zz);
    const sigma=sa+sb;
    const util=allow>0?sigma/allow:0;
    if(m.id.startsWith('Bm119') && util>worst.util) worst={util,id:m.id,sn:m.sn,sigma,allow};
    if(cat==='brace' && util>worstBrace.util) worstBrace={util,id:m.id,sn:m.sn,sigma,allow};
    return {...m,cat,N:Nmem,My:Mmem,Mz:m.id.startsWith('Bm119')?0:Math.abs(m.Mz),util,pass:util<=1,sigma,allow,solved:true,
      axialFrom:'3D solved',bendingFrom:m.id.startsWith('Bm119')?'3D base tributary':'solved cap'};
  });
  return {rows,worst,worstBrace};
}

function computeSpaceFrameCore(inp, combo){
  const model=buildModel(inp.L_m, inp);
  const {loads}=computeSpaceFrameLoads(inp, combo, model);
  const supports=buildSupports3d(model, combo, inp);
  const sol=solve3d(model, loads, supports);
  const members=memberEndForces(sol.meta, sol.u);
  const tempFactor=(combo && combo.condition==='operating')?0.9:1;
  let Mbase=0, Vres=0, Nax=0;
  for(let c=0;c<4;c++){ Mbase+=Math.hypot(sol.R[6*c+4], sol.R[6*c+5]); Vres+=Math.hypot(sol.R[6*c], sol.R[6*c+1]); Nax+=Math.abs(sol.R[6*c+2]); }
  Mbase/=4; Vres/=4; Nax/=4;
  const unity=memberUnityFromModel(members, model, Mbase, Nax, inp.Fy_MPa*tempFactor, inp.SF);
  const tipN=model.nk(PDF_N_BAYS,2);
  const dRes=Math.hypot(sol.u[6*tipN], sol.u[6*tipN+1], sol.u[6*tipN+2]);
  const OD=inp.OD_mm, t=Math.min(inp.t_mm, inp.OD_mm/2-0.01);
  const A=Math.PI/4*(OD*OD-(OD-2*t)*(OD-2*t));
  const I=Math.PI/64*(Math.pow(OD,4)-Math.pow(OD-2*t,4));
  const Z=I/(OD/2);
  const sigmaEq=unity.worst.sigma||0;
  const allow=inp.Fy_MPa/inp.SF;
  const actualSF=sigmaEq>0?inp.Fy_MPa/sigmaEq:Infinity;
  const stayM=members.find(m=>m.id==='Stay30');
  const kpR=members.filter(m=>m.id.startsWith('Guy')).reduce((s,m)=>s+Math.abs(m.N),0);
  const guyNs=members.filter(m=>/^Guy/.test(m.id)).map(m=>Math.abs(m.N));
  const guyT=guyNs.length?Math.max(...guyNs)/1000/Math.max(1, inp.nGuysEffective||1):0;
  const stayR=stayM?Math.abs(stayM.N)/1000:0;
  const supportsOut={
    turntable:{M_kNm:Mbase/1e6,V_kN:Vres/1000,N_kN:Nax/1000},
    kingpost:{R_kN:kpR/1000,ok:kpR/1000<=inp.kingpostRated_kN},
    windstay:{R_kN:stayR,ok:stayR<=inp.windStayRated_kN},
    boomrest:{R_kN:0,ok:true},
    guys:{T_kN:guyT,util:inp.guyAllow_kN>0?guyT/inp.guyAllow_kN*100:0,ok:inp.guyAllow_kN<=0||guyT<=inp.guyAllow_kN}
  };
  const pass=unity.worst.util<=1 && actualSF>=inp.SF && supportsOut.kingpost.ok && supportsOut.windstay.ok && supportsOut.guys.ok
    && supportsOut.turntable.M_kNm<=inp.ratedMoment_kNm && Math.hypot(supportsOut.turntable.V_kN,supportsOut.turntable.N_kN)<=inp.ratedLoad_kN;
  return {model, sol, members, unity, Mbase, Vres, Nax, dRes, sigmaEq, allow, actualSF, supportsOut, pass, A, I, Z, OD, t, tipN};
}

module.exports = { buildModel, solve3d, buildSupports3d, computeSpaceFrameLoads, memberEndForces, memberUnityFromModel, computeSpaceFrameCore, memberCategory, isUnityTableMember, dryFractionAtY, ropeAnchorNodes, PDF_SECTIONS, PDF_ANCHORS_90, PDF_L_DESIGN_M, PDF_L_PDF90_M, PDF_L_REF_M, PDF_N_BAYS, PDF_DY_M, PDF_E, PDF_G, PDF_E_ROPE, PDF_SW_FACTOR, pdfGeomScale };

if (require.main === module) {
  const inp = {
    L_m: PDF_L_DESIGN_M, OD_mm: 219.1, t_mm: 8.18, Fy_MPa: 241, SF: 1.67,
    angle_deg: 0, addedW_kgpm: 15, tipLoad_kg: 80, extraLoad_kg: 30, extraPos_m: 9.144,
    windSpeed_ms: 40, rhoAir: 1.225, windExposure: 1, Cd: 1.2, DAF: 1.15,
    accidentalDryFactor: 1, liftingLoadFactor: 2,
    boomRestEnabled: true, guysEnabled: true, windStayEnabled: true,
    boomRestPos_m: 5.46, kingpostRated_kN: 80, windStayRated_kN: 25,
    guyAllow_kN: 50, nGuysEffective: 1, ratedMoment_kNm: 60, ratedLoad_kN: 30,
  };
  const combo = {
    label: 'Operating · Heave+Resultant', condition: 'operating', loadFactor: 1,
    sfZ: 3.25, sfY: 0.29, sfX: 0.03, windX: 0.99, windY: 0.10,
    supports: ['turntable', 'kingpost', 'windstay', 'guys'],
  };
  const core = computeSpaceFrameCore(inp, combo);
  console.log('3D model nodes', core.model.nodes.length, 'members', core.model.elements.length,
    'Bm119', core.model.elements.filter(e => e.id.startsWith('Bm119')).length);
  console.log('worst Bm119', core.unity.worst.id, (core.unity.worst.util * 100).toFixed(1) + '%',
    'Mbase', (core.Mbase / 1e6).toFixed(2), 'kN·m', 'dRes', (core.dRes / 1000).toFixed(2), 'm');
  console.log('pass', core.pass, 'kingpost', core.supportsOut.kingpost.R_kN.toFixed(1), 'kN');
}
