"""Electricity's share of cost per token: sensitivity audit (e003, T10).

Reads the cited inputs in ``sources.json`` (next to this file), runs ``gpu_stack.calculator.estimate``
for the README example and for one-at-a-time and grid variations, and translates the e003 timing
savings (``results/cost-v1.json``) into a change in total cost per token.  Writes

    experiments/e003-heatwave/results/cost-audit-v1.json   (with provenance)
    experiments/e003-heatwave/results/cost-audit-v1.md     (generated tables)
    experiments/e003-heatwave/cost_audit/SOURCES.md        (generated sources table)

Run from anywhere:  PYTHONPATH=<this repo>:<heatwave repo> python experiments/e003-heatwave/cost_audit/run_cost_audit.py

Every price, power, life and rate used here is read from ``sources.json`` (each row has a URL and
an access date) or from ``gpu_stack.calculator_cost_basis``; the only numbers typed in this file are
the grid axes (which rows to sweep) and the load factors named below, all labelled as assumptions.
Nothing is measured on a real cluster.  The workload is the README example: 7e9 parameters,
2e12 tokens, 1,024 GPUs.
"""

from __future__ import annotations

import contextlib
import itertools
import json
import statistics
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from gpu_stack import calculator  # noqa: E402
from gpu_stack import calculator_cost_basis as basis  # noqa: E402
from gpu_stack.presets.hardware import H100_SXM_BF16_DENSE_FLOPS  # noqa: E402

SOURCES = HERE / "sources.json"
COST_V1 = HERE.parent / "results" / "cost-v1.json"
OUT = HERE.parent / "results" / "cost-audit-v1.json"
OUT_MD = HERE.parent / "results" / "cost-audit-v1.md"
SOURCES_MD = HERE / "SOURCES.md"

PARAMS, TOKENS, N_GPUS = 7e9, 2e12, 1024  # the README example

# Assumptions made in this file (not read from a source); each is labelled in the output.
ASSUMED_LOAD_FACTORS = (1.0, 0.7)  # tariff demand charge spread over kWh; 0.7 is the e003 scenario utilization
HOURS_PER_MONTH = 8760.0 / 12.0
MFU_RANGE = (0.30, 0.55)  # the range the calculator's own help text gives for real runs (uncited there)
SHARE_LEVELS = (0.10, 0.20, 0.30, 0.50)  # thresholds used to report where electricity becomes a given share
HEADLINE_LAMBDA = 0.5
HEADLINE_KEY = "timestral_28M|f=0.3|W=24|rho=0.7|q=0.5"


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

SRC = json.loads(SOURCES.read_text())
ROWS: Dict[str, Dict[str, Any]] = {r["id"]: r for r in SRC["rows"]}


def row(rid: str) -> Dict[str, Any]:
    return ROWS[rid]


def val(rid: str) -> float:
    v = ROWS[rid]["value"]
    if v is None:
        raise KeyError(f"{rid} has no value")
    return float(v)


def lo_hi(rid: str) -> Tuple[float, float]:
    r = ROWS[rid]
    return float(r["low"]), float(r["high"])


# ---------------------------------------------------------------------------
# e003 timing savings, read from the committed cost result
# ---------------------------------------------------------------------------

COST = json.loads(COST_V1.read_text())["result"]


def timing_saving(pair: str, lam: float) -> Dict[str, float]:
    c = COST["pairs"][pair]["curves"][HEADLINE_KEY]
    i = COST["scenario"]["lambdas"].index(lam)
    return {
        "saving_electricity_frac": c["saving_pct_electricity"][i] / 100.0,
        "saving_total_frac_in_cost_v1": c["saving_pct_total"][i] / 100.0,
        "wholesale_mean_usd_per_kwh": COST["pairs"][pair]["mean_price_test"] * COST["pairs"][pair]["usd_per_price_unit"] / 1000.0,
    }


TIMING = {
    "caiso": {"lambda_0.5": timing_saving("caiso", 0.5), "lambda_0": timing_saving("caiso", 0.0)},
    "de": {"lambda_0.5": timing_saving("de", 0.5), "lambda_0": timing_saving("de", 0.0)},
}
USD_PER_EUR = float(COST["pairs"]["de"]["usd_per_price_unit"])


# ---------------------------------------------------------------------------
# Chips: every bundle field comes from a sources.json row
# ---------------------------------------------------------------------------

NODE_RATED_RATIO = basis.H100_NODE_MEASURED_AVG_W / val("power.dgx_h100.system")  # measured / rated, one H100 node


def _server_power_fraction(rated_w_per_gpu: float, tdp_w: float) -> float:
    """Extra server power so a node draws the same share of its rated power as the measured H100 node does."""
    return round(NODE_RATED_RATIO * rated_w_per_gpu / (tdp_w * basis.GPU_POWER_FRACTION) - 1.0, 2)


def _addon_h100() -> float:
    return basis.NETWORK_PER_GPU_USD + basis.OTHER_IT_PER_GPU_USD


_B200C = row("net.amcompute_b200_576")
_ADDON_B200 = (_B200C["network"] + _B200C["storage"] + _B200C["other"]) / _B200C["n_gpus"]


