"use client";

import type { CaseInputs } from "@/lib/types";

interface InputFormProps {
  inputs: CaseInputs;
  onChange: (inputs: CaseInputs) => void;
  activeTab: string;
  onTabChange: (tab: string) => void;
}

const TABS = ["Fluid", "Well", "Flowline", "Boundary", "Nodal", "Heat Transfer"];

export default function InputForm({ inputs, onChange, activeTab, onTabChange }: InputFormProps) {
  const updateFluid = (field: string, value: number | string) => {
    onChange({ ...inputs, fluid: { ...inputs.fluid, [field]: value } });
  };

  const updateBoundary = (field: string, value: number) => {
    onChange({ ...inputs, boundary_conditions: { ...inputs.boundary_conditions, [field]: value } });
  };

  const updateNodal = (field: string, value: number | string) => {
    onChange({ ...inputs, nodal: { ...inputs.nodal, [field]: value } });
  };

  const updateHeat = (field: string, value: number) => {
    onChange({ ...inputs, heat_transfer: { ...inputs.heat_transfer, [field]: value } });
  };

  const updateWellField = (field: string, value: number) => {
    onChange({ ...inputs, well: { ...inputs.well, [field]: value } });
  };

  const updateSegment = (index: number, field: string, value: number) => {
    const segments = [...inputs.well.segments];
    segments[index] = { ...segments[index], [field]: value };
    onChange({ ...inputs, well: { ...inputs.well, segments } });
  };

  const addSegment = () => {
    const last = inputs.well.segments[inputs.well.segments.length - 1];
    const newSeg = {
      md_top_ft: last?.md_bottom_ft ?? 0,
      md_bottom_ft: (last?.md_bottom_ft ?? 0) + 2000,
      tvd_top_ft: last?.tvd_bottom_ft ?? 0,
      tvd_bottom_ft: (last?.tvd_bottom_ft ?? 0) + 2000,
      inner_diameter_in: 3.958,
      roughness_ft: 0.00015,
      inclination_deg: 90,
    };
    onChange({ ...inputs, well: { ...inputs.well, segments: [...inputs.well.segments, newSeg] } });
  };

  const removeSegment = (index: number) => {
    if (inputs.well.segments.length <= 1) return;
    const segments = inputs.well.segments.filter((_, i) => i !== index);
    onChange({ ...inputs, well: { ...inputs.well, segments } });
  };

  const updateFlowlineSegment = (index: number, field: string, value: number) => {
    const segments = [...inputs.flowline.segments];
    segments[index] = { ...segments[index], [field]: value };
    onChange({ ...inputs, flowline: { ...inputs.flowline, segments } });
  };

  const addFlowlineSegment = () => {
    const newSeg = {
      length_ft: 5000,
      inner_diameter_in: 6.065,
      roughness_ft: 0.00018,
      inclination_deg: 0,
      elevation_change_ft: 0,
      ambient_temp_f: 70,
      u_btu_hr_ft2_f: 2.0,
    };
    onChange({ ...inputs, flowline: { ...inputs.flowline, segments: [...inputs.flowline.segments, newSeg] } });
  };

  const removeFlowlineSegment = (index: number) => {
    const segments = inputs.flowline.segments.filter((_, i) => i !== index);
    onChange({ ...inputs, flowline: { segments } });
  };

  return (
    <div className="panel p-3 h-full flex flex-col">
      <div className="flex gap-1 mb-3 flex-wrap">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => onTabChange(tab)}
            className={`px-2 py-1 text-xs rounded ${
              activeTab === tab ? "bg-primary text-white" : "hover:bg-slate-100 dark:hover:bg-slate-700"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto text-sm space-y-3">
        {activeTab === "Fluid" && (
          <>
            <Field label="Oil API" value={inputs.fluid.oil_api} onChange={(v) => updateFluid("oil_api", v)} />
            <Field label="Gas Gravity" value={inputs.fluid.gas_gravity} onChange={(v) => updateFluid("gas_gravity", v)} step={0.01} />
            <Field label="GOR (scf/stb)" value={inputs.fluid.gor_scf_stb} onChange={(v) => updateFluid("gor_scf_stb", v)} />
            <Field label="Water Cut" value={inputs.fluid.water_cut} onChange={(v) => updateFluid("water_cut", v)} step={0.01} />
            <Field label="Bubble Point (psi)" value={inputs.fluid.bubble_point_psi} onChange={(v) => updateFluid("bubble_point_psi", v)} />
            <Field label="Reservoir Temp (°F)" value={inputs.fluid.reservoir_temp_f} onChange={(v) => updateFluid("reservoir_temp_f", v)} />
            <Field label="Water Salinity (ppm)" value={inputs.fluid.water_salinity_ppm} onChange={(v) => updateFluid("water_salinity_ppm", v)} />
          </>
        )}

        {activeTab === "Well" && (
          <>
            <Field label="Packer Depth (ft)" value={inputs.well.packer_depth_ft} onChange={(v) => updateWellField("packer_depth_ft", v)} />
            <Field label="Perforation Depth (ft)" value={inputs.well.perforation_depth_ft} onChange={(v) => updateWellField("perforation_depth_ft", v)} />
            <Field label="Choke (64ths in)" value={inputs.well.choke_size_64_in} onChange={(v) => updateWellField("choke_size_64_in", v)} />
            <div className="mt-3">
              <div className="flex justify-between items-center mb-2">
                <span className="font-medium text-xs">Tubing Segments</span>
                <button onClick={addSegment} className="text-xs text-primary">+ Add</button>
              </div>
              {inputs.well.segments.map((seg, i) => (
                <div key={i} className="border border-border-light dark:border-border-dark rounded p-2 mb-2">
                  <div className="flex justify-between items-center mb-1">
                    <p className="text-xs font-medium">Segment {i + 1}</p>
                    {inputs.well.segments.length > 1 && (
                      <button onClick={() => removeSegment(i)} className="text-[10px] text-red-500">Remove</button>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <MiniField label="MD Top" value={seg.md_top_ft} onChange={(v) => updateSegment(i, "md_top_ft", v)} />
                    <MiniField label="MD Bot" value={seg.md_bottom_ft} onChange={(v) => updateSegment(i, "md_bottom_ft", v)} />
                    <MiniField label="TVD Top" value={seg.tvd_top_ft ?? seg.md_top_ft} onChange={(v) => updateSegment(i, "tvd_top_ft", v)} />
                    <MiniField label="TVD Bot" value={seg.tvd_bottom_ft ?? seg.md_bottom_ft} onChange={(v) => updateSegment(i, "tvd_bottom_ft", v)} />
                    <MiniField label="ID (in)" value={seg.inner_diameter_in} onChange={(v) => updateSegment(i, "inner_diameter_in", v)} step={0.001} />
                    <MiniField label="Inc (°)" value={seg.inclination_deg} onChange={(v) => updateSegment(i, "inclination_deg", v)} />
                    <MiniField label="Rough (ft)" value={seg.roughness_ft} onChange={(v) => updateSegment(i, "roughness_ft", v)} step={0.00001} />
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {activeTab === "Flowline" && (
          <>
            <div className="flex justify-between items-center mb-2">
              <span className="font-medium text-xs">Pipeline Segments</span>
              <button onClick={addFlowlineSegment} className="text-xs text-primary">+ Add</button>
            </div>
            {inputs.flowline.segments.map((seg, i) => (
              <div key={i} className="border border-border-light dark:border-border-dark rounded p-2 mb-2">
                <div className="flex justify-between items-center mb-1">
                  <p className="text-xs font-medium">Segment {i + 1}</p>
                  <button onClick={() => removeFlowlineSegment(i)} className="text-[10px] text-red-500">Remove</button>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <MiniField label="Length (ft)" value={seg.length_ft} onChange={(v) => updateFlowlineSegment(i, "length_ft", v)} />
                  <MiniField label="ID (in)" value={seg.inner_diameter_in} onChange={(v) => updateFlowlineSegment(i, "inner_diameter_in", v)} step={0.001} />
                  <MiniField label="Elev Δ (ft)" value={seg.elevation_change_ft} onChange={(v) => updateFlowlineSegment(i, "elevation_change_ft", v)} />
                  <MiniField label="Inc (°)" value={seg.inclination_deg} onChange={(v) => updateFlowlineSegment(i, "inclination_deg", v)} />
                  <MiniField label="Ambient (°F)" value={seg.ambient_temp_f} onChange={(v) => updateFlowlineSegment(i, "ambient_temp_f", v)} />
                  <MiniField label="U" value={seg.u_btu_hr_ft2_f} onChange={(v) => updateFlowlineSegment(i, "u_btu_hr_ft2_f", v)} step={0.1} />
                  <MiniField label="Rough (ft)" value={seg.roughness_ft} onChange={(v) => updateFlowlineSegment(i, "roughness_ft", v)} step={0.00001} />
                </div>
              </div>
            ))}
            {inputs.flowline.segments.length === 0 && (
              <p className="text-xs text-slate-500">No flowline segments. Add segments to model surface lines.</p>
            )}
          </>
        )}

        {activeTab === "Boundary" && (
          <>
            <Field label="Liquid Rate (stb/d)" value={inputs.boundary_conditions.liquid_rate_stb_d} onChange={(v) => updateBoundary("liquid_rate_stb_d", v)} />
            <Field label="WHP (psi)" value={inputs.boundary_conditions.wellhead_pressure_psi} onChange={(v) => updateBoundary("wellhead_pressure_psi", v)} />
            <Field label="BHP (psi, optional)" value={inputs.boundary_conditions.bottomhole_pressure_psi ?? 0} onChange={(v) => updateBoundary("bottomhole_pressure_psi", v || 0)} />
          </>
        )}

        {activeTab === "Nodal" && (
          <>
            <Field label="Reservoir Pressure (psi)" value={inputs.nodal.reservoir_pressure_psi} onChange={(v) => updateNodal("reservoir_pressure_psi", v)} />
            <Field label="Productivity Index" value={inputs.nodal.productivity_index} onChange={(v) => updateNodal("productivity_index", v)} step={0.1} />
            <div>
              <label className="text-xs text-slate-500">IPR Model</label>
              <select
                className="input-field mt-0.5"
                value={inputs.nodal.ipr_model}
                onChange={(e) => updateNodal("ipr_model", e.target.value)}
              >
                <option value="pi">Linear PI</option>
                <option value="vogel">Vogel</option>
              </select>
            </div>
          </>
        )}

        {activeTab === "Heat Transfer" && (
          <>
            <Field label="Ambient Temp (°F)" value={inputs.heat_transfer.ambient_temp_f} onChange={(v) => updateHeat("ambient_temp_f", v)} />
            <Field label="U (Btu/hr·ft²·°F)" value={inputs.heat_transfer.overall_u_btu_hr_ft2_f} onChange={(v) => updateHeat("overall_u_btu_hr_ft2_f", v)} step={0.1} />
            <Field label="Burial Depth (ft)" value={inputs.heat_transfer.burial_depth_ft} onChange={(v) => updateHeat("burial_depth_ft", v)} />
            <Field label="Insulation (in)" value={inputs.heat_transfer.insulation_thickness_in} onChange={(v) => updateHeat("insulation_thickness_in", v)} step={0.1} />
          </>
        )}
      </div>
    </div>
  );
}

function Field({ label, value, onChange, step = 1 }: { label: string; value: number; onChange: (v: number) => void; step?: number }) {
  return (
    <div>
      <label className="text-xs text-slate-500">{label}</label>
      <input
        type="number"
        step={step}
        className="input-field mt-0.5"
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
      />
    </div>
  );
}

function MiniField({ label, value, onChange, step = 1 }: { label: string; value: number; onChange: (v: number) => void; step?: number }) {
  return (
    <div>
      <label className="text-[10px] text-slate-500">{label}</label>
      <input
        type="number"
        step={step}
        className="input-field mt-0.5 text-xs py-1"
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
      />
    </div>
  );
}
