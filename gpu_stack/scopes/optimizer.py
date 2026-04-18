"""
scopes/optimizer.py
===================

Optimizers, learning-rate schedules, loss scaling, EMA, and optimizer-state
memory.

The old file had AdamW, a fake Muon placeholder, and gradient clipping. This
version adds a real iterative Newton-Schulz map, standard optimizer families,
schedule formulas, and the low-precision loss-scaling logic that the earlier
pass had left stranded in prose.
"""

import sympy as sp
from ..core import IterativeEquation, PiecewiseEquation, System, eq, var
from .parallelism import n_params


sys_opt = System(
    name="optimizer",
    scope="optimizer",
    description="AdamW, Muon, SGD-family optimizers, schedules, EMA, and optimizer-state memory.",
)


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
)


# ---------------------------------------------------------------------------
# Muon and Newton-Schulz orthogonalization
# ---------------------------------------------------------------------------

X_ns = var(
    "opt.muon.X", "X_muon_opt", "matrix",
    "Orthogonalized Muon update after Newton-Schulz iteration.",
    scope="optimizer",
)
ns_coeffs = var(
    "opt.muon.ns_coeffs", "c_ns_opt", "triple",
    "Opaque convenience handle for the Newton-Schulz coefficient triple. Retained for compatibility.",
    scope="optimizer",
)
ns_coeff_a = var(
    "opt.muon.ns_coeff_a", "a_ns_opt", "dimensionless",
    "Linear coefficient in the Newton-Schulz polynomial map.",
    scope="optimizer",
)
ns_coeff_b = var(
    "opt.muon.ns_coeff_b", "b_ns_opt", "dimensionless",
    "Cubic coefficient in the Newton-Schulz polynomial map.",
    scope="optimizer",
    positive=False,
)
ns_coeff_c = var(
    "opt.muon.ns_coeff_c", "c_ns_poly_opt", "dimensionless",
    "Quintic coefficient in the Newton-Schulz polynomial map.",
    scope="optimizer",
)
ns_iterations = var(
    "opt.muon.ns_iterations", "N_ns_iter_opt", "iterations",
    "Iteration count used by the Muon Newton-Schulz inner loop.",
    scope="optimizer",
    integer=True,
)
ns_input = var(
    "opt.muon.ns_input", "X_ns_in_opt", "matrix",
    "Input matrix to the Newton-Schulz orthogonalization map.",
    scope="optimizer",
)
ns_residual = var(
    "opt.muon.ns_residual", "r_ns_opt", "dimensionless",
    "Residual measuring how close X^T X is to identity after orthogonalization.",
    scope="optimizer",
)
ns_tol = var(
    "opt.muon.ns_tol", "eps_ns_opt", "dimensionless",
    "Tolerance for the Newton-Schulz residual.",
    scope="optimizer",
)
muon_beta = var(
    "opt.muon.beta", "beta_muon_opt", "dimensionless",
    "Muon momentum coefficient.",
    scope="optimizer",
)
muon_momentum_prev = var(
    "opt.muon.m_prev", "m_prev_muon_opt", "moment",
    "Previous Muon momentum.",
    scope="optimizer",
    positive=False,
)
muon_momentum = var(
    "opt.muon.m", "m_muon_opt", "moment",
    "Current Muon momentum.",
    scope="optimizer",
    positive=False,
)
muon_update = var(
    "opt.muon.update", "u_muon_opt", "moment",
    "Muon update after orthogonalization.",
    scope="optimizer",
    positive=False,
)


eq_muon_momentum = eq(
    "opt.eq.muon_momentum",
    muon_momentum.symbol,
    muon_beta.symbol * muon_momentum_prev.symbol + (1 - muon_beta.symbol) * g.symbol,
    "Muon keeps only a first-moment momentum tensor.",
)

eq_ns_iterations_default = eq(
    "opt.eq.muon_ns_iterations_default",
    ns_iterations.symbol,
    5,
    "A common Muon configuration uses five Newton-Schulz iterations.",
)