def build_chips() -> Dict[str, Dict[str, Any]]:
    h100 = calculator.GPUS["H100-SXM"]
    chips: Dict[str, Dict[str, Any]] = {}
    chips["H100"] = {
        "gpu": h100, "gpu_price": basis.H100_PRICE_USD, "other_hardware_fraction": basis.OTHER_HARDWARE_FRACTION,
        "server_power_fraction": basis.SERVER_POWER_FRACTION, "tdp_w": 700.0, "peak_flops": H100_SXM_BF16_DENSE_FLOPS,
        "price_range_ratio": (lo_hi("price.h100.gpu_sxm5")[0] / val("price.h100.gpu_sxm5"),
                              lo_hi("price.h100.gpu_sxm5")[1] / val("price.h100.gpu_sxm5")),
        "price_basis": "H100 SXM5 card (IntuitionLabs) x (1 + servers, network, storage share from calculator_cost_basis)",
        "rental_ids": ["rent.h100.lambda_sxm", "rent.h100.runpod_sxm", "rent.h100.aws_p5", "rent.h100.coreweave",
                       "rent.h100.spheron_ondemand"],
    }
    # H200: HGX system and DGX system midpoint, per GPU, plus the H100 cluster's network and other hardware per GPU.
    h200_sys = (val("price.h200.sys_hgx_new") + val("price.h200.sys_dgx")) / 2.0 / 8.0
    chips["H200"] = {
        "gpu": replace(h100, key="H200-SXM", label="NVIDIA H200 SXM"), "gpu_price": h200_sys,
        "other_hardware_fraction": round(_addon_h100() / h200_sys, 2),
        "server_power_fraction": _server_power_fraction(val("power.dgx_h100.system") / 8.0, val("power.h200.tdp")),
        "tdp_w": val("power.h200.tdp"), "peak_flops": val("flops.h200.bf16_sparse") / 2.0,
        "price_range_ratio": (((val("price.h200.sys_hgx_new") + lo_hi("price.h200.sys_dgx")[0]) / 2.0) /
                              ((val("price.h200.sys_hgx_new") + val("price.h200.sys_dgx")) / 2.0),
                              ((val("price.h200.sys_hgx_new") + lo_hi("price.h200.sys_dgx")[1]) / 2.0) /
                              ((val("price.h200.sys_hgx_new") + val("price.h200.sys_dgx")) / 2.0)),
        "price_basis": "mean of HGX H200 (AMCompute) and DGX H200 (IntuitionLabs) system prices, per GPU, plus H100-cluster network and other IT per GPU",
        "rental_ids": ["rent.h200.runpod", "rent.h200.coreweave"],
    }
    b200_sys = val("price.b200.sys_hgx") / 8.0
    chips["B200"] = {
        "gpu": replace(h100, key="B200-SXM", label="NVIDIA B200 (HGX)"), "gpu_price": b200_sys,
        "other_hardware_fraction": round(_ADDON_B200 / b200_sys, 2),
        "server_power_fraction": _server_power_fraction(val("power.b200.dgx_system") / 8.0, val("power.b200.tdp")),
        "tdp_w": val("power.b200.tdp"), "peak_flops": val("flops.b200.bf16_sparse_hgx8") / 8.0 / 2.0,
        "price_range_ratio": (lo_hi("price.b200.sys_hgx")[0] / val("price.b200.sys_hgx"),
                              lo_hi("price.b200.sys_hgx")[1] / val("price.b200.sys_hgx")),
        "price_basis": "HGX B200 8-GPU server (AMCompute) per GPU, plus 576-GPU B200 cluster network, storage and other per GPU",
        "rental_ids": ["rent.b200.lambda", "rent.b200.coreweave"],
    }
    gb_rack = val("price.gb200.rack") / 72.0
    chips["GB200"] = {
        "gpu": replace(h100, key="GB200-NVL72", label="NVIDIA GB200 (NVL72)"), "gpu_price": gb_rack,
        "other_hardware_fraction": round(_ADDON_B200 / gb_rack, 2),
        "server_power_fraction": _server_power_fraction(val("power.gb200.rack") / 72.0, val("power.gb200.gpu")),
        "tdp_w": val("power.gb200.gpu"), "peak_flops": val("flops.gb200.bf16_dense"),
        "price_range_ratio": (lo_hi("price.gb200.rack")[0] / val("price.gb200.rack"),
                              lo_hi("price.gb200.rack")[1] / val("price.gb200.rack")),
        "price_basis": "GB200 NVL72 rack price (Wing VC) per GPU, plus 576-GPU B200 cluster network, storage and other per GPU",
        "rental_ids": ["rent.gb200.coreweave"],
    }
    return chips


CHIPS = build_chips()


def rental_rate(chip: str, kind: str) -> float:
    """USD per GPU-hour: median on-demand across listed providers; committed = on-demand x (1 - discount)."""
    od = statistics.median(val(i) for i in CHIPS[chip]["rental_ids"])
    if kind == "on_demand":
        return od
    if kind == "committed_1y":
        return od * (1.0 - val("rent.discount.committed_1y"))
    if kind == "committed_3y":
        return od * (1.0 - val("rent.discount.committed_3y"))
    raise KeyError(kind)


# ---------------------------------------------------------------------------
# Electricity price cases
# ---------------------------------------------------------------------------

_E20 = row("elec.pge_e20_transmission")
_E20_ENERGY = statistics.mean(_E20["energy_usd_per_kwh"])


