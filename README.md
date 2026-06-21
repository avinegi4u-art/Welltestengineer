# Welltestengineer

Well testing and completion engineering tools (single-file HTML apps).

## Apps

| File | Purpose |
|------|---------|
| `dst-bha-tally-app.html` | DST / completion BHA tally builder — volumes, depths, connections, Excel/PDF import, export |
| `dst-pressure-transient-analysis.html` | DST real-time pressure transient analysis — BHP, rates, Horner, derivative, PI, skin, office report |
| `dst-live-data-simulator.py` | Local JSON endpoint simulator for testing real-time DST polling |
| `DST-2 BHA GD Chetna D_33#G 17.2 ppg, Final.xlsx` | Reference Halliburton BHA worksheet (ONGC / GD Chetna / DST-2) |
| `dst-2-bha-reference.js` | Embedded reference string for one-click load in the tally app |
| `vertical-kill-sheet-app.html` | Vertical well kill sheet with live formulas |
| `acid-calculator-v5.html` | Acid job calculator |
| `Carbonate Acid Job Calculator.html` | Carbonate acid job planner |

Open any `.html` file in a browser — no build step required.

## Real-time DST simulator

Run a local simulated feed:

`python3 dst-live-data-simulator.py`

Then open `http://127.0.0.1:4180/dst-pressure-transient-analysis.html`, click **Use local simulator**, and use **Poll once** or **Start polling**.
