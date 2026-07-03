"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { SensitivityResult } from "@/lib/types";
import Chart from "./Chart";
import type { Data } from "plotly.js";

const PARAM_PRESETS: Record<string, { label: string; values: number[] }> = {
  tubing_id: { label: "Tubing ID (in)", values: [2.441, 2.992, 3.476, 3.958, 4.67] },
  choke_size: { label: "Choke (64ths in)", values: [16, 24, 32, 40, 48] },
  whp: { label: "WHP (psi)", values: [300, 400, 500, 600, 700] },
  gor: { label: "GOR (scf/stb)", values: [500, 800, 1000, 1200, 1500] },
  water_cut: { label: "Water Cut (fraction)", values: [0.05, 0.1, 0.2, 0.3, 0.5] },
};

const VLP_COLORS = ["#f59e0b", "#16a34a", "#8b5cf6", "#ec4899", "#06b6d4", "#84cc16"];

interface SensitivityPanelProps {
  caseId: number | null;
}

export default function SensitivityPanel({ caseId }: SensitivityPanelProps) {
  const [parameter, setParameter] = useState("tubing_id");
  const [customValues, setCustomValues] = useState("");
  const [result, setResult] = useState<SensitivityResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runSensitivity = async () => {
    if (!caseId) return;
    setLoading(true);
    setError(null);
    try {
      const values = customValues.trim()
        ? customValues.split(",").map((v) => parseFloat(v.trim())).filter((v) => !Number.isNaN(v))
        : PARAM_PRESETS[parameter].values;
      const data = await api.sensitivity(caseId, parameter, values);
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sensitivity failed");
    } finally {
      setLoading(false);
    }
  };

  const chartData: Data[] = [];
  if (result) {
    chartData.push({
      x: result.ipr_rates_stb_d,
      y: result.ipr_pressures_psi,
      type: "scatter",
      mode: "lines",
      name: "IPR",
      line: { color: "#2563eb", width: 3 },
    });
    result.curves.forEach((curve, i) => {
      chartData.push({
        x: curve.rates_stb_d,
        y: curve.vlp_pressures_psi,
        type: "scatter",
        mode: "lines",
        name: curve.label,
        line: { color: VLP_COLORS[i % VLP_COLORS.length], width: 2, dash: "dot" },
      });
      chartData.push({
        x: [curve.operating_rate_stb_d],
        y: [curve.operating_bhp_psi],
        type: "scatter",
        mode: "markers",
        name: `${curve.label} op.`,
        marker: { color: VLP_COLORS[i % VLP_COLORS.length], size: 9 },
        showlegend: false,
      });
    });
  }

  return (
    <div className="panel p-4">
      <h3 className="font-semibold mb-3 text-sm">Nodal Sensitivity — VLP Overlay</h3>

      <div className="flex flex-wrap gap-2 mb-3 items-end">
        <div>
          <label className="text-xs text-slate-500">Parameter</label>
          <select
            className="input-field mt-0.5 text-xs"
            value={parameter}
            onChange={(e) => { setParameter(e.target.value); setCustomValues(""); }}
          >
            {Object.entries(PARAM_PRESETS).map(([key, { label }]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
        </div>
        <div className="flex-1 min-w-[160px]">
          <label className="text-xs text-slate-500">Values (comma-separated, optional)</label>
          <input
            className="input-field mt-0.5 text-xs"
            placeholder={PARAM_PRESETS[parameter].values.join(", ")}
            value={customValues}
            onChange={(e) => setCustomValues(e.target.value)}
          />
        </div>
        <button
          onClick={runSensitivity}
          disabled={!caseId || loading}
          className="btn-primary text-xs py-1.5"
        >
          {loading ? "Running..." : "Run Sweep"}
        </button>
      </div>

      {error && (
        <p className="text-xs text-red-600 dark:text-red-400 mb-2">{error}</p>
      )}

      {!caseId && (
        <p className="text-xs text-slate-500">Select a case to run sensitivity analysis.</p>
      )}

      {result && (
        <>
          <div className="h-72 mb-3">
            <Chart
              data={chartData}
              layout={{
                xaxis: { title: "Liquid Rate (stb/d)" },
                yaxis: { title: "Bottomhole Pressure (psi)" },
                showlegend: true,
                legend: { orientation: "h", y: 1.12, font: { size: 9 } },
              }}
            />
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border-light dark:border-border-dark text-slate-500">
                  <th className="text-left py-1">Case</th>
                  <th className="text-right py-1">Rate (stb/d)</th>
                  <th className="text-right py-1">BHP (psi)</th>
                  <th className="text-left py-1">Status</th>
                </tr>
              </thead>
              <tbody>
                {result.curves.map((c) => (
                  <tr key={c.label} className="border-b border-border-light dark:border-border-dark">
                    <td className="py-1.5">{c.label}</td>
                    <td className="text-right">{c.operating_rate_stb_d.toFixed(0)}</td>
                    <td className="text-right">{c.operating_bhp_psi.toFixed(0)}</td>
                    <td className="py-1.5">
                      <StatusBadge status={c.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {result.diagnostics.length > 0 && (
            <div className="mt-3 text-xs text-slate-600 dark:text-slate-400 space-y-1">
              {result.diagnostics.map((d, i) => (
                <p key={i}>• {d}</p>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    operating_point_found: "text-green-700 dark:text-green-400",
    rate_limited_by_vlp: "text-amber-700 dark:text-amber-400",
    ipr_limited: "text-blue-700 dark:text-blue-400",
    no_operating_point: "text-red-700 dark:text-red-400",
  };
  const labels: Record<string, string> = {
    operating_point_found: "OK",
    rate_limited_by_vlp: "VLP limited",
    ipr_limited: "IPR limited",
    no_operating_point: "No match",
  };
  return (
    <span className={styles[status] ?? "text-slate-500"}>
      {labels[status] ?? status}
    </span>
  );
}