def tariff_built(load_factor: float) -> float:
    """PG&E E-20 transmission: mean of the five listed energy rates plus the demand charge spread over kWh."""
    return _E20_ENERGY + _E20["demand_usd_per_kw_month"] / (HOURS_PER_MONTH * load_factor)


REGIONS: List[Dict[str, Any]] = [
    {"id": "NM", "label": "New Mexico industrial average (EIA 2025, lowest state)", "usd_per_kwh": val("elec.eia2025.nm_industrial"),
     "source_ids": ["elec.eia2025.nm_industrial"]},
    {"id": "TX", "label": "Texas industrial average (EIA 2025)", "usd_per_kwh": val("elec.eia2025.tx_industrial"),
     "source_ids": ["elec.eia2025.tx_industrial"]},
    {"id": "US", "label": "U.S. industrial average (EIA 2025), the calculator default", "usd_per_kwh": val("elec.eia2025.us_industrial"),
     "source_ids": ["elec.eia2025.us_industrial"]},
    {"id": "VA", "label": "Virginia industrial average (EIA 2025)", "usd_per_kwh": val("elec.eia2025.va_industrial"),
     "source_ids": ["elec.eia2025.va_industrial"]},
    {"id": "CA-E20", "label": f"California PG&E E-20 transmission tariff, energy + demand charge only, load factor {ASSUMED_LOAD_FACTORS[0]} "
     "(riders and non-avoidable charges not itemised in the source)", "usd_per_kwh": tariff_built(ASSUMED_LOAD_FACTORS[0]),
     "source_ids": ["elec.pge_e20_transmission"]},
    {"id": "DE", "label": "Germany industry average (BDEW 2026 year to date, EUR converted at the e003 mean ECB rate)",
     "usd_per_kwh": val("elec.de.bdew_industry") * USD_PER_EUR, "source_ids": ["elec.de.bdew_industry"], "wholesale_pair": "de"},
    {"id": "CA", "label": "California industrial average (EIA 2025)", "usd_per_kwh": val("elec.eia2025.ca_industrial"),
     "source_ids": ["elec.eia2025.ca_industrial"], "wholesale_pair": "caiso"},
]
REGIONS_EXTRA = [
    {"id": "CA-E20-LF0.7", "label": f"California PG&E E-20 transmission, energy + demand only, load factor {ASSUMED_LOAD_FACTORS[1]}",
     "usd_per_kwh": tariff_built(ASSUMED_LOAD_FACTORS[1]), "source_ids": ["elec.pge_e20_transmission"], "wholesale_pair": "caiso"},
]
for _r in REGIONS:
    if _r["id"] == "CA-E20":
        _r["wholesale_pair"] = "caiso"

PUE_CASES = [("Google fleet", val("pue.google")), ("calculator default", 1.2), ("Uptime capacity-weighted", val("pue.uptime_weighted")),
             ("Uptime per-facility mean", val("pue.uptime_mean"))]
LIFE_CASES = [4.0, 5.0, 6.0]


# ---------------------------------------------------------------------------
# Running the calculator
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def facility(usd_per_w: Optional[float] = None, life_years: Optional[float] = None) -> Iterator[None]:
    """Temporarily change the facility constants the calculator reads from ``calculator_cost_basis``."""
    old = (basis.FACILITY_USD_PER_W, basis.FACILITY_USEFUL_LIFE_YEARS)
    try:
        if usd_per_w is not None:
            basis.FACILITY_USD_PER_W = usd_per_w
        if life_years is not None:
            basis.FACILITY_USEFUL_LIFE_YEARS = life_years
        calculator.build_model.cache_clear()
        yield
    finally:
        basis.FACILITY_USD_PER_W, basis.FACILITY_USEFUL_LIFE_YEARS = old
        calculator.build_model.cache_clear()


def run(chip: str = "H100", *, price_ratio: float = 1.0, basis_kind: str = "purchase", fac_usd_per_w: Optional[float] = None,
        fac_life: Optional[float] = None, rental_override: Optional[float] = None, **kw: float) -> Dict[str, Any]:
    c = CHIPS[chip]
    args: Dict[str, Any] = {
        "gpu_price": c["gpu_price"] * price_ratio, "other_hardware_fraction": c["other_hardware_fraction"],
        "server_power_fraction": c["server_power_fraction"], "tdp_w": c["tdp_w"], "peak_flops": c["peak_flops"],
    }
    args.update(kw)
    ctx = facility(fac_usd_per_w, fac_life) if (fac_usd_per_w is not None or fac_life is not None) else contextlib.nullcontext()
    with ctx:
        e = calculator.estimate(PARAMS, TOKENS, c["gpu"], N_GPUS, **args)
    mtok = TOKENS / 1e6
    out: Dict[str, Any] = {
        "chip": chip, "basis": basis_kind, "gpu_hours": e.gpu_hours, "training_days": e.training_days, "energy_mwh": e.energy_mwh,
        "electricity_cost_usd": e.electricity_cost, "inputs": {k: e.inputs[k] for k in sorted(e.inputs)},
    }
    if basis_kind == "purchase":
        out["hardware_cost_usd"] = e.hardware_cost
        out["total_cost_usd"] = e.total_cost
        out["rental_usd_per_gpu_hour"] = None
    else:
        rate = rental_override if rental_override is not None else rental_rate(chip, basis_kind)
        out["rental_usd_per_gpu_hour"] = rate
        out["hardware_cost_usd"] = None
        out["total_cost_usd"] = rate * e.gpu_hours  # price paid to the lessor; electricity is inside it
    out["total_usd_per_mtoken"] = out["total_cost_usd"] / mtok
    out["electricity_usd_per_mtoken"] = e.electricity_cost / mtok
    out["electricity_share"] = e.electricity_cost / out["total_cost_usd"]
    out["electricity_usd_per_kwh"] = e.inputs["electricity_price"]
    return out


