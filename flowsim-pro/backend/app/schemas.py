"""Pydantic schemas for API request/response."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class FluidInput(BaseModel):
    model_type: str = "black_oil"
    oil_api: float = 35.0
    gas_gravity: float = 0.65
    water_salinity_ppm: float = 50000.0
    gor_scf_stb: float = 800.0
    water_cut: float = 0.10
    bubble_point_psi: float = 2500.0
    reservoir_temp_f: float = 180.0
    pvt_table: list[dict[str, float]] | None = None


class TubingSegmentInput(BaseModel):
    md_top_ft: float
    md_bottom_ft: float
    tvd_top_ft: float | None = None
    tvd_bottom_ft: float | None = None
    inner_diameter_in: float = 3.958
    roughness_ft: float = 0.00015
    inclination_deg: float = 90.0


class WellInput(BaseModel):
    segments: list[TubingSegmentInput] = []
    packer_depth_ft: float = 8000.0
    perforation_depth_ft: float = 8500.0
    choke_size_64_in: float = 32.0
    wellhead_pressure_psi: float = 500.0


class PipelineSegmentInput(BaseModel):
    length_ft: float
    inner_diameter_in: float = 6.0
    roughness_ft: float = 0.00015
    inclination_deg: float = 0.0
    elevation_change_ft: float = 0.0
    ambient_temp_f: float = 70.0
    u_btu_hr_ft2_f: float = 2.0


class FlowlineInput(BaseModel):
    segments: list[PipelineSegmentInput] = []


class NodalInput(BaseModel):
    reservoir_pressure_psi: float = 3500.0
    productivity_index: float = 2.0
    ipr_model: str = "pi"


class BoundaryConditions(BaseModel):
    liquid_rate_stb_d: float = 2000.0
    wellhead_pressure_psi: float = 500.0
    bottomhole_pressure_psi: float | None = None


class HeatTransferInput(BaseModel):
    ambient_temp_f: float = 70.0
    overall_u_btu_hr_ft2_f: float = 3.0
    burial_depth_ft: float = 0.0
    insulation_thickness_in: float = 0.0


class CaseCreate(BaseModel):
    name: str = "Untitled Case"
    description: str = ""
    case_type: str = "well_tubing_flowline"
    fluid: FluidInput = Field(default_factory=FluidInput)
    well: WellInput = Field(default_factory=WellInput)
    flowline: FlowlineInput = Field(default_factory=FlowlineInput)
    nodal: NodalInput = Field(default_factory=NodalInput)
    network: dict[str, Any] = Field(default_factory=dict)
    heat_transfer: HeatTransferInput = Field(default_factory=HeatTransferInput)
    boundary_conditions: BoundaryConditions = Field(default_factory=BoundaryConditions)


class CaseUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    case_type: str | None = None
    fluid: FluidInput | None = None
    well: WellInput | None = None
    flowline: FlowlineInput | None = None
    nodal: NodalInput | None = None
    network: dict[str, Any] | None = None
    heat_transfer: HeatTransferInput | None = None
    boundary_conditions: BoundaryConditions | None = None


class CaseResponse(BaseModel):
    id: int
    name: str
    description: str
    case_type: str
    inputs: dict[str, Any]
    outputs: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SolveRequest(BaseModel):
    case_id: int | None = None
    inputs: CaseCreate | None = None


class CompareRequest(BaseModel):
    case_ids: list[int]


class SensitivityRequest(BaseModel):
    case_id: int
    parameter: str
    values: list[float]


class ExportRequest(BaseModel):
    case_id: int
    format: str = "pdf"  # pdf | json | csv
