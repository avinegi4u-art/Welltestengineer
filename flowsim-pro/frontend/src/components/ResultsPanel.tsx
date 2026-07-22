"use client";

import type { SimulationOutput } from "@/lib/types";

interface ResultsPanelProps {
  output: SimulationOutput | null;
  loading?: boolean;
}

export default function ResultsPanel({ output, loading }: ResultsPanelProps) {
  if (loading) {
    return (
      <div className="panel p-4 h-full">
        <h3 className="font-semibold mb-3">Results</h3>
        <p className="text-sm text-slate-500">Solving...</p>
      </div>
    );
  }

  if (!output) {
    return (
      <div className="panel p-4 h-full">
        <h3 className="font-semibold mb-3">Results</h3>
        <p className="text-sm text-slate-500">Run simulation to see results.</p>
      </div>
    );
  }

  const summary = output.summary;

  return (
    <div className="panel p-4 h-full overflow-y-auto">
      <h3 className="font-semibold mb-3">Results</h3>

      {!output.success && (
        <div className="mb-3 p-2 bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300 text-sm rounded">
          Simulation failed
        </div>
      )}

      <div className="space-y-2 text-sm">
        {summary.liquid_rate_stb_d != null && (
          <Row label="Liquid Rate" value={`${summary.liquid_rate_stb_d.toFixed(0)} stb/d`} />
        )}
        {summary.wellhead_pressure_psi != null && (
          <Row label="WHP" value={`${summary.wellhead_pressure_psi.toFixed(1)} psi`} />
        )}
        {summary.bottomhole_pressure_psi != null && (
          <Row label="BHP" value={`${summary.bottomhole_pressure_psi.toFixed(1)} psi`} />
        )}
        {summary.drawdown_psi != null && (
          <Row label="Drawdown" value={`${summary.drawdown_psi.toFixed(1)} psi`} />
        )}
        {summary.choke_dp_psi != null && (
          <Row label="Choke ΔP" value={`${Number(summary.choke_dp_psi).toFixed(1)} psi`} />
        )}
        {summary.flowline_pressure_drop_psi != null && (
          <Row label="Flowline ΔP" value={`${summary.flowline_pressure_drop_psi.toFixed(1)} psi`} />
        )}
        {summary.nodal_operating_rate_stb_d != null && (
          <Row label="Nodal Rate" value={`${summary.nodal_operating_rate_stb_d.toFixed(0)} stb/d`} />
        )}
      </div>

      {output.nodal_analysis && (
        <div className="mt-4">
          <h4 className="text-xs font-semibold text-slate-500 mb-1">Nodal</h4>
          <div className="space-y-1 text-xs">
            <Row label="Status" value={(output.nodal_analysis.status ?? "—").replace(/_/g, " ")} />
            {output.nodal_analysis.aof_stb_d != null && (
              <Row label="AOF" value={`${output.nodal_analysis.aof_stb_d.toFixed(0)} stb/d`} />
            )}
            {output.nodal_analysis.convergence_error_psi != null && (
              <Row label="Error" value={`${output.nodal_analysis.convergence_error_psi.toFixed(2)} psi`} />
            )}
          </div>
          {output.nodal_analysis.message && (
            <p className="mt-2 text-[11px] text-slate-500 leading-snug">{output.nodal_analysis.message}</p>
          )}
        </div>
      )}

      {output.warnings.length > 0 && (
        <div className="mt-4">
          <h4 className="text-xs font-semibold text-amber-600 mb-1">Warnings</h4>
          <ul className="text-xs space-y-1">
            {output.warnings.map((w, i) => (
              <li key={i} className="text-amber-700 dark:text-amber-400">• {w}</li>
            ))}
          </ul>
        </div>
      )}

      {output.diagnostics.length > 0 && (
        <div className="mt-4">
          <h4 className="text-xs font-semibold text-slate-500 mb-1">Diagnostics</h4>
          <ul className="text-xs space-y-1 text-slate-600 dark:text-slate-400">
            {output.diagnostics.map((d, i) => (
              <li key={i}>• {d}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between py-1 border-b border-border-light dark:border-border-dark">
      <span className="text-slate-500">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
