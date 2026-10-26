"""Build sim-scenario-v2.json: scenario v1 with GPU power levels calibrated on data.

Usage:
  python experiments/e003-heatwave/make_scenario_v2.py <heatwave repo>/results/calibration/datacenter_power.json

The calibration result is produced by the Heatwave repo's
experiments/calibration/datacenter_power.py from PUBLIC H100 SXM telemetry
(Elsayed et al. 2026, Scientific Data 13:1268, doi:10.1038/s41597-026-07496-6,
data CC BY 4.0) and one MEASURED laptop ratio (checkpoint/compute from the NVML
energy counter of an RTX 3060 Laptop GPU run). This script copies the medians
into the scenario and records the calibration file's sha256, so every changed
number traces to that file. Everything else stays as in v1 (simulated
scenario choices and labeled assumptions).
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main(cal_path: str) -> None:
    cal_file = Path(cal_path)
    cal = json.loads(cal_file.read_text())
    r = cal["result"]
    v1 = json.loads((HERE / "sim-scenario-v1.json").read_text())
    v2 = copy.deepcopy(v1)
    v2["scenario_id"] = v1["scenario_id"].replace("v1", "v2") if "v1" in v1["scenario_id"] else v1["scenario_id"] + "-v2"
    med = lambda k: float(r[k]["median"])  # noqa: E731
    src = "Elsayed et al. 2026 H100 SXM llm_training, median over %d GPU-sessions" % r["n_gpu_sessions"]
    v2["gpu"]["compute_fraction_of_tdp"] = med("compute_fraction_of_limit")
    v2["gpu"]["compute_fraction_of_step"] = 1.0 - med("low_phase_fraction_of_active_time")
    pl = v2["power_levels"]
    pl["idle_ratio_override"] = med("idle_ratio")
    pl["comm_ratio"] = med("low_phase_ratio")
    pl["checkpoint_ratio"] = float(r["laptop_checkpoint"]["ratio"])
    pl["calibration_notes"] = {
        "compute_w": f"public data: compute power / 700 W limit = {med('compute_fraction_of_limit'):.4f} ({src})",
        "idle_w": f"public data: idle/compute = {med('idle_ratio'):.4f} ({src})",
        "comm_w": f"public data: low-phase/compute = {med('low_phase_ratio'):.4f} ({src})",
        "checkpoint_w": ("measured laptop data: checkpoint/compute = %.4f from the NVML energy counter "
                         "(RTX 3060 Laptop GPU; transfer to a datacenter GPU is an assumption)" % r["laptop_checkpoint"]["ratio"]),
    }
    v2["thermal"]["gpu_to_air_k_per_w"] = med("temp_per_power_k_per_w")
    v2["calibration"] = {
        "file": "heatwave/results/calibration/datacenter_power.json",
        "sha256": hashlib.sha256(cal_file.read_bytes()).hexdigest(),
        "producer_script": cal["provenance"]["script"],
        "producer_script_sha256": cal["provenance"]["script_sha256"],
        "producer_git_commit": cal["provenance"]["git"]["commit"],
        "fields": {
            "gpu.compute_fraction_of_tdp": "compute_fraction_of_limit.median",
            "gpu.compute_fraction_of_step": "1 - low_phase_fraction_of_active_time.median",
            "power_levels.idle_ratio_override": "idle_ratio.median",
            "power_levels.comm_ratio": "low_phase_ratio.median",
            "power_levels.checkpoint_ratio": "laptop_checkpoint.ratio (measured laptop)",
            "thermal.gpu_to_air_k_per_w": "temp_per_power_k_per_w.median",
        },
    }
    v2["assumptions"] = [a for a in v1["assumptions"]] + [
        "v2 calibration: compute level, idle level, communication (low-phase) level, compute share of a step, "
        "and the GPU-to-air temperature offset are medians from public H100 SXM telemetry (Elsayed et al. 2026, "
        "CC BY 4.0); the checkpoint level is a measured laptop ratio. These replace the corresponding v1 values; "
        "the v1 text above describing those fields is superseded by this calibration block.",
    ]
    out = HERE / "sim-scenario-v2.json"
    out.write_text(json.dumps(v2, indent=1) + "\n")
    print("wrote", out)
    for k, v in v2["calibration"]["fields"].items():
        a, b = k.split(".")
        print(f"  {k} = {v2[a][b]}  <- {v}")


if __name__ == "__main__":
    main(sys.argv[1])
