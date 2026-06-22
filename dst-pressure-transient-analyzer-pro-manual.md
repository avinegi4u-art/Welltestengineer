# DST Pressure Transient Analyzer Pro v2.11 Manual

## Purpose

DST Pressure Transient Analyzer Pro is a browser-local screening tool for monitoring drill stem test pressure and rate behavior while a job is running. It supports CSV imports, pasted rows, manual readings, JSON endpoint polling, period correction, Horner buildup screening, derivative diagnostics, step-rate screening, multi-buildup comparison, and report export.

Use the results for engineering screening only. Final DST interpretation requires calibrated gauges, validated rates, phase behavior review, wellbore storage and afterflow diagnosis, and senior engineering approval.

## Quick start

1. Open `dst-pressure-transient-analysis-pro-v2.2 1.html` in a browser.
2. Click `Load DST demo` to review the workflow, or import/paste job data in the `Data link` tab.
3. Confirm pressure, liquid rate, gas rate, and temperature units before import.
4. Review `Detected DST periods` and correct flow, shut-in, cleanup, restart, or afterflow labels as needed.
5. Enter reservoir and fluid inputs in the `Analysis` tab.
6. Adjust the Horner fit start/end to avoid early storage and late boundary effects.
7. Review confidence, derivative regimes, superposition notes, and quality checks in `Diagnostics`.
8. Use `Step-rate` when the DST includes stimulation or rate-step data.
9. Build the report in `Report`, then export text, HTML, PDF, plots, CSV, JSON, or a case backup.

## Accepted data columns

The importer accepts flexible header names. Each row needs a timestamp and bottomhole pressure.

| Channel | Example headers |
| --- | --- |
| Time | `time`, `timestamp`, `date_time`, `datetime`, `sample_time`, `reading_time` |
| BHP | `bhp`, `bhp_psi`, `bottomhole_pressure`, `downhole_pressure`, `gauge_pressure` |
| WHP | `whp`, `wellhead_pressure`, `surface_pressure_psi`, `thp`, `tubing_head_pressure` |
| Rate | `rate`, `rate_bpd`, `surface_rate`, `liquid_rate`, `q`, `q_total` |
| Oil | `oil`, `oil_rate`, `oil_bpd`, `qo`, `q_oil` |
| Water | `water`, `water_rate`, `water_bpd`, `qw`, `q_water` |
| Gas | `gas`, `gas_rate`, `gas_mscfd`, `qg`, `q_gas` |
| Temperature | `temp`, `temperature`, `temp_f`, `gauge_temperature`, `bh_temp` |

## Interpretation workflow

- Start with QC flags: duplicate timestamps, unsorted imports, sparse shut-in points, pressure range issues, pressure spikes, and temperature jumps.
- Verify period labels before interpreting Horner, derivative, superposition, or step-rate output.
- Use the Horner fit window to exclude early wellbore storage/afterflow and late boundary effects.
- Treat p*, permeability, skin, and PI as screening values until rate history, gauge drift, PVT, completion geometry, and boundaries are validated.
- Add key events for perforation, acid, step-rate start/end, shut-in, restart, gauge change, or interpretation notes.

## Step-rate workflow

- Use event filtering to isolate stages after acid or step-rate events.
- Use manual grouping when multiple flowing periods represent one operational stage.
- Compare pressure-vs-rate slope breaks only after stage pressures are stable.
- Use multi-buildup comparison to screen pre-acid and post-acid changes in k, skin, PI, and p*.

## Outputs

- `Save case`: stores the case in browser local storage.
- `Download case`: exports a portable JSON case backup with rows, inputs, units, events, manual period edits, import stats, and version metadata.
- `Export CSV`: exports normalized row data.
- `Export JSON`: exports rows plus compact analysis results.
- `Build report`: creates the interpretation note.
- `Export plots PNG`: exports trend, Horner, derivative, step-rate, and injectivity/falloff charts.

