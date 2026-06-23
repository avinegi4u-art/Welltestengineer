"""Horner analysis, flow regime detection, and parameter estimation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats

from .data_loader import PressureSeries, ReservoirProperties
from .derivative import DerivativeResult, compute_derivative
from .models import ModelType, TypeCurveParams, auto_fit_derivative
from .superposition import SuperpositionResult, apply_superposition_to_buildup


@dataclass
class HornerResult:
    permeability_md: float
    skin: float
    p_star_psi: float
    slope_psi_per_cycle: float
    intercept_psi: float
    r2: float
    fit_start_hr: float
    fit_end_hr: float
    n_points: int
    confidence: str
    notes: str


@dataclass
class FlowRegime:
    name: str
    start_hr: float
    end_hr: float
    confidence: str
    hint: str


@dataclass
class BuildupInterpretation:
    horner: HornerResult | None
    derivative: DerivativeResult
    superposition: SuperpositionResult
    regimes: list[FlowRegime]
    typecurve_k_md: float | None
    typecurve_skin: float | None
    wellbore_storage_coeff: float | None
    overall_confidence: str
    hints: list[str]


def horner_permeability(slope_psi_per_log_cycle: float, q_bpd: float, b_rb: float, mu_cp: float, h_ft: float) -> float:
    """k = 162.6 q μ B / (|m| h) — m in psi/cycle on Horner semi-log plot."""
    m = abs(slope_psi_per_log_cycle)
    if m < 1e-9:
        return float("nan")
    return 162.6 * q_bpd * mu_cp * b_rb / (m * h_ft)


def horner_skin(
    p1hr: float,
    pwf: float,
    m: float,
    k_md: float,
    phi: float,
    mu: float,
    ct: float,
    rw: float,
) -> float:
    if not np.isfinite(k_md) or k_md <= 0 or abs(m) < 1e-9:
        return float("nan")
    term = np.log10(k_md / (phi * mu * ct * rw ** 2))
    return 1.151 * ((p1hr - pwf) / m - term + 3.23)


def fit_horner(
    superposition: SuperpositionResult,
    props: ReservoirProperties,
    fit_start_hr: float | None = None,
    fit_end_hr: float | None = None,
) -> HornerResult:
    """Linear fit Δp vs log10((tp+Δt)/Δt)."""
    dt = superposition.dt_hr
    dp = superposition.delta_p_psi
    horner = superposition.horner_ratio
    log_h = np.log10(np.maximum(horner, 1.0001))

    t0 = fit_start_hr if fit_start_hr is not None else np.percentile(dt, 15)
    t1 = fit_end_hr if fit_end_hr is not None else np.percentile(dt, 75)
    mask = (dt >= t0) & (dt <= t1) & np.isfinite(dp)
    if np.sum(mask) < 3:
        mask = np.ones_like(dt, dtype=bool)

    x = log_h[mask]
    y = dp[mask]
    slope, intercept, r, _, _ = stats.linregress(x, y)
    k = horner_permeability(slope, superposition.q_ref_bpd, props.b, props.mu, props.h)
    p1hr = intercept + slope * 0.0  # at log10(H)=0 → H=1 → Δt large
    p_star = intercept  # extrapolated to infinite Horner time
    skin = horner_skin(p1hr, props.pwf, slope, k, props.phi, props.mu, props.ct, props.rw)

    r2 = r ** 2
    if r2 >= 0.97 and np.sum(mask) >= 6:
        conf = "high"
    elif r2 >= 0.92:
        conf = "medium"
    else:
        conf = "low"

    return HornerResult(
        permeability_md=float(k),
        skin=float(skin),
        p_star_psi=float(p_star),
        slope_psi_per_cycle=float(slope),
        intercept_psi=float(intercept),
        r2=float(r2),
        fit_start_hr=float(t0),
        fit_end_hr=float(t1),
        n_points=int(np.sum(mask)),
        confidence=conf,
        notes=f"Horner fit on {np.sum(mask)} points, R²={r2:.3f}. k from Darcy slope m={slope:.2f} psi/cycle.",
    )


def detect_flow_regimes(deriv: DerivativeResult) -> list[FlowRegime]:
    """Identify storage, radial, boundary from derivative slope in log-log space."""
    dt = deriv.dt_hr
    d = deriv.derivative_psi_per_hr
    mask = np.isfinite(d) & (d > 0)
    if np.sum(mask) < 5:
        return []

    log_t = np.log10(dt[mask])
    log_d = np.log10(d[mask])
    t_vis = dt[mask]
    regimes: list[FlowRegime] = []

    # Sliding window slope
    window = max(3, len(log_t) // 8)
    slopes = []
    centers = []
    for i in range(0, len(log_t) - window, max(1, window // 2)):
        sl, _, r, _, _ = stats.linregress(log_t[i : i + window], log_d[i : i + window])
        slopes.append(sl)
        centers.append(t_vis[i + window // 2])

    slopes = np.array(slopes)
    centers = np.array(centers)

    # Storage: slope ~ +1
    storage_idx = np.where(slopes > 0.65)[0]
    if len(storage_idx):
        i0, i1 = storage_idx[0], storage_idx[-1]
        regimes.append(
            FlowRegime(
                "wellbore storage",
                float(centers[i0]),
                float(centers[i1]),
                "medium",
                f"Early-time unit slope behavior (~+1) between {centers[i0]:.3f}–{centers[i1]:.3f} hr.",
            )
        )

    # Radial: slope ~ 0
    radial_idx = np.where(np.abs(slopes) < 0.25)[0]
    if len(radial_idx):
        i0, i1 = radial_idx[0], radial_idx[-1]
        regimes.append(
            FlowRegime(
                "radial flow",
                float(centers[i0]),
                float(centers[i1]),
                "high" if len(radial_idx) >= 2 else "medium",
                f"Radial flow detected between {centers[i0]:.3f}–{centers[i1]:.3f} hr (derivative plateau).",
            )
        )

    # Boundary: late positive slope or uplift
    if len(slopes) >= 3:
        late = slopes[-max(2, len(slopes) // 4) :]
        if np.mean(late) > 0.35:
            regimes.append(
                FlowRegime(
                    "boundary effect",
                    float(centers[-len(late)]),
                    float(centers[-1]),
                    "medium",
                    "Possible boundary effect at late time — derivative rises.",
                )
            )

    return regimes


def estimate_wellbore_storage(deriv: DerivativeResult, q_bpd: float, b: float) -> float | None:
    early = deriv.derivative_psi_per_hr[: max(3, len(deriv.dt_hr) // 5)]
    early = early[np.isfinite(early) & (early > 0)]
    if len(early) < 2:
        return None
    # C ≈ qB / (24 * (dΔp/d ln t)) screening
    slope_storage = np.median(early)
    return float(q_bpd * b / (24 * max(slope_storage, 1e-6)))


def interpret_buildup(
    buildup: PressureSeries,
    full_series: PressureSeries | None = None,
    bourdet_l: float = 0.15,
    fit_start: float | None = None,
    fit_end: float | None = None,
) -> BuildupInterpretation:
    """Full interpretation pipeline for one buildup."""
    props = buildup.properties
    if props.is_gas:
        from .gas import estimate_muz_from_pvt, pseudopressure, pseudotime

        muz = estimate_muz_from_pvt(buildup.pressure_psi, props.gamma_g, props.t_res_f)
        buildup = PressureSeries(
            time_hr=pseudotime(buildup.time_hr, muz, props.ct),
            pressure_psi=pseudopressure(buildup.pressure_psi, muz),
            rate_bpd=buildup.rate_bpd,
            source=buildup.source + " (gas m(p))",
            properties=props,
        )

    superpos = apply_superposition_to_buildup(buildup, full_series)
    deriv = compute_derivative(superpos.dt_hr, superpos.delta_p_psi, bourdet_l=bourdet_l)
    horner = fit_horner(superpos, props, fit_start, fit_end)
    regimes = detect_flow_regimes(deriv)
    hints = [r.hint for r in regimes]

    tc = auto_fit_derivative(superpos.dt_hr, deriv.derivative_psi_per_hr, props, ModelType.RADIAL, k0=horner.permeability_md, skin0=horner.skin)
    c = estimate_wellbore_storage(deriv, superpos.q_ref_bpd, props.b)

    confs = [horner.confidence]
    if regimes:
        confs.append("high" if any(r.name == "radial flow" and r.confidence == "high" for r in regimes) else "medium")
    overall = "high" if confs.count("high") >= 2 else "medium" if "low" not in confs else "low"

    return BuildupInterpretation(
        horner=horner,
        derivative=deriv,
        superposition=superpos,
        regimes=regimes,
        typecurve_k_md=tc.params.k_md,
        typecurve_skin=tc.params.skin,
        wellbore_storage_coeff=c,
        overall_confidence=overall,
        hints=hints,
    )


def interpret_dst_workflow(
    series: PressureSeries,
    bourdet_l: float = 0.15,
    min_buildup_hr: float = 0.5,
    min_buildup_points: int = 8,
) -> list[BuildupInterpretation]:
    """Analyze each detected buildup in a DST sequence."""
    from .data_loader import detect_cycles, split_buildups

    detect_cycles(series)
    buildups = [
        b
        for b in split_buildups(series)
        if b.time_hr[-1] >= min_buildup_hr and b.n >= min_buildup_points
    ]
    return [interpret_buildup(b, series, bourdet_l=bourdet_l) for b in buildups]
