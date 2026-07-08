#!/usr/bin/env python3
"""Generate upgraded Upstream Calculations App HTML."""
import json, re, textwrap

SRC = "/workspace/_calc_data_backup.json"
OUT = "/workspace/Oil and gas calculations-app.html"

with open(SRC) as f:
    calc_data = json.load(f)

# Notes/cautions keyed by segment|name
NOTES = {
    "Drilling|Hydrostatic pressure": "Single-phase fluid column; temperature/MW variation not included.",
    "Drilling|ECD": "Uses simplified annular loss; validate with hydraulics model for HPHT.",
    "Well Control|Kill mud weight": "Assumes static well; dynamic circulating kill requires additional margin.",
    "Well Control|MAASP": "Use most recent LOT/FIT at casing shoe; include choke line friction if applicable.",
    "Completion|Burst / collapse / tension check": "Compare worst-case loads to rated values; apply design SF per operator standard.",
    "Production|Oil PI": "Valid for stabilized flow above bubble point; use pseudopressure for gas.",
    "Production|Productivity decline": "Select decline model based on drive mechanism and b-factor diagnostics.",
    "Well Testing & DST|Permeability from build-up": "Valid for infinite-acting radial flow; check for boundaries/phase change.",
    "Well Testing & DST|Skin": "s > -3 often indicates stimulation; large positive s suggests damage.",
    "Well Testing & DST|Build-up Horner ratio": "Requires prior constant-rate drawdown tp before shut-in.",
    "Well Testing & DST|Radius of investigation": "Approximate; affected by layering, faults, and dual porosity.",
    "Well Testing & DST|Wellbore storage coefficient": "Early-time dominated; use log-log derivative to identify end of storage.",
    "Surface Well Testing|Choke flow estimate gas": "Gilbert-type correlation; verify against field calibration.",
    "Sampling & PVT|Gas formation volume factor": "Use z-factor correlation appropriate for composition and P,T range.",
    "Sampling & PVT|Compressibility factor": "EOS selection critical near critical point; lab validation preferred.",
    "Acidizing & Stimulation|Maximum allowable surface pressure": "Respect frac gradient and completion pressure ratings.",
}

DEFAULT_NOTE = "Screening calculation only; confirm with operator procedures, OEM limits, and calibrated software."

# Engine definitions: type -> {inputs, compute_js, formula, assumptions}
ENGINES = {}

def key(seg, name):
    return f"{seg}|{name}"

def reg(k, **kw):
    ENGINES[k] = kw

# Register explicit engines for all calculable formulas
reg(key("Drilling","Hydrostatic pressure"),
    inputs=[("mw","Mud weight","density"),("tvd","TVD","length")],
    formula="P = 0.052 × MW × TVD",
    assumptions=["Static column","Single fluid"],
    compute="return 0.052 * v.mw * v.tvd",
    out=("pressure","Pressure"))

reg(key("Drilling","Pressure gradient"),
    inputs=[("p","Pressure","pressure"),("d","Depth/TVD","length")],
    formula="Gradient = P / TVD", assumptions=["Linear gradient"],
    compute="return v.p / v.d", out=("gradient","Gradient"))

reg(key("Drilling","Equivalent mud weight"),
    inputs=[("p","Pressure","pressure"),("tvd","TVD","length")],
    formula="EMW = P / (0.052 × TVD)", assumptions=["Static"],
    compute="return v.p / (0.052 * v.tvd)", out=("density","EMW"))

reg(key("Drilling","Annular capacity"),
    inputs=[("dh","Hole ID","diameter"),("dp","Pipe OD","diameter")],
    formula="Cap = (Dh² − Dp²) / 1029.4 bbl/ft", assumptions=["Circular annulus"],
    compute="return (v.dh**2 - v.dp**2) / 1029.4", out=("vol_per_length","Capacity"))

reg(key("Drilling","Pipe capacity"),
    inputs=[("id","Pipe ID","diameter")],
    formula="Cap = ID² / 1029.4 bbl/ft", assumptions=["Circular pipe"],
    compute="return v.id**2 / 1029.4", out=("vol_per_length","Capacity"))

reg(key("Drilling","Displacement"),
    inputs=[("od","Pipe OD","diameter")],
    formula="Disp = OD² / 1029.4 bbl/ft", assumptions=["Circular pipe"],
    compute="return v.od**2 / 1029.4", out=("vol_per_length","Displacement"))

reg(key("Drilling","Volume"),
    inputs=[("cap","Capacity","vol_per_length"),("len","Length","length")],
    formula="V = capacity × length", assumptions=["Constant ID"],
    compute="return v.cap * v.len", out=("volume","Volume"))

reg(key("Drilling","Pump output"),
    inputs=[("liner","Liner ID","diameter"),("stroke","Stroke","length")],
    formula="bbl/stk = liner² × stroke / 1029.4", assumptions=["Single acting pump"],
    compute="return (v.liner**2 * v.stroke) / 1029.4", out=("pump_output","Pump output"))

