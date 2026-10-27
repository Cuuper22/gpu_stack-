# Cost correction: before and after (generated)

Base commit 8b8a654651fa10cddd65dc6d7f69a21957e17646. README example: 7e9 parameters, 2e12 tokens, 1,024 H100-SXM, MFU 40%, PUE 1.2.

| quantity | before | after |
|---|---|---|
| electricity cost (USD) | 4,026 | 5,766 |
| hardware cost (USD) | 67,090 | 71,910 |
| total cost (USD) | 71,116 | 77,675 |
| cost per million tokens (USD) | 0.03556 | 0.03884 |
| energy (MWh) | 49.52 | 67.75 |
| electricity share of total | 5.66% | 7.42% |

## Step ladder (changes applied one at a time, cumulative)

| step | electricity (USD) | hardware (USD) | total (USD) | electricity share | USD per million tokens |
|---|---|---|---|---|---|
| base-commit inputs (facility term off, as before) | 4,026 | 67,090 | 71,116 | 5.66% | 0.03556 |
| electricity 0.0813 -> 0.0851 USD/kWh (EIA 2025 industrial) | 4,215 | 67,090 | 71,304 | 5.91% | 0.03565 |
| H100 price 30,000 -> 37,500 USD | 4,215 | 83,862 | 88,077 | 4.79% | 0.04404 |
| server life 4 -> 5.5 years | 4,215 | 60,991 | 65,205 | 6.46% | 0.03260 |
| servers, network, storage 0.40 -> 0.49 of card price (building moved out) | 4,215 | 64,912 | 69,126 | 6.10% | 0.03456 |
| extra server power 0.25 -> 0.71 (measured node power) | 5,766 | 64,912 | 70,677 | 8.16% | 0.03534 |
| facility 11.3 USD/W over 13 years added (= new defaults) | 5,766 | 71,910 | 77,675 | 7.42% | 0.03884 |

## DGX H100 full-TCO pack (pythia_70m_dgx_h100_us_2024_industrial_full_tco_assumption), Pythia-70M single node

| quantity | before | after |
|---|---|---|
| econ.cost.per_token | 6.32873e-10 | 6.005e-10 |
| econ.run.power_cost | 9.21602 | 11.0592 |
| econ.run.capacity_charge_cost | 1.25954 | 0 |
| econ.run.hw_cost | 122.75 | 112.458 |
| econ.run.total_cost | 189.794 | 180.086 |
| econ.job.dc_power | 10200 | 12240 |
| econ.cluster.capex_rate | 0.00276126 | 0.00252974 |
| electricity (energy + demand charge) share of run total | 5.52% | 6.14% |
