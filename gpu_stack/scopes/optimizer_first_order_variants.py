"""
scopes/optimizer_first_order_variants.py
========================================

SGD, Nesterov, RMSProp, LAMB, and Lion declarations.
"""

import sympy as sp
from ..core import eq, var

from .optimizer_first_order_adamw import eps_adam, m_hat, v_hat
from .optimizer_first_order_common import (
    ADAM_REF,
    ADAMW_REF,
    DIMENSIONLESS,
    LAMB_REF,
    LION_REF,
    RMSPROP_REF,
    SGD_MOMENTUM_REF,
    g,
    lr,
    theta,
    wd,
)


sgd_velocity_prev = var(
    "opt.sgd.velocity_prev", "v_prev_sgd_opt", "moment",
    "Previous SGD momentum buffer.",
    scope="optimizer",
    positive=False,
    sp_units=DIMENSIONLESS,
    references=[SGD_MOMENTUM_REF],
)
sgd_velocity = var(
    "opt.sgd.velocity", "v_sgd_opt", "moment",
    "Current SGD momentum buffer.",
    scope="optimizer",
    positive=False,
    sp_units=DIMENSIONLESS,
    references=[SGD_MOMENTUM_REF],
)
sgd_momentum_coeff = var(
    "opt.sgd.momentum", "mu_sgd_opt", "dimensionless",
    "Momentum coefficient for SGD.",
    scope="optimizer",
    sp_units=DIMENSIONLESS,
    references=[SGD_MOMENTUM_REF],
)
theta_next_sgd = var(
    "opt.sgd.theta_next", "theta_next_sgd_opt", "param",
    "Parameter after an SGD-with-momentum update.",
    scope="optimizer",
    positive=False,
    sp_units=DIMENSIONLESS,
    references=[SGD_MOMENTUM_REF],
)
theta_next_nesterov = var(
    "opt.sgd.theta_next_nesterov", "theta_next_nest_opt", "param",
    "Parameter after a Nesterov update.",
    scope="optimizer",
    positive=False,
    sp_units=DIMENSIONLESS,
    references=[SGD_MOMENTUM_REF],
)
rmsprop_avg_prev = var(
    "opt.rmsprop.avg_prev", "v_prev_rms_opt", "moment",
    "Previous RMSProp second-moment accumulator.",
    scope="optimizer",
    sp_units=DIMENSIONLESS,
    references=[RMSPROP_REF],
)
rmsprop_avg = var(
    "opt.rmsprop.avg", "v_rms_opt", "moment",
    "Current RMSProp second-moment accumulator.",
    scope="optimizer",
    sp_units=DIMENSIONLESS,
    references=[RMSPROP_REF],
)
beta_rms = var(
    "opt.rmsprop.beta", "beta_rms_opt", "dimensionless",
    "RMSProp averaging coefficient.",
    scope="optimizer",
    sp_units=DIMENSIONLESS,
    references=[RMSPROP_REF],
)
eps_rms = var(
    "opt.rmsprop.eps", "eps_rms_opt", "dimensionless",
    "RMSProp denominator epsilon.",
    scope="optimizer",
    sp_units=DIMENSIONLESS,
    references=[RMSPROP_REF],
)
theta_next_rms = var(
    "opt.rmsprop.theta_next", "theta_next_rms_opt", "param",
    "Parameter after an RMSProp update.",
    scope="optimizer",
    positive=False,
    sp_units=DIMENSIONLESS,
    references=[RMSPROP_REF],
)
weight_norm = var(
    "opt.lamb.weight_norm", "n_w_lamb_opt", "value",
    "Layer weight norm used by LAMB.",
    scope="optimizer",
    sp_units=DIMENSIONLESS,
    references=[LAMB_REF],
)
update_norm = var(
    "opt.lamb.update_norm", "n_u_lamb_opt", "value",
    "Norm of the Adam-like update inside LAMB.",
    scope="optimizer",
    sp_units=DIMENSIONLESS,
    references=[LAMB_REF],
)
trust_ratio = var(
    "opt.lamb.trust_ratio", "r_trust_lamb_opt", "dimensionless",
    "LAMB trust ratio.",
    scope="optimizer",
    sp_units=DIMENSIONLESS,
    references=[LAMB_REF],
)
theta_next_lamb = var(
    "opt.lamb.theta_next", "theta_next_lamb_opt", "param",
    "Parameter after a LAMB update.",
    scope="optimizer",
    positive=False,
    sp_units=DIMENSIONLESS,
    references=[LAMB_REF],
)
lion_m_prev = var(
    "opt.lion.m_prev", "m_prev_lion_opt", "moment",
    "Previous Lion momentum-like buffer.",
    scope="optimizer",
    positive=False,
    sp_units=DIMENSIONLESS,
    references=[LION_REF],
)
lion_m = var(
    "opt.lion.m", "m_lion_opt", "moment",
    "Current Lion momentum-like buffer.",
    scope="optimizer",
    positive=False,
    sp_units=DIMENSIONLESS,
    references=[LION_REF],
)
lion_beta1 = var(
    "opt.lion.beta1", "beta1_lion_opt", "dimensionless",
    "Lion coefficient for the signed update direction.",
    scope="optimizer",
    sp_units=DIMENSIONLESS,
    references=[LION_REF],
)
lion_beta2 = var(
    "opt.lion.beta2", "beta2_lion_opt", "dimensionless",
    "Lion coefficient for the momentum buffer update.",
    scope="optimizer",
    sp_units=DIMENSIONLESS,
    references=[LION_REF],
)
lion_direction = var(
    "opt.lion.direction", "d_lion_opt", "dimensionless",
    "Signed Lion update direction.",
    scope="optimizer",
    positive=False,
    sp_units=DIMENSIONLESS,
    references=[LION_REF],
)
theta_next_lion = var(
    "opt.lion.theta_next", "theta_next_lion_opt", "param",
    "Parameter after a Lion update.",
    scope="optimizer",
    positive=False,
    sp_units=DIMENSIONLESS,
    references=[LION_REF],
)


