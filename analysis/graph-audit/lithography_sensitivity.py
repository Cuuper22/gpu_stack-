"""Does the nuclear / quark / binding bookkeeping in the lithography layer change any number
that reaches gpu.peak_flops, training.tokens_per_sec, econ.job.dc_power or econ.cost.per_token?

Run:  PYTHONPATH=<repo> <venv python> -B analysis/graph-audit/lithography_sensitivity.py

Three tests.
 1. Symbolic: medium number density N = rho/m with rho = m*phi/V_pack. Mass cancels, so the
    nuclear binding energy of the medium cannot affect N, the refractive index, or NA.
 2. Numeric: the only other place nuclear mass enters is the reduced-mass factor of the source
    transition energy. Size of that effect for tin-120 with textbook liquid-drop coefficients.
 3. Hand run of the hydrogenic transition-energy chain for tin with 10 electrons removed,
    compared with the real EUV line (13.5 nm, 91.8 eV). Shows what the chain can and cannot say.
"""
from __future__ import annotations

import math

import sympy as sp

import gpu_stack  # noqa: F401
from gpu_stack import Registry

E = Registry.equations
V = Registry.variables


def eq_by_suffix(suffix):
    hits = [e for n, e in E.items() if n.endswith(suffix)]
    assert len(hits) == 1, (suffix, [h.name for h in hits])
    return hits[0]


# ---------------------------------------------------------------- 1. mass cancellation
rho_eq = eq_by_suffix("lithography_medium_mass_density_from_packing")
n_eq = eq_by_suffix("lithography_medium_number_density_from_mass")
m_eq = eq_by_suffix("lithography_medium_particle_mass")
M_eq = eq_by_suffix("lithography_medium_molar_mass")
print("1. medium number density")
for e in (rho_eq, n_eq, m_eq, M_eq):
    print(f"   {e.name.split('lithography_')[1]:45s} {e.lhs} = {e.rhs}")
N_expr = n_eq.rhs.subs(rho_eq.lhs, rho_eq.rhs)
m_sym = m_eq.lhs
M_sym = M_eq.lhs
N_expr = N_expr.subs(m_sym, m_eq.rhs).subs(M_sym, M_eq.rhs)
N_expr = sp.simplify(N_expr)
print("   N after substituting rho, m, M and simplifying:", N_expr)
formula_mass = [s for s in N_expr.free_symbols if "rest_mass" in s.name or str(s).startswith("m_formula")]
print("   depends on formula-unit rest mass / binding energy:", bool(formula_mass))

# ---------------------------------------------------------------- 2. reduced-mass effect
amu = 1.66053906660e-27
m_e = 9.1093837015e-31
m_n, m_p = 1.67492749804e-27, 1.67262192369e-27
MeV = 1.602176634e-13
c = 299792458.0
# Textbook liquid-drop coefficients (MeV), Krane-style values, used only to size the effect
aV, aS, aC, aA, aP = 15.75, 17.8, 0.711, 23.7, 11.18
Z, N_ = 50, 70  # tin-120
A = Z + N_
pair = aP / math.sqrt(A)  # even-even
B = aV * A - aS * A ** (2 / 3) - aC * Z * (Z - 1) / A ** (1 / 3) - aA * (N_ - Z) ** 2 / A + pair
m_free = N_ * m_n + Z * m_p
m_nuc = m_free - B * MeV / c ** 2
eta = lambda m: (m_e * m / (m_e + m)) / m_e
rel = (eta(m_nuc) - eta(m_free)) / eta(m_free)
print(f"\n2. tin-120 SEMF binding energy {B:.0f} MeV (real 1020.5 MeV); mass defect fraction {B*MeV/c**2/m_free:.4f}")
print(f"   reduced-mass factor eta_mu with vs without binding: relative change {rel:.2e}")
print(f"   the same factor varies {1-eta(m_free):.2e} from 1 in total (m_e/m_nuc)")

# ---------------------------------------------------------------- 3. transition chain by hand
Ry = 13.605693123  # eV
Zs = 50
n_low = 4          # graph: Z <= 60 -> 4
cap_inner = n_low * (n_low - 1) * (2 * n_low - 1) / 3   # 28
shell_cap = 2 * n_low ** 2                              # 32
for removed in (0, 5, 10, 13):
    bound = Zs - removed
    outer = max(0, bound - cap_inner - shell_cap)
    inner = min(cap_inner, bound - outer)
    occ = bound - inner - outer
    sigma = (bound - outer - occ) * 1.0 + (occ - 1) * 0.5
    zeff = Zs - sigma
    Et = Ry * zeff ** 2 * (1 / n_low ** 2 - 1 / (n_low + 1) ** 2)
    lam = 1239.84193 / Et
    print(f"3. Sn^{removed}+: Z_eff={zeff:5.1f}  E={Et:7.2f} eV  lambda={lam:7.2f} nm")
print("   real EUV line: 13.5 nm = 91.8 eV (4d-4f / 4p-4d transitions of Sn^8+..Sn^14+, many-electron)")