reg(key("Drilling","SPM for target rate"),
    inputs=[("q","Target rate","rate_liquid"),("po","Pump output","pump_output")],
    formula="SPM = Q / pump output", assumptions=["Constant pump efficiency"],
    compute="return v.q / v.po", out=("spm","SPM"))

reg(key("Drilling","Annular velocity"),
    inputs=[("q","Flow rate","rate_gpm"),("dh","Hole ID","diameter"),("dp","Pipe OD","diameter")],
    formula="AV = 24.51 × Q / (Dh² − Dp²) ft/min", assumptions=["Laminar/turbulent not distinguished"],
    compute="return 24.51 * v.q / (v.dh**2 - v.dp**2)", out=("velocity","Annular velocity"))

reg(key("Drilling","Jet velocity"),
    inputs=[("q","Flow rate","rate_gpm"),("area","Nozzle area","area_in2")],
    formula="V = 0.3208 × Q / nozzle area", assumptions=["Incompressible flow"],
    compute="return 0.3208 * v.q / v.area", out=("velocity_fps","Jet velocity"))

reg(key("Drilling","Bit hydraulic horsepower"),
    inputs=[("q","Flow rate","rate_gpm"),("dp","Bit ΔP","pressure")],
    formula="HHP = Q × ΔP / 1714", assumptions=["Steady flow"],
    compute="return v.q * v.dp / 1714", out=("power_hp","HHP"))

reg(key("Drilling","Bit impact force"),
    inputs=[("q","Flow rate","rate_gpm"),("mw","Mud weight","density"),("dp","Bit ΔP","pressure")],
    formula="IF = 0.01823 × Q × √(MW × ΔP)", assumptions=["Field correlation"],
    compute="return 0.01823 * v.q * Math.sqrt(v.mw * v.dp)", out=("force","Impact force"))

reg(key("Drilling","ROP"),
    inputs=[("ft","Footage","length"),("t","Time","time_hr")],
    formula="ROP = footage / time", assumptions=["Constant conditions"],
    compute="return v.ft / v.t", out=("rop","ROP"))

reg(key("Drilling","Ton-mile"),
    inputs=[("load","Hook load","force"),("dist","Travel distance","length")],
    formula="Ton-mile = load × distance / 5280", assumptions=["Vertical component approximation"],
    compute="return v.load * v.dist / 5280", out=("ton_mile","Ton-mile"))

reg(key("Drilling","Buoyancy factor"),
    inputs=[("mw","Mud weight","density")],
    formula="BF = 1 − MW/65.5", assumptions=["Steel in mud"],
    compute="return 1 - v.mw / 65.5", out=("dimensionless","Buoyancy factor"))

reg(key("Drilling","Maximum overpull / stretch"),
    inputs=[("f","Force","force"),("l","Length","length"),("a","Cross-section area","area_in2"),("e","Young's modulus","modulus")],
    formula="ΔL = F × L / (A × E)", assumptions=["Elastic deformation"],
    compute="return v.f * v.l / (v.a * v.e)", out=("length","Stretch"))

reg(key("Drilling","ECD"),
    inputs=[("mw","Mud weight","density"),("loss","Annular pressure loss","pressure"),("tvd","TVD","length")],
    formula="ECD = MW + annular loss / (0.052 × TVD)", assumptions=["Vertical well"],
    compute="return v.mw + v.loss / (0.052 * v.tvd)", out=("density","ECD"))

reg(key("Drilling","Lag strokes / lag time"),
    inputs=[("av","Annular volume","volume"),("po","Pump output","pump_output")],
    formula="Lag = annular volume / pump output", assumptions=["Full circulation"],
    compute="return v.av / v.po", out=("strokes","Lag strokes"))

reg(key("Well Control","Kill mud weight"),
    inputs=[("omw","Original MW","density"),("sidpp","SIDPP","pressure"),("tvd","TVD","length")],
    formula="KMW = OMW + SIDPP / (0.052 × TVD)", assumptions=["Static kill basis"],
    compute="return v.omw + v.sidpp / (0.052 * v.tvd)", out=("density","Kill MW"))

reg(key("Well Control","Formation pressure"),
    inputs=[("mw","Mud weight","density"),("tvd","TVD","length"),("sidpp","SIDPP","pressure")],
    formula="Pf = 0.052 × MW × TVD + SIDPP", assumptions=["Static"],
    compute="return 0.052 * v.mw * v.tvd + v.sidpp", out=("pressure","Formation pressure"))

reg(key("Well Control","ICP"),
    inputs=[("scr","SCR pressure","pressure"),("sidpp","SIDPP","pressure")],
    formula="ICP = SCR + SIDPP", assumptions=["Driller's method start"],
    compute="return v.scr + v.sidpp", out=("pressure","ICP"))

