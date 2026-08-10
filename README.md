# Welltestengineer

Well testing, completion, and production engineering tools for field engineers. Most apps are **single-file HTML** — open in a browser with no build step. [FlowSim Pro](flowsim-pro/) is a full-stack multiphase flow simulator.

## Quick start

| I want to… | Open / run |
|------------|------------|
| Analyze DST pressure transients | **`dst-pressure-transient-analysis-pro-v2.15.html`** |
| Design casing / tubing integrity | **`casing-design-pro-v3.html`** |
| Build a DST BHA tally | **`dst-bha-tally-app.html`** |
| Plan a carbonate acid job | **`Carbonate Acid Job Calculator.html`** |
| Calculate CO₂ corrosion (browser) | **`Corrosion-norsok_m506_calculator.html`** |
| Calculate CO₂ corrosion (Python) | `norsokm506_01.py` |
| Fill a vertical kill sheet | **`vertical-kill-sheet-app.html`** |
| Select DST tubing | **`DST tubing selection.html`** |
| Browse upstream calculators | **`Oil and gas calculations-app.html`** |
| Run multiphase flow simulation | [FlowSim Pro](flowsim-pro/) — see below |

---

## Applications

### DST Pressure Transient Analyzer Pro

| File | Version | Notes |
|------|---------|-------|
| **`dst-pressure-transient-analysis-pro-v2.15.html`** | **v2.15.4** | **Current.** Kappa-style workspace (Loglog · Results · Semilog · History), Plotly charts with SVG offline fallback, V8.1 period detector, vSH04 deconvolution, surface-rate upload, composite inversion, Bayesian uncertainty, office sign-off. Requires `welltest-pta-engine.js` in the same folder. |
| `dst-pressure-transient-analysis-pro-v2.14.html` | v2.14 | Previous release — interactive Plotly PTA workspace, Horner & Bourdet, auto model match. |
| `welltest-pta-engine.js` | — | Shared engine module for v2.15 (period detection, deconvolution, surface rates). |
| `dst-pta-pro-v2.7-user-manual.html` | Manual | Printable user manual (written for v2.7; core workflows still apply). |

Older PTA versions (v2.0–v2.11) are in [`archive/pta/`](archive/pta/).

### Casing design

| File | Version | Notes |
|------|---------|-------|
| **`casing-design-pro-v3.html`** | **Pro v5** | Wear allowance, APB, deviation survey/DLS, multi-fluid columns, running drag/shock, depth-wise triaxial engine. Workflow stepper, KPI dashboard, export. |

Legacy v2.1 is in [`archive/misc/CasingDesign.html`](archive/misc/CasingDesign.html).

### DST BHA tally

| File | Notes |
|------|-------|
| **`dst-bha-tally-app.html`** | BHA tally builder — volumes, depths, connections, SVG diagram, Excel/PDF import, export, dark/light theme. |
| `dst-2-bha-reference.js` / `.json` | Reference data for one-click load (DST-2 / GD Chetna). |
| `DST-2 BHA GD Chetna D_33#G 17.2 ppg, Final.xlsx` | Reference Halliburton BHA worksheet. |
| `Tally.xlsx` | Sample tally spreadsheet. |

### Stimulation

| File | Notes |
|------|-------|
| **`Carbonate Acid Job Calculator.html`** | Full carbonate acid job design — volumes, spend, wormholing, checklist persistence, engineering guidance. Integrity checksum: `Carbonate Acid Job Calculator.html.sha256`. |

### Corrosion (NORSOK M-506)

| File | Notes |
|------|-------|
| **`Corrosion-norsok_m506_calculator.html`** | Browser-based CO₂ internal corrosion rate calculator. |
| `norsokm506_01.py` | Python module — import and call `Cal_Norsok()` with flow, fluid, and chemistry inputs. |
| `test_norsok01.py` | Example script demonstrating the Python module (not an automated test suite). |

### Well control & completions

| File | Notes |
|------|-------|
| **`vertical-kill-sheet-app.html`** | API field-units kill sheet with live formulas and bi-directional unit conversion. |
| **`DST tubing selection.html`** | DST tubing selector (production v1.0). |

### Reference hub

| File | Notes |
|------|-------|
| **`Oil and gas calculations-app.html`** | Searchable index of upstream calculators — drilling, completions, production, well testing, DST, wireline, CT, cementing, stimulation, unit conversion. |

---

## FlowSim Pro

Steady-state multiphase flow simulation for wells, flowlines, pipelines, and production networks.

```
flowsim-pro/
├── backend/     FastAPI + Python simulation engine
└── frontend/    Next.js + React + Tailwind + Plotly
```

### Backend

```bash
cd flowsim-pro/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd flowsim-pro/frontend
npm install
npm run dev
```

Open http://localhost:3000. User manual: `flowsim-pro/docs/FlowSim_Pro_User_Manual.pdf`.

### Tests

```bash
cd flowsim-pro/backend
pytest tests/ -v
```

See [flowsim-pro/README.md](flowsim-pro/README.md) for API endpoints, engine modules, and model assumptions.

---

## Archive

Superseded versions are kept in [`archive/`](archive/) for reference only. See [`archive/README.md`](archive/README.md) for the full list.

---

## License

See [LICENSE.txt](LICENSE.txt).
