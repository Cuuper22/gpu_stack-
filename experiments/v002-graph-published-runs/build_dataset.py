"""Build heldout-runs.json (the frozen held-out dataset for study V002).

Run once, before any prediction. Every number below was read by hand from the
cited primary source (PDF page numbers are PDF page indices of the file whose
SHA-256 is recorded under "sources"). Derived values are marked
kind="derived" and carry their arithmetic. The script does not fetch anything;
it reads local copies only to record their SHA-256.

Usage:
    python build_dataset.py <dir with downloaded sources> <out.json>
"""

from __future__ import annotations

import hashlib
import json
import os
import sys

SRC_DIR = sys.argv[1] if len(sys.argv) > 1 else "."
OUT = sys.argv[2] if len(sys.argv) > 2 else "heldout-runs.json"

# ---------------------------------------------------------------------------
# Sources: id -> (url, local file for hashing, description)
# ---------------------------------------------------------------------------
SOURCES = {
    "llama1": ("https://arxiv.org/abs/2302.13971", "llama1.pdf", "Touvron et al. 2023, LLaMA"),
    "llama2": ("https://arxiv.org/abs/2307.09288", "llama2.pdf", "Touvron et al. 2023, Llama 2"),
    "llama3": ("https://arxiv.org/abs/2407.21783", "llama3.pdf", "Llama Team 2024, The Llama 3 Herd of Models"),
    "llama31card": ("https://github.com/meta-llama/llama-models/blob/main/models/llama3_1/MODEL_CARD.md", "llama31_card.md", "Meta Llama 3.1 model card (raw file fetched 2026-10-01)"),
    "bloom": ("https://arxiv.org/abs/2211.05100", "bloom.pdf", "BigScience 2022, BLOOM"),
    "luccioni": ("https://arxiv.org/abs/2211.02001", "luccioni.pdf", "Luccioni et al. 2022, Estimating the carbon footprint of BLOOM"),
    "pythia": ("https://arxiv.org/abs/2304.01373", "pythia.pdf", "Biderman et al. 2023, Pythia"),
    "pythia_readme": ("https://github.com/EleutherAI/pythia", "pythia_readme.md", "Pythia README (raw file fetched 2026-10-01)"),
    "palm": ("https://arxiv.org/abs/2204.02311", "palm.pdf", "Chowdhery et al. 2022, PaLM"),
    "gopher": ("https://arxiv.org/abs/2112.11446", "gopher.pdf", "Rae et al. 2021, Gopher"),
    "falcon_tii": ("https://arxiv.org/abs/2311.16867", "falcon_tii.pdf", "Almazrouei et al. 2023, The Falcon Series"),
    "falcon_blog": ("https://huggingface.co/blog/falcon-180b", "falcon.html", "Hugging Face blog on TII Falcon-180B"),
    "mpt7b_blog": ("https://www.databricks.com/blog/mpt-7b", "mpt7b.html", "MosaicML/Databricks MPT-7B announcement, 2023-05-05"),
    "smollm3_blog": ("https://huggingface.co/blog/smollm3", "smollm3.html", "Hugging Face SmolLM3 blog"),
    "bloomberg": ("https://arxiv.org/abs/2303.17564", "bloomberg.pdf", "Wu et al. 2023, BloombergGPT"),
    "starcoder": ("https://arxiv.org/abs/2305.06161", "starcoder.pdf", "Li et al. 2023, StarCoder"),
    "mtnlg": ("https://arxiv.org/abs/2201.11990", "mtnlg.pdf", "Smith et al. 2022, Megatron-Turing NLG 530B"),
    "glm130b": ("https://arxiv.org/abs/2210.02414", "glm130b.pdf", "Zeng et al. 2022, GLM-130B"),
    "patterson": ("https://arxiv.org/abs/2104.10350", "patterson.pdf", "Patterson et al. 2021, Carbon emissions and large neural network training"),
    "olmo2": ("https://arxiv.org/abs/2501.00656", "olmo2.pdf", "OLMo Team 2025, 2 OLMo 2 Furious (v3)"),
    "olmo1": ("https://arxiv.org/abs/2402.00838", "olmo.pdf", "Groeneveld et al. 2024, OLMo"),
    "morrison": ("https://arxiv.org/abs/2503.05804", "morrison.pdf", "Morrison et al. 2025, Holistically evaluating the environmental impact of creating language models"),
    "a100ds": ("https://www.nvidia.com/content/dam/en-zz/Solutions/Data-Center/a100/pdf/nvidia-a100-datasheet-us-nvidia-1758950-r4-web.pdf", "a100ds.bin", "NVIDIA A100 datasheet"),
    "v100ds": ("https://images.nvidia.com/content/technologies/volta/pdf/tesla-volta-v100-datasheet-letter-fnl-web.pdf", "v100ds.bin", "NVIDIA V100 datasheet"),
    "h100page": ("https://www.nvidia.com/en-us/data-center/h100/", "h100_jina.txt", "NVIDIA H100 product page, fetched via r.jina.ai on 2026-10-01 (Product Specifications table)"),
    "dgxa100": ("https://images.nvidia.com/aem-dam/Solutions/Data-Center/nvidia-dgx-a100-datasheet.pdf", "dgxa100.pdf", "NVIDIA DGX A100 datasheet (used only for prior anchors in protocol)"),
    "megatron21": ("https://arxiv.org/abs/2104.04473", "megatron21.pdf", "Narayanan et al. 2021 (NOT a held-out record; MFU prior anchor only)"),
}