eq_ns_input = eq(
    "opt.eq.muon_ns_input",
    ns_input.symbol,
    muon_momentum.symbol,
    "The Newton-Schulz inner loop starts from the current Muon momentum tensor.",
)
_ns_iter = sp.Symbol("X_iter_ns_opt")
_T = sp.Function("Transpose")
_F = sp.Function("FroNorm")
ns_iteration_map = (
    ns_coeff_a.symbol * _ns_iter
    + ns_coeff_b.symbol * _ns_iter * _T(_ns_iter) * _ns_iter
    + ns_coeff_c.symbol * _ns_iter * (_T(_ns_iter) * _ns_iter) ** 2
)
eq_ns_iteration = IterativeEquation(
    "opt.eq.muon_ns_iteration",
    X_ns.symbol,
    ns_iteration_map,
    iteration_variable=_ns_iter,
    initial=ns_input.symbol,
    n_iter=5,
    convergence=sp.Symbol("r_ns_opt") <= ns_tol.symbol,
    description="Muon applies a Newton-Schulz polynomial iteration to approximate the orthogonal factor of the momentum tensor without an explicit SVD.",
    references=["Jordan et al., Muon, 2024."],
)

eq_ns_residual = eq(
    "opt.eq.muon_ns_residual",
    ns_residual.symbol,
    _F(_T(X_ns.symbol) * X_ns.symbol - sp.Symbol("I_ns_opt")),
    "A standard orthogonalization residual is the Frobenius norm of X^T X minus the identity.",
)

eq_muon_update = eq(
    "opt.eq.muon_update",
    muon_update.symbol,
    X_ns.symbol,
    "Muon uses the orthogonalized Newton-Schulz output as the update direction.",
)

eq_muon_step = eq(
    "opt.eq.muon_step",
    theta_next.symbol,
    theta.symbol - lr.symbol * muon_update.symbol,
    "Muon subtracts the orthogonalized momentum scaled by the learning rate.",
)


# ---------------------------------------------------------------------------
# MuonClip and gradient clipping
# ---------------------------------------------------------------------------

max_logit = var(
    "opt.muonclip.max_logit", "L_max_opt", "value",
    "Maximum observed attention-logit magnitude from the previous step.",
    scope="optimizer",
)
clip_threshold = var(
    "opt.muonclip.threshold", "tau_clip_opt", "value",
    "Target upper bound on attention logits.",
    scope="optimizer",
)
clip_factor = var(
    "opt.muonclip.factor", "alpha_qk_opt", "dimensionless",
    "Rescaling factor applied to Q and K projections.",
    scope="optimizer",
)
g_norm = var(
    "opt.grad_norm", "g_norm_opt", "grad",
    "Global gradient norm.",
    scope="optimizer",
)
clip_norm = var(
    "opt.clip_norm", "g_clip_opt", "grad",
    "Gradient-clipping threshold.",
    scope="optimizer",
)
g_clipped = var(
    "opt.grad_clipped", "g_clipped_opt", "grad",
    "Gradient after global-norm clipping.",
    scope="optimizer",
    positive=False,
)


eq_muonclip_factor = eq(
    "opt.eq.muonclip_factor",
    clip_factor.symbol,
    sp.Min(1, clip_threshold.symbol / max_logit.symbol),
    "QK-Clip rescales Q and K by min(1, threshold / observed_max_logit).",
)

