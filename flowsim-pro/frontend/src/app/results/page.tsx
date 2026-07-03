"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import type { SimulationCase } from "@/lib/types";
import ProfileCharts from "@/components/ProfileCharts";
import ResultsPanel from "@/components/ResultsPanel";
import Chart from "@/components/Chart";
import type { Data } from "plotly.js";

function ResultsContent() {
  const searchParams = useSearchParams();
  const compareParam = searchParams.get("compare");
  const caseIdParam = searchParams.get("id");

  const [cases, setCases] = useState<SimulationCase[]>([]);
  const [comparison, setComparison] = useState<Record<string, unknown>[] | null>(null);
  const [selectedCase, setSelectedCase] = useState<SimulationCase | null>(null);

  useEffect(() => {
    const load = async () => {
      const all = await api.listCases();
      setCases(all);

      if (compareParam) {
        const ids = compareParam.split(",").map(Number);
        const result = await api.compareCases(ids);
        setComparison(result.cases);
      } else if (caseIdParam) {
        const c = await api.getCase(parseInt(caseIdParam));
        setSelectedCase(c);
        if (!c.outputs) {
          const out = await api.solveCase(c.id);
          setSelectedCase({ ...c, outputs: out });
        }
      } else if (all.length > 0) {
        const c = all[0];
        if (!c.outputs) {
          const out = await api.solveCase(c.id);
          setSelectedCase({ ...c, outputs: out });
        } else {
          setSelectedCase(c);
        }
      }
    };
    load();
  }, [compareParam, caseIdParam]);

  const compareData: Data[] = comparison
    ? [
        {
          x: comparison.map((_, i) => `Case ${i + 1}`),
          y: comparison.map((c) => (c.liquid_rate_stb_d as number) ?? 0),
          type: "bar",
          name: "Liquid Rate",
          marker: { color: "#2563eb" },
        },
        {
          x: comparison.map((_, i) => `Case ${i + 1}`),
          y: comparison.map((c) => (c.bottomhole_pressure_psi as number) ?? 0),
          type: "bar",
          name: "BHP",
          marker: { color: "#f59e0b" },
        },
      ]
    : [];

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Results Viewer</h1>

      {comparison && (
        <div className="mb-6">
          <h2 className="font-semibold mb-3">Case Comparison</h2>
          <div className="panel p-4 h-72 mb-4">
            <Chart
              data={compareData}
              layout={{
                barmode: "group",
                xaxis: { title: "Case" },
                yaxis: { title: "Value" },
                showlegend: true,
              }}
            />
          </div>
          <div className="panel overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 dark:bg-slate-800">
                <tr>
                  <th className="p-2 text-left">Case</th>
                  <th className="p-2 text-right">Rate (stb/d)</th>
                  <th className="p-2 text-right">WHP (psi)</th>
                  <th className="p-2 text-right">BHP (psi)</th>
                  <th className="p-2 text-right">Flowline ΔP</th>
                </tr>
              </thead>
              <tbody>
                {comparison.map((c, i) => (
                  <tr key={i} className="border-t border-border-light dark:border-border-dark">
                    <td className="p-2">Case {i + 1}</td>
                    <td className="p-2 text-right">{(c.liquid_rate_stb_d as number)?.toFixed?.(0) ?? "—"}</td>
                    <td className="p-2 text-right">{(c.wellhead_pressure_psi as number)?.toFixed?.(1) ?? "—"}</td>
                    <td className="p-2 text-right">{(c.bottomhole_pressure_psi as number)?.toFixed?.(1) ?? "—"}</td>
                    <td className="p-2 text-right">{(c.flowline_pressure_drop_psi as number)?.toFixed?.(1) ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {selectedCase && !comparison && (
        <div className="grid grid-cols-12 gap-4">
          <div className="col-span-9">
            <h2 className="font-semibold mb-3">{selectedCase.name}</h2>
            <ProfileCharts output={selectedCase.outputs} />
          </div>
          <div className="col-span-3">
            <ResultsPanel output={selectedCase.outputs} />
          </div>
        </div>
      )}

      {!selectedCase && !comparison && cases.length === 0 && (
        <p className="text-slate-500">No cases available. Create a case in the editor first.</p>
      )}

      {!compareParam && !caseIdParam && cases.length > 1 && (
        <div className="mt-6 panel p-4">
          <h3 className="font-semibold mb-2 text-sm">Available Cases</h3>
          <div className="flex flex-wrap gap-2">
            {cases.map((c) => (
              <button
                key={c.id}
                onClick={() => setSelectedCase(c)}
                className="btn-secondary text-xs"
              >
                {c.name}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function ResultsPage() {
  return (
    <Suspense fallback={<div className="p-6">Loading results...</div>}>
      <ResultsContent />
    </Suspense>
  );
}
