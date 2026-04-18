"""
scopes/optimizer_first_order.py
===============================

First-order optimizer foundations.

This helper defines the shared gradient, parameter, learning-rate, and
optimizer-state memory handles used across every optimizer family, plus the
first-order methods themselves: SGD with momentum, Nesterov, AdamW with its
bias-corrected moments, RMSProp, LAMB, Lion, and the EMA of deployment
weights.
"""

import sympy as sp
from ..core import RelationRole, eq, var


# ---------------------------------------------------------------------------
# Shared optimizer state
# ---------------------------------------------------------------------------

g = var(
    "opt.grad", "g_opt", "grad",
    "Gradient at step t.",
    scope="optimizer",
    positive=False,
)
lr = var(
    "opt.lr", "eta_opt", "dimensionless",
    "Selected learning rate used by the optimizer update.",
    scope="optimizer",
)
wd = var(
    "opt.weight_decay", "lambda_wd_opt", "dimensionless",
    "Weight-decay coefficient.",
    scope="optimizer",
)
theta = var(
    "opt.param", "theta_opt", "param",
    "Parameter value at step t.",
    scope="optimizer",
    positive=False,
)
theta_next = var(
    "opt.param_next", "theta_next_opt", "param",
    "Parameter value at step t + 1 under the selected optimizer.",
    scope="optimizer",
    positive=False,
)
t_step = var(
    "opt.step_index", "t_opt", "step",
    "Optimizer step index, starting at one.",
    scope="optimizer",
    integer=True,
)


# ---------------------------------------------------------------------------
# Shared optimizer-state byte sizing
# ---------------------------------------------------------------------------

bytes_per_opt_param = var(
    "opt.bytes_per_param", "B_opt_state_opt", "byte/param",
    "Bytes per optimizer-state value.",
    scope="optimizer",
)


# ---------------------------------------------------------------------------
# AdamW
# ---------------------------------------------------------------------------

m = var(
    "opt.adam.m", "m_adam_opt", "moment",
    "AdamW first-moment estimate.",
    scope="optimizer",
    positive=False,
)
v_adam = var(
    "opt.adam.v", "v_adam_opt", "moment",
    "AdamW second-moment estimate.",
    scope="optimizer",
)
m_prev = var(
    "opt.adam.m_prev", "m_prev_adam_opt", "moment",
    "Previous AdamW first moment.",
    scope="optimizer",
    positive=False,
)
v_prev = var(
    "opt.adam.v_prev", "v_prev_adam_opt", "moment",
    "Previous AdamW second moment.",
    scope="optimizer",
)
beta1 = var(
    "opt.adam.beta1", "beta1_adam_opt", "dimensionless",
    "EMA coefficient for AdamW first moment.",
    scope="optimizer",
)
beta2 = var(
    "opt.adam.beta2", "beta2_adam_opt", "dimensionless",
    "EMA coefficient for AdamW second moment.",
    scope="optimizer",
)
eps_adam = var(
    "opt.adam.eps", "eps_adam_opt", "dimensionless",
    "Numerical stability epsilon in AdamW.",
    scope="optimizer",
)
m_hat = var(
    "opt.adam.m_hat", "mhat_adam_opt", "moment",
    "Bias-corrected AdamW first moment.",
    scope="optimizer",
    positive=False,
)
v_hat = var(
    "opt.adam.v_hat", "vhat_adam_opt", "moment",
    "Bias-corrected AdamW second moment.",
    scope="optimizer",
)


eq_adam_m = eq(
    "opt.eq.adam_m",
    m.symbol,
    beta1.symbol * m_prev.symbol + (1 - beta1.symbol) * g.symbol,
    "AdamW first-moment update.",
)

eq_adam_v = eq(
    "opt.eq.adam_v",
    v_adam.symbol,
    beta2.symbol * v_prev.symbol + (1 - beta2.symbol) * g.symbol ** 2,
    "AdamW second-moment update.",
)

eq_adam_m_hat = eq(
    "opt.eq.adam_m_hat",
    m_hat.symbol,
    m.symbol / (1 - beta1.symbol ** t_step.symbol),
    "Bias correction for the first moment.",
)

eq_adam_v_hat = eq(
    "opt.eq.adam_v_hat",
    v_hat.symbol,
    v_adam.symbol / (1 - beta2.symbol ** t_step.symbol),
    "Bias correction for the second moment.",
)

eq_adam_step = eq(
    "opt.eq.adam_step",
    theta_next.symbol,
    theta.symbol - lr.symbol * (m_hat.symbol / (sp.sqrt(v_hat.symbol) + eps_adam.symbol) + wd.symbol * theta.symbol),
    "AdamW subtracts the adaptive update and decoupled weight decay.",
    references=["Loshchilov and Hutter, Decoupled Weight Decay Regularization, ICLR 2019."],
    role=RelationRole.VARIANT,
    variant="adamw",
)


# ---------------------------------------------------------------------------
# SGD, Nesterov, RMSProp, LAMB, Lion
# ---------------------------------------------------------------------------

