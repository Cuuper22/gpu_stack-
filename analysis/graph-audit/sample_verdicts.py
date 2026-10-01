"""Hand-review verdicts for a stratified sample of equations, as data.

Run:  PYTHONPATH=<repo> <venv python> -B analysis/graph-audit/sample_verdicts.py [--csv out.csv]

Verdict codes
  C  CORRECT
  S  CORRECT-BUT-SIMPLIFIED (the note states the regime where it holds)
  X  SUSPECT (plausible but likely misleading, ambiguous, or disconnected)
  W  WRONG (the note gives the correct form)
  R  REFERENCE-MISMATCH (formula may be fine, the cited source does not say this)

The script checks that every named equation exists, finds its file:line, and adds whether the
equation is in the structural cone of the four headline targets and whether any shipped
scenario trace executes it.
"""
from __future__ import annotations

import csv
import glob
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))
import gpu_stack  # noqa: F401,E402
from gpu_stack import Registry  # noqa: E402
from inventory import TARGETS, cone  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# (equation name, verdict, note)
ROWS = [
    # ---- training (headline path)
    ("training.eq.t_compute", "C", "F_exec / (N_GPU * P_pwlim). Executed FLOPs = model FLOPs x recompute x optimizer multiplier."),
    ("training.eq.t_step_nominal", "S", "Serial sum compute + comm + HBM time. Holds only with zero compute/comm overlap."),
    ("training.eq.t_comm_dp", "S", "Ring allreduce form is right (numeric PASS). All of it is exposed: no overlap with backward."),
    ("training.eq.t_bubbles", "W", "T_nom*phi uses phi = bubble/total as an overhead ratio. Correct: T_nom*phi/(1-phi) (= T_nom*(p-1)/m)."),
    ("training.eq.overhead_fraction", "S", "Adds eval, pipeline, restart, straggler fractions. First order, small fractions only."),
    ("training.eq.wallclock", "S", "T_nom/availability, and power is then billed for the downtime too."),
    ("training.eq.tokens_per_sec", "C", "tokens per step / step time."),
    ("training.eq.mfu", "C", "Achieved model FLOPs / raw peak. Variant from_time is the same quantity."),
    ("training.eq.hfu", "C", "Executed chip FLOPs / power-limited peak."),
    ("training.eq.t_mem_bound", "S", "HBM bytes / BW added after compute, not overlapped; a roofline would take the max."),
    ("training.eq.t_comm_cp", "S", "Bytes x (1-overlap) / BW; no alpha term, bandwidth must be an algorithm bandwidth."),
    ("training.eq.flops_executed_step", "C", "Product of model FLOPs and two multipliers."),
    ("training.eq.n_steps", "C", "tokens / tokens-per-step."),
    ("training.eq.energy_per_token", "C", "IT power x step time / tokens per step (IT only, no PUE)."),
    # ---- architecture
    ("arch.eq.flops_step_dense", "R", "6*P_total*T cites Kaplan 2020, whose N excludes embeddings. Counts the embedding table as matmul work: +23% on Pythia-70M, +0.6% Pythia-160M, -2.7% GPT-3 (no attention term)."),
    ("arch.eq.params_dense_total", "C", "Pythia-70M -0.04%, GPT-3 -0.25%, Llama-3.1-405B +0.2% vs published counts."),
    ("arch.eq.params_attn_per_layer", "C", "Q,K,V,O with GQA scaling on K,V."),
    ("arch.eq.params_ffn_per_layer", "C", "matrices x d_model x d_ffn (2 plain, 3 gated)."),
    ("arch.eq.kv_gqa", "C", "2 * bytes * d_head * h_kv per token per layer (Pope 2022 form)."),
    ("arch.eq.kv_mla", "W", "2*bytes*d_latent. DeepSeek-V2 caches one shared latent plus a rotary key: (d_c+d_R)*bytes (graph is 1.78x too big at 512/64)."),
    ("arch.eq.attn_scores_flops_per_layer", "C", "2*L^2*d, full (non-causal) matrix, forward."),
    ("arch.eq.kv_total", "S", "Per sequence; no batch factor."),
    ("arch.eq.params_active_moe", "X", "Only expert+router+shared params of MoE layers. Omits attention, embeddings, dense layers, so 6*P_active understates FLOPs."),
    ("arch.eq.flops_step_moe", "X", "Inherits the active-parameter definition above."),
    ("arch.eq.flops_per_token_dense", "S", "Detailed forward count (decorative; the headline path uses 6N instead). Scores not causal-halved."),
    # ---- parallelism
    ("par.eq.bubble_1f1b", "S", "(p-1)/(p+m-1) is bubble/total, right as defined. Consumer treats it as overhead/ideal (see t_bubbles)."),
    ("par.eq.bubble_gpipe", "X", "(p-1)/m is overhead/ideal. Same bubble as 1F1B in Narayanan 2021, but a different number in the graph."),
    ("par.eq.bubble_interleaved", "W", "Correct overhead is (p-1)/(v*m). Graph uses (p/v-1)/(p/v+m-1): 0.27 vs 0.44 at p=8,v=2,m=8."),
    ("par.eq.bubble_zb", "X", "|tb-tf|/(tb+tf) is not from the zero-bubble paper; no source."),
    ("par.eq.bubble_dualpipe", "X", "Heuristic (1-overlap) scaling of the 1F1B bubble; not the DualPipe bubble formula."),
    ("par.eq.bubble_chimera", "X", "Same heuristic as DualPipe."),
    ("par.eq.mem_zero1", "C", "2+2+K/Nd bytes per param (numeric PASS vs Rajbhandari 2020)."),
    ("par.eq.mem_zero2", "C", "2+(2+K)/Nd."),
    ("par.eq.mem_zero3", "C", "(2+2+K)/Nd."),
    ("par.eq.mem_act", "S", "Layers x tokens x hidden x bytes x tensors-per-layer x keep. No attention-score term (flash attention assumed)."),
    ("par.eq.recompute_flop_multiplier", "X", "1+rho. Full recompute is 4/3, so rho must be a fraction of total step FLOPs; the root is described as a fraction of activations."),
    ("par.eq.tp_comm_per_block", "S", "tokens x hidden x bytes x #allreduces. No 2(t-1)/t factor, no alpha."),
    ("par.eq.tp_exposed_time", "S", "bytes x (1-overlap) / group bandwidth (must be algorithm bandwidth)."),
    ("par.eq.moe_payload_per_layer", "S", "Dispatch + combine, forward only; backward doubles it; no (ep-1)/ep."),
    ("par.eq.n_gpus", "C", "Product of axes; SP nested in TP."),
    ("par.eq.cpu_offload_time", "C", "bytes / bandwidth."),
    # ---- collectives / links
    ("col.eq.allreduce_ring", "C", "2(p-1)a + 2(p-1)/p*N*b (numeric PASS)."),
    ("col.eq.allreduce_tree", "S", "Is Rabenseifner halving/doubling, not NCCL double binary tree. Needs power-of-two p."),
    ("col.eq.allreduce_hier", "C", "Intra RS+AG on NVLink, inter allreduce on N/p_node shards."),
    ("col.eq.allgather_ring", "C", "(p-1)a + (p-1)/p*N*b."),
    ("col.eq.reducescatter_ring", "C", "Same as allgather."),
    ("col.eq.allgather_hier", "W", "Inter-node term N*b_SO*(m-1)/m lacks /ranks_per_node. RS_hier has it. RS+AG != AR_hier."),
    ("col.eq.reducescatter_hier", "C", "Inter term N*b*(m-1)/(m*p_node)."),
    ("col.eq.alltoall_pairwise", "C", "(p-1)a + (p-1)/p*N*b."),
    ("col.eq.alltoall_hier", "C", "Two local permutes plus one inter-node exchange."),
    ("col.eq.allreduce", "S", "min over variants: assumes the runtime always picks the best algorithm."),
    ("col.eq.exposed_async_tp", "C", "max(0, T_comm - T_compute)."),
    ("link.eq.alpha_beta", "C", "alpha + B*beta + queueing (Hockney 1994)."),
    ("link.eq.effective_bw", "C", "line rate x packet eff x fabric eff / oversubscription."),
    ("link.eq.queue_per_packet", "C", "M/M/1 wait rho/(1-rho) x service time."),
    ("link.eq.queue_msg", "X", "Sums the per-packet wait over all packets; pipelined packets do not each wait, so it overcounts."),
    # ---- kernel / gpu / memory
    ("kernel.eq.roofline", "C", "min of compute and per-level AI x BW ceilings."),
    ("kernel.eq.time_body", "C", "max of the time lower bounds."),
    ("kernel.eq.matmul_flops", "C", "2MNK."),
    ("kernel.eq.matmul_bytes_tiled", "C", "A and B tiles per K-sweep per output tile, plus C write."),
    ("kernel.eq.attn_flops", "C", "4*BH*L^2*d*causal_factor."),
    ("kernel.eq.attn_bytes_naive", "S", "Score matrix counted once; real kernels move it 2-4 times."),
    ("kernel.eq.attn_bytes_flash", "S", "Q,K,V,O once; ignores K/V re-reads (IO is Theta(N^2 d^2 / M))."),
    ("kernel.eq.latency_hiding_factor", "S", "min(1, occ/occ_full): a heuristic, not from Dao or Williams."),
    ("gpu.eq.peak_flops", "C", "N_SM x per-SM peak."),
    ("arith.eq.peak_flops_sm", "C", "FLOP/MMA x MMA/cycle x tensor cores x clock."),
    ("gpu.eq.power_throttle_factor", "S", "Linear TDP/P. Real DVFS has P ~ f^2..3, so this over-throttles."),
    ("gpu.eq.memory_power", "C", "HBM bytes/s x J/byte x utilization."),
    ("mem.eq.hbm_bw_per_channel", "C", "pins x rate x eff / 8. H100: 5 x 1024 x 5.23 Gb/s / 8 = 3.35 TB/s."),
    ("mem.eq.hbm_bw_effective", "C", "Product of controller, thermal, bank, refresh factors."),
    ("mem.eq.avg_global_load_latency", "C", "Standard AMAT over L1, L2, HBM plus TLB."),
    # ---- thermal / cluster
    ("thermal.eq.dc_total_power", "C", "IT + cooling + UPS + transformer + lighting + misc."),
    ("thermal.eq.pue_definition", "C", "P_dc / P_IT."),
    ("thermal.eq.chiller_power", "C", "Q / COP."),
    ("thermal.eq.q_removed", "C", "m_dot c_p dT."),
    ("thermal.eq.pump_power_per_gpu", "C", "flow x dP / eta."),
    ("thermal.eq.water_evap_rate", "C", "Q/h_fg: 1 MW -> 1467 kg/h."),
    ("thermal.eq.water_blowdown_rate", "C", "E/(N_coc-1)."),
    ("thermal.eq.heat_to_reject", "S", "Excludes chiller compressor work from tower load."),
    ("cluster.eq.node_power", "C", "GPUs + CPU + RAM + NIC + SSD + misc."),
    ("cluster.eq.site_total_power_est", "X", "A second PUE-like constant (k_site_pow) not linked to thermal.dc.total_power."),
    ("cluster.eq.optimal_checkpoint_interval", "S", "Young 1974 sqrt(2*delta*M). Daly 2006 is 4% lower at delta/M=0.006. Needs delta << M."),
    ("cluster.eq.lost_work_fraction", "C", "T_opt/(2M)."),
    ("cluster.eq.availability_from_reliability", "X", "Formula is fine, but the output feeds nothing; training.cluster_availability is an unlinked root."),
    # ---- economics
    ("econ.eq.amortized", "S", "(C-resid)/life, straight line, zero cost of capital. Annuity at 10% WACC is ~28% higher (inferred)."),
    ("econ.eq.cluster_capex_rate", "S", "One life and one residual for IT and building alike."),
    ("econ.eq.job_capex_rate", "S", "Site rate x job share / utilization: job pays for idle share."),
    ("econ.eq.ws_from_kwh", "C", "1 kWh = 3.6e6 W*s."),
    ("econ.eq.capacity_charge_rate", "S", "30-day month (30.44 true). Presets double count it against an EIA average price."),
    ("econ.eq.carbon_emission_rate", "C", "I[kg/kWh]*P[W]/3.6e6."),
    ("econ.eq.carbon_cost_rate", "C", "kg/s x $/t / 1000."),
    ("econ.eq.maintenance_cost_rate", "C", "capex x fraction/yr / 365 d."),
    ("econ.eq.network_transit_cost_rate", "C", "B/s x $/GB / 1e9."),
    ("econ.eq.job_dc_power", "S", "Site power x GPU share; assumes uniform load."),
    ("econ.eq.run_power_cost", "C", "P x T x $/(W*s)."),
    ("econ.eq.run_total", "C", "hw + power + other opex."),
    ("econ.eq.cost_per_token", "C", "run cost / tokens."),
    ("econ.eq.discount_factor_run", "C", "(1+r)^(-T/yr); decorative."),
    # ---- optimizer / precision
    ("opt.eq.adam_step", "C", "AdamW with bias correction and decoupled decay."),
    ("opt.eq.lamb_step", "S", "Trust ratio unclamped (You et al. use a clamp function)."),
    ("opt.eq.lion_step", "C", "Chen et al. 2023."),
    ("opt.eq.muon_ns_iteration", "S", "Schematic: X^3 * X^T^2 is not a valid matrix expression; right only for scalars."),
    ("opt.eq.lr_cosine", "C", "Warmup then half cosine."),
    ("precision.eq.max_normal", "S", "IEEE-like only. OCP FP8 E4M3 gives 240 here vs 448 real."),
    ("precision.eq.machine_eps", "C", "2^-m (ULP at 1)."),
    ("precision.eq.quant_error_variance", "C", "q^2/12."),
    ("precision.eq.sr_error_variance", "C", "(x_hi-x)(x-x_lo)."),
    # ---- physical
    ("physical.eq.elmore_delay", "S", "Omits R_wire*C_load; no ln2. Fine only when wire C dominates the load."),
    ("physical.eq.clock_frequency_timing_model", "X", "f = eta/t_elmore of ONE stage; real paths are ~20-30 stages, so eta hides logic depth."),
    ("physical.eq.dynamic_power", "C", "alpha C V^2 f."),
    ("physical.eq.gate_input_capacitance", "S", "Cox*L*W only; no overlap or fringe capacitance."),
    ("physical.eq.interconnect_c_per_length_geom", "X", "Uses width/spacing; sidewall coupling goes as thickness/spacing. Fringe factor absorbs the error."),
    ("physical.eq.process_node_from_pitches", "S", "Node name = fudge factor x sqrt(CPP*MMP)."),
    ("physical.eq.landauer_energy", "C", "kT ln2."),
    ("physical.eq.mosfet_saturation", "C", "Square law with channel-length modulation."),
    ("memcell.eq.dram_charge_sharing", "X", "dV = C V/(C+Cbl) assumes a 0 V bitline; with Vdd/2 precharge the signal is half."),
    ("memcell.eq.sram_read_snm", "X", "Trip point minus read-disturb voltage is a margin, not a butterfly-curve SNM."),
    ("memcell.eq.dram_refresh_period", "S", "Q/I_leak uses full stored charge; usable charge is C*dV."),
    # ---- lithography / nuclear
    ("physical.eq.gate_lithography_resolution", "C", "Rayleigh CD = k1*lambda/NA."),
    ("physical.eq.lithography_numerical_aperture", "C", "n sin(theta)."),
    ("physical.eq.lithography_source_transition_energy", "X", "Hydrogenic Ry*Zeff^2*(1/n^2-1/(n+1)^2) with Slater-like screening. Sn^10+ gives 14.9 nm vs real 13.5 nm; not a many-electron line."),
    ("physical.eq.lithography_source_saha_ionization_fraction", "S", "Single-stage Saha; real Sn plasma needs the multi-stage balance."),
    ("physical.eq.lithography_source_nuclear_binding_energy", "S", "SEMF form is right. Effect on the wavelength is 4e-8 (reduced mass), so it cannot matter."),
    ("physical.eq.lithography_source_pairing_reference_mass_number", "X", "A_ref = A, so the pairing term is s*Delta_ref for every nucleus and loses its 1/sqrt(A) scaling."),
    ("physical.eq.lithography_medium_number_density_from_mass", "C", "N = rho/m with rho = m*phi/V: mass cancels, binding energy cannot affect N or n."),
    ("physical.eq.lithography_medium_component_a_effective_intercomponent_radius", "X", "Atomic spacing built from nuclear radius r0*A^(1/3) times a free scale factor (~1e5)."),
    ("physical.eq.lithography_medium_relative_permittivity", "C", "Clausius-Mossotti."),
    ("physical.eq.lithography_medium_electric_polarizability", "S", "Undamped Lorentz oscillator."),
    ("physical.eq.lithography_source_plasma_drive_spot_radius_from_focus", "C", "w0 = (2/pi) F# M^2 lambda."),
    ("physical.eq.lithography_source_plasma_absorption_cross_section_from_lorentz_oscillator", "S", "Lorentz line shape with collisional damping."),
]


