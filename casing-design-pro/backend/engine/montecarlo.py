"""Monte Carlo probabilistic casing design."""

from __future__ import annotations

import copy
import math
import random
from typing import Any

from engine.analyzer import run_analysis


def randn() -> float:
    u1 = max(random.random(), 1e-12)
    u2 = random.random()
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


def perturb_profiles(profiles: list[dict], inp: dict) -> list[dict]:
    """Sample PP/FG/MW perturbations for one Monte Carlo trial."""
    pp_sigma = inp.get("ppUncertaintyPct", 5) / 100.0
    fg_sigma = inp.get("fgUncertaintyPct", 5) / 100.0
    mw_sigma = inp.get("mwUncertaintyPct", 2) / 100.0
    out = []
    for p in profiles:
        q = copy.deepcopy(p)
        q["pp"] = max(p["pp"] * (1 + randn() * pp_sigma), 0.1)
        q["fg"] = max(p["fg"] * (1 + randn() * fg_sigma), 0.1)
        q["mwInt"] = max(p.get("mwInt", p.get("mw_int", 8.6)) * (1 + randn() * mw_sigma), 0.1)
        q["mwExt"] = max(p.get("mwExt", p.get("mw_ext", 8.6)) * (1 + randn() * mw_sigma), 0.1)
        out.append(q)
    return out


def percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (k - f) * (sorted_vals[c] - sorted_vals[f])


def run_monte_carlo(payload: dict[str, Any], iterations: int = 500) -> dict[str, Any]:
    iterations = max(min(int(iterations), 5000), 50)
    inp = payload.get("inputs", {})
    state = payload.get("state", {})
    base_profiles = state.get("profiles", [])
    utils: list[float] = []
    failures = 0

    for _ in range(iterations):
        trial_state = copy.deepcopy(state)
        trial_state["profiles"] = perturb_profiles(base_profiles, inp)
        trial_inp = {**inp, "probDesignEnabled": False}
        result = run_analysis({"inputs": trial_inp, "state": trial_state, "scenarios": payload.get("scenarios")})
        u = result.get("max_util", 0)
        utils.append(u)
        if u >= 1.0:
            failures += 1

    utils.sort()
    return {
        "iterations": iterations,
        "p10": percentile(utils, 10),
        "p50": percentile(utils, 50),
        "p90": percentile(utils, 90),
        "p95": percentile(utils, 95),
        "mean": sum(utils) / len(utils) if utils else 0,
        "max": utils[-1] if utils else 0,
        "pass_probability": 1.0 - failures / iterations if iterations else 0,
        "failure_count": failures,
    }