sgd_velocity_prev = var(
    "opt.sgd.velocity_prev", "v_prev_sgd_opt", "moment",
    "Previous SGD momentum buffer.",
    scope="optimizer",
    positive=False,
)
sgd_velocity = var(
    "opt.sgd.velocity", "v_sgd_opt", "moment",
    "Current SGD momentum buffer.",
    scope="optimizer",
    positive=False,
)
sgd_momentum_coeff = var(
    "opt.sgd.momentum", "mu_sgd_opt", "dimensionless",
    "Momentum coefficient for SGD.",
    scope="optimizer",
)
theta_next_sgd = var(
    "opt.sgd.theta_next", "theta_next_sgd_opt", "param",
    "Parameter after an SGD-with-momentum update.",
    scope="optimizer",
    positive=False,
)
theta_next_nesterov = var(
    "opt.sgd.theta_next_nesterov", "theta_next_nest_opt", "param",
    "Parameter after a Nesterov update.",
    scope="optimizer",
    positive=False,
)
rmsprop_avg_prev = var(
    "opt.rmsprop.avg_prev", "v_prev_rms_opt", "moment",
    "Previous RMSProp second-moment accumulator.",
    scope="optimizer",
)
rmsprop_avg = var(
    "opt.rmsprop.avg", "v_rms_opt", "moment",
    "Current RMSProp second-moment accumulator.",
    scope="optimizer",
)
beta_rms = var(
    "opt.rmsprop.beta", "beta_rms_opt", "dimensionless",
    "RMSProp averaging coefficient.",
    scope="optimizer",
)
eps_rms = var(
    "opt.rmsprop.eps", "eps_rms_opt", "dimensionless",
    "RMSProp denominator epsilon.",
    scope="optimizer",
)
theta_next_rms = var(
    "opt.rmsprop.theta_next", "theta_next_rms_opt", "param",
    "Parameter after an RMSProp update.",
    scope="optimizer",
    positive=False,
)
weight_norm = var(
    "opt.lamb.weight_norm", "n_w_lamb_opt", "value",
    "Layer weight norm used by LAMB.",
    scope="optimizer",
)
update_norm = var(
    "opt.lamb.update_norm", "n_u_lamb_opt", "value",
    "Norm of the Adam-like update inside LAMB.",
    scope="optimizer",
)
trust_ratio = var(
    "opt.lamb.trust_ratio", "r_trust_lamb_opt", "dimensionless",
    "LAMB trust ratio.",
    scope="optimizer",
)
theta_next_lamb = var(
    "opt.lamb.theta_next", "theta_next_lamb_opt", "param",
    "Parameter after a LAMB update.",
    scope="optimizer",
    positive=False,
)
lion_m_prev = var(
    "opt.lion.m_prev", "m_prev_lion_opt", "moment",
    "Previous Lion momentum-like buffer.",
    scope="optimizer",
    positive=False,
)
lion_m = var(
    "opt.lion.m", "m_lion_opt", "moment",
    "Current Lion momentum-like buffer.",
    scope="optimizer",
    positive=False,
)
lion_beta1 = var(
    "opt.lion.beta1", "beta1_lion_opt", "dimensionless",
    "Lion coefficient for the signed update direction.",
    scope="optimizer",
)
lion_beta2 = var(
    "opt.lion.beta2", "beta2_lion_opt", "dimensionless",
    "Lion coefficient for the momentum buffer update.",
    scope="optimizer",
)
lion_direction = var(
    "opt.lion.direction", "d_lion_opt", "dimensionless",
    "Signed Lion update direction.",
    scope="optimizer",
    positive=False,
)
theta_next_lion = var(
    "opt.lion.theta_next", "theta_next_lion_opt", "param",
    "Parameter after a Lion update.",
    scope="optimizer",
    positive=False,
)


eq_sgd_velocity = eq(
    "opt.eq.sgd_velocity",
    sgd_velocity.symbol,
    sgd_momentum_coeff.symbol * sgd_velocity_prev.symbol + g.symbol,
    "SGD with momentum updates its velocity buffer by adding the new gradient to the decayed previous buffer.",
)

eq_sgd_step = eq(
    "opt.eq.sgd_step",
    theta_next_sgd.symbol,
    theta.symbol - lr.symbol * sgd_velocity.symbol,
    "SGD with momentum subtracts the velocity buffer scaled by the learning rate.",
)

eq_nesterov_step = eq(
    "opt.eq.nesterov_step",
    theta_next_nesterov.symbol,
    theta.symbol - lr.symbol * (g.symbol + sgd_momentum_coeff.symbol * sgd_velocity.symbol),
    "Nesterov evaluates the gradient at a look-ahead point by adding a momentum correction to the immediate gradient.",
)

eq_rmsprop_avg = eq(
    "opt.eq.rmsprop_avg",
    rmsprop_avg.symbol,
    beta_rms.symbol * rmsprop_avg_prev.symbol + (1 - beta_rms.symbol) * g.symbol ** 2,
    "RMSProp tracks an EMA of squared gradients.",
)

