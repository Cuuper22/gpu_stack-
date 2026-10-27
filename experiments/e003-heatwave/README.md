# e003 Heatwave: forecast-driven power and thermal decisions

Experiment e003 adds power and heat to the lab. A simulated two-site cluster (the e001 sites, site-a and site-b) runs training jobs whose GPUs draw power in the e002 shape: steady compute, a dip while workers wait on communication, a dip at every checkpoint. Each rack heats up through a lumped thermal model, cooling answers with a lag, breakers trip, the grid curtails, GPUs fail. Three decisions then act on 21-quantile forecasts from Mistral's Timestral (Oct 2026) and from classical baselines, against reacting without a forecast, against the e001 averaging rule, and against perfect foresight:

1. **Power-cap packing** (`run_packing.py`, `results/packing-v1.json`): admit queued jobs while the planned site power, a chosen forecast quantile, stays under the cap; a learned policy picks the quantile per situation.
2. **Outage response** (`run_outage.py`, `results/outage-v1.json`, PENDING v2): warn when the forecast probability of trouble within the horizon is high, checkpoint early, then move the work to the other site or pause it.
3. **Cost timing** (`run_cost.py`, `results/cost-v1.json`): shift flexible work into cheaper and cleaner hours of real public price and carbon series; trace dollars per token against carbon per token.

The forecasting studies, the measured laptop runs and the public data live in the companion repository Heatwave (github.com/Cuuper22/heatwave once published; it imports this branch for the simulator).

## What is simulated, what is measured, what is public

Everything the simulator outputs is **simulated**. Its inputs are labeled in each scenario's `assumptions` list and in every run's metadata:

- GPU power levels (`sim-scenario-v2.json` onward) are calibrated on **public** H100 SXM telemetry (Elsayed et al. 2026, Scientific Data 13:1268, CC BY 4.0): compute at 0.855 of the 700 W limit, idle at 0.213 of compute, the communication dip at 0.249 of compute for 14% of a step, and a GPU-to-air temperature offset of 0.0256 K/W (medians over 72 GPU-sessions; `make_scenario_v2.py` copies them from the Heatwave calibration result and records its sha256). The checkpoint level is a **measured** laptop ratio (0.612, NVML energy counter). The first scenario (v1) used laptop ratios from e002 for idle power, which put idle at 0.764 of compute (`results/sim-smoke-v1.json`); v2 replaced them.
- `sim-scenario-v3.json` equals v2 except that the job schedule and the synthetic weather follow the run seed (in v2 every seed shared one schedule, which made seed intervals too narrow). Final packing numbers use v3.
- Thermal throttle thresholds, breaker curves, cooling lags and event rates are scenario assumptions with no default numbers in code; event precursors (a supply temperature that creeps up before a cooling failure, a GPU that runs hot before it dies) are assumptions of the simulation, and every event type also occurs with no precursor.
- Cost timing uses **public** CAISO and DE-LU day-ahead prices and carbon intensity directly, with a modeled workload from `gpu_stack.calculator`.

## Files

| file | what |
|---|---|
| `gpu_stack/research/heatwave_thermal.py` | lumped RC rack/GPU thermal model with exact integration, least-squares fit, throttle and cooling-power models |
| `gpu_stack/research/heatwave_events.py` | cooling failures, breaker trips, grid curtailments, hardware faults, with and without precursors |
| `gpu_stack/research/heatwave_sim.py` | the cluster simulator: sites (multisite `Site`), racks, GPUs, jobs, controller hook, multi-scale outputs that add up across GPU, rack and site |
| `gpu_stack/research/heatwave_packing.py`, `heatwave_outage.py`, `heatwave_cost.py` | the three decisions |
| `gpu_stack/scopes/power_forecast*.py` | the calculator scope: planning at a quantile, stranded power, RC thermal closed forms, early-checkpoint value, time shifting |
| `sim-scenario-v{1,2,3}.json` | simulator scenarios |
| `{packing,outage,cost}-scenario-v1.json` | decision scenarios |
| `results/` | result files with provenance (script and module sha256, git commit, seeds, hardware) |

## Results

Numbers, intervals and caveats are in each result file; a curated list with file and key for every number is `results/HEADLINE.md` in the Heatwave repository. In short (all simulated except cost timing, which uses public price and carbon):

- Packing, 6 held-out seeds: reacting to measured power packs 1,841 GPU-hours with 42.5 kWh above the cap; planning on Timestral-5M's 90th percentile packs 1,531 GPU-hours with 7.1 kWh above it. The learned quantile policy beats reacting by $747 per episode at an over-cap penalty of $40/kWh and by $5,575 at $160/kWh, and loses by $295 at $2.5/kWh.
- Outage response: PENDING (v2 with the per-GPU precursor channel).
- Cost timing, CAISO, last 26 weeks: Timestral-28M cuts the electricity cost of a 30% flexible share by 8.6% (perfect foresight 9.0%, seasonal naive 8.3%) and total cost per token by 0.22%.

Run commands are in each `run_*.py` docstring.
