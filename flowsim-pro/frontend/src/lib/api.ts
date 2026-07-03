import type { CaseInputs, SimulationCase, SimulationOutput, SensitivityResult } from "./types";

const API_BASE = "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json();
}

export const api = {
  health: () => request<{ status: string }>("/health"),

  listCases: () => request<SimulationCase[]>("/cases"),

  getCase: (id: number) => request<SimulationCase>(`/cases/${id}`),

  createCase: (data: { name: string; description?: string; case_type?: string } & Partial<CaseInputs>) =>
    request<SimulationCase>("/cases", { method: "POST", body: JSON.stringify(data) }),

  updateCase: (id: number, data: Partial<{ name: string; description: string } & CaseInputs>) =>
    request<SimulationCase>(`/cases/${id}`, { method: "PUT", body: JSON.stringify(data) }),

  deleteCase: (id: number) => request<{ deleted: number }>(`/cases/${id}`, { method: "DELETE" }),

  duplicateCase: (id: number) => request<SimulationCase>(`/cases/${id}/duplicate`, { method: "POST" }),

  solveCase: (caseId?: number, inputs?: Record<string, unknown>) =>
    request<SimulationOutput>("/solve", {
      method: "POST",
      body: JSON.stringify(caseId ? { case_id: caseId } : { inputs }),
    }),

  compareCases: (caseIds: number[]) =>
    request<{ cases: Record<string, unknown>[] }>("/compare", {
      method: "POST",
      body: JSON.stringify({ case_ids: caseIds }),
    }),

  sensitivity: (caseId: number, parameter: string, values: number[]) =>
    request<SensitivityResult>("/sensitivity", {
      method: "POST",
      body: JSON.stringify({ case_id: caseId, parameter, values }),
    }),

  exportReport: async (caseId: number, format: "pdf" | "json" | "csv") => {
    const res = await fetch(`${API_BASE}/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ case_id: caseId, format }),
    });
    if (!res.ok) throw new Error(`Export failed: ${res.status}`);
    return res.blob();
  },

  downloadManual: async () => {
    const res = await fetch(`${API_BASE}/manual`);
    if (!res.ok) throw new Error(`Manual download failed: ${res.status}`);
    return res.blob();
  },
};

export const defaultInputs: CaseInputs = {
  fluid: {
    model_type: "black_oil",
    oil_api: 35,
    gas_gravity: 0.65,
    water_salinity_ppm: 50000,
    gor_scf_stb: 800,
    water_cut: 0.1,
    bubble_point_psi: 2500,
    reservoir_temp_f: 180,
  },
  well: {
    segments: [
      { md_top_ft: 0, md_bottom_ft: 8000, tvd_top_ft: 0, tvd_bottom_ft: 8000, inner_diameter_in: 3.958, roughness_ft: 0.00015, inclination_deg: 90 },
    ],
    packer_depth_ft: 7500,
    perforation_depth_ft: 8500,
    choke_size_64_in: 32,
    wellhead_pressure_psi: 500,
  },
  flowline: { segments: [] },
  nodal: { reservoir_pressure_psi: 3500, productivity_index: 2.0, ipr_model: "pi" },
  network: {},
  heat_transfer: { ambient_temp_f: 70, overall_u_btu_hr_ft2_f: 3.0, burial_depth_ft: 0, insulation_thickness_in: 0 },
  boundary_conditions: { liquid_rate_stb_d: 2000, wellhead_pressure_psi: 500, bottomhole_pressure_psi: null },
};
