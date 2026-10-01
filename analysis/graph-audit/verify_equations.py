"""Numeric spot checks of graph equations against independent reference formulas.

Run:  PYTHONPATH=<repo> <venv python> -B analysis/graph-audit/verify_equations.py

Each check evaluates the registered equation (by substituting values for its variables)
and compares it with a hand-written reference. Output: one line per check, PASS or DIFF,
with the two numbers. DIFF lines are the evidence behind the SUSPECT/WRONG items in REPORT.md.
"""
from __future__ import annotations

import math

import sympy as sp

import gpu_stack  # noqa: F401
from gpu_stack import Registry

V = Registry.variables
E = Registry.equations
RESULTS = []


def evaluate(eq_name: str, values: dict) -> float:
    e = E[eq_name]
    sub = {}
    for name, val in values.items():
        sub[V[name].symbol] = val
    expr = e.rhs.subs(sub)
    return float(expr)


def check(label, graph, ref, rel=1e-9, note=""):
    ok = math.isclose(graph, ref, rel_tol=rel, abs_tol=0.0)
    RESULTS.append(ok)
    print(f"{'PASS' if ok else 'DIFF'}  {label:58s} graph={graph:.6g} ref={ref:.6g}"
          + (f"  ratio={graph/ref:.4g}" if ref else "") + (f"  | {note}" if note else ""))


# ---------------------------------------------------------------- collectives
p, m = 64, 8          # ranks, ranks per node
nodes = p // m
N = 1e9
a_l, b_l = 5e-6, 1 / 50e9          # generic link
a_nv, b_nv = 1e-6, 1 / 450e9
a_so, b_so = 5e-6, 1 / 50e9
col = {
    "col.n_ranks": p, "col.payload": N, "col.ring_steps": p - 1,
    "link.alpha": a_l, "link.beta": b_l,
    "col.tree_depth": math.ceil(math.log2(p)),
    "col.ranks_per_node": m, "col.n_nodes": nodes,
    "link.nvlink.alpha": a_nv, "link.nvlink.beta": b_nv,
    "link.scaleout.alpha": a_so, "link.scaleout.beta": b_so,
}
ar_ring = evaluate("col.eq.allreduce_ring", col)
check("allreduce ring = 2(p-1)a + 2(p-1)/p N b", ar_ring, 2 * (p - 1) * a_l + 2 * (p - 1) / p * N * b_l)
ar_tree = evaluate("col.eq.allreduce_tree", col)
check("allreduce 'tree' = Rabenseifner 2log2(p)a + 2(p-1)/p N b", ar_tree,
      2 * math.log2(p) * a_l + 2 * (p - 1) / p * N * b_l,
      note="this is recursive halving/doubling, not NCCL double binary tree")
ag_ring = evaluate("col.eq.allgather_ring", col)
check("allgather ring = (p-1)a + (p-1)/p N b", ag_ring, (p - 1) * a_l + (p - 1) / p * N * b_l)
ar_h = evaluate("col.eq.allreduce_hier", col)
rs_h = evaluate("col.eq.reducescatter_hier", col)
ag_h = evaluate("col.eq.allgather_hier", col)
check("hier: allreduce == reducescatter + allgather", ar_h, rs_h + ag_h, rel=1e-9,
      note="allgather_hier inter-node bandwidth term lacks the 1/ranks_per_node factor")
ref_ag_h = ((m - 1) / m * N * b_nv + (nodes - 1) / (nodes * m) * N * b_so
            + (m - 1) * a_nv + (nodes - 1) * a_so)
check("allgather_hier vs independent derivation", ag_h, ref_ag_h,
      note="reference inter-node term is N(nodes-1)/(nodes*ranks_per_node)*beta_SO, same as reducescatter_hier")
a2a = evaluate("col.eq.alltoall_pairwise", col)
check("alltoall pairwise = (p-1)a + (p-1)/p N b", a2a, (p - 1) * a_l + (p - 1) / p * N * b_l)

# ------------------------------------------------------- pipeline bubbles
pp, mb = 8, 8
bub = {"par.pp.n_stages": pp, "par.pp.n_microbatches": mb}
phi = evaluate("par.eq.bubble_1f1b", bub)
check("1F1B bubble: graph phi vs Narayanan (p-1)/m (overhead over ideal)", phi, (pp - 1) / mb,
      note="graph phi=(p-1)/(p+m-1) is bubble/total, but training.eq.t_bubbles uses it as overhead/nominal")