reg(key("Well Control","FCP"),
    inputs=[("scr","SCR pressure","pressure"),("kmw","Kill MW","density"),("omw","Original MW","density")],
    formula="FCP = SCR × KMW/OMW", assumptions=["Constant pump rate"],
    compute="return v.scr * v.kmw / v.omw", out=("pressure","FCP"))

reg(key("Well Control","Gas influx height"),
    inputs=[("vol","Influx volume","volume"),("cap","Annular capacity","vol_per_length")],
    formula="h = influx volume / annular capacity", assumptions=["Gas at top of annulus"],
    compute="return v.vol / v.cap", out=("length","Influx height"))

reg(key("Well Control","Trip margin"),
    inputs=[("margin","Additional MW margin","density")],
    formula="TM = additional hydrostatic margin", assumptions=["Operator-defined"],
    compute="return v.margin", out=("density","Trip margin"))

reg(key("Well Control","Bullheading pressure"),
    inputs=[("bhp","Target BHP","pressure"),("hyd","Hydrostatic","pressure")],
    formula="Psurf = target BHP − hydrostatic", assumptions=["Static fluid column"],
    compute="return v.bhp - v.hyd", out=("pressure","Surface pressure"))

reg(key("Completion","Tubing capacity"),
    inputs=[("id","Tubing ID","diameter")],
    formula="Cap = ID² / 1029.4", assumptions=["Circular tubing"],
    compute="return v.id**2 / 1029.4", out=("vol_per_length","Capacity"))

reg(key("Completion","Annulus capacity"),
    inputs=[("cid","Casing ID","diameter"),("tod","Tubing OD","diameter")],
    formula="Cap = (casing ID² − tubing OD²)/1029.4", assumptions=["Concentric"],
    compute="return (v.cid**2 - v.tod**2) / 1029.4", out=("vol_per_length","Capacity"))

reg(key("Completion","Packer fluid hydrostatic"),
    inputs=[("mw","Fluid density","density"),("tvd","TVD","length")],
    formula="P = 0.052 × MW × TVD", assumptions=["Static"],
    compute="return 0.052 * v.mw * v.tvd", out=("pressure","Hydrostatic"))

reg(key("Completion","Tubing stretch"),
    inputs=[("f","Load","force"),("l","Length","length"),("a","Area","area_in2"),("e","E","modulus")],
    formula="ΔL = F × L / (A × E)", assumptions=["Elastic"],
    compute="return v.f * v.l / (v.a * v.e)", out=("length","Stretch"))

reg(key("Completion","Thermal expansion"),
    inputs=[("alpha","Coefficient α","thermal_exp"),("l","Length","length"),("dt","ΔT","temperature_delta")],
    formula="ΔL = α × L × ΔT", assumptions=["Linear expansion"],
    compute="return v.alpha * v.l * v.dt", out=("length","Expansion"))

reg(key("Completion","Tubing movement due to piston effect"),
    inputs=[("dp","ΔP","pressure"),("area","Effective area","area_in2")],
    formula="F = ΔP × effective area", assumptions=["Sealed annulus"],
    compute="return v.dp * v.area", out=("force","Force"))

reg(key("Completion","Burst / collapse / tension check"),
    inputs=[("rating","Rating","pressure"),("load","Applied load","pressure")],
    formula="SF = rating / applied load", assumptions=["SF > 1 required"],
    compute="return v.rating / v.load", out=("dimensionless","Safety factor"))

reg(key("Completion","Perforation friction estimate"),
    inputs=[("c","C coefficient","dimensionless"),("q","Rate","rate_liquid"),("spf","Shot density","spf"),("d","Perf diameter","diameter")],
    formula="ΔPpf ≈ C × q² / perf_density²", assumptions=["Empirical"],
    compute="return v.c * v.q**2 / (v.spf**2)", out=("pressure","Perf friction"))

reg(key("Cementing","Sacks required"),
    inputs=[("vol","Required slurry volume","volume"),("yield","Yield","yield_vol")],
    formula="sx = volume / yield", assumptions=["Known yield"],
    compute="return v.vol / v.yield", out=("sacks","Sacks"))

reg(key("Cementing","Annular cement volume"),
    inputs=[("cap","Annular capacity","vol_per_length"),("intv","Interval","length"),("ex","Excess fraction","dimensionless")],
    formula="V = cap × interval × (1+excess)", assumptions=["Circular annulus"],
    compute="return v.cap * v.intv * (1 + v.ex)", out=("volume","Volume"))

reg(key("Cementing","Displacement volume"),
    inputs=[("cap","Pipe capacity","vol_per_length"),("len","Length","length")],
    formula="V = capacity × length", assumptions=["Full string fill"],
    compute="return v.cap * v.len", out=("volume","Volume"))

