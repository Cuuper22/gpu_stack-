"""Numeric sanity of the shipped presets against public values and hand arithmetic.

Run:  PYTHONPATH=<repo> <venv python> -B analysis/graph-audit/scenario_sanity.py
"""
from __future__ import annotations

import math

import gpu_stack  # noqa: F401
from gpu_stack import Registry, resolve
from gpu_stack.presets import hardware, scenarios

V = Registry.variables
f = float


def line(label, graph, ref, note=""):
    r = graph / ref if ref else float("nan")
    print(f"{label:62s} graph={graph:<12.5g} ref={ref:<12.5g} ratio={r:6.3f} {note}")


print("== A. H100 / DGX H100 hardware presets vs public specs (values as assigned) ==")
h = hardware.dgx_h100_8gpu_node.assignments
line("gpu.peak_flops (FP32, non-tensor) vs H100 SXM FP32 67 TF", h["gpu.peak_flops"], 67e12)
line("gpu.peak_flops_sparse vs 1979 TF (FP16 TC with sparsity)", h["gpu.peak_flops_sparse"], 1979e12)
line("  dense BF16 TC = sparse/2 = 989.5 TF; ratio dense-TC / assigned peak", 1979e12 / 2, h["gpu.peak_flops"],
     "<- training runs use tensor cores, graph uses the FP32 number")
line("gpu.tdp vs 700 W", h["gpu.tdp"], 700.0)
line("mem.hbm.bw vs 3.35 TB/s", h["mem.hbm.bw"], 3.35e12)
line("mem.hbm.capacity (80e9 B) vs 80 GiB physical", h["mem.hbm.capacity"], 80 * 2**30, "decimal-vs-binary, 7% low")
line("gpu.nvlink.bw (900e9) vs NVLink4 per-direction 450 GB/s", h["gpu.nvlink.bw"], 450e9,
     "<- 900 GB/s is bidirectional total; alpha-beta needs per direction")
line("cluster.node.nic.port_rate vs 400 Gb/s = 50 GB/s per direction", h["cluster.node.nic.port_rate"], 50e9, "(unidirectional, inconsistent with NVLink above)")
line("cluster.node.hbm_capacity vs 640 GB", h["cluster.node.hbm_capacity"], 640e9)

print("\n== B. Known-model FLOP accounting through the graph (6 N D) ==")
gpt3 = {"arch.n_layers": 96, "arch.d_model": 12288, "arch.d_ffn": 49152, "arch.n_heads": 96, "arch.n_kv_heads": 96,
        "arch.vocab": 50257, "arch.output.untied_factor": 0, "arch.ffn.weight_matrices": 2, "arch.norm.param_multiplier": 4}
P = f(resolve("arch.params_total_dense", assignments=gpt3).value)
line("GPT-3 params from graph vs 175e9", P, 175e9)
line("GPT-3 6*N*D (D=300e9) vs published 3.14e23 FLOP", 6 * P * 300e9, 3.14e23)
llama = {"arch.n_layers": 126, "arch.d_model": 16384, "arch.d_ffn": 53248, "arch.n_heads": 128, "arch.n_kv_heads": 8,
         "arch.vocab": 128256, "arch.output.untied_factor": 1, "arch.ffn.weight_matrices": 3, "arch.norm.param_multiplier": 2}
P = f(resolve("arch.params_total_dense", assignments=llama).value)
line("Llama-3.1-405B params from graph vs 405e9", P, 405e9)
line("Llama-3.1-405B 6*N*D (D=15.6e12) vs reported 3.8e25 FLOP", 6 * P * 15.6e12, 3.8e25)

print("\n== C. Pythia-70M on one DGX H100 (shipped industrial pack) ==")
pk = scenarios.pythia_70m_dgx_h100_us_2024_industrial_energy_floor_cost
res = {t: resolve(t, assignments=dict(pk.assignments), variants=dict(pk.variants)) for t in
       ("arch.params_total_dense", "arch.flops.step_dense", "training.tokens_per_sec", "training.wallclock",
        "econ.run.power_cost", "econ.cost.per_token")}
P = f(res["arch.params_total_dense"].value)
tps = f(res["training.tokens_per_sec"].value)
D = 299_892_736_000
line("Pythia-70M params vs model card 70,426,624", P, 70_426_624)
line("tokens/s = 8 GPUs * 67 TF / (6 N)  (ideal, 100% MFU of FP32 peak)", tps, 8 * 67e12 / (6 * P))
exact = (6 * (512 * 512 * 4 + 2 * 2048 * 512 + 4 * 512) + 2 * 50304 * 512 + 6 * 4 * 2048 * 512) * 3 / 3
# exact forward FLOPs per token: layers*(2*(4h^2+2*4h^2)+4*s*h) + 2*h*V ; training = 3x forward
fwd = 6 * (2 * (4 * 512**2 + 2 * 2048 * 512) + 4 * 2048 * 512) + 2 * 512 * 50304
line("graph FLOP/token vs exact 3x forward FLOP/token", 6 * P, 3 * fwd, "<- embedding table counted as matmul params")
wall = f(res["training.wallclock"].value)
line("wallclock = D / tokens_per_s", wall, D / tps)
line("  wallclock in hours (graph)", wall / 3600, wall / 3600)
line("power cost = 10.2 kW * wallclock * $0.0813/kWh", f(res["econ.run.power_cost"].value), 10.2 * wall / 3600 * 0.0813)
line("energy-floor cost per token = power cost / D", f(res["econ.cost.per_token"].value), 10.2 * wall / 3600 * 0.0813 / D)
print(f"   energy per token = {10200 / tps * 1e3:.2f} mJ; at real bf16 tensor-core speeds the same run is ~15x shorter")

print("\n== D. Full-TCO pack: where does the cost come from? ==")
tco = scenarios.pythia_70m_dgx_h100_us_2024_industrial_full_tco_assumption
r = resolve("econ.cost.per_token", assignments=dict(tco.assignments), variants=dict(tco.variants))
vals = {k: f(v) for k, v in r.values.items() if k.startswith("econ.run.") or k in ("econ.cluster.capex_total", "econ.job.capex_rate")}
tot = vals["econ.run.total_cost"]
for k in ("econ.run.hw_cost", "econ.run.power_cost", "econ.run.capacity_charge_cost", "econ.run.maintenance_cost",
          "econ.run.staff_cost", "econ.run.water_cost", "econ.run.network_cost", "econ.run.carbon_cost"):
    print(f"   {k:34s} ${vals[k]:10.2f}  {100*vals[k]/tot:5.1f}%")
print(f"   total ${tot:.2f}; cost/token {f(r.value):.4g}; site capex ${vals['econ.cluster.capex_total']:.0f}")
cap = vals["econ.cluster.capex_total"]
hand_hw = cap * (1 - 0.05) / 126_230_400 / 0.90 * wall
line("hw cost hand check = capex*(1-resid)/life/util*wall (f_job=1)", vals["econ.run.hw_cost"], hand_hw)
print("   facility capex shares the 4-year IT life; demand charge (capacity_charge) is added on top of an EIA average price")
print("   that the economics preset says already blends demand charges (double count).")

print("\n== E. Fixture: dense_training_cost_fixture ==")
fx = scenarios.dense_training_cost_fixture
for t in ("training.t_step", "training.tokens_per_sec", "econ.job.dc_power", "econ.run.total_cost", "econ.cost.per_token"):
    print(f"   {t:28s} {f(fx.resolve(t).value):.6g}")
print("   capex_rate = $20/s = $631M per year of one 8-GPU node: round-number fixture, not a price.")