def timing_columns(case: Dict[str, Any], region: Optional[Dict[str, Any]]) -> Dict[str, float]:
    """Change in total cost per token if electricity cost falls by the e003 savings (negative = cheaper)."""
    share = case["electricity_share"]
    out: Dict[str, float] = {}
    for pair, tag in (("caiso", "caiso"), ("de", "de")):
        s = TIMING[pair]["lambda_0.5"]["saving_electricity_frac"]
        out[f"delta_total_pct_if_whole_bill_follows_wholesale_{tag}"] = -100.0 * share * s
    if region is not None and region.get("wholesale_pair"):
        pair = region["wholesale_pair"]
        s = TIMING[pair]["lambda_0.5"]["saving_electricity_frac"]
        frac = min(1.0, TIMING[pair]["lambda_0.5"]["wholesale_mean_usd_per_kwh"] / case["electricity_usd_per_kwh"])
        out["wholesale_linked_fraction_of_price"] = frac
        out["delta_electricity_pct_region_matched"] = -100.0 * s * frac
        out["delta_total_pct_region_matched"] = -100.0 * share * s * frac
        out["region_matched_pair"] = pair  # type: ignore[assignment]
    return out


# ---------------------------------------------------------------------------
# Analyses
# ---------------------------------------------------------------------------


def base_case() -> Dict[str, Any]:
    return run("H100")


def defaults_by_chip() -> List[Dict[str, Any]]:
    rows = []
    for chip in CHIPS:
        for kind in ("purchase", "on_demand", "committed_1y", "committed_3y"):
            rows.append(run(chip, basis_kind="purchase" if kind == "purchase" else kind))
    return rows


def one_at_a_time(chip: str) -> List[Dict[str, Any]]:
    base = run(chip)
    out = []

    def add(name: str, setting: str, source: str, case: Dict[str, Any], region: Optional[Dict[str, Any]] = None) -> None:
        d = {"parameter": name, "setting": setting, "source": source, "electricity_share": case["electricity_share"],
             "total_usd_per_mtoken": case["total_usd_per_mtoken"], "electricity_usd_per_mtoken": case["electricity_usd_per_mtoken"],
             "base_electricity_share": base["electricity_share"]}
        d.update(timing_columns(case, region))
        out.append(d)

    lo_r, hi_r = CHIPS[chip]["price_range_ratio"]
    for tag, r in (("low", lo_r), ("high", hi_r)):
        add("chip purchase price", f"{tag} end of cited range (x{r:.3f})", CHIPS[chip]["price_basis"], run(chip, price_ratio=r))
    for y in (4.0, 6.0):
        add("server useful life", f"{y} years", "operators' reported server lives, 4 to 6 years (sources.json life.*)", run(chip, useful_life_years=y))
    for f, tag in ((0.0, "no residual"), (0.45, "45% resale (used-market share at age 3, Silicon Data text)")):
        add("residual value", f"{f:.0%} ({tag})", row("resid.silicondata_h100")["source"], run(chip, residual_fraction=f))
    for name, p in PUE_CASES:
        if abs(p - 1.2) > 1e-12:
            add("PUE", f"{p} ({name})", "pue.* rows", run(chip, pue=p))
    for reg in REGIONS + REGIONS_EXTRA:
        if reg["id"] != "US":
            add("electricity price", f"{reg['id']}: {reg['usd_per_kwh']:.4f} USD/kWh", ", ".join(reg["source_ids"]),
                run(chip, electricity_price=reg["usd_per_kwh"]), reg)
    for m in MFU_RANGE:
        add("MFU", f"{m}", "calculator help text (uncited range)", run(chip, mfu=m))
    if chip == "H100":
        for w in (5910.0, 7790.0):
            spf = w / (8 * 700.0 * basis.GPU_POWER_FRACTION) - 1.0
            add("node power", f"{w / 1000:.2f} kW average per node (extra server power {spf:.2f})",
                "arXiv 2506.14551 Table 2 (min and max of listed averages)", run(chip, server_power_fraction=spf))
        lo_o = (basis.SERVER_NON_GPU_PER_GPU_USD * 0 + (basis.HGX_H100_SYSTEM_USD - 8 * basis.H100_PRICE_USD) / 8 + basis.NETWORK_PER_GPU_USD + basis.OTHER_IT_PER_GPU_USD) / basis.H100_PRICE_USD
        hi_o = ((basis.DGX_H100_SYSTEM_USD - 8 * basis.H100_PRICE_USD) / 8 + basis.NETWORK_PER_GPU_USD + basis.OTHER_IT_PER_GPU_USD) / basis.H100_PRICE_USD
        add("servers, network, storage share of card price", f"{lo_o:.2f} (HGX server)", "price.h100.sys_hgx_new, net.amcompute_h100_meta",
            run(chip, other_hardware_fraction=lo_o))
        add("servers, network, storage share of card price", f"{hi_o:.2f} (DGX server)", "price.h100.sys_dgx, net.amcompute_h100_meta",
            run(chip, other_hardware_fraction=hi_o))
    add("facility cost", "0 USD/W (term removed)", "ablation", run(chip, fac_usd_per_w=0.0))
    add("facility cost", f"{row('fac.jll_per_mw_2026')['emerging_markets_lt'] / 1e6:.0f} USD/W (JLL emerging markets, below)", "fac.jll_per_mw_2026",
        run(chip, fac_usd_per_w=row("fac.jll_per_mw_2026")["emerging_markets_lt"] / 1e6))
    add("facility cost", f"{row('fac.jll_per_mw_2026')['premium_markets_gt'] / 1e6:.0f} USD/W (JLL premium markets, above)", "fac.jll_per_mw_2026",
        run(chip, fac_usd_per_w=row("fac.jll_per_mw_2026")["premium_markets_gt"] / 1e6))
    for y in (lo_hi("life.facility.heavy_equipment_amzn")[0], val("life.facility.buildings_amzn")):
        add("facility life", f"{y:.0f} years", "life.facility.* rows (Amazon FY2025 10-K)", run(chip, fac_life=y))
    for kind in ("on_demand", "committed_1y", "committed_3y"):
        add("cost basis", f"rental, {kind.replace('_', ' ')} (lessor's electricity as a share of the rental price)",
            "rent.* rows", run(chip, basis_kind=kind))
    rids = CHIPS[chip]["rental_ids"]
    rates = sorted(val(i) for i in rids)
    if len(rates) > 1:
        add("cost basis", f"rental on-demand, cheapest listed ({rates[0]} USD/GPU-hour)", "rent.* rows", run(chip, basis_kind="on_demand", rental_override=rates[0]))
        add("cost basis", f"rental on-demand, dearest listed ({rates[-1]} USD/GPU-hour)", "rent.* rows", run(chip, basis_kind="on_demand", rental_override=rates[-1]))
    return out


