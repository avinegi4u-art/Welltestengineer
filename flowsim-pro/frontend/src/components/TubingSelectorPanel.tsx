"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { TubingSelectionResult } from "@/lib/types";
import Chart from "./Chart";
import type { Data } from "plotly.js";
import { Ruler } from "lucide-react";

interface TubingSelectorPanelProps {
  caseId: number | null;
  onApplyId?: (idIn: number) => void;
}

export default function TubingSelectorPanel({ caseId, onApplyId }: TubingSelectorPanelProps) {
  const [cFactor, setCFactor] = useState(100);
  const [result, setResult] = useState<TubingSelectionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    if (!caseId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.selectTubing(caseId, cFactor);
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Tubing selection failed");
    } finally {
      setLoading(false);
    }
  };

  const chartData: Data[] = [];
  if (result) {
    chartData.push({
      x: result.candidates.map((c) => c.inner_diameter_in),
      y: result.candidates.map((c) => c.operating_rate_stb_d),
      type: "scatter",
      mode: "lines+markers",
      name: "Nodal rate",
      marker: { size: 8, color: "#2563eb" },
      line: { color: "#2563eb" },
    });
    chartData.push({
      x: result.candidates.map((c) => c.inner_diameter_in),
      y: result.candidates.map((c) => c.max_mixture_velocity_ft_s),
      type: "scatter",
      mode: "lines+markers",
      name: "Mixture v (ft/s)",
      yaxis: "y2",
      marker: { size: 7, color: "#ea580c" },
      line: { color: "#ea580c", dash: "dot" },
    });
  }

  return (
    <div className="panel p-3">
      <div className="flex items-center justify-between mb-3 gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          <Ruler className="w-4 h-4 text-primary" />
          <h3 className="font-semibold text-sm">Tubing Selector</h3>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-500">Phase B</span>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-slate-500">C-factor</label>
          <input
            type="number"
            className="input-field w-20 text-xs py-1"
            value={cFactor}
            onChange={(e) => setCFactor(parseFloat(e.target.value) || 100)}
          />
          <button onClick={run} disabled={!caseId || loading} className="btn-primary text-xs px-3 py-1.5">
            {loading ? "Running..." : "Run Sweep"}
          </button>
        </div>
      </div>

      <p className="text-xs text-slate-500 mb-3">
        Sweeps the tubing catalog through nodal analysis. Ranks by operating rate with API RP 14E erosional screening.
      </p>

      {error && <p className="text-xs text-red-600 mb-2">{error}</p>}

      {result && (
        <>
          {result.recommended_label && (
            <div className="mb-3 p-2 rounded bg-emerald-50 dark:bg-emerald-900/20 text-sm flex items-center justify-between gap-2">
              <span>
                Recommended: <strong>{result.recommended_label}</strong>{" "}
                (ID {result.recommended_id_in?.toFixed(3)} in)
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
              xaxis: { title: "Tubing ID (in)" },
              yaxis: { title: "Rate (stb/d)" },
              yaxis2: { title: "Velocity (ft/s)", overlaying: "y", side: "right" },
              legend: { orientation: "h", y: 1.15 },
            }}
          />

          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="bg-slate-50 dark:bg-slate-800">
                <tr>
                  <th className="p-2 text-left">Size</th>
                  <th className="p-2 text-right">ID</th>
                  <th className="p-2 text-right">Rate</th>
                  <th className="p-2 text-right">BHP</th>
                  <th className="p-2 text-right">v / Ve</th>
                  <th className="p-2 text-left">Status</th>
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
                    <td className="p-2 text-right">{c.operating_rate_stb_d.toFixed(0)}</td>
                    <td className="p-2 text-right">{c.operating_bhp_psi.toFixed(0)}</td>
                    <td className={`p-2 text-right ${c.erosion_ok ? "" : "text-amber-600"}`}>
                      {c.erosion_ratio.toFixed(2)}
                    </td>
                    <td className="p-2 text-slate-500">{c.status.replace(/_/g, " ")}</td>
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
