export interface SimulationCase {
  id: number;
  name: string;
  description: string;
  case_type: string;
  inputs: CaseInputs;
  outputs: SimulationOutput | null;
  created_at: string;
  updated_at: string;
}

export interface CaseInputs {
  fluid: FluidInput;
  well: WellInput;
  flowline: FlowlineInput;
  nodal: NodalInput;
  network: Record<string, unknown>;
  heat_transfer: HeatTransferInput;
  boundary_conditions: BoundaryConditions;
}

export interface FluidInput {
  model_type: string;
  oil_api: number;
  gas_gravity: number;
  water_salinity_ppm: number;
  gor_scf_stb: number;
  water_cut: number;
  bubble_point_psi: number;
  reservoir_temp_f: number;
}

export interface WellInput {
  segments: TubingSegment[];
  packer_depth_ft: number;
  perforation_depth_ft: number;
  choke_size_64_in: number;
  wellhead_pressure_psi: number;
}

export interface TubingSegment {
  md_top_ft: number;
  md_bottom_ft: number;
  tvd_top_ft?: number;
  tvd_bottom_ft?: number;
  inner_diameter_in: number;
  roughness_ft: number;
  inclination_deg: number;
}

export interface FlowlineInput {
  segments: PipelineSegment[];
}

export interface PipelineSegment {
  length_ft: number;
  inner_diameter_in: number;
  roughness_ft: number;
  inclination_deg: number;
  elevation_change_ft: number;
  ambient_temp_f: number;
  u_btu_hr_ft2_f: number;
}

export interface NodalInput {
  reservoir_pressure_psi: number;
  productivity_index: number;
  ipr_model: string;
}

export interface HeatTransferInput {
  ambient_temp_f: number;
  overall_u_btu_hr_ft2_f: number;
  burial_depth_ft: number;
  insulation_thickness_in: number;
}

export interface BoundaryConditions {
  liquid_rate_stb_d: number;
  wellhead_pressure_psi: number;
  bottomhole_pressure_psi?: number | null;
}

export interface SimulationOutput {
  success: boolean;
  warnings: string[];
  assumptions: Record<string, string>;
  fluid_summary: Record<string, unknown>;
  well_profile: ProfilePoint[];
  flowline_profile: FlowlineProfilePoint[];
  nodal_analysis: NodalAnalysis | null;
  network_results: Record<string, unknown> | null;
  summary: Record<string, number>;
  diagnostics: string[];
}

export interface ProfilePoint {
  md_ft: number;
  tvd_ft: number;
  pressure_psi: number;
  temperature_f: number;
  holdup: number;
  dpdz_psi_ft: number;
}

export interface FlowlineProfilePoint {
  distance_ft: number;
  pressure_psi: number;
  temperature_f: number;
  holdup: number;
  velocity_ft_s: number;
}

export interface NodalAnalysis {
  rates_stb_d: number[];
  ipr_pressures_psi: number[];
  vlp_pressures_psi: number[];
  operating_rate_stb_d: number;
  operating_bhp_psi: number;
  operating_whp_psi: number;
  convergence_error_psi: number;
  status?: string;
  message?: string;
  aof_stb_d?: number;
}

export interface SensitivityCurve {
  parameter: string;
  value: number;
  label: string;
  rates_stb_d: number[];
  vlp_pressures_psi: number[];
  operating_rate_stb_d: number;
  operating_bhp_psi: number;
  status: string;
  message: string;
}

export interface SensitivityResult {
  parameter: string;
  ipr_rates_stb_d: number[];
  ipr_pressures_psi: number[];
  curves: SensitivityCurve[];
  diagnostics: string[];
}