HF_API = {  # exact parameter counts from the Hugging Face model API `safetensors.total`, fetched 2026-10-01
    "meta-llama/Llama-2-7b-hf": (6738417664, "01c7f73d771dfac7d292323805ebc428287df4f9"),
    "meta-llama/Llama-2-13b-hf": (13015866880, "5c31dfb671ce7cfe2d7bb7c04375e44c55e815b1"),
    "meta-llama/Llama-2-70b-hf": (68976653312, "3aba440b59558f995867ba6e1f58f21d0336b5bb"),
    "meta-llama/Llama-3.1-8B": (8030261248, "d04e592bb4f6aa9cfee91e2e20afa771667e1d4b"),
    "meta-llama/Llama-3.1-70B": (70553706496, "349b2ddb53ce8f2849a6c168a81980ab25258dac"),
    "meta-llama/Llama-3.1-405B": (405853388800, "b906e4dc842aa489c962f9db26554dcfdde901fe"),
    "HuggingFaceTB/SmolLM3-3B-Base": (3075098624, "d78a42f79198603e614095753484a04c10c2b940"),
    "tiiuae/falcon-180B": (179522565120, "d2ea5531862d4fe907280234990e6380d2befd97"),
    "allenai/OLMo-2-1124-7B": (7298617344, "7df9a82518afdecae4e8c026b27adccc8c1f0032"),
    "allenai/OLMo-2-1124-13B": (13716198400, "3fefddc1bf18a30e1d9b91000271630718f2aa8b"),
}


def c(src, loc, quote=None):
    d = {"src": src, "loc": loc}
    if quote:
        d["quote"] = quote
    return d


def num(value, kind, cite, **extra):
    d = {"value": value, "kind": kind, "cite": cite}
    d.update(extra)
    return d


def hf(model):
    v, rev = HF_API[model]
    return num(
        v, "exact_hf_safetensors_total",
        [c("hf_api", f"https://huggingface.co/api/models/{model} field safetensors.total, revision {rev}")],
    )


# ---------------------------------------------------------------------------
# Hardware: peak dense 16-bit tensor FLOP/s and TDP (W) per accelerator
# ---------------------------------------------------------------------------
HARDWARE = {
    "A100-SXM-40GB": {
        "peak_flops_dense_16bit": 312e12, "tdp_w": 400.0,
        "cite": [c("a100ds", "PDF p1, spec table", "FP16 Tensor Core 312 TFLOPS | 624 TFLOPS* (*with sparsity); Max TDP SXM 400W")],
    },
    "A100-SXM-80GB": {
        "peak_flops_dense_16bit": 312e12, "tdp_w": 400.0,
        "cite": [c("a100ds", "PDF p1, spec table", "same 312 TFLOPS dense / 400W SXM column for 80GB"),
                 c("luccioni", "PDF p4 s4.2", "A100 SXM4 80GB TDP of 400W")],
    },
    "H100-SXM-80GB": {
        "peak_flops_dense_16bit": 989e12, "tdp_w": 700.0,
        "cite": [c("h100page", "Product Specifications table, H100 SXM column",
                   "BFLOAT16 Tensor Core* 1,979 teraFLOPS (*with sparsity); Max TDP up to 700W"),
                 c("llama3", "PDF p9", "each running at 700W TDP")],
        "note": "Dense peak = 1,979/2 = 989.5 TFLOP/s (derived: NVIDIA marks the 1,979 figure 'with sparsity'; "
                "the A100 datasheet shows the same 2x dense-to-sparse convention). Rounded to 989e12.",
    },
    "V100-SXM2": {
        "peak_flops_dense_16bit": 125e12, "tdp_w": 300.0,
        "cite": [c("v100ds", "PDF p1", "Tensor Performance 125 TFLOPS (SXM2); Max Power 300 W")],
    },
    "TPUv3": {
        "peak_flops_dense_16bit": 123e12, "tdp_w": 450.0,
        "cite": [c("patterson", "PDF p6, Table 4 and its footnote 12", "TDP 450 W; peak TeraFLOPS/second is ... 123 for TPU v3")],
    },
    "TPUv4": {
        "peak_flops_dense_16bit": 275e12, "tdp_w": None,
        "cite": [c("palm", "PDF p66, App. B", "(238.3 x 6 x 540)/(275 x 6144)")],
        "note": "No sourced TPU v4 TDP, so TPU v4 records cannot enter any TDP-based energy test.",
    },
}

# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------
R = []


def D(**kw):
    kw.setdefault("notes", [])
    return kw


def rec(**kw):
    kw.setdefault("stratum", "dense")
    kw.setdefault("notes", [])
    kw.setdefault("arch", None)
    kw.setdefault("mfu_reported", None)
    kw.setdefault("energy", None)
    kw.setdefault("accel_count", None)
    kw.setdefault("time", None)
    R.append(kw)


def hours(value, kind, cite, derivation=None):
    d = {"value": value, "kind": kind, "cite": cite}
    if derivation:
        d["derivation"] = derivation
    return d


