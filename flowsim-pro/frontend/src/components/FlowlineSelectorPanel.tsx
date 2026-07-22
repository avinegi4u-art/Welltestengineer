"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { FlowlineSelectionResult } from "@/lib/types";
import Chart from "./Chart";
import type { Data } from "plotly.js";
import { GitBranch } from "lucide-react";

interface FlowlineSelectorPanelProps {
  caseId: number | null;
  onApplyId?: (idIn: number) => void;
}

export default function FlowlineSelectorPanel({ caseId, onApplyId }: FlowlineSelectorPanelProps) {
  const [targetDp, setTargetDp] = useState(50);
  const [cFactor, setCFactor] = useState(100);
  const [result, setResult] = useState<FlowlineSelectionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    if (!caseId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.selectFlowline(caseId, targetDp, cFactor);
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Flowline selection failed");
    } finally {
      setLoading(false);
    }
  };

  const chartData: Data[] = [];
  if (result) {
    chartData.push({
      x: result.candidates.map((c) => c.inner_diameter_in),
      y: result.candidates.map((c) => c.pressure_drop_psi),
      type: "scatter",
      mode: "lines+markers",
      name: "ΔP (psi)",
      marker: { size: 8, color: "#2563eb" },
      line: { color: "#2563eb" },
    });
    chartData.push({
      x: result.candidates.map((c) => c.inner_diameter_in),
      y: result.candidates.map((c) => c.max_velocity_ft_s),
      type: "scatter",
      mode: "lines+markers",
      name: "Max v (ft/s)",
      yaxis: "y2",
      marker: { size: 7, color: "#ea580c" },
      line: { color: "#ea580c", dash: "dot" },
    });
    if (result.target_dp_psi > 0) {
      chartData.push({
        x: [result.candidates[0]?.inner_diameter_in, result.candidates.at(-1)?.inner_diameter_in],
        y: [result.target_dp_psi, result.target_dp_psi],
        type: "scatter",
        mode: "lines",
        name: "ΔP target",
        line: { color: "#16a34a", dash: "dash" },
      });
    }
  }

  return (
    <div className="panel p-3">
      <div className="flex items-center justify-between mb-3 gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-primary" />
          <h3 className="font-semibold text-sm">Flowline Selector</h3>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-500">Phase C</span>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <label className="text-xs text-slate-500">Target ΔP</label>
          <input
            type="number"
            className="input-field w-20 text-xs py-1"
            value={targetDp}
            onChange={(e) => setTargetDp(parseFloat(e.target.value) || 50)}
          />
          <label className="text-xs text-slate-500">C</label>
          <input
            type="number"
            className="input-field w-16 text-xs py-1"
            value={cFactor}
            onChange={(e) => setCFactor(parseFloat(e.target.value) || 100)}
          />
          <button onClick={run} disabled={!caseId || loading} className="btn-primary text-xs px-3 py-1.5">
            {loading ? "Running..." : "Run Sweep"}
          </button>
        </div>
      </div>

      <p className="text-xs text-slate-500 mb-3">
        Sweeps pipe catalog IDs for Beggs-Brill ΔP and velocity. Recommends the smallest ID that meets the ΔP target and erosional limit.
      </p>

      {error && <p className="text-xs text-red-600 mb-2">{error}</p>}

      {result && (
        <>
          {result.recommended_label && (
            <div className="mb-3 p-2 rounded bg-emerald-50 dark:bg-emerald-900/20 text-sm flex items-center justify-between gap-2">
              <span>
                Min recommended: <strong>{result.recommended_label}</strong>{" "}
                (ID {result.recommended_id_in?.toFixed(3)} in) for ΔP ≤ {result.target_dp_psi} psi
              </span>
              {onApplyId && result.recommended_id_in != null && (
                <button
                  className="btn-secondary text-xs px-2 py-1"
                  onClick={() => onApplyId(result.recommended_id_in!)}
                >
                  Apply ID
                </button>
              )}
            </div>
          )}

          <Chart
            data={chartData}
            layout={{
              height: 260,
              margin: { t: 30, r: 50, b: 40, l: 50 },
              xaxis: { title: "Pipe ID (in)" },
              yaxis: { title: "ΔP (psi)" },
              yaxis2: { title: "Velocity (ft/s)", overlaying: "y", side: "right" },
              legend: { orientation: "h", y: 1.15 },
            }}
          />

          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="bg-slate-50 dark:bg-slate-800">
                <tr>
                  <th className="p-2 text-left">Pipe</th>
                  <th className="p-2 text-right">ID</th>
                  <th className="p-2 text-right">ΔP</th>
                  <th className="p-2 text-right">Outlet P</th>
                  <th className="p-2 text-right">v / Ve</th>
                  <th className="p-2 text-center">Meets</th>
                  <th className="p-2"></th>
                </tr>
              </thead>
              <tbody>
                {result.candidates.map((c) => (
                  <tr
                    key={c.label}
                    className={`border-t border-border-light dark:border-border-dark ${
                      c.recommended ? "bg-emerald-50/60 dark:bg-emerald-900/20" : ""
                    }`}
                  >
                    <td className="p-2 font-medium">{c.label}</td>
                    <td className="p-2 text-right">{c.inner_diameter_in.toFixed(3)}</td>
                    <td className="p-2 text-right">{c.pressure_drop_psi.toFixed(1)}</td>
                    <td className="p-2 text-right">{c.outlet_pressure_psi.toFixed(0)}</td>
                    <td className={`p-2 text-right ${c.erosion_ok ? "" : "text-amber-600"}`}>
                      {c.erosion_ratio.toFixed(2)}
                    </td>
                    <td className="p-2 text-center">{c.meets_dp_target ? "✓" : "—"}</td>
                    <td className="p-2 text-right">
                      {onApplyId && (
                        <button
                          className="text-primary hover:underline"
                          onClick={() => onApplyId(c.inner_diameter_in)}
                        >
                          Apply
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