# training uses T_step = T_nom*(1+phi); correct is T_nom*(1+(p-1)/m)
check("pipeline step-time multiplier used by training vs Narayanan 1+(p-1)/m", 1 + phi, 1 + (pp - 1) / mb)
gp = evaluate("par.eq.bubble_gpipe", bub)
check("GPipe vs 1F1B bubble (same bubble in Narayanan 2021)", gp, phi,
      note="graph gives two different values for schedules with identical bubble")
vv = 2
il = evaluate("par.eq.bubble_interleaved", {**bub, "par.pp.virtual_stages": vv})
check("interleaved: graph vs Narayanan (p-1)/(v m) overhead", il, (pp - 1) / (vv * mb))

# ------------------------------------------------------- FLOPs per token
def megatron_flops_per_iter(B, s, l, h, Vv):  # Narayanan 2021 eq. (4), with activation recompute
    return 96 * B * s * l * h * h * (1 + s / (6 * h) + Vv / (16 * l * h))


def exact_train_flops_no_recompute(B, s, l, h, Vv, ffn=4):
    # 3x forward; forward per token: 2*(4h^2+2*ffn*h*... ) projections + attention scores/values 4*s*h + logits 2*h*V
    per_tok_fwd = l * (2 * (4 * h * h + 2 * ffn * h * h) + 4 * s * h) + 2 * h * Vv
    return 3 * per_tok_fwd * B * s


for name, (l, h, s, Vv) in {
    "Pythia-70M": (6, 512, 2048, 50304),
    "Pythia-160M": (12, 768, 2048, 50304),
    "GPT-3 175B": (96, 12288, 2048, 50257),
}.items():
    ffn = 4
    P_nonemb = l * (4 * h * h + 2 * ffn * h * h + 4 * h)
    P_graph = P_nonemb + 2 * Vv * h if name.startswith("Pythia") else P_nonemb + Vv * h
    tokens = 2048
    graph = 6 * P_graph * tokens
    ref = exact_train_flops_no_recompute(1, s, l, h, Vv)
    check(f"6*N_total*T vs exact (no recompute) {name}", graph, ref, rel=0.05,
          note=f"N_total={P_graph/1e6:.1f}M; DIFF means more than 5% apart")

# Verify the graph's own Pythia-70M params against the model card (70,426,624 total)
pyth = {
    "arch.n_layers": 6, "arch.d_model": 512, "arch.d_ffn": 2048, "arch.n_heads": 8, "arch.vocab": 50304,
    "arch.output.untied_factor": 1, "arch.n_kv_heads": 8, "arch.ffn.weight_matrices": 2, "arch.norm.param_multiplier": 4,
}
from gpu_stack import resolve  # noqa: E402
r = resolve("arch.params_total_dense", assignments=pyth)
check("Pythia-70M total params vs model card 70,426,624 (biases excluded in graph)", float(r.value), 70_426_624, rel=2e-3)

# ------------------------------------------------------- KV cache
check("KV bytes/token/layer GQA = 2*bytes*d_head*h_kv",
      evaluate("arch.eq.kv_gqa", {"arch.kv.bytes_per_val": 2, "arch.head_dim": 128, "arch.n_kv_heads": 8}), 2 * 2 * 128 * 8)
# DeepSeek-V2 MLA: cache per token per layer = (d_c + d_R) elements, d_c=512, d_R=64, one shared latent
mla = evaluate("arch.eq.kv_mla", {"arch.kv.bytes_per_val": 2, "arch.mla.d_latent": 512})
check("MLA bytes/token/layer vs DeepSeek-V2 (d_c+d_R)*bytes", mla, (512 + 64) * 2,
      note="graph stores K and V latents separately (factor 2); V2 shares one latent")

# ------------------------------------------------------- Young / Daly
Mtbf, dlt, R = 6 * 3600.0, 120.0, 600.0
young = evaluate("cluster.eq.optimal_checkpoint_interval", {"cluster.rel.site_mtbf": Mtbf, "cluster.rel.checkpoint_time": dlt})
check("Young interval sqrt(2*delta*M)", young, math.sqrt(2 * dlt * Mtbf))
daly = math.sqrt(2 * dlt * (Mtbf + R)) - dlt
print(f"INFO  Daly (2006) first-order interval = {daly:.1f}s vs Young {young:.1f}s ({(young/daly-1)*100:.1f}% difference at delta/M={dlt/Mtbf:.3f})")