# ---- LLaMA-1 (Meta; A100-80GB; GPU-hours in Table 15) ----------------------
for name, params, toks, gh in [
    ("7B", 6.7e9, 1.0e12, 82432),
    ("13B", 13.0e9, 1.0e12, 135168),
    ("33B", 32.5e9, 1.4e12, 530432),
    ("65B", 65.2e9, 1.4e12, 1022362),
]:
    r = D(
        id=f"llama1-{name.lower()}", name=f"LLaMA-{name}", family="llama1", tier="A",
        used_in=["T1"],
        params=num(params, "paper_rounded", [c("llama1", "PDF p3, Table 2", f"params {params/1e9:.1f}B")]),
        tokens=num(toks, "paper", [c("llama1", "PDF p3, Table 2", f"n tokens {toks/1e12:.1f}T")]),
        accelerator="A100-SXM-80GB",
        time={"accel_hours": hours(gh, "reported", [c("llama1", "PDF p11, Table 15", f"A100-80GB 400W GPU-hours {gh:,}")])},
    )
    if name == "65B":
        r["accel_count"] = num(2048, "reported", [c("llama1", "PDF p4", "380 tokens/sec/GPU on 2048 A100 GPU with 80GB")])
        r["notes"].append("Same paper states 380 tokens/s/GPU on 2048 GPUs and ~21 days for 1.4T tokens (PDF p4); "
                          "2048 x 21 d x 24 = 1,032,192 h, within 1% of Table 15 (consistency check only).")
    r["notes"].append("Table 15 GPU-hours are the authors' accounting (same table gives energy = hours x 400 W x PUE 1.1, i.e. circular for energy; energy not used).")
    rec(**r)

# ---- Llama 2 (A100-80GB; hours in Table 2; params exact from HF API) ----------
for name, gh, hfm in [
    ("7B", 184320, "meta-llama/Llama-2-7b-hf"),
    ("13B", 368640, "meta-llama/Llama-2-13b-hf"),
    ("34B", 1038336, None),
    ("70B", 1720320, "meta-llama/Llama-2-70b-hf"),
]:
    r = D(
        id=f"llama2-{name.lower()}", name=f"Llama 2 {name}", family="llama2", tier="A",
        used_in=["T1"],
        tokens=num(2.0e12, "paper", [c("llama2", "PDF p6, Table 1", f"{name} ... 2.0T")]),
        accelerator="A100-SXM-80GB",
        time={"accel_hours": hours(gh, "reported", [c("llama2", "PDF p7, Table 2", f"{name} GPU hours {gh}")])},
    )
    if hfm:
        r["params"] = hf(hfm)
    else:
        r["params"] = num(34e9, "nominal", [c("llama2", "PDF p6, Table 1", "34B (model never released; no exact count)")])
    r["notes"].append("Hardware: RSC (400 W cap) and a production cluster (350 W cap), PDF p6. GPU count and wall time not reported.")
    r["notes"].append("Reported power per GPU is the TDP cap, so Llama 2 energy is hours x TDP by construction; not used in energy tests.")
    rec(**r)

# ---- Llama 3.1 (H100-80GB; hours in model card; 405B paper) -------------------
rec(
    id="llama31-405b", name="Llama 3.1 405B", family="llama3", tier="A", used_in=["T1", "T2"],
    params=hf("meta-llama/Llama-3.1-405B"),
    tokens=num(15.6e12, "paper", [c("llama3", "PDF p1 and p3", "pre-train a model with 405B parameters on 15.6T tokens")]),
    accelerator="H100-SXM-80GB",
    accel_count=num(16384, "up_to", [c("llama3", "PDF p9", "trained on up to 16K H100 GPUs")]),
    time={"accel_hours": hours(30.84e6, "reported", [c("llama31card", "Training Time (GPU hours) table", "Llama 3.1 405B 30.84M")])},
    mfu_reported={
        "value": 0.41, "range": [0.38, 0.43], "convention": "BF16 MFU after Chowdhery et al. (PaLM definition)",
        "cite": [c("llama3", "PDF p10, Table 4 and text", "overall BF16 MFU of 38-43% ... 43% on 8K GPUs, 41% on 16K GPUs DP=128, 38% with CP=16")],
        "note": "Three stages with different MFU; the whole-run mix is unknown. value=0.41 is the middle stage; range is the full reported spread.",
    },
    notes=["Model card GPU hours cover the whole Llama 3.1 405B training including long-context continuation; paper says >90% effective training time (PDF p13).",
           "Tokens: paper gives 15.6T for the 405B pre-training; model card says '15T+'."],
)
for name, gh, hfm in [("8B", 1.46e6, "meta-llama/Llama-3.1-8B"), ("70B", 7.0e6, "meta-llama/Llama-3.1-70B")]:
    rec(
        id=f"llama31-{name.lower()}", name=f"Llama 3.1 {name}", family="llama3", tier="B", used_in=["T1_tierB"],
        params=hf(hfm),
        tokens=num(15e12, "lower_bound", [c("llama31card", "model table, Token count", "15T+")]),
        accelerator="H100-SXM-80GB",
        time={"accel_hours": hours(gh, "reported", [c("llama31card", "Training Time (GPU hours) table", f"Llama 3.1 {name} {gh/1e6:.2f}M (3 significant digits)")])},
        notes=["Tier B: token count is only given as '15T+' (a lower bound), so FLOPs are a lower bound."],
    )