eq_sgd_velocity = eq(
    "opt.eq.sgd_velocity",
    sgd_velocity.symbol,
    sgd_momentum_coeff.symbol * sgd_velocity_prev.symbol + g.symbol,
    "SGD with momentum updates its velocity buffer by adding the new gradient to the decayed previous buffer.",
    references=[SGD_MOMENTUM_REF],
    check_units=True,
)

eq_sgd_step = eq(
    "opt.eq.sgd_step",
    theta_next_sgd.symbol,
    theta.symbol - lr.symbol * sgd_velocity.symbol,
    "SGD with momentum subtracts the velocity buffer scaled by the learning rate.",
    references=[SGD_MOMENTUM_REF],
    check_units=True,
)

eq_nesterov_step = eq(
    "opt.eq.nesterov_step",
    theta_next_nesterov.symbol,
    theta.symbol - lr.symbol * (g.symbol + sgd_momentum_coeff.symbol * sgd_velocity.symbol),
    "Nesterov evaluates the gradient at a look-ahead point by adding a momentum correction to the immediate gradient.",
    references=[SGD_MOMENTUM_REF],
    check_units=True,
)

eq_rmsprop_avg = eq(
    "opt.eq.rmsprop_avg",
    rmsprop_avg.symbol,
    beta_rms.symbol * rmsprop_avg_prev.symbol + (1 - beta_rms.symbol) * g.symbol ** 2,
    "RMSProp tracks an EMA of squared gradients.",
    references=[RMSPROP_REF],
    check_units=True,
)

