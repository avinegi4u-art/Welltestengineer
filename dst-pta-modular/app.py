"""
DST PTA — Streamlit field interface with Plotly log-log diagnostics.

Run: streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from dst_pta.conditioning import condition_series
from dst_pta.data_loader import (
    ReservoirProperties,
    attach_properties,
    detect_cycles,
    load_dataframe,
    split_buildups,
)
from dst_pta.derivative import reference_slopes
from dst_pta.interpretation import interpret_buildup, interpret_dst_workflow
from dst_pta.models import ModelType, auto_fit_derivative, model_derivative, TypeCurveParams
from dst_pta.reporting import generate_report

st.set_page_config(page_title="DST PTA", layout="wide", page_icon="🛢️")
st.title("DST Pressure Transient Analysis")
st.caption("Fast, transparent PTA for DST sequences — superposition, Bourdet derivative, Horner, type curves.")

SAMPLE = ROOT / "sample_data" / "dst_demo.csv"


@st.cache_data
def load_csv_bytes(data: bytes):
    import io
    df = pd.read_csv(io.BytesIO(data))
    return load_dataframe(df)


def sidebar_properties() -> ReservoirProperties:
    st.sidebar.header("Reservoir & fluid")
    return ReservoirProperties(
        q=st.sidebar.number_input("q (bpd)", value=380.0, min_value=0.1),
        b=st.sidebar.number_input("B (rb/STB)", value=1.2, min_value=0.5),
        mu=st.sidebar.number_input("μ (cp)", value=1.15, min_value=0.01),
        h=st.sidebar.number_input("h (ft)", value=55.0, min_value=1.0),
        phi=st.sidebar.number_input("φ", value=0.18, min_value=0.01, max_value=0.45),
        ct=st.sidebar.number_input("ct (1/psi)", value=1.2e-5, format="%.2e"),
        rw=st.sidebar.number_input("rw (ft)", value=0.33, min_value=0.01),
        tp=st.sidebar.number_input("tp (hr)", value=4.0, min_value=0.01),
        pwf=st.sidebar.number_input("pwf (psi)", value=7780.0),
        is_gas=st.sidebar.checkbox("Gas well (m(p) / pseudotime)", value=False),
        gamma_g=st.sidebar.number_input("Gas gravity γg", value=0.65),
        t_res_f=st.sidebar.number_input("Reservoir T (°F)", value=180.0),
    )


def plot_loglog(interp, props, model_overlay=None, shift_log_t=0.0, shift_log_p=0.0):
    d = interp.derivative
    sp = interp.superposition
    fig = make_subplots(rows=1, cols=1)

    mask_p = sp.delta_p_psi > 0
    fig.add_trace(go.Scatter(
        x=np.log10(sp.dt_hr[mask_p]),
        y=np.log10(sp.delta_p_psi[mask_p]),
        mode="lines+markers",
        name="Δp",
        line=dict(color="#63a7ff"),
    ))
    mask_d = np.isfinite(d.derivative_psi_per_hr) & (d.derivative_psi_per_hr > 0)
    fig.add_trace(go.Scatter(
        x=np.log10(d.dt_hr[mask_d]) + shift_log_t,
        y=np.log10(d.derivative_psi_per_hr[mask_d]) + shift_log_p,
        mode="lines+markers",
        name="Bourdet derivative",
        line=dict(color="#ffba66"),
    ))

    if len(d.dt_hr[mask_d]) > 2:
        anchor_dt = d.dt_hr[mask_d][len(d.dt_hr[mask_d]) // 3]
        anchor_d = d.derivative_psi_per_hr[mask_d][len(d.dt_hr[mask_d]) // 3]
        refs = reference_slopes(d.dt_hr[mask_d], anchor_dt, anchor_d)
        for name, (tx, ty) in refs.items():
            fig.add_trace(go.Scatter(
                x=np.log10(tx),
                y=np.log10(ty),
                mode="lines",
                name=name,
                line=dict(dash="dash", width=1),
                opacity=0.6,
            ))

    if model_overlay is not None:
        fig.add_trace(go.Scatter(
            x=np.log10(d.dt_hr[mask_d]),
            y=np.log10(model_overlay[mask_d]),
            mode="lines",
            name="Type curve",
            line=dict(color="#c7a6ff", dash="dot"),
        ))

    fig.update_layout(
        title="Log-log: pressure & derivative",
        xaxis_title="log10 Δt (hr)",
        yaxis_title="log10 psi / (psi/hr)",
        height=480,
        legend=dict(orientation="h"),
        template="plotly_dark",
    )
    return fig


def plot_horner(interp):
    sp = interp.superposition
    h = interp.horner
    if not h:
        return None
    log_h = np.log10(np.maximum(sp.horner_ratio, 1.0))
    mask = (sp.dt_hr >= h.fit_start_hr) & (sp.dt_hr <= h.fit_end_hr)
    x_fit = np.linspace(log_h.min(), log_h.max(), 20)
    y_fit = h.intercept_psi + h.slope_psi_per_cycle * x_fit
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=log_h, y=sp.delta_p_psi, mode="markers", name="Data"))
    fig.add_trace(go.Scatter(x=log_h[mask], y=sp.delta_p_psi[mask], mode="markers", name="Fit window", marker=dict(color="orange")))
    fig.add_trace(go.Scatter(x=x_fit, y=y_fit, mode="lines", name=f"Fit R²={h.r2:.3f}", line=dict(color="#3dd7b6")))
    fig.update_layout(
        title="Horner plot: Δp vs log10((tp+Δt)/Δt)",
        xaxis_title="log10 Horner ratio",
        yaxis_title="Δp (psi)",
        height=400,
        template="plotly_dark",
    )
    return fig


# --- UI ---
props = sidebar_properties()
st.sidebar.header("Conditioning")
median_w = st.sidebar.slider("Median filter window", 1, 15, 5)
outlier_thr = st.sidebar.slider("Outlier MAD threshold", 2.0, 8.0, 4.5)
bourdet_l = st.sidebar.slider("Bourdet L", 0.05, 0.5, 0.15, 0.01)

uploaded = st.sidebar.file_uploader("CSV (time_hr, pressure_psi, rate_bpd)", type=["csv"])
use_sample = st.sidebar.button("Load demo DST")

series = None
if use_sample and SAMPLE.exists():
    series = load_dataframe(pd.read_csv(SAMPLE))
    st.sidebar.success("Demo loaded")
elif uploaded:
    series = load_csv_bytes(uploaded.getvalue())
    st.sidebar.success(f"Loaded {series.n} points")

if series is None:
    st.info("Upload a CSV or load the demo DST to begin.")
    st.stop()

series = attach_properties(series, props)
conditioned, qc = condition_series(series, median_window=median_w, outlier_threshold=outlier_thr)
detect_cycles(conditioned)

col1, col2, col3 = st.columns(3)
col1.metric("Points", qc["points_out"])
col2.metric("Outliers removed", qc["outliers_removed"])
col3.metric("Cycles", len(conditioned.cycles))

tab1, tab2, tab3, tab4 = st.tabs(["Trend", "Buildup PTA", "Multi-cycle", "Report"])

with tab1:
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(x=conditioned.time_hr, y=conditioned.pressure_psi, name="BHP", line=dict(color="#63a7ff")))
    if conditioned.rate_bpd is not None:
        fig_trend.add_trace(go.Scatter(x=conditioned.time_hr, y=conditioned.rate_bpd, name="Rate", yaxis="y2", line=dict(color="#7ee787")))
    for c in conditioned.cycles:
        fig_trend.add_vrect(x0=c.start_hr, x2=c.end_hr, fillcolor="rgba(255,186,102,0.08)" if c.kind == "shut-in" else "rgba(126,231,135,0.06)", line_width=0)
    fig_trend.update_layout(
        title="Pressure & rate vs time",
        yaxis=dict(title="psi"),
        yaxis2=dict(title="bpd", overlaying="y", side="right"),
        height=420,
        template="plotly_dark",
    )
    st.plotly_chart(fig_trend, use_container_width=True)

buildups = split_buildups(conditioned)
if not buildups:
    st.warning("No shut-in buildup detected — check rate threshold or period labels.")

with tab2:
    if buildups:
        bi = st.selectbox("Buildup", range(len(buildups)), format_func=lambda i: f"Buildup #{i+1} ({buildups[i].time_hr[-1]:.2f} hr)")
        b = buildups[bi]
        fit_start = st.slider("Horner fit start (hr)", 0.0, float(b.time_hr[-1] * 0.8), float(b.time_hr[-1] * 0.1))
        fit_end = st.slider("Horner fit end (hr)", fit_start + 0.01, float(b.time_hr[-1]), float(b.time_hr[-1] * 0.85))

        interp = interpret_buildup(b, conditioned, bourdet_l=bourdet_l, fit_start=fit_start, fit_end=fit_end)

        c1, c2, c3, c4 = st.columns(4)
        if interp.horner:
            c1.metric("k (md)", f"{interp.horner.permeability_md:.2f}", interp.horner.confidence)
            c2.metric("Skin", f"{interp.horner.skin:.1f}")
            c3.metric("p* (psi)", f"{interp.horner.p_star_psi:.0f}")
            c4.metric("Confidence", interp.overall_confidence)

        st.plotly_chart(plot_loglog(interp, props), use_container_width=True)
        if plot_horner(interp):
            st.plotly_chart(plot_horner(interp), use_container_width=True)

        st.subheader("Flow regimes")
        for r in interp.regimes:
            st.write(f"**{r.name}** ({r.confidence}): {r.hint}")

        st.subheader("Type curve")
        model_name = st.selectbox("Model", [m.value for m in ModelType])
        model = ModelType(model_name)
        shift_t = st.slider("Manual log-t shift", -0.3, 0.3, 0.0, 0.01)
        shift_p = st.slider("Manual log-p shift", -0.3, 0.3, 0.0, 0.01)
        if st.button("Auto-fit type curve"):
            tc = auto_fit_derivative(
                interp.superposition.dt_hr,
                interp.derivative.derivative_psi_per_hr,
                props,
                model,
                k0=interp.horner.permeability_md if interp.horner else 10,
                skin0=interp.horner.skin if interp.horner else 0,
            )
            st.success(f"Fit: k={tc.params.k_md:.2f} md, S={tc.params.skin:.1f}, RMSE(log)={tc.rmse_log:.3f}")
            overlay = model_derivative(model, interp.superposition.dt_hr, tc.params, props)
            st.plotly_chart(plot_loglog(interp, props, overlay, shift_t, shift_p), use_container_width=True)

with tab3:
    results = interpret_dst_workflow(conditioned, bourdet_l=bourdet_l)
    if results:
        rows = []
        for i, r in enumerate(results):
            if r.horner:
                rows.append({
                    "Buildup": i + 1,
                    "k (md)": round(r.horner.permeability_md, 2),
                    "Skin": round(r.horner.skin, 1),
                    "p* (psi)": round(r.horner.p_star_psi, 0),
                    "R²": round(r.horner.r2, 3),
                    "Confidence": r.overall_confidence,
                })
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
    else:
        st.write("No multi-cycle results.")

with tab4:
    results = interpret_dst_workflow(conditioned, bourdet_l=bourdet_l)
    report = generate_report(conditioned, results, qc)
    st.text_area("Auto report", report, height=500)
    st.download_button("Download report (.txt)", report, file_name="dst_pta_report.txt")
