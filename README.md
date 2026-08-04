# Welltestengineer

Well testing and completion engineering tools (single-file HTML apps).

## Apps

| File | Purpose |
|------|---------|
| `dst-bha-tally-app.html` | DST / completion BHA tally builder — volumes, depths, connections, Excel/PDF import, export |
| `dst-pressure-transient-analysis-pro-v2.15.html` | **DST PTA Pro v2.15.4** (open this one) — Kappa-style left-rail workspace with Analytical mosaic (Loglog · Results · Semilog · History), Generate analytical model dialog, Plotly charts + SVG offline fallback, auto-match, composite inversion, Bayesian uncertainty, office sign-off; **plus v2.12 parity**: welltest-pta V8.1 period detector, vSH04 multi-event deconvolution, separate surface-rate upload/forward-fill (`welltest-pta-engine.js`) |
| `dst-pressure-transient-analysis-pro-v2.14.html` | DST PTA Pro v2.14 — interactive Plotly PTA workspace (zoom/pan/select-fit) with SVG offline fallback; Horner & Bourdet, auto model match, boundary & composite inversion screening |
| `dst-pressure-transient-analysis-pro-v2.11.html` | DST PTA Pro v2.11 — local-first senior engineer DST/PTA: variable-rate superposition, Horner & derivative analysis, boundary detection, composite screening, physics Bayesian uncertainty, interpretation gating, office sign-off, engineering audit trail |
| `dst-pressure-transient-analysis-pro-v2.10.html` | DST PTA Pro v2.10 — reservoir-aware Bayesian posteriors, refined multilayer inversion, sparse boundary confidence, office/reserves sign-off workflow, auditable curve dominance |
| `dst-pressure-transient-analysis-pro-v2.9.html` | DST PTA Pro v2.9 — Bayesian credible intervals, fitted multilayer inversion, usage matrix, curve dominance |
| `dst-pressure-transient-analysis-pro-v2.8.html` | DST PTA Pro v2.8 — probabilistic P10/P50/P90, multilayer screening, boundary confidence, reserves report language |
| `dst-pressure-transient-analysis-pro-v2.7.html` | DST PTA Pro v2.7 — calibrated uncertainty, hardened gating, boundary logic, model arbitration, composite screening |
| `dst-pta-pro-v2.7-user-manual.html` | **Printable user manual** for v2.7 — open in browser, then Print → Save as PDF |
| `dst-pressure-transient-analysis-pro-v2.6.html` | DST PTA Pro v2.6 — prior release |
| `dst-pressure-transient-analysis.html` | Older DST analyzer v2.0 — superseded by Pro v2.15 |
| `DST-2 BHA GD Chetna D_33#G 17.2 ppg, Final.xlsx` | Reference Halliburton BHA worksheet (ONGC / GD Chetna / DST-2) |
| `dst-2-bha-reference.js` | Embedded reference string for one-click load in the tally app |
| `vertical-kill-sheet-app.html` | Vertical well kill sheet with live formulas |
| `acid-calculator-v5.html` | Acid job calculator |
| `CasingDesign.html` | WellCat-style casing screening v2.1 — burst, collapse, tension (superseded by Pro v3) |
| `casing-design-pro-v3.html` | **Casing Design Pro v5** — wear allowance, APB, deviation survey/DLS, multi-fluid columns, running drag/shock, plus all v4 depth-wise triaxial engine. Redesigned UI: workflow stepper, KPI dashboard, filters, toasts, keyboard shortcuts (`Ctrl+Enter` to run) |

Open any `.html` file in a browser — no build step required.