# ---- Pythia (A100-40GB; counts and hours in Appendix D, Table 5) --------------
PYTHIA = [  # name, non-embedding params, layers, d_model, heads, gpus, gpu_hours
    ("70M", 18915328, 6, 512, 8, 32, 510),
    ("160M", 85056000, 12, 768, 12, 32, 1030),
    ("410M", 302311424, 24, 1024, 16, 32, 2540),
    ("1B", 805736448, 16, 2048, 8, 64, 4830),
    ("1.4B", 1208602624, 24, 2048, 16, 64, 7120),
    ("2.8B", 2517652480, 32, 2560, 32, 64, 14240),
    ("6.9B", 6444163072, 32, 4096, 32, 128, 33500),
    ("12B", 11327027200, 36, 5120, 40, 256, 72300),
]
for name, nonemb, L, d, H, g, gh in PYTHIA:
    total = nonemb + 2 * 50304 * d
    rec(
        id=f"pythia-{name.lower()}", name=f"Pythia {name}", family="pythia", tier="A", used_in=["T1", "S2"],
        params=num(total, "derived",
                   [c("pythia", "PDF p2, Table 1", f"non-embedding params {nonemb:,}"),
                    c("pythia_readme", "README Models table + HF config", "untied embedding and unembedding, vocab 50304")],
                   derivation=f"{nonemb} + 2 * 50304 * {d} (embedding + unembedding, both vocab x d_model)"),
        tokens=num(299892736000, "exact", [c("pythia_readme", "README: 'Each model saw 299,892,736,000 ~= 300B tokens'")]),
        accelerator="A100-SXM-40GB",
        accel_count=num(g, "reported", [c("pythia", "PDF p21, Table 5", f"{name} GPU count {g}")]),
        time={"accel_hours": hours(gh, "reported", [c("pythia", "PDF p21, Table 5", f"total GPU hours {gh:,} (iteration time x iterations x GPUs / 3600)")])},
        arch={"n_layers": L, "d_model": d, "d_ffn": 4 * d, "n_heads": H, "n_kv_heads": H, "vocab": 50304,
              "ffn_weight_matrices": 2, "untied_output": True, "norm_param_multiplier": 4,
              "cite": [c("pythia", "PDF p2, Table 1", f"layers {L}, model dim {d}, heads {H}"), c("pythia", "PDF p22, App. E config listing", "norm layernorm"),
                       c("pythia_readme", "README + HF config", "vocab 50304; d_ffn = 4 x d_model (HF config intermediate_size)")]},
        notes=["GPU-hours in Table 5 are computed from logged iteration time, not billed time (paper caption). fp16 except 1B (bf16); same A100 peak.",
               "Repo preset gpu_stack/presets/workload.py already contains Pythia-70M and 160M shapes (not hours); disclosed leakage of model shape only."],
    )

# ---- BLOOM-176B --------------------------------------------------------------
rec(
    id="bloom-176b", name="BLOOM 176B", family="bloom", tier="A", used_in=["T1", "S2"],
    params=num(176247e6, "paper", [c("bloom", "PDF p21, hyperparameter table", "Parameters 176,247M")]),
    tokens=num(366e9, "paper", [c("bloom", "PDF p21", "Total tokens 366B")]),
    accelerator="A100-SXM-80GB",
    accel_count=num(384, "reported", [c("bloom", "PDF p18, s3.4.1", "48 nodes, each having 8 NVIDIA A100 80GB GPUs (a total of 384 GPUs)")]),
    time={"accel_hours": hours(1082990, "reported",
                               [c("bloom", "PDF p18", "consumed 1,082,990 compute hours"),
                                c("luccioni", "PDF p2, Table 1", "Total training time 118 days, 5 hours, 41 min; GPU hours 1,082,990")])},
    arch={"n_layers": 70, "d_model": 14336, "d_ffn": 4 * 14336, "n_heads": 112, "n_kv_heads": 112, "vocab": 250680,
          "ffn_weight_matrices": 2, "untied_output": False, "norm_param_multiplier": 4,
          "cite": [c("bloom", "PDF p21 table", "Layers 70, Hidden dim 14336, Attention heads 112, Vocab 250,680, Tied emb True, GELU"),
                   c("bloom", "PDF p18", "final size of 250,680 vocabulary items")]},
    notes=["Best-configuration throughput 156 TFLOPs (PDF p20) is a peak figure, not stored as MFU.",
           "Luccioni's 433,196 kWh = 1,082,990 h x 0.4 kW exactly (PDF p4): TDP x hours by construction, excluded from energy tests."],
)

# ---- PaLM 540B (TPU v4) --------------------------------------------------------
rec(
    id="palm-540b", name="PaLM 540B", family="palm", tier="A", used_in=["T1", "T2"],
    params=num(540.35e9, "paper", [c("palm", "PDF p6, Table 1", "PaLM 540B 540.35 (billions)")]),
    tokens=num(780e9, "paper", [c("palm", "PDF p3", "780 billion tokens")]),
    accelerator="TPUv4",
    accel_count=num(6144, "reported", [c("palm", "PDF p1", "6144 TPU v4 chips")]),
    time={"accel_hours": hours(6144 * 1200 + 3072 * 336, "derived",
                               [c("palm", "PDF p66", "6144 TPU v4 chips for 1200 hours and 3072 TPU v4 chips for 336 hours including some downtime and repeated steps")],
                               derivation="6144*1200 + 3072*336 = 8,404,992 chip-hours")},
    mfu_reported={"value": 0.457, "range": [0.457, 0.462], "convention": "PaLM MFU: 45.7% without self-attention FLOPs, 46.2% with; 6ND matches the 'without' number",
                  "cite": [c("palm", "PDF p9", "MFU of PaLM 540B is 45.7% without self-attention or 46.2% with it; HFU 57.8%")]},
    notes=["Measured system power 378.5 W per chip and PUE 1.08 are reported (PDF p66) but TPU v4 has no sourced TDP, so no energy test."],
)

