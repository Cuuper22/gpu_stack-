"""
scopes/power_forecast.py
========================

Aggregator for the forecast-aware power, thermal, and cost scope.

The scopes below this one describe a cluster as it is: its power, its cooling,
its cost. A probabilistic forecast of power, temperature, price, and carbon
adds a way to act before the numbers arrive, and this scope holds the
equations behind those actions so the calculator can reason about them with
units. Four groups, in dependency order: planning (plan site power at a
forecast quantile, packing under a power cap, expected over-cap energy and
penalty, stranded power), a lumped RC thermal model (time constant, steady
state, temperature after a time, time to throttle, cooling margin), early
checkpoints (expected GPU-hours saved per fault by a warning), and time
shifting (energy-weighted price and carbon paid, cost and carbon per token).

Quantities that a forecaster supplies are root inputs with no default. They
point at gpu_stack experiments/e003-heatwave, which produces them. This file
re-exports all of the helpers so public imports stay stable.
"""

from ..core import System

from .power_forecast_planning import *
from .power_forecast_planning import (
    POWER_FORECAST_PLANNING_EQUATIONS,
    POWER_FORECAST_PLANNING_VARIABLES,
)
from .power_forecast_rc import *
from .power_forecast_rc import (
    POWER_FORECAST_RC_EQUATIONS,
    POWER_FORECAST_RC_VARIABLES,
)
from .power_forecast_checkpoint import *
from .power_forecast_checkpoint import (
    POWER_FORECAST_CHECKPOINT_EQUATIONS,
    POWER_FORECAST_CHECKPOINT_VARIABLES,
)
from .power_forecast_shift import *
from .power_forecast_shift import (
    POWER_FORECAST_SHIFT_EQUATIONS,
    POWER_FORECAST_SHIFT_VARIABLES,
)


sys_power_forecast = System(
    name="power_forecast",
    scope="power_forecast",
    description="Forecast-quantile power planning, lumped RC thermal, early checkpoints, and time-shifted cost and carbon per token.",
)


POWER_FORECAST_VARIABLES = (
    POWER_FORECAST_PLANNING_VARIABLES
    + POWER_FORECAST_RC_VARIABLES
    + POWER_FORECAST_CHECKPOINT_VARIABLES
    + POWER_FORECAST_SHIFT_VARIABLES
)

POWER_FORECAST_EQUATIONS = (
    POWER_FORECAST_PLANNING_EQUATIONS
    + POWER_FORECAST_RC_EQUATIONS
    + POWER_FORECAST_CHECKPOINT_EQUATIONS
    + POWER_FORECAST_SHIFT_EQUATIONS
)

for v in POWER_FORECAST_VARIABLES:
    sys_power_forecast.add(v)

for e in POWER_FORECAST_EQUATIONS:
    sys_power_forecast.add(e)


__all__ = [
    *[name for name in globals() if not name.startswith("_")],
]
