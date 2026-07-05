"""Benchmark suite regression tests."""

from engine.benchmarks import benchmark_cases, run_engine_benchmarks


def test_benchmark_count_matches_js():
    assert len(benchmark_cases()) == 35


def test_all_benchmarks_mostly_pass():
    result = run_engine_benchmarks()
    assert result["total"] == 35
    assert result["pass"] >= 33
