"""
gpu_stack.calculator_cost_basis
===============================

The cited cost inputs behind the calculator's defaults (``gpu_stack.calculator``).

Each constant is either a number read from a source (URL and access date next
to it) or an arithmetic combination of such numbers, written out so the
derivation can be re-run. The audit that collected these sources, with every
row's range, evidence and the value the calculator used before this change, is
``experiments/e003-heatwave/cost_audit/sources.json``; the test
``tests/test_calculator_cost_basis.py`` checks that this module and that table
agree.

Nothing here is a measurement of one specific cluster. Where a source gives a
range, the default is the midpoint and the range is kept in this module so the
sensitivity script can sweep it.

All sources were accessed on 2026-10-26.
"""

from __future__ import annotations

import statistics
from typing import Dict, Tuple

ACCESSED = "2026-10-26"

# ---------------------------------------------------------------------------
# GPU purchase prices (USD per GPU, new, SXM)
# ---------------------------------------------------------------------------

# IntuitionLabs, "Data Center GPU Pricing 2026" (published 2026-07-20, updated
# 2026-10-11), Table 2: H100 SXM5 80GB per GPU new, $35,000 to $40,000 (it
# cites CloudZero). https://intuitionlabs.ai/articles/data-center-gpu-pricing-2026
H100_PRICE_RANGE_USD: Tuple[float, float] = (35_000.0, 40_000.0)
H100_PRICE_USD: float = sum(H100_PRICE_RANGE_USD) / 2.0

# Jarvislabs, "A100 price" (March 2026 snapshot, updated 2026-10): A100 80GB
# SXM new, $10,000 to $15,000. https://jarvislabs.ai/blog/a100-price
A100_PRICE_RANGE_USD: Tuple[float, float] = (10_000.0, 15_000.0)
A100_PRICE_USD: float = sum(A100_PRICE_RANGE_USD) / 2.0

# ---------------------------------------------------------------------------
# Electricity
# ---------------------------------------------------------------------------

# U.S. EIA, Electric Power Annual 2025, Table 2.10 (average price by state and
# sector): U.S. industrial 8.51 cents/kWh. This is revenue divided by sales,
# so it already contains the utilities' energy, delivery and demand charges.
# https://www.eia.gov/electricity/annual/html/epa_02_10.html
ELECTRICITY_USD_PER_KWH: float = 0.0851

# ---------------------------------------------------------------------------
# Useful life of GPU servers (years), as the operators report it
# ---------------------------------------------------------------------------

# (operator, years, source). Where a filing gives a range the upper end is
# used, because that is the life applied to newly bought AI servers.
OPERATOR_SERVER_LIVES: Tuple[Tuple[str, float, str], ...] = (
    ("Microsoft", 6.0, "https://www.hudson-labs.com/research/msft-server-useful-life"),
    ("Alphabet", 6.0, "https://abc.xyz/investor/static/pdf/2022Q4_alphabet_earnings_release.pdf"),
    ("Meta", 5.5, "https://investor.atmeta.com/investor-news/press-release-details/2025/"
                  "Meta-Reports-Fourth-Quarter-and-Full-Year-2024-Results/default.aspx"),
    ("Amazon", 5.0, "https://app.edgar.tools/companies/AMZN/disclosures/property-plant-equipment"),
    ("Oracle", 5.5, "https://www.globaldatacenterhub.com/p/how-long-does-an-ai-chip-last-and"),
    ("CoreWeave", 6.0, "https://blockspace.media/insight/coreweave-a100-contract-challenges-gpu-depreciation-model/"),
    ("Nebius", 4.0, "https://thecuberesearch.com/298-breaking-analysis-resetting-gpu-depreciation-why-ai-factories-"
                    "bend-but-dont-break-useful-life-assumptions/"),
    ("Lambda", 5.0, "https://thecuberesearch.com/298-breaking-analysis-resetting-gpu-depreciation-why-ai-factories-"
                    "bend-but-dont-break-useful-life-assumptions/"),
)
USEFUL_LIFE_RANGE_YEARS: Tuple[float, float] = (
    min(y for _, y, _ in OPERATOR_SERVER_LIVES),
    max(y for _, y, _ in OPERATOR_SERVER_LIVES),
)
USEFUL_LIFE_YEARS: float = float(statistics.median(y for _, y, _ in OPERATOR_SERVER_LIVES))

# Amazon FY2025 10-K, property and equipment: heavy equipment ten to thirteen
# years, buildings up to forty years. The facility slice uses the upper end of
# heavy equipment (power and cooling plant dominate the facility cost).
# https://app.edgar.tools/companies/AMZN/disclosures/property-plant-equipment
FACILITY_USEFUL_LIFE_YEARS: float = 13.0

# ---------------------------------------------------------------------------
# Everything bought with a GPU except the GPU card (as a share of its price)
# ---------------------------------------------------------------------------