eq_rmsprop_step = eq(
    "opt.eq.rmsprop_step",
    theta_next_rms.symbol,
    theta.symbol - lr.symbol * g.symbol / (sp.sqrt(rmsprop_avg.symbol) + eps_rms.symbol),
    "RMSProp rescales the gradient by the square root of its running second moment.",
)

eq_trust_ratio = eq(
    "opt.eq.lamb_trust_ratio",
    trust_ratio.symbol,
    weight_norm.symbol / update_norm.symbol,
    "LAMB uses the ratio of weight norm to update norm to set a layer-wise trust ratio.",
)

eq_lamb_step = eq(
    "opt.eq.lamb_step",
    theta_next_lamb.symbol,
    theta.symbol - lr.symbol * trust_ratio.symbol * (m_hat.symbol / (sp.sqrt(v_hat.symbol) + eps_adam.symbol) + wd.symbol * theta.symbol),
    "LAMB scales an Adam-like update by the layer-wise trust ratio.",
)

eq_lion_direction = eq(
    "opt.eq.lion_direction",
    lion_direction.symbol,
    sp.sign(lion_beta1.symbol * lion_m_prev.symbol + (1 - lion_beta1.symbol) * g.symbol),
    "Lion uses the sign of a momentum-filtered gradient as the update direction.",
)

eq_lion_m = eq(
    "opt.eq.lion_m",
    lion_m.symbol,
    lion_beta2.symbol * lion_m_prev.symbol + (1 - lion_beta2.symbol) * g.symbol,
    "Lion keeps a low-memory momentum-like buffer.",
)

eq_lion_step = eq(
    "opt.eq.lion_step",
    theta_next_lion.symbol,
    theta.symbol - lr.symbol * (lion_direction.symbol + wd.symbol * theta.symbol),
    "Lion subtracts the signed update direction and decoupled weight decay.",
)


# ---------------------------------------------------------------------------
# EMA
# ---------------------------------------------------------------------------

ema_decay = var(
    "opt.ema.decay", "beta_ema_opt", "dimensionless",
    "Exponential-moving-average decay for deployment weights.",
    scope="optimizer",
)
ema_prev = var(
    "opt.ema.prev", "theta_ema_prev_opt", "param",
    "Previous EMA weights.",
    scope="optimizer",
    positive=False,
)
ema_theta = var(
    "opt.ema.theta", "theta_ema_opt", "param",
    "Current EMA weights.",
    scope="optimizer",
    positive=False,
)


eq_ema_theta = eq(
    "opt.eq.ema_theta",
    ema_theta.symbol,
    ema_decay.symbol * ema_prev.symbol + (1 - ema_decay.symbol) * theta_next.symbol,
    "EMA weights blend the previous EMA with the latest parameter value.",
)


OPT_FIRST_ORDER_VARIABLES = [
    g, lr, wd, theta, theta_next, t_step,
    bytes_per_opt_param,
    m, v_adam, m_prev, v_prev, beta1, beta2, eps_adam, m_hat, v_hat,
    sgd_velocity_prev, sgd_velocity, sgd_momentum_coeff,
    theta_next_sgd, theta_next_nesterov,
    rmsprop_avg_prev, rmsprop_avg, beta_rms, eps_rms, theta_next_rms,
    weight_norm, update_norm, trust_ratio, theta_next_lamb,
    lion_m_prev, lion_m, lion_beta1, lion_beta2, lion_direction,
    theta_next_lion,
    ema_decay, ema_prev, ema_theta,
]

OPT_FIRST_ORDER_EQUATIONS = [
    eq_adam_m,
    eq_adam_v,
    eq_adam_m_hat,
    eq_adam_v_hat,
    eq_adam_step,
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
    eq_ema_theta,
]


__all__ = [
    "g", "lr", "wd", "theta", "theta_next", "t_step",
    "bytes_per_opt_param",
    "m", "v_adam", "m_prev", "v_prev", "beta1", "beta2", "eps_adam",
    "m_hat", "v_hat",
    "sgd_velocity_prev", "sgd_velocity", "sgd_momentum_coeff",
    "theta_next_sgd", "theta_next_nesterov",
    "rmsprop_avg_prev", "rmsprop_avg", "beta_rms", "eps_rms",
    "theta_next_rms",
    "weight_norm", "update_norm", "trust_ratio", "theta_next_lamb",
    "lion_m_prev", "lion_m", "lion_beta1", "lion_beta2",
    "lion_direction", "theta_next_lion",
    "ema_decay", "ema_prev", "ema_theta",
    "eq_adam_m", "eq_adam_v", "eq_adam_m_hat", "eq_adam_v_hat",
    "eq_adam_step",
    "eq_sgd_velocity", "eq_sgd_step", "eq_nesterov_step",
    "eq_rmsprop_avg", "eq_rmsprop_step",
    "eq_trust_ratio", "eq_lamb_step",
    "eq_lion_direction", "eq_lion_m", "eq_lion_step",
    "eq_ema_theta",
    "OPT_FIRST_ORDER_VARIABLES", "OPT_FIRST_ORDER_EQUATIONS",
]