def grid() -> List[Dict[str, Any]]:
    cases = []
    for chip, life, reg, (pname, pue) in itertools.product(CHIPS, LIFE_CASES, REGIONS, PUE_CASES):
        c = run(chip, useful_life_years=life, pue=pue, electricity_price=reg["usd_per_kwh"])
        cases.append({"chip": chip, "basis": "purchase", "life_years": life, "region": reg["id"], "pue": pue, "pue_label": pname,
                      "electricity_usd_per_kwh": reg["usd_per_kwh"], "electricity_share": c["electricity_share"],
                      "total_usd_per_mtoken": c["total_usd_per_mtoken"], "electricity_usd_per_mtoken": c["electricity_usd_per_mtoken"],
                      **timing_columns(c, reg)})
    for chip, kind, reg, (pname, pue) in itertools.product(CHIPS, ("on_demand", "committed_1y", "committed_3y"), REGIONS, PUE_CASES):
        c = run(chip, basis_kind=kind, pue=pue, electricity_price=reg["usd_per_kwh"])
        cases.append({"chip": chip, "basis": f"rental_{kind}", "life_years": None, "region": reg["id"], "pue": pue, "pue_label": pname,
                      "electricity_usd_per_kwh": reg["usd_per_kwh"], "electricity_share": c["electricity_share"],
                      "total_usd_per_mtoken": c["total_usd_per_mtoken"], "electricity_usd_per_mtoken": c["electricity_usd_per_mtoken"],
                      "rental_usd_per_gpu_hour": c["rental_usd_per_gpu_hour"], **timing_columns(c, reg)})
    return cases


def breakeven_prices() -> List[Dict[str, Any]]:
    """Electricity price (USD/kWh) at which the share equals each level; the share is E/(E+H) and E is linear in price."""
    out = []
    for chip in CHIPS:
        for life in (4.0, 5.5, 6.0):
            c = run(chip, useful_life_years=life)
            e_per_price = c["electricity_cost_usd"] / c["electricity_usd_per_kwh"]
            h = c["hardware_cost_usd"]
            rec = {"chip": chip, "life_years": life, "hardware_cost_usd": h, "energy_kwh": e_per_price}
            for s in SHARE_LEVELS:
                rec[f"price_for_share_{int(s * 100)}pct_usd_per_kwh"] = s / (1 - s) * h / e_per_price
            out.append(rec)
    return out


