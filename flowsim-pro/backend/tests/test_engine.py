"""FlowSim Pro backend tests."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.fluid import FluidModel, FluidProperties
from engine.pipeline import PipelineGeometry, PipelineModel, PipelineSegment
from engine.solver import SimulationSolver
from engine.units import api_to_sg, pressure_to_psi, PressureUnit, validate_positive
from engine.well import TubingSegment, WellGeometry, WellModel


SAMPLE_PATH = Path(__file__).parent.parent / "sample_data" / "deviated_well_example.json"


class TestUnits:
    def test_api_to_sg(self):
        assert abs(api_to_sg(35) - 0.8498) < 0.01

    def test_pressure_conversion(self):
        assert abs(pressure_to_psi(1.0, PressureUnit.BAR) - 14.5038) < 0.1

    def test_validate_positive(self):
        with pytest.raises(ValueError):
            validate_positive(-1, "test")


class TestFluidModel:
    def test_black_oil_properties(self):
        props = FluidProperties(oil_api=35, gas_gravity=0.65, gor_scf_stb=800)
        model = FluidModel(props)
        rs = model.solution_gor(3000)
        assert rs > 0
        bo = model.oil_formation_volume_factor(3000, 180, rs)
        assert 1.0 < bo < 3.0
        state = model.mixture_properties(2000, 150, 1000)
        assert 0 < state.liquid_holdup < 1
        assert state.mixture_density_lb_ft3 > 0

    def test_water_cut_rates(self):
        props = FluidProperties(water_cut=0.2, gor_scf_stb=500)
        model = FluidModel(props)
        oil, gas, water = model.compute_rates(1000)
        assert abs(oil - 800) < 1
        assert abs(water - 200) < 1


class TestWellModel:
    def test_vertical_well_traverse(self):
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
            liquid_rate_stb_d=1500,
            wellhead_pressure_psi=500,
        )
        well = WellModel(fluid, geo)
        profile = well.traverse_top_down(whp_psi=500, liquid_rate=1500)
        assert len(profile) > 1
        assert profile[-1].pressure_psi > profile[0].pressure_psi

    def test_bhp_exceeds_whp(self):
        props = FluidProperties()
        fluid = FluidModel(props)
        geo = WellGeometry(
            segments=[
                TubingSegment(
                    md_top_ft=0, md_bottom_ft=5000,
                    tvd_top_ft=0, tvd_bottom_ft=5000,
                    inner_diameter_in=4.0,
                )
            ],
        )
        well = WellModel(fluid, geo)
        profile = well.traverse_top_down(whp_psi=400, liquid_rate=1000)
        assert profile[-1].pressure_psi > 400


class TestPipelineModel:
    def test_flowline_pressure_drop(self):
        props = FluidProperties()
        fluid = FluidModel(props)
        geo = PipelineGeometry(
            segments=[PipelineSegment(length_ft=10000, inner_diameter_in=6.0)],
            inlet_pressure_psi=500,
            liquid_rate_stb_d=2000,
        )
        pipe = PipelineModel(fluid, geo)
        dp = pipe.total_pressure_drop()
        assert dp > 0
        profile = pipe.traverse()
        assert profile[-1].pressure_psi < profile[0].pressure_psi


class TestSimulationSolver:
    @pytest.fixture
    def sample_case(self):
        with open(SAMPLE_PATH) as f:
            return json.load(f)

    def test_end_to_end_solve(self, sample_case):
        solver = SimulationSolver(sample_case)
        output = solver.solve()
        assert output.success
        assert len(output.well_profile) > 5
        assert output.summary["bottomhole_pressure_psi"] > output.summary["wellhead_pressure_psi"]

    def test_flowline_profile(self, sample_case):
        solver = SimulationSolver(sample_case)
        output = solver.solve()
        assert len(output.flowline_profile) > 1
        assert output.summary.get("flowline_pressure_drop_psi", 0) > 0

    def test_nodal_analysis(self, sample_case):
        solver = SimulationSolver(sample_case)
        output = solver.solve()
        assert output.nodal_analysis is not None
        assert output.nodal_analysis["operating_rate_stb_d"] > 0
        assert output.nodal_analysis["convergence_error_psi"] < 100

    def test_compare_cases(self, sample_case):
        solver = SimulationSolver(sample_case)
        out1 = solver.solve()
        out2 = solver.solve()
        comparison = SimulationSolver.compare_cases([
            {"summary": out1.summary},
            {"summary": out2.summary},
        ])
        assert len(comparison["cases"]) == 2
