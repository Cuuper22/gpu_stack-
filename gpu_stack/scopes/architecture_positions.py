"""
scopes/architecture_positions.py
================================

Positional encoding schemes. Covers sinusoidal encodings, RoPE, ALiBi, and a
YaRN-style context-extension scale factor.
"""

from ..core import eq, var

from .architecture_embeddings import d_model


# ---------------------------------------------------------------------------
# Positional encoding
# ---------------------------------------------------------------------------

position_index = var(
    "arch.pos.index", "p_pos_arch", "tokens",
    "Token position index.",
    scope="architecture",
)
head_pair_index = var(
    "arch.pos.head_pair_index", "i_pair_arch", "dimensionless",
    "Pair index inside the rotary or sinusoidal subspace.",
    scope="architecture",
)
sinusoid_base = var(
    "arch.pos.sinusoid_base", "theta_sin_arch", "dimensionless",
    "Base used by sinusoidal positional encoding.",
    scope="architecture",
)
sinusoid_inv_freq = var(
    "arch.pos.sinusoid_inv_freq", "omega_sin_arch", "dimensionless",
    "Inverse-frequency factor for one sinusoidal pair.",
    scope="architecture",
)
sinusoid_phase = var(
    "arch.pos.sinusoid_phase", "phi_sin_arch", "dimensionless",
    "Sinusoidal phase for one coordinate pair.",
    scope="architecture",
)
rope_theta_base = var(
    "arch.pos.rope_theta_base", "theta_rope_arch", "dimensionless",
    "RoPE base frequency parameter.",
    scope="architecture",
)
rope_rotary_dim = var(
    "arch.pos.rope_rotary_dim", "d_rope_arch", "dim",
    "Dimension participating in RoPE.",
    scope="architecture",
)
rope_inv_freq = var(
    "arch.pos.rope_inv_freq", "omega_rope_arch", "dimensionless",
    "RoPE inverse-frequency term for one pair.",
    scope="architecture",
)
rope_angle = var(
    "arch.pos.rope_angle", "phi_rope_arch", "dimensionless",
    "RoPE rotation angle for one pair.",
    scope="architecture",
)
relative_distance = var(
    "arch.pos.relative_distance", "Delta_pos_arch", "tokens",
    "Relative token distance used by ALiBi.",
    scope="architecture",
)
alibi_slope = var(
    "arch.pos.alibi_slope", "m_alibi_arch", "dimensionless",
    "ALiBi slope for one head.",
    scope="architecture",
)
alibi_bias = var(
    "arch.pos.alibi_bias", "b_alibi_arch", "dimensionless",
    "Attention bias contributed by ALiBi.",
    scope="architecture",
)
context_train_len = var(
    "arch.pos.context_train_len", "L_train_ctx_arch", "tokens",
    "Context length used during base training of the positional scheme.",
    scope="architecture",
)
context_target_len = var(
    "arch.pos.context_target_len", "L_target_ctx_arch", "tokens",
    "Target context length after extension.",
    scope="architecture",
)
yarn_scale = var(
    "arch.pos.yarn_scale", "s_yarn_arch", "dimensionless",
    "Context-extension scale factor used by YaRN-style RoPE stretching.",
    scope="architecture",
)


eq_sinusoid_inv_freq = eq(
    "arch.eq.sinusoid_inv_freq",
    sinusoid_inv_freq.symbol,
    sinusoid_base.symbol ** (-2 * head_pair_index.symbol / d_model.symbol),
    "Sinusoidal encodings use exponentially spaced inverse frequencies across coordinate pairs.",
)

eq_sinusoid_phase = eq(
    "arch.eq.sinusoid_phase",
    sinusoid_phase.symbol,
    position_index.symbol * sinusoid_inv_freq.symbol,
    "The sinusoidal phase is position times inverse frequency.",
)

eq_rope_inv_freq = eq(
    "arch.eq.rope_inv_freq",
    rope_inv_freq.symbol,
    rope_theta_base.symbol ** (-2 * head_pair_index.symbol / rope_rotary_dim.symbol),
    "RoPE uses exponentially spaced inverse frequencies across the rotary subspace.",
)

eq_rope_angle = eq(
    "arch.eq.rope_angle",
    rope_angle.symbol,
    position_index.symbol * rope_inv_freq.symbol,
    "RoPE rotates each pair by position times inverse frequency.",
)

eq_alibi_bias = eq(
    "arch.eq.alibi_bias",
    alibi_bias.symbol,
    -alibi_slope.symbol * relative_distance.symbol,
    "ALiBi adds a head-specific linear penalty with distance.",
)

eq_yarn_scale = eq(
    "arch.eq.yarn_scale",
    yarn_scale.symbol,
    context_target_len.symbol / context_train_len.symbol,
    "A simple context-extension scale is target context divided by training context.",
)


ARCH_POSITIONS_VARIABLES = [
    position_index, head_pair_index, sinusoid_base, sinusoid_inv_freq,
    sinusoid_phase, rope_theta_base, rope_rotary_dim, rope_inv_freq,
    rope_angle, relative_distance, alibi_slope, alibi_bias,
    context_train_len, context_target_len, yarn_scale,
]

ARCH_POSITIONS_EQUATIONS = [
    eq_sinusoid_inv_freq,
    eq_sinusoid_phase,
    eq_rope_inv_freq,
    eq_rope_angle,
    eq_alibi_bias,
    eq_yarn_scale,
]


__all__ = [
    "position_index", "head_pair_index", "sinusoid_base", "sinusoid_inv_freq",
    "sinusoid_phase", "rope_theta_base", "rope_rotary_dim", "rope_inv_freq",
    "rope_angle", "relative_distance", "alibi_slope", "alibi_bias",
    "context_train_len", "context_target_len", "yarn_scale",
    "eq_sinusoid_inv_freq", "eq_sinusoid_phase", "eq_rope_inv_freq",
    "eq_rope_angle", "eq_alibi_bias", "eq_yarn_scale",
    "ARCH_POSITIONS_VARIABLES", "ARCH_POSITIONS_EQUATIONS",
]
