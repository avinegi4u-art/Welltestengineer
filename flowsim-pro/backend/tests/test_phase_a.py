"""Tests for Beggs-Brill correlation and Phase A nodal enhancements."""

import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.beggs_brill import flow_regime, segment_gradients, FlowRegime
from engine.fluid import FluidModel, FluidProperties
from engine.nodal import NodalAnalyzer
from engine.solver import SimulationSolver
from engine.well import TubingSegment, WellGeometry, WellModel

SAMPLE_PATH = Path(__file__).parent.parent / "sample_data" / "deviated_well_example.json"


class TestBeggsBrill:
    def test_flow_regime_segregated(self):
        regime = flow_regime(0.005, 0.1)
        assert regime == FlowRegime.SEGREGATED

    def test_segment_gradients_downward(self):
        bb = segment_gradients(
            diameter_ft=0.33,
            roughness_ft=0.00015,
            length_ft=1000,
            inclination_deg=90,
            superficial_liquid_ft_s=0.5,
            superficial_gas_ft_s=2.0,
            liquid_density_lb_ft3=45,
            gas_density_lb_ft3=2,
            liquid_viscosity_lb_ft_s=0.001,
            marching_downward=True,
        )
        assert 0 < bb.liquid_holdup <= 1
        assert bb.dpdz_total_psi_ft > 0  # BHP gain going down in vertical well

    def test_holdup_bounded(self):
        bb = segment_gradients(
            diameter_ft=0.5,
            roughness_ft=0.00015,
            length_ft=500,
            inclination_deg=45,
            superficial_liquid_ft_s=1.0,
            superficial_gas_ft_s=5.0,
            liquid_density_lb_ft3=50,
            gas_density_lb_ft3=1,
            liquid_viscosity_lb_ft_s=0.001,
            marching_downward=True,
        )
        assert bb.liquid_holdup >= 0.01


class TestNodalPhaseA:
    @pytest.fixture
    def analyzer(self):
        props = FluidProperties(gor_scf_stb=800, water_cut=0.1)
        fluid = FluidModel(props)
        geo = WellGeometry(
            segments=[
                TubingSegment(
                    md_top_ft=0, md_bottom_ft=8000,
                    tvd_top_ft=0, tvd_bottom_ft=8000,
                    inner_diameter_in=3.958,
                )
            ],
            wellhead_pressure_psi=500,
        )
        return NodalAnalyzer(fluid, geo, reservoir_pressure_psi=3500, productivity_index_stb_d_psi=2.0)

    def test_operating_point_status(self, analyzer):
        result = analyzer.solve_operating_point(whp_psi=500)
        assert result.status in (
            "operating_point_found",
            "rate_limited_by_vlp",
            "ipr_limited",
            "no_operating_point",
        )
        assert len(result.message) > 0

    def test_sensitivity_vlp_overlay(self, analyzer):
        sweep = analyzer.sensitivity("tubing_id", [2.992, 3.958, 4.67])
        assert len(sweep.curves) == 3
        assert len(sweep.ipr_rates_stb_d) > 0
        for curve in sweep.curves:
            assert len(curve.rates_stb_d) > 0
            assert len(curve.vlp_pressures_psi) > 0
            assert curve.label.startswith("ID")

    def test_sensitivity_to_dict(self, analyzer):
        sweep = analyzer.sensitivity("whp", [400, 500, 600])
        d = analyzer.sensitivity_to_dict(sweep)
        assert d["parameter"] == "whp"
        assert len(d["curves"]) == 3
        assert "diagnostics" in d


class TestBeggsBrillWellTraverse:
    def test_bhp_exceeds_whp_with_bb(self):
        props = FluidProperties()
        fluid = FluidModel(props)
        geo = WellGeometry(
            segments=[
                TubingSegment(
                    md_top_ft=0, md_bottom_ft=8000,
                    tvd_top_ft=0, tvd_bottom_ft=8000,
                    inner_diameter_in=3.958,
                )
            ],
        )
        well = WellModel(fluid, geo, flow_correlation="beggs_brill")
        profile = well.traverse_top_down(whp_psi=500, liquid_rate=1500)
        assert profile[-1].pressure_psi > profile[0].pressure_psi


class TestEndToEndPhaseA:
    @pytest.fixture
    def sample_case(self):
        with open(SAMPLE_PATH) as f:
            return json.load(f)

    def test_nodal_has_status_message(self, sample_case):
        solver = SimulationSolver(sample_case)
        output = solver.solve()
        assert output.nodal_analysis is not None
        assert "status" in output.nodal_analysis
        assert "message" in output.nodal_analysis

    def test_assumptions_beggs_brill(self, sample_case):
        solver = SimulationSolver(sample_case)
        output = solver.solve()
        assert "Beggs-Brill" in output.assumptions["multiphase_flow"]