def self_checks() -> Dict[str, Any]:
    """Consistency checks that must hold; their values are recorded in the result."""
    h = run("H100")
    direct = calculator.estimate(PARAMS, TOKENS, "H100-SXM", N_GPUS)
    checks: Dict[str, Any] = {
        "h100_bundle_matches_calculator_default": abs(h["electricity_cost_usd"] - direct.electricity_cost) / direct.electricity_cost,
        "h100_bundle_total_matches_calculator_default": abs(h["total_cost_usd"] - direct.total_cost) / direct.total_cost,
    }
    with facility(basis.FACILITY_USD_PER_W, basis.FACILITY_USEFUL_LIFE_YEARS):
        again = calculator.estimate(PARAMS, TOKENS, "H100-SXM", N_GPUS)
    checks["facility_context_identity"] = abs(again.total_cost - direct.total_cost) / direct.total_cost
    s = TIMING["caiso"]["lambda_0.5"]["saving_electricity_frac"], TIMING["de"]["lambda_0.5"]["saving_electricity_frac"]
    checks["e003_saving_caiso_pct_at_lambda_0.5"] = 100 * s[0]
    checks["e003_saving_de_pct_at_lambda_0.5"] = 100 * s[1]
    for k in ("h100_bundle_matches_calculator_default", "h100_bundle_total_matches_calculator_default", "facility_context_identity"):
        assert checks[k] < 1e-12, (k, checks[k])
    assert round(100 * s[0], 1) == 8.6 and round(100 * s[1], 1) == 12.6, s
    return checks


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------


def pct(x: float, nd: int = 1) -> str:
    return f"{100 * x:.{nd}f}%"


def sources_markdown() -> str:
    lines = [
        "# Cost audit sources (generated)",
        "",
        "Generated by `run_cost_audit.py` from `sources.json`. Access date for web sources: " + SRC["access_date"] + ".",
        "Column `gpu_stack before` is what the calculator or presets used before the T10 correction, with where.",
        "",
        "## Fetch notes",
        "",
    ] + [f"- {n}" for n in SRC["fetch_notes"]] + ["", "## Sources", "", "| id | publisher | title | published | kind | URL |", "|---|---|---|---|---|---|"]
    for sid, s in SRC["sources"].items():
        lines.append(f"| {sid} | {s['publisher']} | {s['title']} | {s['published']} | {s['kind']} | {s['url']} |")
    lines += ["", "## Rows", "", "| id | item | value | low-high | unit | source | basis | gpu_stack before |", "|---|---|---|---|---|---|---|---|"]
    for r in SRC["rows"]:
        v = "" if r.get("value") is None else f"{r['value']:g}"
        rng = "" if r.get("low") is None else f"{r['low']:g} - {r['high']:g}"
        cur = r.get("current")
        cur_s = "" if not cur else f"{cur['value']:g} ({cur['where']})"
        lines.append(f"| {r['id']} | {r['item']} | {v} | {rng} | {r['unit']} | {r['source']} | {r.get('basis', '')} | {cur_s} |")
    return "\n".join(lines) + "\n"