# ---- Gopher 280B (TPU v3) ------------------------------------------------------
rec(
    id="gopher-280b", name="Gopher 280B", family="gopher", tier="A", used_in=["T1", "T2"],
    params=num(280e9, "nominal", [c("gopher", "PDF p6, Table 1", "Gopher 280B")]),
    tokens=num(300e9, "paper", [c("gopher", "PDF p6", "We train all models for 300 billion tokens")]),
    accelerator="TPUv3",
    accel_count=num(4096, "reported", [c("gopher", "PDF p103, Table A27", "280B ... 4096 TPUv3 chips")]),
    time={"accel_hours": hours(4096 * 920, "derived", [c("gopher", "PDF p103", "We trained Gopher for 920 hours")],
                               derivation="4096 chips * 920 h = 3,768,320 chip-hours (assumes all 920 h on 4096 chips)")},
    mfu_reported={"value": 0.325, "range": [0.325, 0.325], "convention": "PaLM-paper MFU for Gopher, from 0.0152 steps/s (personal communication to PaLM authors)",
                  "cite": [c("palm", "PDF p9, Table 3 and text", "MFU number for Gopher is 32.5% based on training speed of 0.0152 steps per second")]},
    notes=["Gopher energy (1,066 MWh in Luccioni Table 4) = chip-hours x 283 W, a category-average power, not run-specific; not used."],
)

# ---- Falcon-180B (tier B: hours from a partner blog, rounded) ------------------
rec(
    id="falcon-180b", name="Falcon 180B", family="falcon", tier="B", used_in=["T1_tierB"],
    params=hf("tiiuae/falcon-180B"),
    tokens=num(3.5e12, "paper", [c("falcon_tii", "PDF p2, Table 1", "Pretraining [tokens] 3,500B"), c("falcon_blog", "blog text", "trained on 3.5 trillion tokens")]),
    accelerator="A100-SXM-40GB",
    accel_count=num(4096, "up_to", [c("falcon_tii", "PDF p2 and p24", "Training [A100s] 4,096; nodes with 8 x A100 40GB")]),
    time={"accel_hours": hours(7.0e6, "approximate", [c("falcon_blog", "blog text", "on up to 4096 GPUs simultaneously ... for a total of ~7,000,000 GPU hours")])},
    notes=["Tier B: GPU-hours is '~7,000,000' (one significant digit) from the Hugging Face blog, not from the TII paper."],
)

# ---- MPT-7B (MosaicML blog) -----------------------------------------------------
rec(
    id="mpt-7b", name="MPT-7B", family="mpt", tier="A", used_in=["T1"],
    params=num(6.7e9, "blog_rounded", [c("mpt7b_blog", "blog text", "MPT-7B Base is a decoder-style transformer with 6.7B parameters")]),
    tokens=num(1.0e12, "blog", [c("mpt7b_blog", "blog text", "trained on 1T tokens")]),
    accelerator="A100-SXM-40GB",
    accel_count=num(440, "reported", [c("mpt7b_blog", "blog text", "~9.5 days to train on 440xA100-40GB GPUs")]),
    time={"accel_hours": hours(440 * 9.5 * 24, "derived", [c("mpt7b_blog", "blog text + Table 3", "~9.5 days ... 440xA100-40GB; Time to Train is total runtime incl. restarts")],
                               derivation="440 * 9.5 d * 24 = 100,320 GPU-hours (days given to 0.5 d)")},
    notes=["Blog also states cost ~$200k at $2/A100-40GB/hr, i.e. hours x stated rate (circular; money not testable)."],
)

# ---- SmolLM3 (HF blog) -----------------------------------------------------------
rec(
    id="smollm3-3b", name="SmolLM3 3B", family="smollm3", tier="A", used_in=["T1", "S2"],
    params=hf("HuggingFaceTB/SmolLM3-3B-Base"),
    tokens=num(11.2e12, "blog", [c("smollm3_blog", "blog text", "we train SmolLM3 on 11.2T tokens using a three-stage training strategy")]),
    accelerator="H100-SXM-80GB",
    accel_count=num(384, "reported", [c("smollm3_blog", "blog text", "trained on 384 H100 GPUs for 24 days")]),
    time={"accel_hours": hours(384 * 24 * 24, "derived", [c("smollm3_blog", "blog text", "384 H100 GPUs for 24 days")],
                               derivation="384 * 24 d * 24 = 221,184 GPU-hours (days given to the day)")},
    arch={"n_layers": 36, "d_model": 2048, "d_ffn": 11008, "n_heads": 16, "n_kv_heads": 4, "vocab": 128256,
          "ffn_weight_matrices": 3, "untied_output": False, "norm_param_multiplier": 2,
          "cite": [c("hf_api", "https://huggingface.co/HuggingFaceTB/SmolLM3-3B-Base/raw/main/config.json",
                     "num_hidden_layers 36, hidden_size 2048, intermediate_size 11008, heads 16, kv heads 4, vocab 128256, tie_word_embeddings true, silu (gated), rms_norm_eps (RMSNorm: 2 norms x weight only)")]},
)

# ---- BloombergGPT -------------------------------------------------------------------
rec(
    id="bloomberggpt-50b", name="BloombergGPT 50B", family="bloomberg", tier="A", used_in=["T1", "S2"],
    params=num(50.6e9, "paper", [c("bloomberg", "PDF p11, Table 4", "Total Parameters 50.6B")]),
    tokens=num(569e9, "paper", [c("bloomberg", "PDF p11, Table 4", "Tokens 569B")]),
    accelerator="A100-SXM-40GB",
    accel_count=num(512, "reported", [c("bloomberg", "PDF p11, Table 4", "Hardware 64 x 8 A100 40GB")]),
    time={"accel_hours": hours(512 * 53 * 24, "derived", [c("bloomberg", "PDF p16", "139,200 steps (~53 days)")],
                               derivation="512 * 53 d * 24 = 651,264 GPU-hours; cross-check 139,200 steps x 32.5 s = 52.4 d (Table 4 step time)")},
    arch={"n_layers": 70, "d_model": 7680, "d_ffn": 4 * 7680, "n_heads": 40, "n_kv_heads": 40, "vocab": 131072,
          "ffn_weight_matrices": 2, "untied_output": False, "norm_param_multiplier": 4,
          "cite": [c("bloomberg", "PDF p11, Table 4 and s3.1", "70 layers, 40 heads, vocab 131,072, hidden 7,680; GELU FFN; tied embeddings")]},
    notes=["Paper also reports avg 102 TFLOPs per GPU (counts activation-checkpoint recompute), total FLOPS 2.36e23; not used as MFU (convention unclear)."],
)