# ------------------------------------------------------- economics scale factors
check("kWh -> W*s: $/kWh / 3.6e6", evaluate("econ.eq.ws_from_kwh", {"econ.power.price_kwh": 0.1}), 0.1 / 3.6e6)
check("carbon kg/s = I[kg/kWh]*P[W]/3.6e6", evaluate("econ.eq.carbon_emission_rate", {"econ.carbon.intensity_kg_per_kwh": 0.386, "econ.job.dc_power": 1e4}), 0.386 * 1e4 / 3.6e6)
check("capacity charge: $/kW-month over 30 d", evaluate("econ.eq.capacity_charge_rate", {"econ.power.peak_demand_kw": 10.0, "econ.power.capacity_charge_kw_month": 8.0}), 10 * 8 / (30 * 86400))
check("maintenance: fraction/yr over 365 d", evaluate("econ.eq.maintenance_cost_rate", {"econ.cluster.capex_total": 1e6, "econ.maintenance.fraction_per_year": 0.02}), 1e6 * 0.02 / (365 * 86400))
print(f"INFO  year length used: maintenance 365.00 d, preset useful_life 365.25 d, staff rate 365.25 d, demand charge month 30 d (vs 30.44 d)")
check("ring DP time (training.eq.t_comm_dp)",
      evaluate("training.eq.t_comm_dp", {"par.dp": 16, "training.dp.grad_bytes": 2e9, "training.dp.bucket_count": 20,
                                         "training.dp.alpha": 5e-6, "training.dp.beta": 1 / 50e9}),
      2 * 15 / 16 * 2e9 / 50e9 + 20 * 2 * 15 * 5e-6)

# ------------------------------------------------------- ZeRO memory (Rajbhandari 2020): psi params, K=12 Adam
psi, nd = 7.5e9, 64
shared = {"par.mem.params": 2 * psi, "par.mem.grads": 2 * psi, "par.mem.opt": 12 * psi, "par.fsdp.shard_group": nd,
          "par.mem.act_per_gpu": 0.0}
check("ZeRO-1 bytes/param = 2+2+K/Nd", evaluate("par.eq.mem_zero1", shared) / psi, 2 + 2 + 12 / nd)
check("ZeRO-2 bytes/param = 2+(2+K)/Nd", evaluate("par.eq.mem_zero2", shared) / psi, 2 + (2 + 12) / nd)
check("ZeRO-3 bytes/param = (2+2+K)/Nd", evaluate("par.eq.mem_zero3", shared) / psi, (2 + 2 + 12) / nd)

# ------------------------------------------------------- HBM / GPU
hbm = evaluate("mem.eq.hbm_bw_per_channel", {"mem.hbm.pins_per_channel": 128, "mem.hbm.protocol_efficiency": 1.0, "mem.hbm.pin_rate": 6.4e9})
check("HBM3 channel bytes/s: 128 pins x 6.4 Gb/s / 8", hbm, 128 * 6.4e9 / 8)
print(f"INFO  H100 SXM: 5 stacks x 1024 pins x 5.23 Gb/s / 8 = {5*1024*5.23e9/8/1e12:.2f} TB/s (spec 3.35 TB/s)")

# ------------------------------------------------------- thermal / facility
pue = evaluate("thermal.eq.dc_total_power", {
    "cluster.site.power_it": 1e6, "thermal.facility.cooling_power": 1e5, "thermal.facility.lighting": 0.0,
    "thermal.facility.misc": 0.0, "thermal.facility.ups_loss": 4e4, "thermal.facility.transformer_loss": 2e4}) / 1e6
check("PUE = (IT+cool+ups+xfmr)/IT", pue, 1.16)
evap = evaluate("thermal.eq.water_evap_rate", {"thermal.facility.heat_to_reject": 1e6, "thermal.water.latent_heat": 2.454e6})
print(f"INFO  1 MW rejected evaporatively -> {evap*3600/0.998:.0f} L/h (physics: 1 MW / 2.454 MJ/kg = 1467 kg/h, so PASS in spirit)")

# ------------------------------------------------------- clock model
print("INFO  clock: f = eta * 1/t_elmore where t_elmore is ONE gate+wire stage; real critical paths are ~20-30 FO4 deep,"
      " so eta_clk_derate must absorb logic depth (see REPORT).")

n_bad = sum(1 for r_ in RESULTS if not r_)
print(f"\n{len(RESULTS)} checks, {len(RESULTS)-n_bad} PASS, {n_bad} DIFF")