reg(key("Cementing","Mix water"),
    inputs=[("sx","Sacks","sacks"),("wps","Water per sack","vol_per_sack")],
    formula="Water = sacks × gal/sk", assumptions=["Field mix sheet"],
    compute="return v.sx * v.wps", out=("volume_gal","Mix water"))

reg(key("Cementing","TOC after pumping"),
    inputs=[("vol","Slurry volume","volume"),("cap","Annular capacity","vol_per_length")],
    formula="TOC = slurry volume / annular capacity", assumptions=["No losses"],
    compute="return v.vol / v.cap", out=("length","TOC length"))

reg(key("Cementing","Equivalent circulating density during cementing"),
    inputs=[("mw","Density","density"),("loss","Friction","pressure"),("tvd","TVD","length")],
    formula="ECD = MW + loss/(0.052×TVD)", assumptions=["Vertical"],
    compute="return v.mw + v.loss / (0.052 * v.tvd)", out=("density","ECD"))

reg(key("Cementing","Bump pressure differential"),
    inputs=[("fp","Final pressure","pressure"),("cp","Circulating pressure","pressure")],
    formula="ΔP = final − circulating", assumptions=["At bump"],
    compute="return v.fp - v.cp", out=("pressure","ΔP"))

reg(key("Coiled Tubing","CT internal capacity"),
    inputs=[("id","CT ID","diameter")],
    formula="Cap = ID² / 1029.4", assumptions=["Circular"],
    compute="return v.id**2 / 1029.4", out=("vol_per_length","Capacity"))

reg(key("Coiled Tubing","CT displacement"),
    inputs=[("od","CT OD","diameter")],
    formula="Disp = OD² / 1029.4", assumptions=["Circular"],
    compute="return v.od**2 / 1029.4", out=("vol_per_length","Displacement"))

reg(key("Coiled Tubing","Pump time to bottom"),
    inputs=[("vol","CT volume","volume"),("rate","Pump rate","rate_liquid")],
    formula="t = volume / rate", assumptions=["Constant rate"],
    compute="return v.vol / v.rate", out=("time_hr","Pump time"))

reg(key("Wireline Perforation","Shot density"),
    inputs=[("shots","Shots","count"),("len","Interval length","length")],
    formula="SPF = shots / ft", assumptions=["Even distribution"],
    compute="return v.shots / v.len", out=("spf","SPF"))

reg(key("Wireline Perforation","Perforated interval height"),
    inputs=[("top","Top depth","length"),("bot","Bottom depth","length")],
    formula="h = bottom − top", assumptions=["Measured depth"],
    compute="return v.bot - v.top", out=("length","Height"))

reg(key("Wireline Perforation","Underbalance / overbalance"),
    inputs=[("pres","Reservoir pressure","pressure"),("pwb","Wellbore pressure","pressure")],
    formula="ΔP = Pres − Pwb", assumptions=["Static"],
    compute="return v.pres - v.pwb", out=("pressure","ΔP"))

reg(key("Wireline Perforation","Gun clearance"),
    inputs=[("cid","Conduit ID","diameter"),("god","Gun OD","diameter")],
    formula="Clearance = conduit ID − gun OD", assumptions=["Concentric"],
    compute="return v.cid - v.god", out=("length_in","Clearance"))

reg(key("Wireline Open Hole","Porosity from density"),
    inputs=[("rhoma","Matrix density","density_gcc"),("rhob","Bulk density","density_gcc"),("rhof","Fluid density","density_gcc")],
    formula="φd = (ρma − ρb)/(ρma − ρf)", assumptions=["Known matrix/fluid"],
    compute="return (v.rhoma - v.rhob) / (v.rhoma - v.rhof)", out=("fraction","Porosity"))

reg(key("Wireline Open Hole","Water saturation (Archie)"),
    inputs=[("a","a","dimensionless"),("rw","Rw","resistivity"),("phi","Porosity","fraction"),("m","m","dimensionless"),("rt","Rt","resistivity"),("n","n","dimensionless")],
    formula="Sw = (a×Rw/(φ^m×Rt))^(1/n)", assumptions=["Clean formation Archie"],
    compute="return Math.pow(v.a * v.rw / (Math.pow(v.phi, v.m) * v.rt), 1/v.n)", out=("fraction","Sw"))

reg(key("Production","Oil PI"),
    inputs=[("q","Rate","rate_liquid"),("pr","Pr","pressure"),("pwf","Pwf","pressure")],
    formula="PI = q / (Pr − Pwf)", assumptions=["Steady state, single phase oil"],
    compute="return v.q / (v.pr - v.pwf)", out=("pi","PI"))

reg(key("Production","Gas deliverability"),
    inputs=[("c","C","deliverability_c"),("pr","Pr","pressure"),("pwf","Pwf","pressure"),("n","n","dimensionless")],
    formula="q = C(Pr² − Pwf²)^n", assumptions=["Empirical deliverability"],
    compute="return v.c * Math.pow(v.pr**2 - v.pwf**2, v.n)", out=("rate_gas","Gas rate"))