eq_grad_clip = eq(
    "opt.eq.grad_clip",
    g_clipped.symbol,
    g.symbol * sp.Min(1, clip_norm.symbol / g_norm.symbol),
    "Global-norm clipping rescales the gradient when its norm exceeds the threshold.",
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
# Learning-rate schedules
# ---------------------------------------------------------------------------

lr_base = var(
    "opt.schedule.lr_base", "eta_base_opt", "dimensionless",
    "Base learning rate before schedule multipliers.",
    scope="optimizer",
)
warmup_steps = var(
    "opt.schedule.warmup_steps", "N_warm_opt", "steps",
    "Warmup steps.",
    scope="optimizer",
    integer=True,
)
schedule_total_steps = var(
    "opt.schedule.total_steps", "N_sched_total_opt", "steps",
    "Total scheduled steps.",
    scope="optimizer",
    integer=True,
)
wsd_stable_steps = var(
    "opt.schedule.wsd_stable_steps", "N_wsd_stable_opt", "steps",
    "Stable plateau steps in a warmup-stable-decay schedule.",
    scope="optimizer",
    integer=True,
)
loss_scale_growth_interval = var(
    "opt.loss_scale.growth_interval", "N_ls_growth_opt", "steps",
    "Stable steps required before increasing the loss scale.",
    scope="optimizer",
    integer=True,
)
lr_warmup = var(
    "opt.schedule.lr_warmup", "eta_warm_opt", "dimensionless",
    "Learning rate under linear warmup.",
    scope="optimizer",
)
lr_cosine = var(
    "opt.schedule.lr_cosine", "eta_cos_opt", "dimensionless",
    "Learning rate under warmup followed by cosine decay.",
    scope="optimizer",
)
lr_inv_sqrt = var(
    "opt.schedule.lr_inv_sqrt", "eta_isqrt_opt", "dimensionless",
    "Learning rate under inverse-square-root decay.",
    scope="optimizer",
)
lr_wsd = var(
    "opt.schedule.lr_wsd", "eta_wsd_opt", "dimensionless",
    "Learning rate under warmup-stable-decay.",
    scope="optimizer",
)


eq_lr_warmup = eq(
    "opt.eq.lr_warmup",
    lr_warmup.symbol,
    lr_base.symbol * sp.Min(1, t_step.symbol / warmup_steps.symbol),
    "Linear warmup ramps linearly to the base learning rate and then stays there.",
)

eq_lr_cosine = PiecewiseEquation(
    "opt.eq.lr_cosine",
    lr_cosine.symbol,
    pieces=[
        (lr_base.symbol * t_step.symbol / warmup_steps.symbol, t_step.symbol <= warmup_steps.symbol),
        (lr_base.symbol * (1 + sp.cos(sp.pi * (t_step.symbol - warmup_steps.symbol) / (schedule_total_steps.symbol - warmup_steps.symbol))) / 2, True),
    ],
    description="Cosine decay uses linear warmup followed by a half-cosine decay to zero.",
)

eq_lr_inv_sqrt = eq(
    "opt.eq.lr_inv_sqrt",
    lr_inv_sqrt.symbol,
    lr_base.symbol * sp.Min(1, t_step.symbol / warmup_steps.symbol) / sp.sqrt(sp.Max(1, t_step.symbol / warmup_steps.symbol)),
    "Inverse-square-root decay warms up linearly and then falls as 1/sqrt(t).",
)

eq_lr_wsd = PiecewiseEquation(
    "opt.eq.lr_wsd",
    lr_wsd.symbol,
    pieces=[
        (lr_base.symbol * t_step.symbol / warmup_steps.symbol, t_step.symbol <= warmup_steps.symbol),
        (lr_base.symbol, t_step.symbol <= warmup_steps.symbol + wsd_stable_steps.symbol),
        (lr_base.symbol * (schedule_total_steps.symbol - t_step.symbol) / (schedule_total_steps.symbol - warmup_steps.symbol - wsd_stable_steps.symbol), True),
    ],
    description="Warmup-stable-decay uses linear warmup, a flat plateau, and then a linear tail to zero.",
)


# ---------------------------------------------------------------------------
# Dynamic loss scaling for low-precision training
# ---------------------------------------------------------------------------

loss_unscaled = var(
    "opt.loss_scale.loss_unscaled", "L_unscaled_opt", "value",
    "Original loss before scaling.",
    scope="optimizer",
)
loss_scaled = var(
    "opt.loss_scale.loss_scaled", "L_scaled_opt", "value",
    "Scaled loss.",
    scope="optimizer",
)
loss_scale = var(
    "opt.loss_scale.scale", "S_loss_opt", "dimensionless",
    "Current loss scale.",
    scope="optimizer",
)
grad_scaled = var(
    "opt.loss_scale.grad_scaled", "g_scaled_opt", "grad",
    "Gradient observed in the scaled-loss backward pass.",
    scope="optimizer",
    positive=False,
)
grad_unscaled = var(
    "opt.loss_scale.grad_unscaled", "g_unscaled_opt", "grad",
    "Gradient after dividing by the loss scale.",
    scope="optimizer",
    positive=False,
)
overflow_count = var(
    "opt.loss_scale.overflow_count", "N_overflow_opt", "events",
    "Gradient overflow events seen at the current step.",
    scope="optimizer",
    positive=False,
    integer=True,
)
stable_steps_since_overflow = var(
    "opt.loss_scale.stable_steps_since_overflow", "N_stable_ls_opt", "steps",
    "Consecutive stable steps since the last overflow.",
    scope="optimizer",
    positive=False,
    integer=True,
)
loss_scale_growth_factor = var(
    "opt.loss_scale.growth_factor", "r_ls_growth_opt", "dimensionless",
    "Multiplicative growth factor for dynamic loss scaling.",
    scope="optimizer",
)
loss_scale_next = var(
    "opt.loss_scale.scale_next", "S_loss_next_opt", "dimensionless",
    "Loss scale chosen for the next step.",
    scope="optimizer",
)


eq_loss_scaled = eq(
    "opt.eq.loss_scaled",
    loss_scaled.symbol,
    loss_unscaled.symbol * loss_scale.symbol,
    "Scaling the loss scales every gradient in the backward pass by the same factor.",
)

eq_grad_unscaled = eq(
    "opt.eq.grad_unscaled",
    grad_unscaled.symbol,
    grad_scaled.symbol / loss_scale.symbol,
    "Unscaling divides the gradient by the loss scale before the optimizer update.",
)

eq_loss_scale_next = PiecewiseEquation(
    "opt.eq.loss_scale_next",
    loss_scale_next.symbol,
    pieces=[
        (loss_scale.symbol / loss_scale_growth_factor.symbol, overflow_count.symbol > 0),
        (loss_scale.symbol * loss_scale_growth_factor.symbol, stable_steps_since_overflow.symbol >= loss_scale_growth_interval.symbol),
        (loss_scale.symbol, True),
    ],
    description="Dynamic loss scaling shrinks on overflow, grows after a sufficiently long stable streak, and otherwise holds steady.",
)


# ---------------------------------------------------------------------------
# EMA and Shampoo-family state size
# ---------------------------------------------------------------------------

opt_state_mult = var(
    "opt.state_mult", "k_opt_state_opt", "multiplier",
    "Optimizer-state tensors per parameter in the selected optimizer.",
    scope="optimizer",
)
bytes_per_opt_param = var(
    "opt.bytes_per_param", "B_opt_state_opt", "byte/param",
    "Bytes per optimizer-state value.",
    scope="optimizer",
)

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
shampoo_rows = var(
    "opt.shampoo.rows", "N_shampoo_row_opt", "dim",
    "Row dimension of a Shampoo preconditioner block.",
    scope="optimizer",
)
shampoo_cols = var(
    "opt.shampoo.cols", "N_shampoo_col_opt", "dim",
    "Column dimension of a Shampoo preconditioner block.",
    scope="optimizer",
)
shampoo_state_bytes = var(
    "opt.shampoo.state_bytes", "M_shampoo_opt", "byte",
    "Memory footprint of one full Shampoo preconditioner pair.",
    scope="optimizer",
)
distributed_shampoo_shard_degree = var(
    "opt.shampoo.shard_degree", "d_shampoo_opt", "degree",
    "Sharding degree for distributed Shampoo state.",
    scope="optimizer",
)
distributed_shampoo_state_bytes = var(
    "opt.shampoo.state_bytes_distributed", "M_shampoo_dist_opt", "byte",
    "Per-rank Shampoo state after sharding.",
    scope="optimizer",
)


eq_ema_theta = eq(
    "opt.eq.ema_theta",
    ema_theta.symbol,
    ema_decay.symbol * ema_prev.symbol + (1 - ema_decay.symbol) * theta_next.symbol,
    "EMA weights blend the previous EMA with the latest parameter value.",
)

eq_shampoo_state_bytes = eq(
    "opt.eq.shampoo_state_bytes",
    shampoo_state_bytes.symbol,
    2 * bytes_per_opt_param.symbol * (shampoo_rows.symbol ** 2 + shampoo_cols.symbol ** 2),
    "A Shampoo block stores row and column second-order statistics, typically with both accumulator and inverse-root style state.",
)

eq_distributed_shampoo_state_bytes = eq(
    "opt.eq.distributed_shampoo_state_bytes",
    distributed_shampoo_state_bytes.symbol,
    shampoo_state_bytes.symbol / distributed_shampoo_shard_degree.symbol,
    "Distributed Shampoo amortizes the preconditioner state across the chosen shard degree.",
)


# ---------------------------------------------------------------------------
# Optimizer-state memory
# ---------------------------------------------------------------------------

opt_state_bytes = var(
    "opt.state.bytes", "M_opt_state_opt", "byte",
    "Total optimizer-state memory footprint.",
    scope="optimizer",
)


eq_opt_state = eq(
    "opt.eq.state_memory",
    opt_state_bytes.symbol,
    opt_state_mult.symbol * bytes_per_opt_param.symbol * n_params.symbol,
    "Optimizer-state memory equals tensors-per-parameter times bytes-per-state times total parameter count.",
)


OPTIMIZER_VARIABLES = [
    g, lr, wd, theta, theta_next, t_step,
    m, v_adam, m_prev, v_prev, beta1, beta2, eps_adam, m_hat, v_hat,
    X_ns, ns_coeffs, ns_coeff_a, ns_coeff_b, ns_coeff_c, ns_iterations,
    ns_input, ns_residual, ns_tol, muon_beta, muon_momentum_prev,
    muon_momentum, muon_update,
    max_logit, clip_threshold, clip_factor, g_norm, clip_norm, g_clipped,
    sgd_velocity_prev, sgd_velocity, sgd_momentum_coeff,
    theta_next_sgd, theta_next_nesterov,
    rmsprop_avg_prev, rmsprop_avg, beta_rms, eps_rms, theta_next_rms,
    weight_norm, update_norm, trust_ratio, theta_next_lamb,
    lion_m_prev, lion_m, lion_beta1, lion_beta2, lion_direction,
    theta_next_lion,
    lr_base, warmup_steps, schedule_total_steps, wsd_stable_steps,
    loss_scale_growth_interval, lr_warmup, lr_cosine, lr_inv_sqrt, lr_wsd,
    loss_unscaled, loss_scaled, loss_scale, grad_scaled, grad_unscaled,
    overflow_count, stable_steps_since_overflow, loss_scale_growth_factor,
    loss_scale_next,
    ema_decay, ema_prev, ema_theta, shampoo_rows, shampoo_cols,
    shampoo_state_bytes, distributed_shampoo_shard_degree,
    distributed_shampoo_state_bytes,
    opt_state_mult, bytes_per_opt_param, opt_state_bytes,
]

OPTIMIZER_EQUATIONS = [
    eq_adam_m,
    eq_adam_v,
    eq_adam_m_hat,
    eq_adam_v_hat,
    eq_adam_step,
    eq_muon_momentum,
    eq_ns_iterations_default,
    eq_ns_input,
    eq_ns_iteration,
    eq_ns_residual,
    eq_muon_update,
    eq_muon_step,
    eq_muonclip_factor,
    eq_grad_clip,
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
    eq_lr_warmup,
    eq_lr_cosine,
    eq_lr_inv_sqrt,
    eq_lr_wsd,
    eq_loss_scaled,
    eq_grad_unscaled,
    eq_loss_scale_next,
    eq_ema_theta,
    eq_shampoo_state_bytes,
    eq_distributed_shampoo_state_bytes,
    eq_opt_state,
]

for v in OPTIMIZER_VARIABLES:
    sys_opt.add(v)

for e in OPTIMIZER_EQUATIONS:
    sys_opt.add(e)
