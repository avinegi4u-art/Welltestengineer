# DST PTA Modular (Python)

Fast, transparent **DST Pressure Transient Analysis** prototype — field-oriented alternative to heavy desktop PTA tools.

## Features

| Module | Purpose |
|--------|---------|
| `data_loader.py` | CSV import, cycle detection, multi-buildup split |
| `conditioning.py` | Median filter, MAD outlier removal |
| `superposition.py` | Agarwal equivalent time, Horner ratio, multi-rate kernel |
| `derivative.py` | Bourdet derivative, reference slopes (+1, 0, -½) |
| `interpretation.py` | Horner k/skin/p*, flow regime auto-detection |
| `models.py` | IAR, fault, constant pressure, dual porosity + auto-fit |
| `gas.py` | Pseudopressure m(p), pseudotime |
| `reporting.py` | Auto text report |

## Quick start

```bash
cd dst-pta-modular
pip install -r requirements.txt
streamlit run app.py
```

Open the URL shown (default `http://localhost:8501`). Load **demo DST** or upload CSV with columns:

- `time_hr`
- `pressure_psi`
- `rate_bpd` (optional but recommended for cycle detection)

## Run tests

```bash
cd dst-pta-modular
python tests/test_core.py
```

## Architecture

- **Backend:** Python, NumPy, SciPy — transparent petroleum formulas in each module
- **UI:** Streamlit + Plotly (zoom/pan, fit window sliders, type-curve overlay)
- **Offline:** Runs locally; no cloud dependency

## Related

Single-file browser app (no Python): `dst-pressure-transient-analysis-pro-v2.11.html` in repo root.

## Engineering notes

- Horner: `k = 162.6 q μ B / (|m| h)` from semi-log slope
- Bourdet L controls log-time smoothing (default 0.15)
- Type-curve fit minimizes log-derivative RMSE (screening grade)
- Gas mode applies simplified m(p) / pseudotime transform
