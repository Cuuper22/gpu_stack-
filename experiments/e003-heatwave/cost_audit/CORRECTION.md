# Cost correction (T10): what changed, why, and the numbers

Branch `hw-costaudit`. Every figure below is copied from a result file produced by a committed script; the file and script are named next to it.
Source URLs and access dates (2026-10-26) are in `sources.json` (rendered in `SOURCES.md`). Nothing here is measured on a real cluster;
prices are published list, market, filing and tariff figures, many of them from secondary aggregators (marked in `sources.json`).

## Before and after for the README example

Example: 7e9 parameters, 2e12 tokens, 1,024 H100-SXM, MFU 40%, PUE 1.2 (`gpu-stack estimate --params 7e9 --tokens 2e12 --gpu H100-SXM --gpus 1024`).
"Before" is the code of the base commit 8b8a654 run in a separate process; "after" is this branch. Script `run_before_after.py`, result
`../results/cost-audit-correction-v1.json` (table in `../results/cost-audit-correction-v1.md`).

| quantity | before | after |
|---|---|---|
| electricity cost (USD) | 4,026 | 5,766 |
| hardware cost (USD) | 67,090 | 71,910 |
| total cost (USD) | 71,116 | 77,675 |
| cost per million tokens (USD) | 0.03556 | 0.03884 |
| energy (MWh) | 49.52 | 67.75 |
| electricity share of total cost | 5.66% | 7.42% |

The README sentence says "about 6 percent"; the base commit gives 5.66% and this branch gives 7.42%. The README text was not edited.

The ladder in the same result applies the changes one at a time, cumulatively (first row reproduces the base commit exactly, last row equals the new default):

| step | electricity share |
|---|---|
| base-commit inputs | 5.66% |
| electricity 0.0813 to 0.0851 USD/kWh | 5.91% |
| H100 price 30,000 to 37,500 USD | 4.79% |
| server life 4 to 5.5 years | 6.46% |
| servers, network, storage 0.40 to 0.49 of card price | 6.10% |
| extra server power 0.25 to 0.71 | 8.16% |
| facility 11.3 USD/W over 13 years added | 7.42% |

The two changes that move the share most are the measured node power (more kWh per GPU-hour: 5,766 versus 4,215 USD of electricity at the same price) and
the card price (a bigger denominator).

## What changed in the code

Calculator (`gpu_stack/calculator.py`, new `gpu_stack/calculator_cost_basis.py`, which holds each default next to its URL):

| default | before | after | source |
|---|---|---|---|
| electricity price | 0.0813 USD/kWh (EIA 2024 industrial) | 0.0851 USD/kWh | EIA Electric Power Annual 2025, Table 2.10, https://www.eia.gov/electricity/annual/html/epa_02_10.html |
| H100 price | 30,000 USD | 37,500 USD (range 35,000-40,000) | IntuitionLabs, Data Center GPU Pricing 2026, https://intuitionlabs.ai/articles/data-center-gpu-pricing-2026 |
| A100 price | 15,000 USD (no citation) | 12,500 USD (range 10,000-15,000) | Jarvislabs, https://jarvislabs.ai/blog/a100-price |
| server life | 4 years | 5.5 years (median of eight operators, range 4-6) | operator rows `life.*` in `sources.json` |
| servers, network, storage share of card price | 0.40, which included the building | 0.49, building excluded | system prices (IntuitionLabs, AMCompute) and the 24,576-GPU H100 cluster breakdown, https://www.amcompute.com/blog/ai-cluster-cost-breakdown-capex |
| extra server power | 0.25 | 0.71, so an 8-GPU node draws the measured average 7.67 kW | arXiv 2506.14551 Table 2, https://arxiv.org/pdf/2506.14551 |
| facility (building, power, cooling plant) | inside the 0.40 share, on the server life | separate term, 11.3 USD per W of provisioned power, 13-year life | JLL via https://www.datacentres.com/news/data-centre-construction-costs-11m-per-mw ; Amazon FY2025 10-K equipment lives via https://app.edgar.tools/companies/AMZN/disclosures/property-plant-equipment |

The facility term uses the graph's own variables (`econ.cluster.facility_capex`, new `econ.facility.useful_life`, new `econ.cluster.facility_capex_rate`
and `econ.eq.cluster_facility_capex_rate`, all unit-checked) rather than a hand-typed formula; per-GPU facility capex is 11.3 USD/W times the chip rating
times (1 + extra server power). PUE already entered the calculator's site power (`thermal.dc.total_power = PUE x GPUs x TDP x load x (1 + server extra)`).

Economics scope (`gpu_stack/scopes/economics_capex*.py`): the cluster capex rate is now the IT rate (after residual value, over the IT life) plus the facility
rate (over `econ.facility.useful_life`); residual value applies to IT capex only.

Presets (`gpu_stack/presets/dgx_h100_tco.py`, `economics.py`, `scenarios.py`), the three ROADMAP item 4 problems:

| ROADMAP item 4 problem | change |
|---|---|
| facility overhead (PUE) never enters site power | new preset `dgx_h100_site_power_with_pue` (10.2 kW system maximum x PUE 1.2) is part of the full-TCO pack; PUE sources: Google 1.09, AWS 1.14, Microsoft 1.17, Uptime 2026 capacity-weighted 1.36 and per-facility mean 1.52 (rows `pue.*`) |
| demand charge counted twice | `econ.power.capacity_charge_kw_month` is 0 in the full-TCO pack: the EIA average price is revenue divided by sales and already contains demand charges |
| 4-year life applied to the whole facility | `econ.facility.useful_life` = 13 years in the pack; the IT life stays at 4 years there |

