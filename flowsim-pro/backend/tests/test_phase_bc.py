"""Tests for Phase B/C — choke wiring, BB flowline, tubing & flowline selection."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.catalog import FLOWLINE_CATALOG, TUBING_CATALOG, catalog_to_dict
from engine.fluid import FluidModel, FluidProperties
from engine.nodal import NodalAnalyzer
from engine.pipeline import PipelineGeometry, PipelineModel, PipelineSegment
from engine.selection import FlowlineSelector, TubingSelector, erosional_velocity_ft_s
from engine.solver import SimulationSolver
from engine.well import TubingSegment, WellGeometry, WellModel

SAMPLE_PATH = Path(__file__).parent.parent / "sample_data" / "deviated_well_example.json"


@pytest.fixture
def sample_case():
    with open(SAMPLE_PATH) as f:
        return json.load(f)


@pytest.fixture
def fluid():
    return FluidModel(FluidProperties(gor_scf_stb=800, water_cut=0.1, reservoir_temp_f=180))


@pytest.fixture
def well_geo():
    return WellGeometry(
        segments=[
            TubingSegment(
                md_top_ft=0,
                md_bottom_ft=8000,
                tvd_top_ft=0,
                tvd_bottom_ft=8000,
                inner_diameter_in=3.958,
            )
        ],
        choke_size_64_in=32,
        wellhead_pressure_psi=500,
    )


class TestChokeWiring:
    def test_choke_dp_increases_with_rate(self, fluid, well_geo):
        well = WellModel(fluid, well_geo, flow_correlation="beggs_brill")
        dp_low = well.choke_pressure_drop(500, 500)
        dp_high = well.choke_pressure_drop(3000, 500)
        assert dp_high > dp_low
        assert dp_low >= 0

    def test_smaller_bean_higher_dp(self, fluid, well_geo):
        well = WellModel(fluid, well_geo, flow_correlation="beggs_brill")
        well_geo.choke_size_64_in = 48
        dp_large = well.choke_pressure_drop(2000, 500)
        well_geo.choke_size_64_in = 16
        dp_small = well.choke_pressure_drop(2000, 500)
        assert dp_small > dp_large

    def test_choke_affects_vlp_bhp(self, fluid, well_geo):
        analyzer = NodalAnalyzer(fluid, well_geo, 3500, 2.0)
        well_geo.choke_size_64_in = 64
        bhp_open = analyzer.vlp_pressure(2000, 500)
        well_geo.choke_size_64_in = 12
        bhp_restricted = analyzer.vlp_pressure(2000, 500)
        assert bhp_restricted > bhp_open

    def test_choke_sensitivity_moves_operating_rate(self, fluid, well_geo):
        analyzer = NodalAnalyzer(fluid, well_geo, 3500, 2.0)
        result = analyzer.sensitivity("choke_size", [16, 48], include_vlp_curves=False)
        rates = [c.operating_rate_stb_d for c in result.curves]
        assert rates[1] > rates[0]  # larger choke → higher rate


class TestBeggsBrillFlowline:
    def test_flowline_uses_gas_velocity(self, fluid):
        geo = PipelineGeometry(
            segments=[
                PipelineSegment(length_ft=5000, inner_diameter_in=6.065, elevation_change_ft=50)
            ],
            inlet_pressure_psi=500,
            inlet_temperature_f=120,
            liquid_rate_stb_d=2000,
        )
        model = PipelineModel(fluid, geo, flow_correlation="beggs_brill")
        profile = model.traverse()
        assert len(profile) >= 2
        assert profile[0].pressure_psi > profile[-1].pressure_psi
        assert max(p.velocity_ft_s for p in profile) > 0

    def test_smaller_id_higher_dp(self, fluid):
        def dp_for(id_in: float) -> float:
            geo = PipelineGeometry(
                segments=[PipelineSegment(length_ft=2000, inner_diameter_in=id_in)],
                inlet_pressure_psi=1200,
                inlet_temperature_f=100,
                liquid_rate_stb_d=1500,
            )
            model = PipelineModel(fluid, geo, flow_correlation="beggs_brill")
            profile = model.traverse()
            # Ensure we didn't floor both cases at atmospheric
            assert profile[-1].pressure_psi > 14.7 + 1.0
            return model.total_pressure_drop()

        assert dp_for(3.068) > dp_for(6.065)


class TestCatalog:
    def test_catalog_not_empty(self):
        assert len(TUBING_CATALOG) >= 6
        assert len(FLOWLINE_CATALOG) >= 5
        d = catalog_to_dict()
        assert "tubing" in d and "flowline" in d

    def test_erosional_velocity(self):
        ve = erosional_velocity_ft_s(50.0, 100.0)
        assert abs(ve - 100.0 / (50.0**0.5)) < 1e-6


class TestTubingSelector:
    def test_ranks_candidates(self, fluid, well_geo):
        selector = TubingSelector(fluid, well_geo, 3500, 2.0, whp_psi=500)
        result = selector.evaluate()
        assert len(result.candidates) == len(TUBING_CATALOG)
        assert result.recommended_id_in is not None
        rates = [c.operating_rate_stb_d for c in result.candidates]
        # Larger IDs generally unlock higher rates among erosion-safe sizes
        assert max(rates) > min(rates)

    def test_to_dict(self, fluid, well_geo):
        result = TubingSelector(fluid, well_geo, 3500, 2.0).evaluate()
        d = TubingSelector.to_dict(result)
        assert d["recommended_label"]
        assert len(d["candidates"]) >= 1


class TestFlowlineSelector:
    def test_recommends_min_id(self, fluid):
        segs = [PipelineSegment(length_ft=10000, inner_diameter_in=6.065, elevation_change_ft=20)]
        selector = FlowlineSelector(
            fluid, segs, 500, 120, 2000, target_dp_psi=100.0
        )
        result = selector.evaluate()
        assert result.recommended_id_in is not None
        assert len(result.candidates) == len(FLOWLINE_CATALOG)
        # Recommended should meet target when possible
        rec = next(c for c in result.candidates if c.recommended)
        assert rec.inner_diameter_in == result.recommended_id_in

    def test_tighter_target_needs_larger_pipe(self, fluid):
        segs = [PipelineSegment(length_ft=15000, inner_diameter_in=4.026)]
        loose = FlowlineSelector(fluid, segs, 600, 100, 3000, target_dp_psi=200).evaluate()
        tight = FlowlineSelector(fluid, segs, 600, 100, 3000, target_dp_psi=20).evaluate()
        assert tight.recommended_id_in >= loose.recommended_id_in


class TestSolverPhaseBC:
    def test_sample_drawdown_is_pr_minus_bhp(self, sample_case):
        out = SimulationSolver(sample_case).solve()
        assert out.success
        pr = sample_case["nodal"]["reservoir_pressure_psi"]
        bhp = out.summary["bottomhole_pressure_psi"]
        assert abs(out.summary["drawdown_psi"] - (pr - bhp)) < 1.0
        assert "choke_dp_psi" in out.summary
        assert "Beggs-Brill" in out.assumptions["multiphase_flow"]

    def test_expected_bhp_range_updated(self, sample_case):
        out = SimulationSolver(sample_case).solve()
        bhp = out.summary["bottomhole_pressure_psi"]
        # With choke + BB, BHP should remain physically sensible
        assert 2000 < bhp < 5000
        assert out.summary["wellhead_pressure_psi"] < bhp