eq_rmsprop_step = eq(
    "opt.eq.rmsprop_step",
    theta_next_rms.symbol,
    theta.symbol - lr.symbol * g.symbol / (sp.sqrt(rmsprop_avg.symbol) + eps_rms.symbol),
    "RMSProp rescales the gradient by the square root of its running second moment.",
    references=[RMSPROP_REF],
    check_units=True,
)

eq_trust_ratio = eq(
    "opt.eq.lamb_trust_ratio",
    trust_ratio.symbol,
    weight_norm.symbol / update_norm.symbol,
    "LAMB uses the ratio of weight norm to update norm to set a layer-wise trust ratio.",
    references=[LAMB_REF],
    check_units=True,
)

eq_lamb_step = eq(
    "opt.eq.lamb_step",
    theta_next_lamb.symbol,
    theta.symbol - lr.symbol * trust_ratio.symbol * (m_hat.symbol / (sp.sqrt(v_hat.symbol) + eps_adam.symbol) + wd.symbol * theta.symbol),
    "LAMB scales an Adam-like update by the layer-wise trust ratio.",
    references=[ADAM_REF, ADAMW_REF, LAMB_REF],
    check_units=True,
)

eq_lion_direction = eq(
    "opt.eq.lion_direction",
    lion_direction.symbol,
    sp.sign(lion_beta1.symbol * lion_m_prev.symbol + (1 - lion_beta1.symbol) * g.symbol),
    "Lion uses the sign of a momentum-filtered gradient as the update direction.",
    references=[LION_REF],
    check_units=True,
)

eq_lion_m = eq(
    "opt.eq.lion_m",
    lion_m.symbol,
    lion_beta2.symbol * lion_m_prev.symbol + (1 - lion_beta2.symbol) * g.symbol,
    "Lion keeps a low-memory momentum-like buffer.",
    references=[LION_REF],
    check_units=True,
)

eq_lion_step = eq(
    "opt.eq.lion_step",
    theta_next_lion.symbol,
    theta.symbol - lr.symbol * (lion_direction.symbol + wd.symbol * theta.symbol),
    "Lion subtracts the signed update direction and decoupled weight decay.",
    references=[LION_REF, ADAMW_REF],
    check_units=True,
)


OPT_FIRST_ORDER_VARIANT_VARIABLES = [
    sgd_velocity_prev, sgd_velocity, sgd_momentum_coeff,
    theta_next_sgd, theta_next_nesterov,
    rmsprop_avg_prev, rmsprop_avg, beta_rms, eps_rms, theta_next_rms,
    weight_norm, update_norm, trust_ratio, theta_next_lamb,
    lion_m_prev, lion_m, lion_beta1, lion_beta2, lion_direction,
    theta_next_lion,
]

OPT_FIRST_ORDER_VARIANT_EQUATIONS = [
    eq_sgd_velocity,
    eq_sgd_step,
    eq_nesterov_step,
    eq_rmsprop_avg,
    eq_rmsprop_step,
    eq_trust_ratio,
    eq_lamb_step,
    eq_lion_direction,
    eq_lion_m,
    eq_lion_step,
]


__all__ = [
    "sgd_velocity_prev", "sgd_velocity", "sgd_momentum_coeff",
    "theta_next_sgd", "theta_next_nesterov",
    "rmsprop_avg_prev", "rmsprop_avg", "beta_rms", "eps_rms",
    "theta_next_rms",
    "weight_norm", "update_norm", "trust_ratio", "theta_next_lamb",
    "lion_m_prev", "lion_m", "lion_beta1", "lion_beta2",
    "lion_direction", "theta_next_lion",
    "eq_sgd_velocity", "eq_sgd_step", "eq_nesterov_step",
    "eq_rmsprop_avg", "eq_rmsprop_step",
    "eq_trust_ratio", "eq_lamb_step",
    "eq_lion_direction", "eq_lion_m", "eq_lion_step",
    "OPT_FIRST_ORDER_VARIANT_VARIABLES", "OPT_FIRST_ORDER_VARIANT_EQUATIONS",
]