reg(key("Production","GOR"),
    inputs=[("qg","Gas rate","rate_gas"),("qo","Oil rate","rate_liquid")],
    formula="GOR = Qg / Qo", assumptions=["Separator conditions"],
    compute="return v.qg / v.qo", out=("gor","GOR"))

reg(key("Production","Water cut"),
    inputs=[("qw","Water rate","rate_liquid"),("ql","Total liquid rate","rate_liquid")],
    formula="WC = Qw / Ql × 100", assumptions=["Surface rates"],
    compute="return 100 * v.qw / v.ql", out=("percent","Water cut"))

reg(key("Production","BSW"),
    inputs=[("bsw","BS&W volume","volume"),("sample","Sample volume","volume")],
    formula="BSW = BS&W / sample × 100", assumptions=["Representative sample"],
    compute="return 100 * v.bsw / v.sample", out=("percent","BSW"))

reg(key("Production","Liquid rate from tank"),
    inputs=[("vol","Volume","volume"),("t","Time","time_hr")],
    formula="q = volume / time", assumptions=["Constant accumulation"],
    compute="return v.vol / v.t", out=("rate_liquid","Liquid rate"))

reg(key("Production","API gravity"),
    inputs=[("sg","Specific gravity @60°F","sg")],
    formula="API = 141.5/SG − 131.5", assumptions=["60°F reference"],
    compute="return 141.5 / v.sg - 131.5", out=("api","API gravity"))

reg(key("Production","Gas specific gravity"),
    inputs=[("mw","Gas MW","mw")],
    formula="γg = MW / 28.97", assumptions=["Ideal gas basis"],
    compute="return v.mw / 28.97", out=("sg","Gas SG"))

reg(key("Production","Flowing gradient"),
    inputs=[("dp","ΔP","pressure"),("dtvd","ΔTVD","length")],
    formula="Gradient = ΔP / ΔTVD", assumptions=["Single phase approximation"],
    compute="return v.dp / v.dtvd", out=("gradient","Gradient"))

reg(key("Production","Separator efficiency / retention"),
    inputs=[("vol","Vessel volume","volume"),("q","Flow rate","rate_liquid")],
    formula="t = volume / flow", assumptions=["Plug flow approximation"],
    compute="return v.vol / v.q", out=("time_hr","Retention time"))

reg(key("Production","Productivity decline"),
    inputs=[("qi","qi","rate_liquid"),("di","Di (1/day)","dimensionless"),("t","Time (days)","time_hr"),("b","b factor","dimensionless")],
    formula="Hyperbolic: q=qi/(1+bDi t)^(1/b); Exp: q=qi e^(−Di t)", assumptions=["Use plotter below for full curve"],
    compute="return v.b > 0 ? v.qi / Math.pow(1 + v.b * v.di * v.t, 1/v.b) : v.qi * Math.exp(-v.di * v.t)", out=("rate_liquid","Rate"))

reg(key("Completion","Nodal inflow/outflow match"),
    inputs=[("pr","Pr","pressure"),("pi","PI","pi"),("q","Rate","rate_liquid")],
    formula="Linear IPR: Pwf = Pr − q/PI", assumptions=["Use nodal plotter for Vogel + VLP"],
    compute="return v.pr - v.q / v.pi", out=("pressure","Pwf"))

reg(key("Well Testing & DST","Build-up Horner ratio"),
    inputs=[("tp","Flow time tp","time_hr"),("dt","Shut-in Δt","time_hr")],
    formula="H = (tp + Δt) / Δt", assumptions=["Constant rate prior to shut-in"],
    compute="return (v.tp + v.dt) / v.dt", out=("dimensionless","Horner ratio"))

reg(key("Well Testing & DST","Permeability from build-up"),
    inputs=[("q","Rate","rate_liquid"),("mu","Viscosity","viscosity"),("b","FVF","rb_stb"),("h","Net pay","length"),("m","Semilog slope","slope_psi")],
    formula="k = 162.6 qBμ / (m h)", assumptions=["Infinite-acting radial flow, oil units"],
    compute="return 162.6 * v.q * v.b * v.mu / (v.m * v.h)", out=("perm","Permeability"))

reg(key("Well Testing & DST","Radius of investigation"),
    inputs=[("k","Permeability","perm"),("t","Time","time_hr"),("phi","Porosity","fraction"),("mu","Viscosity","viscosity"),("ct","Total compressibility","compressibility")],
    formula="ri ≈ √(0.000264 k t / (φ μ ct))", assumptions=["Homogeneous reservoir"],
    compute="return Math.sqrt(0.000264 * v.k * v.t / (v.phi * v.mu * v.ct))", out=("length","ri"))

