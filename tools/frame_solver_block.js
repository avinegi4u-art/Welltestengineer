  // ---- 2D plane frame solver (direct stiffness, Euler-Bernoulli beams + truss links) ----
  function _matZero(n){ return Array.from({length:n}, ()=>new Float64Array(n)); }
  function _vecZero(n){ return new Float64Array(n); }
  function _addK(K,i,j,v){ K[i][j]+=v; }

  function _beamLocalK(E,A,I,L){
    const EA=E*A, EI=E*I, L2=L*L, L3=L2*L;
    return [
      [EA/L,0,0,-EA/L,0,0],
      [0,12*EI/L3,6*EI/L2,0,-12*EI/L3,6*EI/L2],
      [0,6*EI/L2,4*EI/L,0,-6*EI/L2,2*EI/L],
      [-EA/L,0,0,EA/L,0,0],
      [0,-12*EI/L3,-6*EI/L2,0,12*EI/L3,-6*EI/L2],
      [0,6*EI/L2,2*EI/L,0,-6*EI/L2,4*EI/L],
    ];
  }

  function _transformBeamK(kL,c,s){
    const T=[[c,s,0,0,0,0],[-s,c,0,0,0,0],[0,0,1,0,0,0],[0,0,0,c,s,0],[0,0,0,-s,c,0],[0,0,0,0,0,1]];
    const TT=T[0].map((_,j)=>T.map(r=>r[j]));
    const tmp=Array.from({length:6},()=>new Array(6).fill(0));
    for(let i=0;i<6;i++) for(let j=0;j<6;j++) for(let k=0;k<6;k++) tmp[i][j]+=TT[i][k]*kL[k][j];
    const kg=Array.from({length:6},()=>new Array(6).fill(0));
    for(let i=0;i<6;i++) for(let j=0;j<6;j++) for(let k=0;k<6;k++) kg[i][j]+=tmp[i][k]*T[k][j];
    return kg;
  }

  function _trussGlobalK(E,A,L,c,s){
    const k=E*A/L, cx=c*c, cs=c*s, ss=s*s;
    return [
      [k*cx,k*cs,0,-k*cx,-k*cs,0],
      [k*cs,k*ss,0,-k*cs,-k*ss,0],
      [0,0,0,0,0,0],
      [-k*cx,-k*cs,0,k*cx,k*cs,0],
      [-k*cs,-k*ss,0,k*cs,k*ss,0],
      [0,0,0,0,0,0],
    ];
  }

  function _assembleBeam(K,F,n0,n1,E,A,I,x0,z0,x1,z1,qx,qz){
    const dx=x1-x0, dz=z1-z0, L=Math.hypot(dx,dz);
    if(L<1e-9) return;
    const c=dx/L, s=dz/L;
    const kG=_transformBeamK(_beamLocalK(E,A,I,L),c,s);
    const map=[3*n0,3*n0+1,3*n0+2,3*n1,3*n1+1,3*n1+2];
    for(let a=0;a<6;a++) for(let b=0;b<6;b++) _addK(K,map[a],map[b],kG[a][b]);
    const qn=-qx*s+qz*c, qt=qx*c+qz*s;
    const V0=qn*L/2, M0=qn*L*L/12, V1=qn*L/2, M1=-qn*L*L/12;
    const feL=[qt*L/2,V0,M0,qt*L/2,V1,M1];
    const T=[[c,s,0,0,0,0],[-s,c,0,0,0,0],[0,0,1,0,0,0],[0,0,0,c,s,0],[0,0,0,-s,c,0],[0,0,0,0,0,1]];
    for(let a=0;a<6;a++){
      let fg=0; for(let b=0;b<6;b++) fg+=T[a][b]*feL[b];
      F[map[a]]+=fg;
    }
  }

  function _assembleTruss(K,n0,n1,E,A,x0,z0,x1,z1){
    const dx=x1-x0, dz=z1-z0, L=Math.hypot(dx,dz);
    if(L<1e-9) return null;
    const c=dx/L, s=dz/L;
    const kG=_trussGlobalK(E,A,L,c,s);
    const map=[3*n0,3*n0+1,3*n0+2,3*n1,3*n1+1,3*n1+2];
    for(let a=0;a<6;a++) for(let b=0;b<6;b++) _addK(K,map[a],map[b],kG[a][b]);
    return {L,c,s,E,A,i:n0,j:n1};
  }

  function _gaussSolve(A,b){
    const n=b.length;
    const M=A.map((row,i)=>[...row,b[i]]);
    for(let col=0;col<n;col++){
      let piv=col;
      for(let r=col+1;r<n;r++) if(Math.abs(M[r][col])>Math.abs(M[piv][col])) piv=r;
      [M[col],M[piv]]=[M[piv],M[col]];
      const d=M[col][col];
      if(Math.abs(d)<1e-12) throw new Error('Singular frame stiffness — check support layout.');
      for(let j=col;j<=n;j++) M[col][j]/=d;
      for(let r=0;r<n;r++){
        if(r===col) continue;
        const f=M[r][col];
        for(let j=col;j<=n;j++) M[r][j]-=f*M[col][j];
      }
    }
    return M.map(row=>row[n]);
  }

  function _solveFrame2D(nodes, elements, supports, pointLoads){
    const n=nodes.length, ndof=3*n;
    const K=_matZero(ndof), F=_vecZero(ndof);
    const trussMeta=[];
    for(const pl of pointLoads){
      F[3*pl.node+0]+=pl.fx||0;
      F[3*pl.node+1]+=pl.fz||0;
      F[3*pl.node+2]+=pl.my||0;
    }
    for(const el of elements){
      const p0=nodes[el.i], p1=nodes[el.j];
      if(el.type==='beam') _assembleBeam(K,F,el.i,el.j,el.E,el.A,el.I,p0.x,p0.z,p1.x,p1.z,el.qx||0,el.qz||0);
      else {
        const meta=_assembleTruss(K,el.i,el.j,el.E,el.A,p0.x,p0.z,p1.x,p1.z);
        if(meta) trussMeta.push(meta);
      }
    }
    const fixed=new Set();
    for(const s of supports){
      if(s.ux) fixed.add(3*s.node);
      if(s.uz) fixed.add(3*s.node+1);
      if(s.ry) fixed.add(3*s.node+2);
    }
    const free=[];
    for(let i=0;i<ndof;i++) if(!fixed.has(i)) free.push(i);
    const nf=free.length;
    const Kff=_matZero(nf), Ff=_vecZero(nf);
    for(let a=0;a<nf;a++){
      Ff[a]=F[free[a]];
      for(let b=0;b<nf;b++) Kff[a][b]=K[free[a]][free[b]];
    }
    const u=_vecZero(ndof);
    const uf=_gaussSolve(Kff,Ff);
    for(let a=0;a<nf;a++) u[free[a]]=uf[a];
    const R=_vecZero(ndof);
    for(let i=0;i<ndof;i++){
      let sum=0; for(let j=0;j<ndof;j++) sum+=K[i][j]*u[j];
      R[i]=sum-F[i];
    }
    const trussForces=trussMeta.map(t=>{
      const ui=u[3*t.i], wi=u[3*t.i+1], uj=u[3*t.j], wj=u[3*t.j+1];
      const dl=(uj-ui)*t.c+(wj-wi)*t.s;
      return {T:t.E*t.A/t.L*dl, i:t.i, j:t.j};
    });
    return {u,R,trussForces};
  }

  function _nodeAlongBoom(i,nSeg,Lmm,theta){
    const s=Lmm*i/nSeg;
    return {x:s*Math.cos(theta), z:s*Math.sin(theta), s};
  }

  function _nodeIndexAt(dist_m, Lm, nSeg){
    return Math.min(nSeg, Math.max(0, Math.round(dist_m/Lm*nSeg)));
  }

  function computeFrame(inp, combo){
    const g=9.81, rhoSteel=7.85e-6;
    const E=inp.E_MPa, Lmm=inp.L_m*1000, Lm=inp.L_m;
    const OD=inp.OD_mm, t=Math.min(inp.t_mm, inp.OD_mm/2-0.01);
    const ID=OD-2*t;
    const A=Math.PI/4*(OD*OD-ID*ID);
    const I=Math.PI/64*(Math.pow(OD,4)-Math.pow(ID,4));
    const Z=I/(OD/2);
    const theta=inp.angle_deg*Math.PI/180;
    const cosT=Math.cos(theta), sinT=Math.sin(theta);
    const wSelf=A*rhoSteel*g;
    const wAdded=(inp.addedW_kgpm*g)/1000;
    const wGravity=wSelf+wAdded;
    const Ptip=inp.tipLoad_kg*g;
    const Pextra=inp.extraLoad_kg*g;
    const xp=Math.min(inp.extraPos_m*1000, Lmm);

    const useCombo=!!combo;
    const lf=useCombo?(combo.condition==='lifting'?inp.liftingLoadFactor:combo.loadFactor):1;
    let wMult=lf;
    if(useCombo && combo.condition==='accidental') wMult*=inp.accidentalDryFactor;
    const sfZ=useCombo?combo.sfZ:1;
    const sfY=useCombo?combo.sfY:1;
    const sfX=useCombo?combo.sfX:1;
    const windMultX=useCombo?combo.windX:1;
    const windMultY=useCombo?combo.windY:1;
    const daf=inp.DAF;
    let windSpeed=inp.windSpeed_ms;
    if(useCombo && combo.condition==='survival') windSpeed*=1.15;
    if(useCombo && combo.condition==='lifting') windSpeed=0;

    const wVert0=wGravity*cosT;
    const wZ=wVert0*wMult*daf*sfZ;
    const PtipZ=Ptip*cosT*wMult*daf*sfZ;
    const PextraZ=Pextra*cosT*wMult*daf*sfZ;
    const wAxExtra=wGravity*sinT*wMult*daf*sfY;

    const q_Pa=0.5*inp.rhoAir*windSpeed*windSpeed*inp.windExposure;
    const wWind=q_Pa*inp.Cd*(OD/1000)/1000;
    const wxWind=wWind*windMultX;
    const Fz_total=wZ*Lm + PtipZ + PextraZ;
    const wxDyn=useCombo?(Fz_total*sfX/Math.max(sfZ,1e-9))/Lm:0;
    let wx=wxWind+wxDyn;
    let wz=-wZ;
    if(wAxExtra>0){ wx+=wAxExtra*cosT; wz+=wAxExtra*sinT; }

    const nSeg=12;
    const nodes=[];
    for(let i=0;i<=nSeg;i++) nodes.push(_nodeAlongBoom(i,nSeg,Lmm,theta));
    const elements=[];
    for(let i=0;i<nSeg;i++) elements.push({type:'beam',i,j:i+1,E,A,I,qx:wx,qz:wz});

    const supports=[{node:0,ux:true,uz:true,ry:true}];
    const active=s=>combo && combo.supports.includes(s);
    let kpNode=-1, brNode=-1, wsNode=-1, guyNode=-1;
    if(useCombo && active('kingpost') && inp.kingpostEnabled){
      kpNode=_nodeIndexAt(inp.kingpostPos_m,Lm,nSeg);
      supports.push({node:kpNode,uz:true});
    }
    if(useCombo && active('boomrest') && inp.boomRestEnabled){
      brNode=_nodeIndexAt(inp.boomRestPos_m,Lm,nSeg);
      supports.push({node:brNode,uz:true});
    }
    let nextNode=nSeg+1;
    if(useCombo && active('windstay') && inp.windStayEnabled){
      wsNode=_nodeIndexAt(inp.windStayPos_m,Lm,nSeg);
      const bn=nodes[wsNode];
      nodes.push({x:bn.x+3000, z:0, s:bn.s});
      elements.push({type:'truss',i:wsNode,j:nextNode,E:120000,A:600});
      supports.push({node:nextNode,ux:true,uz:true});
      nextNode++;
    }
    if(useCombo && active('guys') && inp.guysEnabled && inp.nGuysEffective>0){
      guyNode=_nodeIndexAt(inp.guyAttachPos_m,Lm,nSeg);
      const gn=nodes[guyNode];
      const ang=inp.guyAngle_deg*Math.PI/180;
      const gL=inp.guyLength_m*1000;
      nodes.push({x:gn.x-gL*Math.cos(ang), z:gn.z-gL*Math.sin(ang), s:gn.s});
      elements.push({type:'truss',i:guyNode,j:nextNode,E:150000,A:Math.max(200,400*inp.nGuysEffective)});
      supports.push({node:nextNode,ux:true,uz:true});
      nextNode++;
    }

    const pointLoads=[{node:nSeg,fz:-PtipZ,fx:0}];
    if(inp.extraLoad_kg>0) pointLoads.push({node:_nodeIndexAt(inp.extraPos_m,Lm,nSeg),fz:-PextraZ,fx:0});
    if(useCombo && windMultY>0){
      const Fy_w=wWind*Lm*windMultY;
      pointLoads.push({node:nSeg,fx:Fy_w*sinT, fz:-Fy_w*cosT});
    }

    let sol;
    try { sol=_solveFrame2D(nodes, elements, supports, pointLoads); }
    catch(_e){ return compute({...inp, analysisMode:'matrix'}, combo); }

    const {u,R,trussForces}=sol;
    let Mres=Math.abs(R[2]);
    const Vx=R[0], Vz=R[1];
    const Vres=Math.hypot(Vx,Vz);
    const N_d=Math.abs(Vx*cosT+Vz*sinT);
    if(useCombo && active('lifting')) Mres*=0.85;

    const tipUx=u[3*nSeg], tipUz=u[3*nSeg+1];
    const dRes=Math.hypot(tipUx, tipUz);
    const defLimit=Lmm/inp.defLimitDenom;

    const sigmaBend=Z>0?Mres/Z:0;
    const sigmaAxial=A>0?N_d/A:0;
    const sigmaCombined=sigmaBend+sigmaAxial;
    const tau=A>0?2*Vres/A:0;
    const sigmaEq=Math.sqrt(sigmaCombined*sigmaCombined+3*tau*tau);
    const allow=inp.Fy_MPa/inp.SF;
    const actualSF=sigmaEq>0?inp.Fy_MPa/sigmaEq:Infinity;
    const Dt=t>0?OD/t:0;
    const Kbuck=2.0;
    const Pcr=I>0&&Lmm>0?(Math.PI*Math.PI*E*I)/Math.pow(Kbuck*Lmm,2):0;
    const bucklingSF=N_d>0?Pcr/N_d:Infinity;
    const bucklingPass=N_d<=0||bucklingSF>=inp.SF;
    const Rbolt=inp.bcd_mm/2;
    const boltTension_kN=inp.nBolts>0?((2*Mres/(inp.nBolts*Rbolt))+(N_d/inp.nBolts))/1000:0;
    const boltUtil=inp.boltAllow_kN>0?boltTension_kN/inp.boltAllow_kN*100:0;

    const supportsOut={turntable:{M_kNm:Mres/1e6,V_kN:Vres/1000,N_kN:N_d/1000},kingpost:{R_kN:0,ok:true},windstay:{R_kN:0,ok:true},boomrest:{R_kN:0,ok:true},guys:{T_kN:0,util:0,ok:true}};
    if(kpNode>=0){
      supportsOut.kingpost.R_kN=Math.abs(R[3*kpNode+1])/1000;
      supportsOut.kingpost.ok=supportsOut.kingpost.R_kN<=inp.kingpostRated_kN;
    }
    if(brNode>=0){
      supportsOut.boomrest.R_kN=Math.abs(R[3*brNode+1])/1000;
      supportsOut.boomrest.ok=supportsOut.boomrest.R_kN<=inp.boomRestRated_kN;
    }
    if(wsNode>=0){
      const tf=trussForces.find(t=>t.i===wsNode);
      supportsOut.windstay.R_kN=tf?Math.abs(tf.T)/1000:0;
      supportsOut.windstay.ok=supportsOut.windstay.R_kN<=inp.windStayRated_kN;
    }
    if(guyNode>=0){
      const tg=trussForces.find(t=>t.i===guyNode);
      const T=tg?Math.max(0,tg.T)/1000/inp.nGuysEffective:0;
      supportsOut.guys.T_kN=T;
      supportsOut.guys.util=inp.guyAllow_kN>0?T/inp.guyAllow_kN*100:0;
      supportsOut.guys.ok=supportsOut.guys.util<=100;
    }

    const utilStress=allow>0?sigmaEq/allow:0;
    const pass=actualSF>=inp.SF && bucklingPass && boltUtil<=100
      && supportsOut.kingpost.ok && supportsOut.windstay.ok && supportsOut.boomrest.ok && supportsOut.guys.ok
      && supportsOut.turntable.M_kNm<=inp.ratedMoment_kNm
      && Math.sqrt(supportsOut.turntable.V_kN**2+supportsOut.turntable.N_kN**2)<=inp.ratedLoad_kN;

    const n=21, xs=[], Mg=[], Mw=[], Mr=[], defl=[];
    for(let i=0;i<n;i++){
      const x=Lmm*i/(n-1);
      xs.push(x);
      const rem=Lmm-x;
      const mg=wZ*rem*rem/2 + PtipZ*rem + (x<=xp?PextraZ*(xp-x):0);
      const mw=wWind*windMultX*rem*rem/2;
      Mg.push(mg); Mw.push(mw); Mr.push(Math.sqrt(mg*mg+mw*mw));
      defl.push(dRes*(x/Lmm));
    }

    const testLoadFactor=inp.testFactor;
    const dUdl_t=I>0?wVert0*testLoadFactor*Math.pow(Lmm,4)/(8*E*I):0;
    const dTip_t=I>0?Ptip*cosT*testLoadFactor*Math.pow(Lmm,3)/(3*E*I):0;
    const predictedTestDefl=dUdl_t+dTip_t;
    const testLoad_kg=inp.swl_kg*testLoadFactor;

    return {A,I,Z,OD,ID,L:Lmm,theta,wSelf,wAdded,wGravity,Ptip,Pextra,xp,
      Mgrav_d:Mres,Vgrav_d:Vres,N_d,Mwind:Mw[0],Vwind:wxWind*Lm,Mres,Vres,sigmaBend,sigmaAxial,sigmaCombined,tau,sigmaEq,
      allow,actualSF,dVert:dRes,dWind:0,dRes,defLimit, boltTension_kN, boltUtil, R:Rbolt,
      xs,Mg,Mw,Mr,defl, predictedTestDefl, testLoad_kg, Dt, Pcr, bucklingSF, bucklingPass, t,
      comboLabel:combo?combo.label:null, supports:supportsOut, utilStress, pass,
      Fx_total:Vx, Fz_total, Fy_ax:N_d, frameSolver:true, frameNodes:nodes.length, frameElements:elements.length};
  }