def results_markdown(res: Dict[str, Any]) -> str:
    L: List[str] = []
    b = res["base_case"]
    L += [
        "# Electricity share of cost per token: audit results (generated)",
        "",
        "Generated by `experiments/e003-heatwave/cost_audit/run_cost_audit.py`. All cases call `gpu_stack.calculator.estimate` for the",
        "README example (7e9 parameters, 2e12 tokens, 1,024 GPUs, MFU 40%) with the inputs in `cost_audit/sources.json`.",
        "Nothing here is measured on a real cluster; prices are published list or market figures.",
        "",
        f"Base case (H100, calculator defaults): electricity {b['electricity_cost_usd']:,.0f} USD, hardware {b['hardware_cost_usd']:,.0f} USD, "
        f"electricity share {pct(b['electricity_share'], 2)}, total {b['total_usd_per_mtoken']:.5f} USD per million tokens.",
        "",
        "## Defaults by chip and cost basis",
        "",
        "Rental basis: total = rental rate x calculator GPU-hours; electricity is the lessor's electricity cost for the same run, as a share of the rental price.",
        "",
        "| chip | basis | USD/GPU-hour (rental) | GPU price in model (USD) | TDP (W) | facility W/GPU | total USD/Mtoken | electricity USD/Mtoken | electricity share |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for c in res["defaults_by_chip"]:
        ch = CHIPS[c["chip"]]
        fac_w = c["energy_mwh"] * 1e6 / c["gpu_hours"]
        rate = "" if c["rental_usd_per_gpu_hour"] is None else f"{c['rental_usd_per_gpu_hour']:.2f}"
        L.append(f"| {c['chip']} | {c['basis']} | {rate} | {ch['gpu_price'] * (1 + ch['other_hardware_fraction']):,.0f} (all-in) | {ch['tdp_w']:.0f} | {fac_w:.0f} | "
                 f"{c['total_usd_per_mtoken']:.5f} | {c['electricity_usd_per_mtoken']:.5f} | {pct(c['electricity_share'], 2)} |")
    for chip, rows_ in res["one_at_a_time"].items():
        L += ["", f"## One at a time, {chip} (other inputs at their defaults for that chip)", "",
              "`d total (whole bill)` = change in total cost per token if electricity cost falls by the e003 saving at lambda 0.5 "
              f"(CAISO {pct(TIMING['caiso']['lambda_0.5']['saving_electricity_frac'])}, DE-LU {pct(TIMING['de']['lambda_0.5']['saving_electricity_frac'])}) "
              "on the whole electricity bill. `d total (matched)` = same, only on the wholesale-linked part of a retail price, with the CAISO saving "
              "for California prices and the DE-LU saving for the German price.", "",
              "| parameter | setting | source | electricity share | total USD/Mtoken | d total, CAISO saving (whole bill) | d total, DE-LU saving (whole bill) | d total (matched) |",
              "|---|---|---|---|---|---|---|---|"]
        for r in rows_:
            m = r.get("delta_total_pct_region_matched")
            L.append(f"| {r['parameter']} | {r['setting']} | {r['source']} | {pct(r['electricity_share'], 2)} | {r['total_usd_per_mtoken']:.5f} | "
                     f"{r['delta_total_pct_if_whole_bill_follows_wholesale_caiso']:.3f}% | {r['delta_total_pct_if_whole_bill_follows_wholesale_de']:.3f}% | "
                     f"{'' if m is None else f'{m:.3f}%'} |")
    L += ["", "## Grid summary", "",
          "Grid: chip (4) x server life (4, 5, 6 years) x electricity price (7 regions) x PUE (4 cited values) for purchase; "
          "chip x rental basis (3) x region x PUE for rental.", "",
          "| chip | basis | cases | min share | median share | max share | cases at or above 10% | at or above 20% | at or above 30% |",
          "|---|---|---|---|---|---|---|---|---|"]
    for g in res["grid_summary"]:
        L.append(f"| {g['chip']} | {g['basis']} | {g['n']} | {pct(g['min'])} | {pct(g['median'])} | {pct(g['max'])} | {g['n_ge_10']} | {g['n_ge_20']} | {g['n_ge_30']} |")
    L += ["", "## Grid: purchase basis, electricity share by region (PUE 1.2, server life 5 years)", "",
          "| chip | " + " | ".join(r["id"] for r in REGIONS) + " |", "|---|" + "---|" * len(REGIONS)]
    for chip in CHIPS:
        cells = []
        for reg in REGIONS:
            m = [g for g in res["grid"] if g["chip"] == chip and g["basis"] == "purchase" and g["life_years"] == 5.0 and g["region"] == reg["id"] and g["pue"] == 1.2][0]
            cells.append(pct(m["electricity_share"], 1))
        L.append(f"| {chip} | " + " | ".join(cells) + " |")
    L += ["", "Region prices used (USD/kWh): " + "; ".join(f"{r['id']} {r['usd_per_kwh']:.4f}" for r in REGIONS) + ".", ""]
    L += ["## Rental basis: lessor's electricity share of the rental price, by region (PUE 1.2)", "",
          "| chip | basis | " + " | ".join(r["id"] for r in REGIONS) + " |", "|---|---|" + "---|" * len(REGIONS)]
    for chip in CHIPS:
        for kind in ("rental_on_demand", "rental_committed_1y", "rental_committed_3y"):
            cells = []
            for reg in REGIONS:
                m = [g for g in res["grid"] if g["chip"] == chip and g["basis"] == kind and g["region"] == reg["id"] and g["pue"] == 1.2][0]
                cells.append(pct(m["electricity_share"], 1))
            L.append(f"| {chip} | {kind} | " + " | ".join(cells) + " |")
    L += ["", "## Electricity price at which the share reaches a level (purchase basis, PUE 1.2)", "",
          "| chip | life (years) | hardware cost (USD) | energy (kWh) | price for 10% | price for 20% | price for 30% | price for 50% (USD/kWh) |", "|---|---|---|---|---|---|---|---|"]
    for r in res["breakeven"]:
        L.append(f"| {r['chip']} | {r['life_years']} | {r['hardware_cost_usd']:,.0f} | {r['energy_kwh']:,.0f} | "
                 f"{r['price_for_share_10pct_usd_per_kwh']:.3f} | {r['price_for_share_20pct_usd_per_kwh']:.3f} | "
                 f"{r['price_for_share_30pct_usd_per_kwh']:.3f} | {r['price_for_share_50pct_usd_per_kwh']:.3f} |")
    x = res["crosscheck_introl"]
    L += ["", "## Cost-structure cross-check (not an input)", "",
          "A published worked example of a 100-H100 cluster (Introl, 2026-04-04, see `xcheck.introl_100_h100_5yr`) lists costs the calculator does not model "
          "(staff, space, software, maintenance, insurance, bandwidth). Shares of its gross five-year cost (hardware and installation plus five years of annual items, before the residual credit):", "",
          "| item | share of gross 5-year cost |", "|---|---|"]
    for k, v in x["shares"].items():
        L.append(f"| {k} | {pct(v)} |")
    L += ["", "The article's power lines are not consistent with its own inputs (see the row's basis), so this cross-check shows the kinds and rough size of omitted terms, "
          "not a reference value for electricity's share. Omitted terms lower the electricity share of a complete cost per token.", ""]
    L += ["", "## e003 timing savings read from cost-v1.json", "",
          f"Headline policy {HEADLINE_KEY}, lambda {HEADLINE_LAMBDA}: electricity saving CAISO {pct(TIMING['caiso']['lambda_0.5']['saving_electricity_frac'], 2)} "
          f"(wholesale mean {TIMING['caiso']['lambda_0.5']['wholesale_mean_usd_per_kwh'] * 1000:.2f} USD/MWh), DE-LU {pct(TIMING['de']['lambda_0.5']['saving_electricity_frac'], 2)} "
          f"(wholesale mean {TIMING['de']['lambda_0.5']['wholesale_mean_usd_per_kwh'] * 1000:.2f} USD/MWh at {USD_PER_EUR:.4f} USD per EUR). "
          f"At lambda 0: CAISO {pct(TIMING['caiso']['lambda_0']['saving_electricity_frac'], 2)}, DE-LU {pct(TIMING['de']['lambda_0']['saving_electricity_frac'], 2)}.",
          "The savings are on wholesale day-ahead prices. A retail price has a wholesale-linked part and fixed parts (delivery, demand charges, taxes); "
          "the matched columns apply the saving to the wholesale-linked part only. Demand charges would rise if shifting raises the peak load; that is not modelled.", ""]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def summarize_grid(cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    keys = sorted({(c["chip"], c["basis"]) for c in cases}, key=lambda k: (list(CHIPS).index(k[0]), k[1]))
    for chip, bs in keys:
        sh = sorted(c["electricity_share"] for c in cases if c["chip"] == chip and c["basis"] == bs)
        out.append({"chip": chip, "basis": bs, "n": len(sh), "min": sh[0], "median": statistics.median(sh), "max": sh[-1],
                    "n_ge_10": sum(s >= 0.10 for s in sh), "n_ge_20": sum(s >= 0.20 for s in sh), "n_ge_30": sum(s >= 0.30 for s in sh)})
    return out


def crosscheck_introl() -> Dict[str, Any]:
    r = row("xcheck.introl_100_h100_5yr")
    yrs = r["years"]
    items = {
        "hardware": r["year0_hardware"], "installation and training": r["year0_installation_training"],
        "power": yrs * r["annual_power"], "cooling": yrs * r["annual_cooling"], "space": yrs * r["annual_space"],
        "network bandwidth": yrs * r["annual_network_bandwidth"], "software": yrs * r["annual_software"],
        "maintenance": yrs * r["annual_maintenance"], "insurance": yrs * r["annual_insurance"], "personnel": yrs * r["annual_personnel"],
    }
    gross = sum(items.values())
    return {"gross_usd": gross, "items_usd": items, "shares": {k: v / gross for k, v in items.items()},
            "power_plus_cooling_share": (items["power"] + items["cooling"]) / gross}


def main() -> None:
    from heatwave.provenance import write_result

    checks = self_checks()
    g = grid()
    res: Dict[str, Any] = {
        "description": "Electricity's share of total cost per token for the README example across cited inputs; calculator equations only.",
        "workload": {"params": PARAMS, "tokens": TOKENS, "n_gpus": N_GPUS, "gpu_default": "H100-SXM"},
        "self_checks": checks,
        "assumptions_in_script": {"load_factors_for_tariff_demand_charge": list(ASSUMED_LOAD_FACTORS), "mfu_range": list(MFU_RANGE),
                                  "node_power_ratio_measured_over_rated": NODE_RATED_RATIO, "note": "chip bundles derive server_power_fraction from this ratio"},
        "chips": {k: {kk: vv for kk, vv in v.items() if kk != "gpu"} for k, v in CHIPS.items()},
        "regions": [{k: v for k, v in r.items()} for r in REGIONS + REGIONS_EXTRA],
        "e003_timing": {"policy": HEADLINE_KEY, "lambda": HEADLINE_LAMBDA, **{k: v for k, v in TIMING.items()}, "usd_per_eur": USD_PER_EUR},
        "calculator_cost_basis": {
            "electricity_usd_per_kwh": basis.ELECTRICITY_USD_PER_KWH, "useful_life_years": basis.USEFUL_LIFE_YEARS,
            "other_hardware_fraction": basis.OTHER_HARDWARE_FRACTION, "server_power_fraction": basis.SERVER_POWER_FRACTION,
            "facility_usd_per_w": basis.FACILITY_USD_PER_W, "facility_useful_life_years": basis.FACILITY_USEFUL_LIFE_YEARS,
            "h100_price_usd": basis.H100_PRICE_USD, "legacy_defaults": basis.LEGACY_DEFAULTS,
        },
        "base_case": base_case(),
        "defaults_by_chip": defaults_by_chip(),
        "one_at_a_time": {chip: one_at_a_time(chip) for chip in ("H100", "B200")},
        "grid": g,
        "grid_summary": summarize_grid(g),
        "breakeven": breakeven_prices(),
        "crosscheck_introl": crosscheck_introl(),
    }
    res["sources_table_sha256"] = __import__("hashlib").sha256(SOURCES.read_bytes()).hexdigest()
    res["gpu_stack_git"] = gpu_stack_git()
    SOURCES_MD.write_text(sources_markdown())
    OUT_MD.write_text(results_markdown(res))
    write_result(OUT, res, script=__file__, data_kind="public", inputs=[SOURCES, COST_V1],
                 notes="Published list, market and tariff figures (sources.json); modeled workload from the calculator; nothing measured on a cluster. "
                       "The git field is the heatwave repository; the gpu_stack state is in result.gpu_stack_git.")
    print("wrote", OUT, OUT_MD, SOURCES_MD)


def gpu_stack_git() -> Dict[str, str]:
    def git(*a: str) -> str:
        return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()

    dirty = bool(git("status", "--porcelain", "--", ".", ":(exclude)experiments/e003-heatwave/results",
                     ":(exclude)experiments/e003-heatwave/cost_audit/SOURCES.md"))
    return {"repo": "gpu_stack", "commit": git("rev-parse", "HEAD"), "branch": git("rev-parse", "--abbrev-ref", "HEAD"), "dirty": str(dirty).lower()}


if __name__ == "__main__":
    main()
