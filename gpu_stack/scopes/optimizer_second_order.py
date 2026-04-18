"""
scopes/optimizer_second_order.py
================================

Second-order and matrix-structured optimizers.

This helper defines Muon with its Newton-Schulz orthogonalization iteration,
the MuonClip QK rescaling, global-norm gradient clipping, and the Shampoo
preconditioner state that the distributed sharding helper amortizes.
"""

import sympy as sp
from ..core import IterativeEquation, RelationRole, eq, var

from .optimizer_first_order import (
    bytes_per_opt_param,
    g,
    lr,
    theta,
    theta_next,
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
    role=RelationRole.VARIANT,
    variant="muon",
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
# Shampoo preconditioner state
# ---------------------------------------------------------------------------

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


eq_shampoo_state_bytes = eq(
    "opt.eq.shampoo_state_bytes",
    shampoo_state_bytes.symbol,
    2 * bytes_per_opt_param.symbol * (shampoo_rows.symbol ** 2 + shampoo_cols.symbol ** 2),
    "A Shampoo block stores row and column second-order statistics, typically with both accumulator and inverse-root style state.",
)


OPT_SECOND_ORDER_VARIABLES = [
    X_ns, ns_coeffs, ns_coeff_a, ns_coeff_b, ns_coeff_c, ns_iterations,
    ns_input, ns_residual, ns_tol, muon_beta, muon_momentum_prev,
    muon_momentum, muon_update,
    max_logit, clip_threshold, clip_factor, g_norm, clip_norm, g_clipped,
    shampoo_rows, shampoo_cols, shampoo_state_bytes,
]

OPT_SECOND_ORDER_EQUATIONS = [
    eq_muon_momentum,
    eq_ns_iterations_default,
    eq_ns_input,
    eq_ns_iteration,
    eq_ns_residual,
    eq_muon_update,
    eq_muon_step,
    eq_muonclip_factor,
    eq_grad_clip,
    eq_shampoo_state_bytes,
]


__all__ = [
    "X_ns", "ns_coeffs", "ns_coeff_a", "ns_coeff_b", "ns_coeff_c",
    "ns_iterations", "ns_input", "ns_residual", "ns_tol",
    "muon_beta", "muon_momentum_prev", "muon_momentum", "muon_update",
    "max_logit", "clip_threshold", "clip_factor",
    "g_norm", "clip_norm", "g_clipped",
    "shampoo_rows", "shampoo_cols", "shampoo_state_bytes",
    "eq_muon_momentum", "eq_ns_iterations_default", "eq_ns_input",
    "eq_ns_iteration", "eq_ns_residual", "eq_muon_update", "eq_muon_step",
    "eq_muonclip_factor", "eq_grad_clip",
    "eq_shampoo_state_bytes",
    "OPT_SECOND_ORDER_VARIABLES", "OPT_SECOND_ORDER_EQUATIONS",
]