# ---- StarCoderBase ----------------------------------------------------------------------
rec(
    id="starcoderbase-15b", name="StarCoderBase 15.5B", family="starcoder", tier="A", used_in=["T1"],
    params=num(15.5e9, "paper_approx", [c("starcoder", "PDF p17, Table 11", "Num. of parameters ~15.5B")]),
    tokens=num(1.0e12, "paper", [c("starcoder", "PDF p3 and p16", "250k iterations, batch 4M tokens, one trillion tokens")]),
    accelerator="A100-SXM-80GB",
    accel_count=num(512, "reported", [c("starcoder", "PDF p17, s5.6", "512 A100 80 GB GPUs distributed across 64 nodes")]),
    time={"accel_hours": hours(320256, "reported", [c("starcoder", "PDF p17, s5.7", "total number of GPU hours that training took (320,256)")])},
    notes=["Paper's energy (89,671.68 kWh) = 320,256 h x 280 W (assumed average power); circular, not used."],
)

# ---- MT-NLG 530B: three throughput benchmarks (not full runs) --------------------
for nodes, step_s, tflops in [(280, 60.1, 126), (350, 50.2, 121), (420, 44.4, 113)]:
    chips = nodes * 8
    r = D(
        id=f"mtnlg-530b-{nodes}n", name=f"MT-NLG 530B throughput, {nodes} DGX A100 nodes", family="mtnlg", tier="A",
        used_in=["T1"] + (["T2"] if nodes == 280 else []),
        kind="throughput_benchmark",
        params=num(530e9, "paper", [c("mtnlg", "PDF p10, s3.2", "scaled it up to 530 billion parameters")]),
        tokens=None,
        accelerator="A100-SXM-80GB",
        accel_count=num(chips, "reported", [c("mtnlg", "PDF p7, s2.3-2.4", f"{nodes} DGX A100 servers x 8 A100 80GB")]),
        time={"step_time_s": num(step_s, "reported", [c("mtnlg", "PDF p7, s2.4", "iteration times of 60.1, 50.2, and 44.4 seconds (280, 350, 420 servers, batch 1920)")]),
              "tokens_per_step": num(1920 * 2048, "derived", [c("mtnlg", "PDF p10, s3.2", "sequence length 2048, global batch size 1920")], derivation="1920 * 2048 = 3,932,160")},
        notes=["System benchmark of the training stack, not a full run; reported 126/121/113 teraFLOP/s per GPU (hardware FLOPs, PDF p7).",
               "Per-token cost = chips x step time / tokens per step; does not include restarts, evaluation or queue time."],
    )
    if nodes == 280:
        r["mfu_reported"] = {"value": 0.297, "range": [0.297, 0.302], "convention": "PaLM-paper MFU 29.7% without self-attention, 30.2% with, from 65.43K tokens/s (= 1920x2048/60.1 s)",
                             "cite": [c("palm", "PDF p9", "MFU ... for Megatron-Turing NLG 530B is 29.7% without self-attention or 30.2% with it based on 65.43K tokens/sec")]}
    rec(**r)

# ---- GLM-130B (tier B: wall time is an access window) -------------------------------------
rec(
    id="glm-130b", name="GLM-130B", family="glm", tier="B", used_in=["T1_tierB"],
    params=num(130e9, "nominal", [c("glm130b", "PDF p2", "130 billion parameters")]),
    tokens=num(400e9, "paper", [c("glm130b", "PDF p2", "pre-trained over 400 billion tokens on a cluster of 96 NVIDIA DGX-A100 (8x40G)")]),
    accelerator="A100-SXM-40GB",
    accel_count=num(768, "reported", [c("glm130b", "PDF p4", "96 DGX-A100 GPU (8x40G) servers")]),
    time={"accel_hours": hours(768 * 60 * 24, "upper_bound", [c("glm130b", "PDF p4 and p53", "with a 60-day access; training period spanned two months")],
                               derivation="768 * 60 d * 24 = 1,105,920 GPU-hours (60-day access window, so an upper bound)")},
    mfu_reported={"value": 0.325, "range": [0.325, 0.325], "convention": "PaLM definition; HFU 43.3%",
                  "cite": [c("glm130b", "PDF p5", "HFU of 43.3% and MFU of 32.5% due to re-materialization")]},
    notes=["Tier B: hours are bounded by a 60-day access window, not measured."],
)

