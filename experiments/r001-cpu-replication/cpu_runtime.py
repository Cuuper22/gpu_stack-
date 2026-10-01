"""CPU runtime shim for R001.

The E001 engines in gpu_stack/research/ were written for CUDA. They are imported
unchanged. Their model, optimizer, sampling, evaluation and SC1 policy code is
device generic except for one thing: every autocast block says
device_type="cuda" and is switched off on CPU. This module makes those blocks
run as CPU bfloat16 autocast, which matches the original bf16 numerics regime
(the original GPU runs used bf16 autocast). It changes no engine file.

Call install() once per process, before any engine function runs.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

_INSTALLED = False


def install(num_threads: int = 1):
    """Patch torch.autocast for CPU bf16 and fix the thread count. Returns torch."""
    global _INSTALLED
    import torch

    torch.set_num_threads(num_threads)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass
    if _INSTALLED:
        return torch
    real_autocast = torch.autocast

    def cpu_bf16_autocast(device_type="cuda", dtype=None, enabled=True, **kwargs):
        if device_type == "cuda":
            return real_autocast(device_type="cpu", dtype=torch.bfloat16, enabled=True)
        return real_autocast(device_type=device_type, dtype=dtype, enabled=enabled, **kwargs)

    torch.autocast = cpu_bf16_autocast  # type: ignore[assignment]
    _INSTALLED = True
    return torch


class CpuMeter:
    """Wall-clock stand-in for the engine's GPU energy meter. No energy is measured."""

    def __init__(self) -> None:
        self.running = False
        self.started_at = 0.0
        self.active_seconds = 0.0

    def start(self) -> None:
        if not self.running:
            self.started_at = time.perf_counter()
            self.running = True

    def stop(self) -> None:
        if self.running:
            self.active_seconds += time.perf_counter() - self.started_at
            self.running = False

    def result(self) -> dict:
        self.stop()
        return {"energy_measured": False, "reason": "CPU only; no energy counter used"}
