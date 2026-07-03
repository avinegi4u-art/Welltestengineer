"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { SimulationCase } from "@/lib/types";
import { Play, RefreshCw } from "lucide-react";
import Link from "next/link";

export default function DashboardPage() {
  const [cases, setCases] = useState<SimulationCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<number[]>([]);

  const load = async () => {
    setLoading(true);
    try {
      const data = await api.listCases();
      setCases(data);
    } catch {
      setCases([]);
    }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    const c = await api.createCase({ name: `Case ${cases.length + 1}`, description: "" });
    setCases([c, ...cases]);
  };

  const handleSolve = async (id: number) => {
    await api.solveCase(id);
    await load();
  };

  const toggleSelect = (id: number) => {
    setSelected((prev) => prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]);
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-sm text-slate-500 mt-1">Steady-state multiphase flow simulation</p>
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="btn-secondary flex items-center gap-1">
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
          <button onClick={handleCreate} className="btn-primary">+ New Case</button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <StatCard label="Total Cases" value={cases.length} />
        <StatCard label="Solved" value={cases.filter((c) => c.outputs?.success).length} />
        <StatCard label="Selected for Compare" value={selected.length} />
      </div>

      {loading ? (
        <p className="text-slate-500">Loading cases...</p>
      ) : cases.length === 0 ? (
        <div className="panel p-8 text-center">
          <p className="text-slate-500 mb-4">No simulation cases yet.</p>
          <button onClick={handleCreate} className="btn-primary">Create First Case</button>
        </div>
      ) : (
        <div className="panel overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-800">
              <tr>
                <th className="p-3 text-left w-8"></th>
                <th className="p-3 text-left">Name</th>
                <th className="p-3 text-left">Type</th>
                <th className="p-3 text-right">Rate (stb/d)</th>
                <th className="p-3 text-right">BHP (psi)</th>
                <th className="p-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c) => (
                <tr key={c.id} className="border-t border-border-light dark:border-border-dark hover:bg-slate-50 dark:hover:bg-slate-800/50">
                  <td className="p-3">
                    <input type="checkbox" checked={selected.includes(c.id)} onChange={() => toggleSelect(c.id)} />
                  </td>
                  <td className="p-3 font-medium">
                    <Link href={`/editor?id=${c.id}`} className="hover:text-primary">{c.name}</Link>
                  </td>
                  <td className="p-3 text-slate-500">{c.case_type.replace(/_/g, " ")}</td>
                  <td className="p-3 text-right">{c.outputs?.summary?.liquid_rate_stb_d?.toFixed(0) ?? "—"}</td>
                  <td className="p-3 text-right">{c.outputs?.summary?.bottomhole_pressure_psi?.toFixed(0) ?? "—"}</td>
                  <td className="p-3 text-right">
                    <button onClick={() => handleSolve(c.id)} className="p-1.5 hover:bg-primary/10 rounded" title="Solve">
                      <Play className="w-4 h-4 text-primary" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selected.length >= 2 && (
        <div className="mt-4">
          <Link href={`/results?compare=${selected.join(",")}`} className="btn-primary">
            Compare {selected.length} Cases
          </Link>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="panel p-4">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
    </div>
  );
}