Effect on the DGX H100 full-TCO pack (Pythia-70M, single node; same result file): run power cost 9.216 to 11.059 USD, demand charge 1.260 to 0 USD,
hardware 122.75 to 112.46 USD, run total 189.79 to 180.09 USD, cost per token 6.329e-10 to 6.005e-10 USD; electricity (energy plus demand charge) share of run total 5.52% to 6.14%.
The other packs (`pythia_70m_dgx_h100_us_2024_industrial_power`, `scenarios_cited_2026`) still pin site power to the 10.2 kW system maximum and are IT-power packs.

Also: the 2025 EIA flat-tariff presets (`us_2025_*`, `california_2025_*`) were added next to the 2024 ones, which the scenario packs still name;
`docs/data/calculator-model.json` and `docs/data/drivers.json` were regenerated with `scripts/build_site_data.py` (the website reads them); README registry counts were
regenerated by the repo tooling (counts only). Tests that pinned old counts or old values were updated (`tests/test_calculator.py`, `test_cli_resolve.py`,
`test_cli_scenarios.py`, `test_dgx_h100_tco_packs.py`, `test_scenario_audit_text_family_index.py`, `test_import_registry.py`); `tests/test_calculator_cost_basis.py` is new.

## Where the share becomes larger (from `../results/cost-audit-v1.json`)

Table: `../results/cost-audit-v1.md`; script `run_cost_audit.py`. Cases call `gpu_stack.calculator.estimate` for the README workload.

- Calculator defaults: H100 7.42%; with the same method for other chips (single-run defaults for each chip) the shares are H200 6.97%, B200 8.10%, GB200 9.39%.
- Regions (H100, purchase, 5-year life, PUE 1.2): New Mexico 4.8%, Texas 5.2%, U.S. 6.9%, Virginia 7.6%, California PG&E E-20 energy plus demand charge 9.9%, Germany 14.6%, California industrial average 15.3%.
- Server life 4 / 5 / 6 years, H100 at the U.S. price: 5.7% / 6.9% / 8.0% (grid, PUE 1.2).
- PUE 1.09 / 1.36 / 1.52 (H100, U.S. price): 6.79% / 8.33% / 9.22%.
- Grid maxima (chip x life x region x PUE, purchase): H100 21.3%, H200 20.2%, B200 22.9%, GB200 25.9%. Cases at or above 20%: H100 2 of 84, H200 1, B200 5, GB200 11; at or above 30%: none.
- Rental basis (lessor's electricity as a share of the rental price, U.S. price, PUE 1.2): H100 2.5% on-demand, 4.5% one-year committed, 6.7% three-year committed.
- U.S.-average price at which the share reaches 10% (H100, 5.5-year life): 0.118 USD/kWh; 20%: 0.265 USD/kWh; B200: 0.107 and 0.241; GB200: 0.091 and 0.205.
- Residual value: 0% gives 7.11%; 45% (used-market share at age 3, an unstable figure in its source) gives 11.45%.

## What the e003 timing savings are worth per token

e003 (`cost-v1.json`, policy timestral_28M, flexible fraction 0.3, window 24 h, lambda 0.5) saves 8.61% of electricity cost in CAISO and 12.62% in DE-LU, on wholesale
day-ahead prices (35.19 USD/MWh and 139.36 USD/MWh). The share of a retail price that follows wholesale is the wholesale mean divided by the retail price (0.168 for the
California EIA industrial average, 0.704 for the German industry average, 0.276 for the E-20 tariff).

- H100, 5-year life, PUE 1.2, region-matched: California average, total cost per token changes by -0.222%; Germany -1.298%; California E-20 -0.236%.
- Upper bound if the whole electricity bill moved with wholesale (the convention of the cost-v1 headline): at the calculator default (7.42%) -0.639% (CAISO saving) and -0.937% (DE-LU saving);
  across the whole grid the DE-LU saving gives between -0.106% and -3.263%.
- The e003 headline totals (0.2% and 1.2%) are close to the region-matched figures here, because the saving is dollars on the wholesale part only.

Demand charges would rise if shifting raises peak load; that is not modelled.

## Limits and judgement calls

- Prices for cards and systems are from secondary aggregators (IntuitionLabs, AMCompute, Wing VC, Jarvislabs), with ranges kept in `sources.json`. NVIDIA product pages were not on the fetch allowlist; partner-hosted datasheets were used for power and FLOP/s.
- The JLL 11.3 million USD per MW does not say whether the MW is IT load or total; it is read as IT load. Sweeping 0 to 15 USD/W moves the H100 share between 8.16% and 7.21%.
- The 0.49 share of servers, network and storage adds the Meta cluster's "everything else" (3.5k USD per GPU) to a system price that already contains chassis, CPUs and memory, so some overlap is possible; the one-at-a-time rows show 0.42 and 0.56.
- GPU load (80% of rating) is still an uncited calculator assumption; extra server power is set so the node matches measured power at that load.
- No operator's residual value was found (filing notes could not be read); the calculator's 5% is unchanged and uncited.
- Not in the calculator and not added, because no consistent cited basis was found: financing cost, maintenance, staff, software, insurance and network transit. They lower the electricity share of a complete cost. The only worked example found (Introl, 100 H100, April 2026) is internally inconsistent in its power lines; see the cross-check table in `../results/cost-audit-v1.md`.
- B200 and GB200 are not in `calculator.GPUS`; the audit builds them from cited rows inside the script only. A per-GPU B200 TDP (1,000 W, HGX B200 summary) is now citable, so the docstring remark that B200 was left out for lack of a figure is out of date.
- The ROADMAP item 4 list was not edited.

## Checks run

`python -m pytest -q`, `python -m gpu_stack.cli audit --fail-on-issues`, `python -m gpu_stack.docs_stats_check`, `ruff check .`, `node tests/test_calculator_web.mjs` (see the final report for results).