reg(key("Well Testing & DST","PI from test"),
    inputs=[("q","Test rate","rate_liquid"),("pi","Pi","pressure"),("pwf","Pwf","pressure")],
    formula="PI = q / (Pi − Pwf)", assumptions=["Stabilized drawdown/buildup"],
    compute="return v.q / (v.pi - v.pwf)", out=("pi","PI"))

reg(key("Well Testing & DST","Skin"),
    inputs=[("pstar","P*","pressure"),("pi","Pi","pressure"),("m","Slope m","slope_psi"),("k","k","perm"),("phi","Porosity","fraction"),("mu","Viscosity","viscosity"),("ct","ct","compressibility"),("rw","rw","length")],
    formula="s = 1.151[(P*−Pi)/m − log(k/(φμct rw²)) + 3.23]", assumptions=["Oilfield Horner analysis units"],
    compute="return 1.151 * ((v.pstar - v.pi) / v.m - Math.log10(v.k / (v.phi * v.mu * v.ct * v.rw**2)) + 3.23)", out=("dimensionless","Skin"))

reg(key("Well Testing & DST","Wellbore storage coefficient"),
    inputs=[("q","Rate","rate_liquid"),("dt","Early Δt","time_hr"),("dp","Early ΔP","pressure")],
    formula="C ≈ q·Δt / (24·ΔP)", assumptions=["Unit-converted oilfield approximation"],
    compute="return (v.q * v.dt) / (24 * v.dp)", out=("dimensionless","C"))

reg(key("Well Testing & DST","DST hydrostatic gauge check"),
    inputs=[("grad","Fluid gradient","gradient"),("spacing","Gauge spacing","length")],
    formula="ΔP = gradient × spacing", assumptions=["Static fluid"],
    compute="return v.grad * v.spacing", out=("pressure","ΔP"))

reg(key("Surface Well Testing","Separator retention time"),
    inputs=[("vol","Liquid volume","volume"),("q","Liquid rate","rate_liquid")],
    formula="t = volume / rate", assumptions=["Constant rate"],
    compute="return v.vol / v.q", out=("time_hr","Retention"))

reg(key("Surface Well Testing","Choke flow estimate gas"),
    inputs=[("d","Choke ID","diameter"),("p1","Upstream P","pressure"),("p2","Downstream P","pressure"),("t","Temp R","temp_R"),("gamma","Gas gravity","sg")],
    formula="q ≈ 879 d² P1 / √(γ T) when P2/P1 ≤ 0.55", assumptions=["Gilbert-type critical flow"],
    compute="return (v.p2/v.p1 <= 0.55) ? 879*(v.d**2)*v.p1/Math.sqrt(v.gamma*v.t) : NaN", out=("rate_gas","Critical rate"))

reg(key("Surface Well Testing","Flare line velocity"),
    inputs=[("q","Gas rate","rate_gas"),("id","Line ID","diameter")],
    formula="v = Q / area", assumptions=["Ideal gas approx at conditions"],
    compute="const area=Math.PI*(v.id/24)**2; return v.q / area", out=("velocity_fps","Velocity"))

reg(key("Surface Well Testing","Erosion velocity"),
    inputs=[("c","C factor","dimensionless"),("rho","Density","density_lbft3")],
    formula="ve = C / √ρ", assumptions=["API RP 14E basis"],
    compute="return v.c / Math.sqrt(v.rho)", out=("velocity_fps","Erosion velocity"))

reg(key("Surface Well Testing","Transfer pump time"),
    inputs=[("vol","Tank volume","volume"),("rate","Pump rate","rate_liquid")],
    formula="t = volume / rate", assumptions=["Constant rate"],
    compute="return v.vol / v.rate", out=("time_hr","Time"))

reg(key("Sampling & PVT","Sample line purge volume"),
    inputs=[("id","Line ID","diameter"),("len","Length","length"),("factor","Purge factor","dimensionless")],
    formula="V = line cap × purge factor", assumptions=["Circular line"],
    compute="return (v.id**2/1029.4)*v.len*v.factor", out=("volume","Purge volume"))

reg(key("Sampling & PVT","Oil formation volume factor"),
    inputs=[("res","Reservoir oil vol","volume"),("st","Stock tank vol","volume")],
    formula="Bo = res vol / ST vol", assumptions=["Lab measurement"],
    compute="return v.res / v.st", out=("rb_stb","Bo"))

reg(key("Sampling & PVT","Gas formation volume factor"),
    inputs=[("p","Pressure","pressure"),("t","Temperature","temp_R"),("z","Z-factor","dimensionless")],
    formula="Bg ≈ 0.02827 z T / P (rcf/scf)", assumptions=["Ideal gas with z correction"],
    compute="return 0.02827 * v.z * v.t / v.p", out=("rcf_scf","Bg"))

reg(key("Acidizing & Stimulation","Acid volume by interval"),
    inputs=[("gpf","Gal/ft","vol_per_length_gal"),("intv","Interval","length")],
    formula="V = gal/ft × interval", assumptions=["Design basis"],
    compute="return v.gpf * v.intv", out=("volume_gal","Volume"))

