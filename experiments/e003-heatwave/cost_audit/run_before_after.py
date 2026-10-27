"""Before and after of the T10 cost correction, for the README example and the DGX H100 full-TCO pack.

"Before" is computed by the code of the base commit (the commit this branch was cut from), extracted with
``git archive`` into a temporary directory and run in a separate process; "after" is the code in this
working tree.  The step ladder applies the changes one at a time, cumulatively, with the working-tree
calculator, and checks that its first row equals the base-commit result exactly.

Writes ``experiments/e003-heatwave/results/cost-audit-correction-v1.json`` (with provenance) and
``experiments/e003-heatwave/results/cost-audit-correction-v1.md``.

    PYTHONPATH=<this repo>:<heatwave repo> python experiments/e003-heatwave/cost_audit/run_before_after.py
"""

from __future__ import annotations

import ast
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from gpu_stack import calculator  # noqa: E402
from gpu_stack import calculator_cost_basis as basis  # noqa: E402

OUT = HERE.parent / "results" / "cost-audit-correction-v1.json"
OUT_MD = HERE.parent / "results" / "cost-audit-correction-v1.md"
SOURCES = HERE / "sources.json"
BASE_REF = "heatwave"  # the branch this one was cut from; merge-base is recorded
PACK = "pythia_70m_dgx_h100_us_2024_industrial_full_tco_assumption"
PACK_VARS = ["econ.cost.per_token", "econ.run.power_cost", "econ.run.capacity_charge_cost", "econ.run.hw_cost", "econ.run.total_cost",
             "econ.job.dc_power", "econ.cluster.capex_rate"]

CHILD = r"""
import ast, sys
from gpu_stack import calculator as c
import gpu_stack
from gpu_stack.presets import scenarios
e = c.estimate(7e9, 2e12, "H100-SXM", 1024)
out = {"file": gpu_stack.__file__, "estimate": {"electricity_cost": e.electricity_cost, "hardware_cost": e.hardware_cost,
       "total_cost": e.total_cost, "cost_per_million_tokens": e.cost_per_million_tokens, "energy_mwh": e.energy_mwh,
       "inputs": dict(e.inputs)}, "pack": {}}
p = getattr(scenarios, sys.argv[1])
for v in sys.argv[2:]:
    out["pack"][v] = float(p.resolve(v).value)
print(repr(out))
"""


def git(*a: str) -> str:
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()