# Server without its GPUs, per GPU. NVIDIA DGX H100 8-GPU system $300,000 to
# $460,000 (midpoint $380,000; DeployBase via IntuitionLabs, Q1-Q2 2026) and an
# HGX H100 8-GPU server about $339,000 (AMCompute GPU server values, August
# 2026 data, "estimated from GPU list price; not a quoted server price"). The
# non-GPU part is the system price minus eight GPUs; the default is the middle
# of the HGX and DGX values.
# https://intuitionlabs.ai/articles/data-center-gpu-pricing-2026
# https://www.amcompute.com/gpu-server-values
DGX_H100_SYSTEM_USD: float = 380_000.0
HGX_H100_SYSTEM_USD: float = 339_000.0
GPUS_PER_SYSTEM: int = 8
SERVER_NON_GPU_PER_GPU_USD: float = (
    ((HGX_H100_SYSTEM_USD - GPUS_PER_SYSTEM * H100_PRICE_USD) / GPUS_PER_SYSTEM)
    + ((DGX_H100_SYSTEM_USD - GPUS_PER_SYSTEM * H100_PRICE_USD) / GPUS_PER_SYSTEM)
) / 2.0

# Network and everything else for a 24,576 x H100 cluster (Meta, May 2024
# estimate): switches, transceivers and adapters $185.2M; everything else
# $86.0M. https://www.amcompute.com/blog/ai-cluster-cost-breakdown-capex
META_CLUSTER_GPUS: int = 24_576
NETWORK_PER_GPU_USD: float = 185.2e6 / META_CLUSTER_GPUS
OTHER_IT_PER_GPU_USD: float = 86.0e6 / META_CLUSTER_GPUS

OTHER_HARDWARE_FRACTION_EXACT: float = (
    SERVER_NON_GPU_PER_GPU_USD + NETWORK_PER_GPU_USD + OTHER_IT_PER_GPU_USD
) / H100_PRICE_USD
OTHER_HARDWARE_FRACTION: float = round(OTHER_HARDWARE_FRACTION_EXACT, 2)

# ---------------------------------------------------------------------------
# Facility (building shell, electrical and mechanical plant)
# ---------------------------------------------------------------------------

# JLL forecast: global average data centre construction cost $11.3 million per
# MW in 2026 (liquid cooling adds $1-2 million per MW; the article does not say
# whether the MW is IT or total, and this module reads it as IT load).
# https://www.datacentres.com/news/data-centre-construction-costs-11m-per-mw
# Bernstein puts mechanical and electrical at about one third of $35 billion
# per GW, about $11.7 million per MW, which agrees.
# https://www.investing.com/news/stock-market-news/how-much-does-a-gw-of-data-center-capacity-actually-cost-4314046
FACILITY_USD_PER_W: float = 11.3

# ---------------------------------------------------------------------------
# Power at the server
# ---------------------------------------------------------------------------

# Measured average power of one 8-GPU H100 node during LLM training: median of
# the five listed averages (7.79, 7.67, 7.73, 5.91 and 6.78 kW), against the
# 10.2 kW rating. https://arxiv.org/pdf/2506.14551 (Table 2, re-read 2026-10-26)
H100_NODE_MEASURED_SAMPLES_W: Tuple[float, ...] = (7_790.0, 7_670.0, 7_730.0, 5_910.0, 6_780.0)
H100_NODE_MEASURED_AVG_W: float = statistics.median(H100_NODE_MEASURED_SAMPLES_W)
H100_TDP_W: float = 700.0
# The calculator's GPU load (an uncited assumption, kept at its earlier value).
GPU_POWER_FRACTION: float = 0.80
# Extra server power as a share of the GPUs' own power, set so that the
# calculator's node power equals the measured node average:
#   8 x 700 W x 0.80 x (1 + s) = measured average.
SERVER_POWER_FRACTION_EXACT: float = (
    H100_NODE_MEASURED_AVG_W / (GPUS_PER_SYSTEM * H100_TDP_W * GPU_POWER_FRACTION) - 1.0
)
SERVER_POWER_FRACTION: float = round(SERVER_POWER_FRACTION_EXACT, 2)

# Before this change (for the before/after script): see CORRECTION.md.
LEGACY_DEFAULTS: Dict[str, float] = {
    "electricity_price": 0.0813,
    "useful_life_years": 4.0,
    "other_hardware_fraction": 0.40,
    "server_power_fraction": 0.25,
    "h100_price": 30_000.0,
    "a100_price": 15_000.0,
}

__all__ = [
    "A100_PRICE_RANGE_USD", "A100_PRICE_USD", "ACCESSED", "DGX_H100_SYSTEM_USD",
    "ELECTRICITY_USD_PER_KWH", "FACILITY_USD_PER_W", "FACILITY_USEFUL_LIFE_YEARS",
    "GPUS_PER_SYSTEM", "GPU_POWER_FRACTION", "H100_NODE_MEASURED_AVG_W", "H100_NODE_MEASURED_SAMPLES_W",
    "H100_PRICE_RANGE_USD", "H100_PRICE_USD", "H100_TDP_W", "HGX_H100_SYSTEM_USD",
    "LEGACY_DEFAULTS", "META_CLUSTER_GPUS", "NETWORK_PER_GPU_USD", "OPERATOR_SERVER_LIVES",
    "OTHER_HARDWARE_FRACTION", "OTHER_HARDWARE_FRACTION_EXACT", "OTHER_IT_PER_GPU_USD",
    "SERVER_NON_GPU_PER_GPU_USD", "SERVER_POWER_FRACTION", "SERVER_POWER_FRACTION_EXACT",
    "USEFUL_LIFE_RANGE_YEARS", "USEFUL_LIFE_YEARS",
]
