"use client";

import type { SimulationOutput } from "@/lib/types";
import Chart from "./Chart";
import type { Data } from "plotly.js";

interface ProfileChartsProps {
  output: SimulationOutput | null;
}

export default function ProfileCharts({ output }: ProfileChartsProps) {
  if (!output) {
    return (
      <div className="panel p-8 flex items-center justify-center h-96 text-slate-500">
        Select a case and run simulation to view profiles
      </div>
    );
  }

  const wellData: Data[] = [
    {
      x: output.well_profile.map((p) => p.pressure_psi),
      y: output.well_profile.map((p) => p.md_ft),
      type: "scatter",
      mode: "lines",
      name: "Pressure",
      line: { color: "#2563eb", width: 2 },
    },
    {
      x: output.well_profile.map((p) => p.temperature_f),
      y: output.well_profile.map((p) => p.md_ft),
      type: "scatter",
      mode: "lines",
      name: "Temperature",
      line: { color: "#ef4444", width: 2 },
      xaxis: "x2",
    },
  ];

  const flowlineData: Data[] = output.flowline_profile.length > 0 ? [
    {
      x: output.flowline_profile.map((p) => p.distance_ft),
      y: output.flowline_profile.map((p) => p.pressure_psi),
      type: "scatter",
      mode: "lines",
      name: "Flowline P",
      line: { color: "#16a34a", width: 2 },
    },
  ] : [];

  const nodalData: Data[] = output.nodal_analysis ? [
    {
      x: output.nodal_analysis.rates_stb_d,
      y: output.nodal_analysis.ipr_pressures_psi,
      type: "scatter",
      mode: "lines",
      name: "IPR",
      line: { color: "#2563eb", width: 2 },
    },
    {
      x: output.nodal_analysis.rates_stb_d,
      y: output.nodal_analysis.vlp_pressures_psi,
      type: "scatter",
      mode: "lines",
      name: "VLP",
      line: { color: "#f59e0b", width: 2 },
    },
    {
      x: [output.nodal_analysis.operating_rate_stb_d],
      y: [output.nodal_analysis.operating_bhp_psi],
      type: "scatter",
      mode: "markers",
      name: "Operating Point",
      marker: { color: "#ef4444", size: 12, symbol: "circle" },
    },
  ] : [];

  return (
    <div className="space-y-4">
      <div className="panel p-4">
        <h3 className="font-semibold mb-2 text-sm">Well Pressure & Temperature vs MD</h3>
        <div className="h-80">
          <Chart
            data={wellData}
            layout={{
              xaxis: { title: "Pressure (psi)", side: "top", overlaying: "x" },
              xaxis2: { title: "Temperature (°F)", anchor: "y", side: "bottom" },
              yaxis: { title: "MD (ft)", autorange: "reversed" },
              showlegend: true,
              legend: { orientation: "h", y: 1.15 },
            }}
          />
        </div>
      </div>

      {flowlineData.length > 0 && (
        <div className="panel p-4">
          <h3 className="font-semibold mb-2 text-sm">Flowline Pressure Profile</h3>
          <div className="h-64">
            <Chart
              data={flowlineData}
              layout={{
                xaxis: { title: "Distance (ft)" },
                yaxis: { title: "Pressure (psi)" },
              }}
            />
          </div>
        </div>
      )}

      {nodalData.length > 0 && (
        <div className="panel p-4">
          <h3 className="font-semibold mb-2 text-sm">Nodal Analysis — IPR / VLP</h3>
          <div className="h-72">
            <Chart
              data={nodalData}
              layout={{
                xaxis: { title: "Liquid Rate (stb/d)" },
                yaxis: { title: "Bottomhole Pressure (psi)" },
                showlegend: true,
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