# ---- Energy-only and power records ----------------------------------------------------------
# Patterson et al. 2021 Table 4: measured system average power per accelerator (incl. memory, NIC, fans, host CPU).
PATT = [  # key, name, params, chips, days, watts, pue, mwh, accel, tier
    ("t5-11b", "T5-11B", 11e9, 512, 20.0, 310.0, 1.12, 85.7, "TPUv3", "A"),
    ("meena", "Meena 2.6B", 2.6e9, 1024, 30.0, 289.0, 1.09, 232.0, "TPUv3", "A"),
    ("gshard-600b", "GShard-600B (MoE)", 619e9, 1024, 3.1, 288.0, 1.09, 24.1, "TPUv3", "A"),
    ("switch-1500b", "Switch Transformer 1500B (MoE)", 1500e9, 1024, 27.0, 245.0, 1.10, 179.0, "TPUv3", "B"),
    ("gpt3-175b", "GPT-3 175B", 175e9, 10000, 14.8, 330.0, 1.10, 1287.0, "V100-SXM2", "B"),
]
for key, nm, p, chips, days, watts, pue, mwh, acc, tier in PATT:
    ctier_note = {
        "B": "Tier B: " + ("Patterson text says Switch energy was 'estimated' (PDF p6) although Table 4 footnote 14 says Google models were measured."
                           if key.startswith("switch") else
                           "chip count 10,000 is an assumption from an NVIDIA press release (PDF p18 'we used NVIDIA's suggestion of 10,000 GPUs'); power and PUE were measured by OpenAI (footnote 14)."),
        "A": "Measured by Google (Table 4 footnote 14).",
    }[tier]
    rec(
        id=f"patterson-{key}", name=nm, family=f"patterson-{'gpt3' if key=='gpt3-175b' else 'google'}", tier=tier,
        stratum="moe" if "MoE" in nm else "dense", used_in=["E1"] if tier == "A" else ["E1_tierB"],
        kind="energy_only",
        params=num(p, "paper", [c("patterson", "PDF p6, Table 4", f"Number of Parameters (B) {p/1e9:g}")]),
        tokens=None,
        accelerator=acc,
        accel_count=num(chips, "reported" if tier == "A" else "assumed", [c("patterson", "PDF p6, Table 4", f"Number of Chips {chips:,}")]),
        time={"wall_days": num(days, "reported", [c("patterson", "PDF p6, Table 4", f"Training time (days) {days}")])},
        energy={
            "scope": "system_incl_host_and_pue",
            "avg_power_per_accel_w": num(watts, "measured", [c("patterson", "PDF p6, Table 4", "Measured System Average Power per Accelerator, including memory, network interface, fans, host CPU (W)")]),
            "pue": num(pue, "reported", [c("patterson", "PDF p6, Table 4", "Datacenter PUE (when it was run)")]),
            "energy_mwh": num(mwh, "reported", [c("patterson", "PDF p6, Table 4", "Energy Consumption (MWh)")]),
            "check": f"chips x days x 24 x W x PUE = {chips*days*24*watts*pue/1e6:.1f} MWh vs reported {mwh}",
        },
        notes=[ctier_note, "FLOPs and TFLOPS in Table 4 are derived from chips x time and are circular for time prediction; this record is used for power only."],
    )

# OLMo 2 7B / 13B: measured GPU power, extrapolated from one node (Table 19)
for name, hfm, toks, raw_mwh, pue, page_tok in [
    ("7B", "allenai/OLMo-2-1124-7B", 4.05e12, 131.0, 1.2, "7B is trained on 4.05 trillion tokens"),
    ("13B", "allenai/OLMo-2-1124-13B", 5.6e12, 257.0, 1.12, "13B is trained on 5.6 trillion tokens"),
]:
    rec(
        id=f"olmo2-{name.lower()}", name=f"OLMo 2 {name}", family="olmo2", tier="A", used_in=["E2"], kind="energy_only",
        params=hf(hfm),
        tokens=num(toks, "paper", [c("olmo2", "PDF p7", f"OLMo 2 {page_tok}")]),
        accelerator="H100-SXM-80GB",
        accel_count=None,
        energy={
            "scope": "gpu_only_raw",
            "gpu_energy_raw_mwh": num(raw_mwh, "measured_extrapolated",
                                      [c("olmo2", "PDF p35, Table 19", f"OLMo 2 {name} Total GPU Power (MWh) {raw_mwh:g}; PUE {pue}"),
                                       c("olmo2", "PDF p35", "power of an individual node every 25ms ... multiplying by the total number of nodes")]),
            "pue": num(pue, "reported", [c("olmo2", "PDF p35, Table 19", f"Power Usage Effect. {pue}")]),
        },
        notes=["Measured on one node and extrapolated to all nodes; GPU power only (Morrison et al. PDF p4: 'we only measure GPU power consumption'), so a lower bound on node energy.",
               "Morrison et al. 2025 Table 2 lists 157 MWh for 7B (= 131 x 1.2) and 230 MWh for 13B, which conflicts with 257 x 1.12 = 288; the OLMo 2 paper table is used and the conflict is recorded here.",
               "GPU-hours, GPU count and wall time are not reported, so the record enters only the end-to-end energy test (E2)."],
    )
rec(
    id="olmo1-7b-a100", name="OLMo 7B (MosaicML A100 run)", family="olmo1", tier="B", used_in=["E2_tierB"], kind="energy_only",
    params=num(6.9e9, "nominal", [c("olmo1", "PDF p3, Table 1", "7B")]),
    tokens=num(2.0e12, "lower_bound", [c("olmo1", "PDF p5", "both runs resulted in nearly identical performance ... by 2T tokens; checkpoint evaluated at 2.46T tokens")]),
    accelerator="A100-SXM-40GB",
    accel_count=num(216, "reported", [c("olmo1", "PDF p5", "MosaicML: 27 nodes, each node 8x NVIDIA A100 40GB")]),
    energy={"scope": "gpu_only_raw",
            "gpu_energy_raw_mwh": num(104.0, "measured_extrapolated", [c("olmo1", "PDF p18, Table 6", "OLMo-7B A100-40GB GPU Power Consumption (MWh) 104; PUE 1.1"),
                                                                       c("olmo2", "PDF p35, Table 19", "OLMo 7B 104, PUE 1.1")]),
            "pue": num(1.1, "reported", [c("olmo1", "PDF p18, Table 6", "PUE 1.1")])},
    notes=["Tier B: the paper does not say how many tokens the A100 run itself consumed (>=2T); params are the nominal '7B'."],
)

