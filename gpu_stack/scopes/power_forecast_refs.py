"""
The References shared by the forecast-aware power, thermal, and cost scope.

The scope turns the decisions a quantile forecaster feeds (plan power at a
chosen quantile, checkpoint early, shift flexible work) into equations with
units. Each decision rests on a published result, and each root input that a
forecaster will later supply points at the experiment that produces it. The
References are defined once here so the planning, thermal, checkpoint, and
time-shifting files cite the same sources and stay free of circular imports.

Two kinds of reference appear. Sources (papers, a textbook) justify the
equation. Model references say, in one sentence, what the equation assumes.
Root inputs that will come from a forecaster carry E003_INPUT_REF and no
default value anywhere in the scope.
"""

from ..core import Reference, var


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

GNEITING_RAFTERY_2007_REF = Reference(
    "Gneiting, T. and Raftery, A. E. (2007). Strictly Proper Scoring Rules, "
    "Prediction, and Estimation. Journal of the American Statistical "
    "Association 102(477), 359-378. A quantile forecast at level q is "
    "calibrated when the observation falls below it with probability q.",
    kind="paper",
    url="https://doi.org/10.1198/016214506000001437",
    year=2007,
    doi="10.1198/016214506000001437",
)

KOENKER_2005_REF = Reference(
    "Koenker, R. (2005). Quantile Regression. Cambridge University Press. "
    "The conditional q-quantile minimizes expected pinball (check) loss, so "
    "P(Y > quantile_q) = 1 - q under a correctly specified model.",
    kind="textbook",
    url="https://doi.org/10.1017/CBO9780511754098",
    year=2005,
    doi="10.1017/CBO9780511754098",
)

KOENKER_BASSETT_1978_REF = Reference(
    "Koenker, R. and Bassett, G. (1978). Regression Quantiles. Econometrica "
    "46(1), 33-50. Defines the quantile loss that quantile forecasters minimize.",
    kind="paper",
    url="https://doi.org/10.2307/1913643",
    year=1978,
    doi="10.2307/1913643",
)

FAN_WEBER_BARROSO_2007_REF = Reference(
    "Fan, X., Weber, W.-D., and Barroso, L. A. (2007). Power provisioning for "
    "a warehouse-sized computer. Proceedings of the 34th Annual International "
    "Symposium on Computer Architecture (ISCA), 13-23. Studies the gap "
    "between provisioned power capacity and the power a facility draws.",
    kind="paper",
    url="https://doi.org/10.1145/1250662.1250665",
    year=2007,
    doi="10.1145/1250662.1250665",
)

INCROPERA_LUMPED_REF = Reference(
    "Incropera, F. P., DeWitt, D. P., Bergman, T. L., and Lavine, A. S. "
    "Fundamentals of Heat and Mass Transfer (Wiley), chapter on transient "
    "conduction, lumped capacitance method: for a body with thermal "
    "resistance R and heat capacity C, theta(t) = theta_i * exp(-t / (R*C)), "
    "where theta is the temperature difference to the surroundings.",
    kind="textbook",
)

YOUNG_1974_REF = Reference(
    "Young, J. W. (1974). A first order approximation to the optimum "
    "checkpoint interval. Communications of the ACM 17(9), 530-531. A fault "
    "arriving at a uniformly random point of a checkpoint interval loses, on "
    "average, half an interval of work.",
    kind="paper",
    url="https://doi.org/10.1145/361147.361115",
    year=1974,
    doi="10.1145/361147.361115",
)

DALY_2006_REF = Reference(
    "Daly, J. T. (2006). A higher order estimate of the optimum checkpoint "
    "interval (title shortened). Future Generation Computer Systems 22(3), "
    "303-312. Extends Young's estimate to include checkpoint write time and "
    "restart time.",
    kind="paper",
    url="https://doi.org/10.1016/j.future.2004.11.016",
    year=2006,
    doi="10.1016/j.future.2004.11.016",
)