reg(key("Acidizing & Stimulation","Pump time"),
    inputs=[("vol","Volume","volume_gal"),("rate","Rate","rate_gpm")],
    formula="t = volume / rate", assumptions=["Constant rate"],
    compute="return v.vol / v.rate", out=("time_hr","Pump time"))

reg(key("Acidizing & Stimulation","Bottomhole treating pressure"),
    inputs=[("whp","WHP","pressure"),("hyd","Hydrostatic","pressure"),("fric","Friction","pressure"),("pf","Perf friction","pressure")],
    formula="BHTP = WHP + hydrostatic + friction + perf friction", assumptions=["Injection"],
    compute="return v.whp + v.hyd + v.fric + v.pf", out=("pressure","BHTP"))

reg(key("Acidizing & Stimulation","Maximum allowable surface pressure"),
    inputs=[("frac","Frac limit","pressure"),("hyd","Hydrostatic","pressure"),("fric","Friction","pressure")],
    formula="MASP = frac limit − hydrostatic − friction", assumptions=["No breakdown desired"],
    compute="return v.frac - v.hyd - v.fric", out=("pressure","MASP"))

reg(key("Acidizing & Stimulation","Injectivity index"),
    inputs=[("q","Injection rate","rate_liquid"),("pinj","Pinj","pressure"),("pres","Pres","pressure")],
    formula="II = q / (Pinj − Pres)", assumptions=["Steady injection"],
    compute="return v.q / (v.pinj - v.pres)", out=("ii","II"))

reg(key("Acidizing & Stimulation","Diverter concentration"),
    inputs=[("mass","Diverter mass","mass"),("vol","Carrier volume","volume_gal")],
    formula="Conc = mass / volume", assumptions=["Uniform slurry"],
    compute="return v.mass / v.vol", out=("conc","Concentration"))

# Generic fallback for remaining entries
def generic_engine(seg, name, formula, inputs_list):
    ins = []
    for i, lbl in enumerate(inputs_list):
        ins.append((f"x{i+1}", lbl, "dimensionless"))
    return {
        "inputs": ins,
        "formula": formula,
        "assumptions": ["Manual/interpretive calculation — enter parameters per field procedure"],
        "compute": "return Object.values(v).reduce((a,b)=>a+b,0)/Object.keys(v).length",
        "out": ("dimensionless","Result (avg of inputs — replace with job-specific method)"),
        "generic": True,
    }

calc_registry = {}
for seg, rows in calc_data.items():
    for name, formula, inputs_list in rows:
        k = key(seg, name)
        if k in ENGINES:
            calc_registry[k] = ENGINES[k]
        else:
            calc_registry[k] = generic_engine(seg, name, formula, inputs_list)
        calc_registry[k]["notes"] = NOTES.get(k, DEFAULT_NOTE)
        calc_registry[k]["segment"] = seg
        calc_registry[k]["name"] = name

print(f"Registry: {len(calc_registry)} entries, explicit: {sum(1 for v in calc_registry.values() if not v.get('generic'))}")

# Write registry JSON for embedding
registry_json = json.dumps(calc_registry, separators=(',', ':'))
calc_data_json = json.dumps(calc_data, separators=(',', ':'))

with open('/workspace/_upstream_styles.css') as f:
    css = f.read()
with open('/workspace/_upstream_app.js') as f:
    app_js = f.read()

