import pytest

from gpu_stack.presets import scenarios
from gpu_stack.research.backends import CompositeWorldModel, PredictionRequest
from gpu_stack.research.symbolic_backend import (
    SymbolicPredictionError,
    SymbolicResolverBackend,
)


def test_symbolic_backend_resolves_existing_full_tco_scenario():
    preset = scenarios.pythia_70m_dgx_h100_us_2024_industrial_full_tco_assumption
    backend = SymbolicResolverBackend(preset=preset)
    request = PredictionRequest(
        target="econ.cost.per_token",
        scenario_id=preset.name,
    )
    estimate = CompositeWorldModel((backend,)).predict(request)
    assert estimate.value > 0
    assert estimate.diagnostics["trace_steps"] > 0
    assert estimate.provenance


def test_symbolic_backend_rejects_open_frontier_instead_of_returning_symbolic_value():
    preset = scenarios.pythia_70m_dgx_h100_us_2024_industrial_power
    backend = SymbolicResolverBackend(preset=preset)
    with pytest.raises(SymbolicPredictionError, match="missing|unresolved"):
        backend.predict(
            PredictionRequest("econ.cost.per_token", preset.name)
        )


def test_symbolic_backend_does_not_pretend_to_support_interventions():
    backend = SymbolicResolverBackend(
        preset=scenarios.dense_training_cost_fixture
    )
    with pytest.raises(SymbolicPredictionError, match="temporal interventions"):
        backend.predict(
            PredictionRequest(
                "econ.cost.per_token",
                "fixture",
                intervention={"power_cap_w": 1000},
            )
        )
