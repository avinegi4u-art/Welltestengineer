"use client";

import type { SimulationOutput } from "@/lib/types";

interface AssumptionsPanelProps {
  output: SimulationOutput | null;
}

export default function AssumptionsPanel({ output }: AssumptionsPanelProps) {
  const assumptions = output?.assumptions ?? {
    fluid_model: "Black-oil with Standing Bo and Beggs-Robinson viscosity",
    multiphase_flow: "Beggs-Brill (1973) holdup and two-phase friction (tubing + flowline)",
    choke: "Multiphase orifice ΔP; WHP boundary is downstream of choke",
    heat_transfer: "Steady-state lumped UA exponential approach to ambient",
    ipr_models: "Linear PI, Vogel",
    selection: "Tubing catalog nodal ranking + flowline diameter sweep (API RP 14E Ve)",
    network_solver: "Iterative pressure balance",
    units: "Field units (psi, ft, stb/d, °F)",
  };

  return (
    <div className="panel p-4">
      <h3 className="font-semibold mb-3 text-sm">Model Assumptions</h3>
      <dl className="space-y-2 text-xs">
        {Object.entries(assumptions).map(([key, val]) => (
          <div key={key}>
            <dt className="font-medium text-slate-500 capitalize">{key.replace(/_/g, " ")}</dt>
            <dd className="text-slate-700 dark:text-slate-300">{Array.isArray(val) ? val.join(", ") : String(val)}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