WIESNER_2021_REF = Reference(
    "Wiesner, P., Behnke, I., Scheinert, D., Gontarska, K., and Thamsen, L. "
    "(2021). Let's wait awhile: how temporal workload shifting can reduce "
    "carbon emissions in the cloud. Proceedings of the 22nd International "
    "Middleware Conference, 260-272. Shifting delay-tolerant work into "
    "lower-carbon hours changes the carbon intensity the work pays.",
    kind="paper",
    url="https://doi.org/10.1145/3464298.3493399",
    year=2021,
    doi="10.1145/3464298.3493399",
)

RADOVANOVIC_2021_REF = Reference(
    "Radovanovic, A. et al. (2021). Carbon-Aware Computing for Datacenters. "
    "arXiv:2106.11750. Shapes flexible datacenter load against day-ahead "
    "grid carbon-intensity forecasts.",
    kind="paper",
    url="https://arxiv.org/abs/2106.11750",
    year=2021,
)


# ---------------------------------------------------------------------------
# Where forecaster-supplied root inputs come from
# ---------------------------------------------------------------------------

E003_INPUT_REF = Reference(
    "gpu_stack experiments/e003-heatwave: the value of this input is produced "
    "by that experiment's quantile forecasts and replays. The scope sets no "
    "default; supply the value from the experiment's result file.",
    kind="memo",
)


# ---------------------------------------------------------------------------
# Model references: one sentence on what each group of equations assumes
# ---------------------------------------------------------------------------

QUANTILE_PLANNING_MODEL_REF = Reference(
    "Planning at quantile q sets planned site power to the forecast "
    "q-quantile; for a calibrated forecast the chance that power exceeds that "
    "plan is 1 - q, and headroom under the cap is the cap minus the plan.",
    kind="model",
)

OVERCAP_COST_MODEL_REF = Reference(
    "Expected over-cap energy is exceedance probability times mean overshoot "
    "power times the planning horizon; its penalty cost is that energy times "
    "an over-cap price.",
    kind="model",
)

STRANDED_POWER_MODEL_REF = Reference(
    "Stranded power is the provisioned cap minus the expected site power; "
    "cap utilization is expected power over the cap.",
    kind="model",
)

LUMPED_RC_MODEL_REF = Reference(
    "A single thermal node with resistance R to its coolant supply and heat "
    "capacity C, driven by constant heat power Q: time constant R*C, steady "
    "state at supply + Q*R, exponential approach between them.",
    kind="model",
)

EARLY_CHECKPOINT_MODEL_REF = Reference(
    "A fault with no warning loses about half a checkpoint interval of work "
    "on every affected GPU; a warning at least one checkpoint-write long lets "
    "the job checkpoint first, so about one write time of work is lost. The "
    "expected loss weights the two cases by forecast recall.",
    kind="model",
)

TIME_SHIFT_MODEL_REF = Reference(
    "A flexible fraction of the job's energy moves to hours with a different "
    "price and carbon intensity; the energy-weighted average paid is the "
    "convex combination of the unshifted and shifted values. Shifted work is "
    "assumed to use cluster hours that would otherwise sit idle, so "
    "non-energy cost per token is unchanged.",
    kind="model",
)


def forecast_var(name, symbol, units, description, references, **kwargs):
    """Declare a Variable in the power_forecast scope with its references."""
    return var(
        name, symbol, units, description,
        scope="power_forecast",
        references=references,
        **kwargs,
    )


__all__ = [
    "forecast_var",
    "GNEITING_RAFTERY_2007_REF",
    "KOENKER_2005_REF",
    "KOENKER_BASSETT_1978_REF",
    "FAN_WEBER_BARROSO_2007_REF",
    "INCROPERA_LUMPED_REF",
    "YOUNG_1974_REF",
    "DALY_2006_REF",
    "WIESNER_2021_REF",
    "RADOVANOVIC_2021_REF",
    "E003_INPUT_REF",
    "QUANTILE_PLANNING_MODEL_REF",
    "OVERCAP_COST_MODEL_REF",
    "STRANDED_POWER_MODEL_REF",
    "LUMPED_RC_MODEL_REF",
    "EARLY_CHECKPOINT_MODEL_REF",
    "TIME_SHIFT_MODEL_REF",
]