html_parts = []
html_parts.append('''<!doctype html>
<html lang="en" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Upstream Calculations App</title>
<meta name="description" content="Offshore upstream oil & gas engineering calculator — DST, CT, wireline, stimulation">
<meta name="theme-color" content="#01696f">
<link rel="manifest" id="appManifest" href="">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
''')
html_parts.append(css)
html_parts.append('''</style>
</head>
<body>
<div class="overlay" id="overlay"></div>
<div class="app-shell">
  <aside class="sidebar" id="sidebar">
    <div class="brand"><div class="logo">UC</div><div><div><strong>Upstream Calculations</strong></div><div class="tiny">Interactive field calculator</div></div></div>
    <input id="search" class="search" placeholder="Search segment, formula, keyword" aria-label="Search calculations">
    <div class="nav" id="nav"></div>
  </aside>
  <main class="main">
    <div class="topbar no-print">
      <button class="btn icon hamburger" id="menuBtn" aria-label="Open navigation menu">☰</button>
      <div class="controls">
        <label class="tiny">Unit system</label>
        <select id="unitSystemSel" class="btn" aria-label="Preferred unit system">
          <option value="field">Field</option><option value="si">SI</option><option value="metric">Metric</option>
        </select>
        <button class="btn" id="themeBtn" aria-label="Cycle theme">Theme</button>
        <button class="btn" id="histBtn" aria-label="Open session log">Session log</button>
        <button class="btn" id="exportCsvBtn" aria-label="Export session log CSV">Export CSV</button>
        <button class="btn primary" id="reportBtn" aria-label="Generate printable report">Generate Report</button>
      </div>
    </div>
    <details class="well-panel no-print" open>
      <summary>Well Context</summary>
      <div class="well-grid" style="margin-top:var(--space-3)">
        <div class="field"><label for="wellName">Well Name</label><input id="wellName" aria-label="Well name"></div>
        <div class="field"><label for="field">Field</label><input id="field" aria-label="Field name"></div>
        <div class="field"><label for="operator">Operator</label><input id="operator" aria-label="Operator"></div>
        <div class="field"><label for="testDate">Test Date</label><input id="testDate" type="date" aria-label="Test date"></div>
        <div class="field"><label for="reservoir">Reservoir</label><input id="reservoir" aria-label="Reservoir"></div>
        <div class="field"><label for="engineer">Engineer Name</label><input id="engineer" aria-label="Engineer name"></div>
      </div>
    </details>
    <div class="hero no-print">
      <span class="pill">Upstream oil &amp; gas — Abu Dhabi offshore ready</span>
      <h1>Interactive calculator for drilling, completions, production, well testing, DST, wireline, CT, cementing, stimulation, and unit conversion.</h1>
      <p class="muted">Field screening tool — not a substitute for operator procedures, OEM manuals, or formal simulation. Works offline after first load.</p>
      <div class="stats">
        <div class="stat"><div class="tiny">Segments</div><div id="segCount" style="font-size:var(--text-xl);font-weight:700"></div></div>
        <div class="stat"><div class="tiny">Calculations</div><div id="calcCount" style="font-size:var(--text-xl);font-weight:700"></div></div>
        <div class="stat"><div class="tiny">Tools</div><div style="font-size:var(--text-xl);font-weight:700">Charts + nodal + Horner</div></div>
        <div class="stat"><div class="tiny">Priority</div><div style="font-size:var(--text-xl);font-weight:700">Safety first</div></div>
      </div>
    </div>
    <section class="grid no-print">
      <div class="card" style="grid-column:span 12"><h2>Quick tools</h2><p class="muted">Unit converter plus 15 high-use field formulas including ri, skin, C, Gilbert choke, ECD, Bg, API, WC, and GOR.</p></div>
      <div class="card" style="grid-column:span 7"><h3>Unit converter</h3>
        <div class="converter">
          <div class="field"><label for="family">Family</label><select id="family" aria-label="Conversion family"></select></div>
          <div class="field"><label for="fromUnit">From</label><select id="fromUnit" aria-label="From unit"></select></div>
          <div class="field"><label for="toUnit">To</label><select id="toUnit" aria-label="To unit"></select></div>
          <div class="field"><label for="fromValue">Value</label><input id="fromValue" type="number" step="any" value="1" aria-label="Value to convert"></div>
        </div>
        <div class="footer-note"><strong>Result:</strong> <span id="convResult">—</span></div>
      </div>
      <div class="card" style="grid-column:span 5"><h3>Quick calculator</h3>
        <div class="field" style="margin-bottom:var(--space-3)"><label for="quickCalc">Formula</label><select id="quickCalc" aria-label="Quick formula"></select></div>
        <div id="quickFields" class="mini-calc"></div>
        <div class="controls" style="margin-top:var(--space-3)">
          <button class="btn primary" id="runCalc" aria-label="Run quick calculation">Calculate</button>
          <button class="btn" id="resetCalc" aria-label="Reset quick calculator">Reset</button>
        </div>
        <div class="footer-note"><strong>Output:</strong> <span id="calcResult">—</span></div>
      </div>
    </section>
    <section class="no-print">
      <div class="section-title"><div><h2 style="margin:0">Calculation library</h2><div class="muted">Expand any row for live calculator, formula derivation, and charts.</div></div></div>
      <div id="library"></div>
    </section>
    <div class="footer-note no-print">Engineering note: upstream calculations are scenario-dependent. Confirm fluid PVT, geometry, trajectory, tool ratings, and real-time pressures before operational decisions.</div>
    <div id="reportPreview" class="report-preview"></div>
  </main>
  <aside class="history-panel" id="historyPanel">
    <h3 style="margin-top:0">Session log</h3>
    <p class="tiny muted">Last 20 calculations with well context.</p>
    <div id="historyList"></div>
  </aside>
</div>
<script>
const calcData = ''')
html_parts.append(calc_data_json)
html_parts.append(';\nconst calcRegistry = ')
html_parts.append(registry_json)
html_parts.append(';\n')
html_parts.append(app_js)
html_parts.append('\ninitUpstreamApp(calcData, calcRegistry);\n</script>\n</body>\n</html>')

out_html = ''.join(html_parts)
with open(OUT, 'w') as f:
    f.write(out_html)

print(f"Wrote {OUT} ({len(out_html)} bytes)")