def locate(name: str) -> str:
    pat = re.compile(r'^\s*"%s",?\s*$' % re.escape(name))
    pat2 = re.compile(r'"%s"' % re.escape(name))
    for path in sorted(glob.glob(os.path.join(ROOT, "gpu_stack", "scopes", "*.py"))):
        with open(path, encoding="utf-8") as fh:
            for i, line in enumerate(fh, 1):
                if pat.match(line) or (pat2.search(line) and ("eq(" in line or "Approximation(" in line)):
                    return f"{os.path.relpath(path, ROOT)}:{i}"
    return "?"


def main():
    csv_path = None
    if "--csv" in sys.argv:
        csv_path = sys.argv[sys.argv.index("--csv") + 1]
    feeds = set()
    for t in TARGETS:
        feeds |= cone(t, "graph")[1]
    # equations executed by shipped scenarios
    from gpu_stack.presets import scenarios
    from gpu_stack.presets.scenarios import SCENARIO_TARGET_SETS
    packs = {p.name: p for p in (scenarios.dense_training_cost_fixture, *scenarios.SOURCED_SCENARIO_PACKS)}
    executed = set()
    for name, targets in SCENARIO_TARGET_SETS.items():
        if name in packs:
            for t in packs[name].evaluate_targets(targets).targets:
                executed |= set(t.trace_equations)
    out = []
    missing = []
    for name, verdict, note in ROWS:
        e = Registry.equations.get(name)
        if e is None:
            missing.append(name)
            continue
        ext = any(r.kind in {"paper", "textbook", "standard", "datasheet", "manual", "database"} for r in e.references)
        out.append((name, locate(name), verdict, "cone" if name in feeds else "decorative",
                    "run" if name in executed else "-", "cites external work" if ext else "prose only", note))
    if missing:
        print("MISSING equation names:", missing)
    c = Counter(r[2] for r in out)
    names = {"C": "CORRECT", "S": "CORRECT-BUT-SIMPLIFIED", "X": "SUSPECT", "W": "WRONG", "R": "REFERENCE-MISMATCH"}
    print(f"{len(out)} equations reviewed")
    for k in "CSXWR":
        print(f"  {names[k]:24s} {c[k]}")
    print(f"  in headline cone: {sum(1 for r in out if r[3]=='cone')}; executed by a shipped scenario: {sum(1 for r in out if r[4]=='run')}")
    print(f"  cite an external work: {sum(1 for r in out if r[5].startswith('cites'))}")
    for r in out:
        if r[2] in "XWR":
            print(f"  {r[2]} {r[0]}  {r[1]}")
    if csv_path:
        with open(csv_path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["equation", "file:line", "verdict", "headline_cone", "run_by_shipped_scenario", "reference", "note"])
            w.writerows(out)


if __name__ == "__main__":
    main()