def before() -> Dict[str, Any]:
    base = git("merge-base", "HEAD", BASE_REF)
    with tempfile.TemporaryDirectory() as td:
        arc = subprocess.run(["git", "archive", base, "gpu_stack"], cwd=REPO, capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", td], input=arc, check=True)
        # run from the extracted tree so that its gpu_stack is the one imported
        r = subprocess.run([sys.executable, "-c", CHILD, PACK, *PACK_VARS], cwd=td, capture_output=True, text=True, check=True,
                           env={"PYTHONPATH": td, "PATH": "/usr/bin:/bin:/usr/local/bin"})
        res = ast.literal_eval(r.stdout.strip().splitlines()[-1])
        assert res["file"].startswith(td), res["file"]
    res["base_commit"] = base
    return res


def est(**kw: float) -> Dict[str, float]:
    e = calculator.estimate(7e9, 2e12, "H100-SXM", 1024, **kw)
    return {"electricity_cost": e.electricity_cost, "hardware_cost": e.hardware_cost, "total_cost": e.total_cost,
            "cost_per_million_tokens": e.cost_per_million_tokens, "energy_mwh": e.energy_mwh}


def ladder() -> List[Dict[str, Any]]:
    L = basis.LEGACY_DEFAULTS
    steps: List[Dict[str, Any]] = []
    cur: Dict[str, float] = {"electricity_price": L["electricity_price"], "useful_life_years": L["useful_life_years"],
                             "other_hardware_fraction": L["other_hardware_fraction"], "server_power_fraction": L["server_power_fraction"],
                             "gpu_price": L["h100_price"]}

    def record(name: str, fac: float) -> None:
        saved = basis.FACILITY_USD_PER_W
        basis.FACILITY_USD_PER_W = fac
        calculator.build_model.cache_clear()
        try:
            r = est(**cur)
        finally:
            basis.FACILITY_USD_PER_W = saved
            calculator.build_model.cache_clear()
        r["step"] = name
        r["electricity_share"] = r["electricity_cost"] / r["total_cost"]
        r["inputs"] = dict(cur)
        r["facility_usd_per_w"] = fac
        steps.append(r)

    record("base-commit inputs (facility term off, as before)", 0.0)
    cur["electricity_price"] = basis.ELECTRICITY_USD_PER_KWH
    record("electricity 0.0813 -> 0.0851 USD/kWh (EIA 2025 industrial)", 0.0)
    cur["gpu_price"] = basis.H100_PRICE_USD
    record("H100 price 30,000 -> 37,500 USD", 0.0)
    cur["useful_life_years"] = basis.USEFUL_LIFE_YEARS
    record("server life 4 -> 5.5 years", 0.0)
    cur["other_hardware_fraction"] = basis.OTHER_HARDWARE_FRACTION
    record("servers, network, storage 0.40 -> 0.49 of card price (building moved out)", 0.0)
    cur["server_power_fraction"] = basis.SERVER_POWER_FRACTION
    record("extra server power 0.25 -> 0.71 (measured node power)", 0.0)
    record("facility 11.3 USD/W over 13 years added (= new defaults)", basis.FACILITY_USD_PER_W)
    return steps


def main() -> None:
    from heatwave.provenance import write_result

    b = before()
    a = est()
    a_pack = {}
    from gpu_stack.presets import scenarios

    p = getattr(scenarios, PACK)
    for v in PACK_VARS:
        a_pack[v] = float(p.resolve(v).value)
    lad = ladder()
    anchor_err = abs(lad[0]["total_cost"] - b["estimate"]["total_cost"]) / b["estimate"]["total_cost"]
    last_err = abs(lad[-1]["total_cost"] - a["total_cost"]) / a["total_cost"]
    assert anchor_err < 1e-12 and last_err < 1e-12, (anchor_err, last_err)
    be = b["estimate"]
    res: Dict[str, Any] = {
        "description": "README example (7e9 parameters, 2e12 tokens, 1,024 H100-SXM) and the DGX H100 full-TCO pack, before and after the T10 correction.",
        "base_commit": b["base_commit"],
        "readme_example": {
            "before": {k: be[k] for k in ("electricity_cost", "hardware_cost", "total_cost", "cost_per_million_tokens", "energy_mwh")},
            "after": a,
            "before_electricity_share": be["electricity_cost"] / be["total_cost"],
            "after_electricity_share": a["electricity_cost"] / a["total_cost"],
            "before_inputs": be["inputs"],
        },
        "step_ladder": lad,
        "ladder_check": {"first_row_vs_base_commit_rel_err": anchor_err, "last_row_vs_new_default_rel_err": last_err},
        "dgx_h100_full_tco_pack": {
            "pack": PACK, "before": b["pack"], "after": a_pack,
            "before_power_share_of_run_total": (b["pack"]["econ.run.power_cost"] + b["pack"]["econ.run.capacity_charge_cost"]) / b["pack"]["econ.run.total_cost"],
            "after_power_share_of_run_total": (a_pack["econ.run.power_cost"] + a_pack["econ.run.capacity_charge_cost"]) / a_pack["econ.run.total_cost"],
        },
    }
    write_result(OUT, res, script=__file__, data_kind="public", inputs=[SOURCES],
                 notes="Base-commit numbers come from the code of that commit run in a separate process; the working-tree numbers from this tree. "
                       "Published list prices; nothing measured on a cluster.")
    OUT_MD.write_text(markdown(res))
    print("wrote", OUT, OUT_MD)


def markdown(r: Dict[str, Any]) -> str:
    ex = r["readme_example"]
    L = ["# Cost correction: before and after (generated)", "",
         f"Base commit {r['base_commit']}. README example: 7e9 parameters, 2e12 tokens, 1,024 H100-SXM, MFU 40%, PUE 1.2.", "",
         "| quantity | before | after |", "|---|---|---|",
         f"| electricity cost (USD) | {ex['before']['electricity_cost']:,.0f} | {ex['after']['electricity_cost']:,.0f} |",
         f"| hardware cost (USD) | {ex['before']['hardware_cost']:,.0f} | {ex['after']['hardware_cost']:,.0f} |",
         f"| total cost (USD) | {ex['before']['total_cost']:,.0f} | {ex['after']['total_cost']:,.0f} |",
         f"| cost per million tokens (USD) | {ex['before']['cost_per_million_tokens']:.5f} | {ex['after']['cost_per_million_tokens']:.5f} |",
         f"| energy (MWh) | {ex['before']['energy_mwh']:,.2f} | {ex['after']['energy_mwh']:,.2f} |",
         f"| electricity share of total | {100 * ex['before_electricity_share']:.2f}% | {100 * ex['after_electricity_share']:.2f}% |",
         "", "## Step ladder (changes applied one at a time, cumulative)", "",
         "| step | electricity (USD) | hardware (USD) | total (USD) | electricity share | USD per million tokens |", "|---|---|---|---|---|---|"]
    for s in r["step_ladder"]:
        L.append(f"| {s['step']} | {s['electricity_cost']:,.0f} | {s['hardware_cost']:,.0f} | {s['total_cost']:,.0f} | "
                 f"{100 * s['electricity_share']:.2f}% | {s['cost_per_million_tokens']:.5f} |")
    p = r["dgx_h100_full_tco_pack"]
    L += ["", f"## DGX H100 full-TCO pack ({p['pack']}), Pythia-70M single node", "",
          "| quantity | before | after |", "|---|---|---|"]
    for v in PACK_VARS:
        L.append(f"| {v} | {p['before'][v]:.6g} | {p['after'][v]:.6g} |")
    L.append(f"| electricity (energy + demand charge) share of run total | {100 * p['before_power_share_of_run_total']:.2f}% | {100 * p['after_power_share_of_run_total']:.2f}% |")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
