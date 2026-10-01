"""R001 Q2: run the SC1 engine's fixed policies on CPU with averaging controls.

The SC1 engine (gpu_stack/research/e001_semantic_consistency.py) is imported and
called unchanged (its _run_policy). Controls are added by wrapping three of its
module-level functions for the duration of a run, never by editing the file:

  _make_run_state      captures the two replicas (and starts the EMA from the warm weights)
  _sample_commitment   records the canonical tick, used for the cosine learning rate
  _apply_pending_gradient / _train_step
                       set the learning rate for this tick before the optimizer step
                       (cosine arms) and update the EMA after it (surviving replica only)
  _evaluate_state      at canonical tick 256 only, also scores the EMA weights

EMA tracks site-a. In every SC1 family the failed site is site-b, so site-a is the
survivor and receives exactly one exact-sync update per canonical tick. The EMA arm
is therefore a free extra measurement on the exact_forward_recovery run: it does not
change training. Cosine arms do change training.
"""

from __future__ import annotations

import copy
import math
import time
from typing import Any, Mapping

from cpu_runtime import install  # noqa: F401  (callers install before use)
from gpu_stack.research import e001_learning_calibration as lc1
from gpu_stack.research import e001_semantic_consistency as sc1


class _Controls:
    def __init__(self, *, lr0: float, total_ticks: int, cosine: bool, ema_decays: list[float]):
        self.lr0 = lr0
        self.total_ticks = total_ticks
        self.cosine = cosine
        self.ema_decays = list(ema_decays)
        self.tick = 0
        self.primary_site: Any = None
        self.ema: dict[float, dict[str, Any]] = {}
        self.updates = 0
        self.ema_final: dict[str, float] = {}

    def lr(self) -> float:
        if not self.cosine:
            return self.lr0
        return self.lr0 * 0.5 * (1.0 + math.cos(math.pi * self.tick / self.total_ticks))

    def set_lr(self, site: Any) -> None:
        if self.cosine:
            value = self.lr()
            for group in site.optimizer.param_groups:
                group["lr"] = value

    def init_ema(self, torch: Any) -> None:
        state = self.primary_site.model.state_dict()
        for decay in self.ema_decays:
            self.ema[decay] = {
                k: v.detach().clone() for k, v in state.items() if v.is_floating_point()
            }

    def update_ema(self, torch: Any) -> None:
        if not self.ema_decays or self.primary_site is None:
            return
        self.updates += 1
        state = self.primary_site.model.state_dict()
        with torch.no_grad():
            for decay, ema in self.ema.items():
                for key, value in ema.items():
                    value.mul_(decay).add_(state[key].detach(), alpha=1.0 - decay)


def run_cell(
    scenario: Mapping[str, Any],
    corpora: Any,
    warm_checkpoint: Any,
    warm_sha256: str,
    stratum: Mapping[str, Any],
    *,
    policy_id: str,
    cosine: bool,
    ema_decays: list[float],
    lr0: float,
    envelope: Mapping[str, Any],
    split: str = "evaluation",
) -> dict[str, Any]:
    """Run one SC1 fixed policy with controls. Returns a compact record (no epoch trace)."""
    _, _, torch, nn, functional = lc1._require_dependencies()
    controls = _Controls(
        lr0=lr0,
        total_ticks=int(scenario["work_contract"]["canonical_ticks"]),
        cosine=cosine,
        ema_decays=ema_decays if policy_id == sc1.EXACT_FORWARD_RECOVERY else [],
    )
    orig = {
        name: getattr(sc1, name)
        for name in (
            "_make_run_state", "_sample_commitment", "_apply_pending_gradient",
            "_train_step", "_evaluate_state",
        )
    }

    def make_run_state(*args, **kwargs):
        result = orig["_make_run_state"](*args, **kwargs)
        replicas = result[4]
        controls.primary_site = replicas["site-a"].site
        controls.init_ema(torch)
        return result

    def sample_commitment(*args, **kwargs):
        controls.tick = int(kwargs["logical_epoch"])
        return orig["_sample_commitment"](*args, **kwargs)

    def apply_pending_gradient(site, gradients):
        controls.set_lr(site)
        orig["_apply_pending_gradient"](site, gradients)
        if site is controls.primary_site:
            controls.update_ema(torch)

    def train_step(torch_, functional_, site, x, y, **kwargs):
        controls.set_lr(site)
        return orig["_train_step"](torch_, functional_, site, x, y, **kwargs)

    def evaluate_state(torch_, functional_, evaluation_model, replicas, corpora_, **kwargs):
        measurement = orig["_evaluate_state"](
            torch_, functional_, evaluation_model, replicas, corpora_, **kwargs
        )
        if controls.ema and controls.updates >= controls.total_ticks:
            optimization = scenario["optimization"]
            for decay, ema in controls.ema.items():
                evaluation_model.load_state_dict(ema)
                mean, _, _ = lc1._evaluate(
                    torch_, functional_, evaluation_model, corpora_.validation,
                    seed=kwargs["validation_seed"] + kwargs["seed"],
                    batch_size=kwargs["batch_size"],
                    context_length=kwargs["context_length"],
                    validation_batches=kwargs["validation_batches"],
                    device=kwargs["device"],
                    autocast_dtype=kwargs["autocast_dtype"] or torch_.bfloat16,
                )
                controls.ema_final[f"{decay:g}"] = mean
        return measurement

    sc1._make_run_state = make_run_state
    sc1._sample_commitment = sample_commitment
    sc1._apply_pending_gradient = apply_pending_gradient
    sc1._train_step = train_step
    sc1._evaluate_state = evaluate_state
    started = time.perf_counter()
    try:
        warm_metadata = {
            "checkpoint_sha256": warm_sha256,
            "reference_local_site_gradient_seconds": 0.1,
            "reference_local_optimizer_apply_seconds": 0.01,
        }
        run = sc1._run_policy(
            scenario, corpora, warm_checkpoint, warm_metadata, stratum,
            split=split, policy_id=policy_id, calibration_envelope=envelope,
        )
    finally:
        for name, fn in orig.items():
            setattr(sc1, name, fn)
    seconds = time.perf_counter() - started
    curve = [
        {"logical_tick": row["logical_tick_after"], "held_out_nll": row["held_out_nll"]}
        for row in run["epoch_trace"]
        if row.get("held_out_nll") is not None
    ]
    return {
        "policy_id": policy_id,
        "cosine": cosine,
        "stratum_id": run["family_or_stratum_id"],
        "stream_seed": run["seed"],
        "initial_held_out_nll": run["initial_held_out_nll"],
        "final_held_out_nll": run["final_held_out_nll"],
        "ema_final_held_out_nll": dict(controls.ema_final),
        "ema_updates": controls.updates,
        "curve": curve,
        "exact_accounting": run["exact_accounting"],
        "diverged": run["diverged"],
        "divergence_reason": run["divergence_reason"],
        "mode_transitions": [
            {"wall_tick": t["wall_tick"], "to_mode": t["to_mode"]} for t in run["mode_transitions"]
        ],
        "physical_seconds": seconds,
    }
