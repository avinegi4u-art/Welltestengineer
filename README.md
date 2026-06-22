# Welltestengineer

Well testing and completion engineering tools (single-file HTML apps).

## Apps

| File | Purpose |
|------|---------|
| `dst-bha-tally-app.html` | DST / completion BHA tally builder — volumes, depths, connections, Excel/PDF import, export |
| `dst-pressure-transient-analysis-pro-v2.11.html` | **DST PTA Pro v2.11** (open this one) — physics-propagated Bayesian priors, evidence-weighted multilayer inversion, minimum shut-in boundary guidance, exportable formal sign-off package, pairwise curve-selection audit |
| `dst-pressure-transient-analysis-pro-v2.10.html` | DST PTA Pro v2.10 — reservoir-aware Bayesian posteriors, refined multilayer inversion, sparse boundary confidence, office/reserves sign-off workflow, auditable curve dominance |
| `dst-pressure-transient-analysis-pro-v2.9.html` | DST PTA Pro v2.9 — Bayesian credible intervals, fitted multilayer inversion, usage matrix, curve dominance |
| `dst-pressure-transient-analysis-pro-v2.8.html` | DST PTA Pro v2.8 — probabilistic P10/P50/P90, multilayer screening, boundary confidence, reserves report language |
| `dst-pressure-transient-analysis-pro-v2.7.html` | DST PTA Pro v2.7 — calibrated uncertainty, hardened gating, boundary logic, model arbitration, composite screening |
| `dst-pta-pro-v2.7-user-manual.html` | **Printable user manual** for v2.7 — open in browser, then Print → Save as PDF |
| `dst-pressure-transient-analysis-pro-v2.6.html` | DST PTA Pro v2.6 — prior release |
| `dst-pressure-transient-analysis.html` | Older DST analyzer v2.0 — superseded by Pro v2.11 |
| `DST-2 BHA GD Chetna D_33#G 17.2 ppg, Final.xlsx` | Reference Halliburton BHA worksheet (ONGC / GD Chetna / DST-2) |
| `dst-2-bha-reference.js` | Embedded reference string for one-click load in the tally app |
| `vertical-kill-sheet-app.html` | Vertical well kill sheet with live formulas |
| `acid-calculator-v5.html` | Acid job calculator |
| `Carbonate Acid Job Calculator.html` | Carbonate acid job planner |

Open any `.html` file in a browser — no build step required.

### Extending DST PTA Pro

Use the **Extend** tab inside `dst-pressure-transient-analysis-pro-v2.11.html` for copy-paste **Feature**, **Bug fix**, and **Refactor** prompts (or download them as `.txt`). Cursor agents also read `.cursor/rules/dst-pta.mdc` when editing PTA HTML files.