# ---------------------------------------------------------------------------
# Excluded candidates (so the reader can see what was dropped and why)
# ---------------------------------------------------------------------------
EXCLUDED = [
    {"id": "opt-175b", "reason": "Tokens consumed are not stated in the OPT paper (only a 300B-token LR schedule and a 180B-token corpus, PDF p2). GPU-hours 809,472 appear only as an assumption in the LLaMA paper (34 days on 992 GPUs, 'see their logs', PDF p10-11). The 147 TFLOP/s figure is 'up to'."},
    {"id": "gpt3-time", "reason": "GPU count (10,000 V100) is an assumption (Patterson PDF p18); total FLOPs and TFLOPS in Patterson Table 4 are derived from chips x time, so time prediction would be circular. GPT-3 enters only as an energy/power record (tier B)."},
    {"id": "patterson-time-and-flops", "reason": "Total computation = measured TFLOPS x chips x time in Table 4, circular for time."},
    {"id": "mlperf-training", "reason": "MLPerf GPT-3 runs start from a checkpoint and stop at a quality target; tokens consumed per submission are not in the results tables, and no primary source with the token count was found. Candidate for a later version."},
    {"id": "chinchilla-70b", "reason": "No chip count or training time found in the Chinchilla paper text."},
    {"id": "gpt-neox-20b", "reason": "Paper gives 96 A100-40GB but no training time or GPU-hours."},
    {"id": "phi-3-mini", "reason": "No hardware or training time found in the technical report text fetched."},
    {"id": "falcon-7b-40b", "reason": "TII paper gives 384 A100 but no wall time or GPU-hours."},
    {"id": "mpt-30b", "reason": "Only MFU lower bounds (>46% A100, >35% H100) across mixed clusters over 2 months; no hours."},
    {"id": "deepseek-v3", "reason": "MoE (37B active of 671B) trained with FP8 on H800 (2,664K GPU-hours pre-training, 14.8T tokens, 2048 H800; PDF p5, p11). H800 peak and FP8-to-peak mapping are not sourced in a primary document I could verify. Candidate for a later MoE/FP8 stratum."},
    {"id": "energy-llama-bloom-gopher-starcoder-opt", "reason": "Reported energy equals GPU-hours x a per-GPU power (TDP or a category-average) x PUE by construction (Luccioni: 1,082,990 h x 400 W = 433,196 kWh exactly; Llama: TDP; StarCoder: 280 W assumed; Gopher: 283 W category average). Using them would test the TDP baseline against itself."},
    {"id": "palm-energy", "reason": "Energy is implied by 378.5 W measured system power x chip-hours x PUE 1.08, but TPU v4 has no sourced TDP so the TDP baseline is undefined."},
    {"id": "money-all", "reason": "Every published dollar cost found is GPU-hours x a stated rental rate (MPT-7B ~$200k at $2/A100-40GB-hr; DeepSeek-V3 $5.576M at $2/H800-hr). That tests arithmetic, not the graph. The README's 'money' claim cannot be tested with primary data of this kind."},
    {"id": "megatron-lm-2021", "reason": "Throughput benchmarks and projected training times, not training runs. Used only as the source of the MFU prior anchor (Table 1: 44-52% of peak, PDF p16)."},
]

# ---------------------------------------------------------------------------
# Assemble
# ---------------------------------------------------------------------------
def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest(), os.path.getsize(path)


sources = {}
for sid, (url, fname, desc) in SOURCES.items():
    p = os.path.join(SRC_DIR, fname)
    entry = {"url": url, "description": desc, "retrieved": "2026-10-01"}
    if os.path.exists(p):
        entry["sha256"], entry["bytes"] = sha(p)
        entry["file"] = fname
    else:
        entry["sha256"] = None
    sources[sid] = entry
sources["hf_api"] = {"url": "https://huggingface.co/api/models/<org>/<model>", "description": "Hugging Face model API, safetensors.total and sha (revisions listed per record)", "retrieved": "2026-10-01", "sha256": None}

# sanity: every cited src exists
def _walk(o):
    if isinstance(o, dict):
        if "src" in o and "loc" in o:
            assert o["src"] in sources, o["src"]
        for v in o.values():
            _walk(v)
    elif isinstance(o, list):
        for v in o:
            _walk(v)

_walk(R)
_walk(HARDWARE)
for r in R:
    assert r["accelerator"] in HARDWARE, r["id"]
    assert r["tier"] in ("A", "B")

out = {
    "schema_version": 1,
    "study": "v002-graph-published-runs",
    "description": "Held-out published training runs, assembled from primary sources before any graph prediction was made.",
    "frozen_note": "SHA-256 of this file is recorded in protocol.md. Do not edit after freezing; deviations go in RESULT.md.",
    "units": {"params": "count", "tokens": "count", "accel_hours": "accelerator-hours", "peak_flops_dense_16bit": "FLOP/s per accelerator", "tdp_w": "W"},
    "tiers": {"A": "all inputs and the target are explicit in a primary source, rounding <= ~5%, no author-flagged assumption",
              "B": "an input or the target is bounded, rounded more coarsely, or partly assumed; analysed only as a sensitivity set"},
    "hardware_specs": HARDWARE,
    "records": R,
    "excluded": EXCLUDED,
    "sources": sources,
    "hf_api_snapshot": {k: {"safetensors_total": v[0], "revision": v[1]} for k, v in HF_API.items()},
}
with open(OUT, "w") as f:
    json.dump(out, f, indent=1, sort_keys=False)
    f.write("\n")
print("wrote", OUT, "records:", len(R), "excluded:", len(EXCLUDED))
