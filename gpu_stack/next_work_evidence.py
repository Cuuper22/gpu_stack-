"""Live evidence collection for next-work reports."""

from __future__ import annotations

import ast
import json
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Mapping

import gpu_stack
import sympy as sp

from . import Registry
from .core.resolver import _boundary_family
from .presets import scenarios


_OBSERVATION_ARTIFACT_SYMBOLS = (
    "Observation",
    "CalibrationSplit",
    "EvaluationSplit",
)
_TEMPORAL_ARTIFACT_SYMBOLS = (
    "TemporalEvent",
    "EventTimeline",
    "VisibleStateSnapshot",
    "TimelineTrace",
)
_INTERVENTION_ARTIFACT_SYMBOLS = (
    "Policy",
    "VisibleDatacenterState",
    "MembershipIntervention",
    "SyncCadenceIntervention",
    "VirtualDatacenter",
)
_EVALUATION_ARTIFACT_SYMBOLS = (
    "PredictionRecord",
    "PredictionInterval",
    "evaluate_predictions",
    "IntervalCoverage",
    "configuration_ranking_correlation",
    "DecisionRegret",
    "ResidualAttribution",
    "StratifiedIntervalCoverage",
    "configuration_kendall_tau_b",
    "BenchmarkAggregation",
    "ExperimentProtocol",
    "ExperimentRunArtifact",
    "EvidenceRequirementSpec",
    "EvidenceRequirementResult",
)
_E001_EXECUTION_SYMBOLS = (
    "E001_PROTOCOL",
    "E001Scenario",
    "AdaptiveConsistencyPolicy",
    "run_e001",
)
_CAUSAL_OBSERVATORY_MARKERS = (
    "causal graph",
    "event timeline",
    "uncertainty",
    "evidence inspector",
    "falsifier",
)


@dataclass(frozen=True)
class _RootDebtRow:
    dependents: int
    name: str
    units: str
    scope: str
    family: str


@dataclass(frozen=True)
class _RootDebtFamily:
    total_weight: int
    root_count: int
    family: str
    roots: tuple[_RootDebtRow, ...]


@dataclass(frozen=True)
class _Evidence:
    stats: Mapping[str, int]
    coverage: Mapping[str, int]
    topological_order_length: int
    cycle_count: int
    root_debt_families: tuple[_RootDebtFamily, ...]
    pythia_report: object | None
    pythia_cost_target: object | None
    euv_report: object | None
    dense_cost_result: object | None
    sourced_pack_count: int
    large_project_files: tuple[tuple[str, int], ...]
    multi_definition_count: int
    collapsed_equation_count: int
    raw_symbol_count: int
    orphan_value_equation_count: int
    repo_root: Path
    research_contract_present: bool
    e001_spec_present: bool
    experiment_spec_count: int
    experiment_result_artifact_count: int
    e001_learning_result_present: bool
    e001_learning_evaluation_observation_count: int
    e001_learning_conclusion: str | None
    e001_learning_candidate_survives: bool | None
    e001_learning_observatory_present: bool
    e002_result_artifact_count: int
    observation_artifact_count: int
    evaluation_observation_reference_count: int
    structured_requirement_result_count: int
    unresolved_requirement_result_count: int
    production_symbol_names: frozenset[str]
    e001_v1_persisted_protocol_hash: str | None
    e001_v1_persisted_engine_source_hash: str | None
    e001_v1_protocol_hash_matches_persisted: bool | None
    e001_v1_engine_hash_matches_persisted: bool | None
    causal_observatory_markers: tuple[str, ...]
    registry_cone_present: bool
    observatory_artifact_present: bool
    e002_spec_present: bool

    @property
    def missing_variable_units(self) -> int:
        return self.coverage["non_constant_variables"] - self.coverage["with_sp_units"]

    @property
    def missing_variable_references(self) -> int:
        return (
            self.coverage["non_constant_variables"]
            - self.coverage["with_references"]
        )

    @property
    def missing_equation_references(self) -> int:
        return self.coverage["equations"] - self.coverage["equations_with_references"]

    @property
    def missing_equation_unit_checks(self) -> int:
        return self.coverage["equations"] - self.coverage["equations_with_unit_check"]

    @property
    def hard_failure_count(self) -> int:
        topo_failure = self.topological_order_length != self.stats["variables"]
        return (
            self.cycle_count
            + self.collapsed_equation_count
            + self.raw_symbol_count
            + self.orphan_value_equation_count
            + int(topo_failure)
        )

    def implemented_symbols(self, expected: tuple[str, ...]) -> tuple[str, ...]:
        """Return expected research artifact symbols found in production code."""
        return tuple(name for name in expected if name in self.production_symbol_names)

    def missing_symbols(self, expected: tuple[str, ...]) -> tuple[str, ...]:
        """Return expected research artifact symbols absent from production code."""
        return tuple(name for name in expected if name not in self.production_symbol_names)

    @property
    def observation_types(self) -> tuple[str, ...]:
        return self.implemented_symbols(_OBSERVATION_ARTIFACT_SYMBOLS)

    @property
    def missing_observation_types(self) -> tuple[str, ...]:
        return self.missing_symbols(_OBSERVATION_ARTIFACT_SYMBOLS)

    @property
    def temporal_types(self) -> tuple[str, ...]:
        return self.implemented_symbols(_TEMPORAL_ARTIFACT_SYMBOLS)

    @property
    def missing_temporal_types(self) -> tuple[str, ...]:
        return self.missing_symbols(_TEMPORAL_ARTIFACT_SYMBOLS)

    @property
    def intervention_types(self) -> tuple[str, ...]:
        return self.implemented_symbols(_INTERVENTION_ARTIFACT_SYMBOLS)

    @property
    def missing_intervention_types(self) -> tuple[str, ...]:
        return self.missing_symbols(_INTERVENTION_ARTIFACT_SYMBOLS)

    @property
    def evaluation_types(self) -> tuple[str, ...]:
        return self.implemented_symbols(_EVALUATION_ARTIFACT_SYMBOLS)

    @property
    def missing_evaluation_types(self) -> tuple[str, ...]:
        return self.missing_symbols(_EVALUATION_ARTIFACT_SYMBOLS)

    @property
    def e001_execution_symbols(self) -> tuple[str, ...]:
        return self.implemented_symbols(_E001_EXECUTION_SYMBOLS)

    @property
    def missing_e001_execution_symbols(self) -> tuple[str, ...]:
        return self.missing_symbols(_E001_EXECUTION_SYMBOLS)


def _collect_evidence(repo_root: Path | None) -> _Evidence:
    resolved_repo_root = (
        repo_root.resolve()
        if repo_root is not None
        else Path(gpu_stack.__file__).resolve().parent.parent
    )
    stats_key = tuple(sorted(Registry.stats().items()))
    coverage_key = tuple(sorted(Registry.coverage().items()))
    return _collect_evidence_cached(
        str(resolved_repo_root),
        _repo_evidence_signature(resolved_repo_root),
        stats_key,
        coverage_key,
    )


def _repo_evidence_signature(repo_root: Path) -> tuple[tuple[str, int, int], ...]:
    """Cheap cache key for files that can change next-work evidence."""

    candidates: set[Path] = set()
    for root, pattern in (
        (repo_root / "gpu_stack", "*.py"),
        (repo_root / "experiments", "*"),
        (repo_root / "observations", "*.json"),
        (repo_root / "docs", "*.html"),
        (repo_root / "docs", "*.js"),
        (repo_root / "docs" / "data", "*.json"),
    ):
        if root.is_dir():
            candidates.update(path for path in root.rglob(pattern) if path.is_file())
    for name in ("README.md", "RESEARCH.md", "pyproject.toml"):
        path = repo_root / name
        if path.is_file():
            candidates.add(path)
    signature = []
    for path in sorted(candidates):
        stat = path.stat()
        signature.append(
            (
                path.relative_to(repo_root).as_posix(),
                stat.st_mtime_ns,
                stat.st_size,
            )
        )
    return tuple(signature)


@lru_cache(maxsize=4)
def _collect_evidence_cached(
    repo_root: str,
    _file_signature: tuple[tuple[str, int, int], ...],
    _stats_key: tuple[tuple[str, int], ...],
    _coverage_key: tuple[tuple[str, int], ...],
) -> _Evidence:
    return _collect_evidence_uncached(Path(repo_root))


def _collect_evidence_uncached(resolved_repo_root: Path) -> _Evidence:
    stats = Registry.stats()
    coverage = Registry.coverage()
    try:
        topological_order_length = len(gpu_stack.topological_sort())
    except RuntimeError:
        topological_order_length = 0

    pythia_name = "pythia_70m_dgx_h100_us_2024_industrial_power"
    euv_name = "euv_tin120_lpp_source_context_assumption"
    sourced_packs = tuple(scenarios.SOURCED_SCENARIO_PACKS)
    reports = {
        pack.name: pack.evaluate_targets(scenarios.scenario_targets_for(pack))
        for pack in sourced_packs
        if pack.name in {pythia_name, euv_name}
    }
    pythia_report = reports.get(pythia_name)
    pythia_cost_target = _target_by_label(pythia_report, "cost_per_token")
    dense_cost_result = scenarios.dense_training_cost_fixture.resolve(
        scenarios.COST_PER_TOKEN_TARGET
    )
    production_symbol_names = _production_symbol_names(resolved_repo_root)
    experiment_specs, experiment_results = _experiment_artifacts(resolved_repo_root)
    research_counts = _research_artifact_counts(
        resolved_repo_root,
        experiment_results,
    )
    e001_v1_identity = _e001_v1_identity(resolved_repo_root)
    e001_learning = _e001_learning_result(resolved_repo_root)

    return _Evidence(
        stats=stats,
        coverage=coverage,
        topological_order_length=topological_order_length,
        cycle_count=len(gpu_stack.find_cycles()),
        root_debt_families=_root_debt_families(),
        pythia_report=pythia_report,
        pythia_cost_target=pythia_cost_target,
        euv_report=reports.get(euv_name),
        dense_cost_result=dense_cost_result,
        sourced_pack_count=len(sourced_packs),
        large_project_files=_large_project_files(repo_root=resolved_repo_root),
        multi_definition_count=sum(
            1 for variable in Registry.variables.values()
            if variable.has_multiple_definitions()
        ),
        collapsed_equation_count=sum(
            1 for equation in Registry.equations.values()
            if equation.as_sympy() in (sp.S.true, sp.S.false)
        ),
        raw_symbol_count=sum(
            1 for equation in Registry.equations.values()
            if equation.raw_dependency_symbols()
        ),
        orphan_value_equation_count=sum(
            1 for equation in Registry.equations.values()
            if equation.role is not gpu_stack.RelationRole.CONSTRAINT
            and equation.lhs_variable() is None
        ),
        repo_root=resolved_repo_root,
        research_contract_present=(resolved_repo_root / "RESEARCH.md").is_file(),
        e001_spec_present=(
            resolved_repo_root
            / "experiments"
            / "e001-beyond-one-datacenter"
            / "experiment.md"
        ).is_file(),
        experiment_spec_count=len(experiment_specs),
        experiment_result_artifact_count=len(experiment_results),
        e001_learning_result_present=bool(e001_learning["present"]),
        e001_learning_evaluation_observation_count=int(
            e001_learning["evaluation_observation_count"]
        ),
        e001_learning_conclusion=(
            str(e001_learning["conclusion"])
            if e001_learning["conclusion"] is not None
            else None
        ),
        e001_learning_candidate_survives=(
            bool(e001_learning["candidate_survives"])
            if e001_learning["candidate_survives"] is not None
            else None
        ),
        e001_learning_observatory_present=(
            resolved_repo_root / "docs" / "data" / "e001-learning-v1.json"
        ).is_file(),
        e002_result_artifact_count=research_counts["e002_results"],
        observation_artifact_count=research_counts["observations"],
        evaluation_observation_reference_count=research_counts[
            "evaluation_observation_references"
        ],
        structured_requirement_result_count=research_counts[
            "structured_requirements"
        ],
        unresolved_requirement_result_count=research_counts[
            "unresolved_requirements"
        ],
        production_symbol_names=production_symbol_names,
        e001_v1_persisted_protocol_hash=e001_v1_identity["persisted_protocol_hash"],
        e001_v1_persisted_engine_source_hash=e001_v1_identity[
            "persisted_engine_source_hash"
        ],
        e001_v1_protocol_hash_matches_persisted=e001_v1_identity[
            "protocol_hash_matches"
        ],
        e001_v1_engine_hash_matches_persisted=e001_v1_identity[
            "engine_hash_matches"
        ],
        causal_observatory_markers=_causal_observatory_markers(resolved_repo_root),
        registry_cone_present=(
            resolved_repo_root / "docs" / "data" / "registry-cone.json"
        ).is_file(),
        observatory_artifact_present=(
            resolved_repo_root / "docs" / "data" / "e001-screening-v1.json"
        ).is_file(),
        e002_spec_present=(
            resolved_repo_root
            / "experiments"
            / "e002-power-waveform-shaping"
            / "experiment.md"
        ).is_file(),
    )


def _e001_learning_result(repo_root: Path) -> dict[str, object]:
    path = (
        repo_root
        / "experiments"
        / "e001-beyond-one-datacenter"
        / "results"
        / "learning-calibration-v1.json"
    )
    empty = {
        "present": False,
        "evaluation_observation_count": 0,
        "conclusion": None,
        "candidate_survives": None,
    }
    if not path.is_file():
        return empty
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return empty
    if not isinstance(payload, dict) or payload.get("schema") != (
        "gpu-stack.e001-recovery-learning-evidence.v1"
    ):
        return empty
    split = payload.get("split")
    evaluation_count = 0
    if isinstance(split, dict):
        evaluation = split.get("evaluation")
        if isinstance(evaluation, dict):
            ids = evaluation.get("observation_ids")
            if isinstance(ids, list):
                evaluation_count = sum(
                    isinstance(item, str) and bool(item) for item in ids
                )
    summary = payload.get("summary")
    conclusion = None
    candidate_survives = None
    if isinstance(summary, dict):
        if isinstance(summary.get("conclusion"), str):
            conclusion = summary["conclusion"]
        if isinstance(summary.get("candidate_survives_lc1"), bool):
            candidate_survives = summary["candidate_survives_lc1"]
    return {
        "present": True,
        "evaluation_observation_count": evaluation_count,
        "conclusion": conclusion,
        "candidate_survives": candidate_survives,
    }


def _e001_v1_identity(repo_root: Path) -> dict[str, str | bool | None]:
    """Compare the frozen v1 source identity with the published v1 projection."""

    from .research.e001 import E001_PROTOCOL
    from .research.e001_v1_identity import (
        E001_V1_FROZEN_ENGINE_SOURCE_SHA256,
        E001_V1_FROZEN_PROTOCOL_SHA256,
    )

    path = repo_root / "docs" / "data" / "e001-screening-v1.json"
    if not path.is_file():
        return {
            "persisted_protocol_hash": None,
            "persisted_engine_source_hash": None,
            "protocol_hash_matches": None,
            "engine_hash_matches": None,
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {
            "persisted_protocol_hash": None,
            "persisted_engine_source_hash": None,
            "protocol_hash_matches": False,
            "engine_hash_matches": False,
        }
    if not isinstance(payload, dict):
        return {
            "persisted_protocol_hash": None,
            "persisted_engine_source_hash": None,
            "protocol_hash_matches": False,
            "engine_hash_matches": False,
        }
    persisted_protocol_hash = payload.get("protocol_hash")
    source_result = payload.get("source_result")
    persisted_engine_source_hash = (
        source_result.get("engine_source_sha256")
        if isinstance(source_result, dict)
        else None
    )
    valid_protocol_hash = (
        persisted_protocol_hash
        if isinstance(persisted_protocol_hash, str)
        else None
    )
    valid_engine_hash = (
        persisted_engine_source_hash
        if isinstance(persisted_engine_source_hash, str)
        else None
    )
    return {
        "persisted_protocol_hash": valid_protocol_hash,
        "persisted_engine_source_hash": valid_engine_hash,
        "protocol_hash_matches": (
            valid_protocol_hash == E001_V1_FROZEN_PROTOCOL_SHA256
            and E001_PROTOCOL.protocol_hash == E001_V1_FROZEN_PROTOCOL_SHA256
        ),
        "engine_hash_matches": (
            valid_engine_hash == E001_V1_FROZEN_ENGINE_SOURCE_SHA256
        ),
    }


def _research_artifact_counts(
    repo_root: Path,
    experiment_results: tuple[Path, ...],
) -> dict[str, int]:
    """Count attached observations and unresolved gates in persisted results."""

    observation_root = repo_root / "observations"
    counts = {
        "observations": (
            len(tuple(observation_root.rglob("*.json")))
            if observation_root.is_dir()
            else 0
        ),
        "evaluation_observation_references": 0,
        "structured_requirements": 0,
        "unresolved_requirements": 0,
        "e002_results": 0,
    }
    evaluation_ids: set[str] = set()
    compact_artifacts: list[dict[str, object]] = []
    observatory_path = repo_root / "docs" / "data" / "e001-screening-v1.json"
    if observatory_path.is_file():
        try:
            observatory = json.loads(observatory_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            observatory = None
        if isinstance(observatory, dict):
            for run in observatory.get("runs", ()):
                if not isinstance(run, dict):
                    continue
                artifact = run.get("experiment_artifact")
                if (
                    isinstance(artifact, dict)
                    and artifact.get("conclusion") != "baseline"
                ):
                    compact_artifacts.append(artifact)

    for path in experiment_results:
        relative_parts = {
            part.lower() for part in path.relative_to(repo_root).parts
        }
        if any(part.startswith("e002-") for part in relative_parts):
            counts["e002_results"] += 1

    # The full result deliberately embeds complete traces and can be tens of
    # megabytes.  The observatory projection carries the same run-artifact
    # gate records in a compact, hash-linked form, so the live compass does not
    # reparse every event snapshot merely to count unresolved requirements.
    if not compact_artifacts:
        for path in experiment_results:
            if path.suffix.lower() != ".json" or path.stat().st_size > 2_000_000:
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict) and isinstance(payload.get("artifacts"), list):
                compact_artifacts.extend(
                    artifact
                    for artifact in payload["artifacts"]
                    if isinstance(artifact, dict)
                )

    for artifact in compact_artifacts:
        for observation_id in artifact.get("evaluation_observation_ids", ()):
            if isinstance(observation_id, str) and observation_id:
                evaluation_ids.add(observation_id)
        requirements = artifact.get("evidence_requirements", ())
        if not isinstance(requirements, list):
            continue
        counts["structured_requirements"] += len(requirements)
        counts["unresolved_requirements"] += sum(
            isinstance(result, dict)
            and result.get("status") in {"unresolved", "not_applicable"}
            for result in requirements
        )
    counts["evaluation_observation_references"] = len(evaluation_ids)
    return counts


def _production_symbol_names(repo_root: Path) -> frozenset[str]:
    """Collect public-capability definitions from the shipped Python package.

    This deliberately scans production modules rather than prose or tests.  A
    research concept documented in ``RESEARCH.md`` should not be reported as
    implemented until a concrete type, function, or module constant exists
    under ``gpu_stack``.
    """

    package_root = repo_root / "gpu_stack"
    if not package_root.is_dir():
        return frozenset()

    names: set[str] = set()
    for path in sorted(package_root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError, UnicodeError):
            # The next-work report must remain available while an unrelated
            # worktree file is temporarily incomplete. Graph audit owns the
            # syntax failure; capability evidence simply declines to count it.
            continue
        for node in tree.body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                names.add(node.name)
            elif isinstance(node, ast.Assign):
                names.update(
                    target.id for target in node.targets if isinstance(target, ast.Name)
                )
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names.add(node.target.id)
    return frozenset(names)


def _experiment_artifacts(repo_root: Path) -> tuple[tuple[Path, ...], tuple[Path, ...]]:
    """Return designed experiment specs and machine-readable result artifacts."""

    experiments_root = repo_root / "experiments"
    if not experiments_root.is_dir():
        return (), ()

    specs = tuple(sorted(experiments_root.glob("*/experiment.md")))
    result_suffixes = {".csv", ".json", ".jsonl", ".parquet"}
    results = tuple(
        sorted(
            path
            for path in experiments_root.rglob("*")
            if path.is_file()
            and path.suffix.lower() in result_suffixes
            and _looks_like_experiment_result(path, experiments_root)
        )
    )
    return specs, results


def _looks_like_experiment_result(path: Path, experiments_root: Path) -> bool:
    """Distinguish result evidence from scenario/configuration inputs."""

    relative = path.relative_to(experiments_root)
    stem = path.stem.lower()
    parent_names = {part.lower() for part in relative.parts[:-1]}
    if parent_names & {"result", "results", "runs", "artifacts", "reports"}:
        return True

    result_markers = ("result", "report", "run-artifact", "residual")
    if any(marker in stem for marker in result_markers):
        return True
    if any(marker in stem for marker in ("scenario", "input", "config")):
        return False

    if path.suffix.lower() not in {".json", ".jsonl"}:
        return False
    try:
        if path.suffix.lower() == ".jsonl":
            first_line = next(
                line for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
            payload = json.loads(first_line)
        else:
            payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, StopIteration, json.JSONDecodeError):
        return False
    if not isinstance(payload, dict):
        return False

    strong_result_keys = {"artifacts", "residuals", "run_id", "runs"}
    return bool(strong_result_keys.intersection(payload))


def _causal_observatory_markers(repo_root: Path) -> tuple[str, ...]:
    """Find research-observatory concepts in the deployable docs application."""

    docs_root = repo_root / "docs"
    candidates = (
        docs_root / "index.html",
        docs_root / "app.js",
        docs_root / "cone-browser.js",
        docs_root / "observatory.html",
        docs_root / "observatory.js",
        docs_root / "styles" / "90-observatory.css",
    )
    rendered = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore").lower()
        for path in candidates
        if path.is_file()
    )
    return tuple(marker for marker in _CAUSAL_OBSERVATORY_MARKERS if marker in rendered)


def _target_by_label(report: object | None, label: str) -> object | None:
    if report is None:
        return None
    for target in getattr(report, "targets", ()):
        if getattr(target, "label", None) == label:
            return target
    return None


def _root_debt_families() -> tuple[_RootDebtFamily, ...]:
    rows = tuple(
        sorted(
            (
                _RootDebtRow(
                    dependents=len(root.dependents()),
                    name=root.name,
                    units=root.units,
                    scope=root.scope,
                    family=_boundary_family(root),
                )
                for root in Registry.roots()
            ),
            key=lambda row: (-row.dependents, row.name),
        )
    )
    grouped: dict[str, list[_RootDebtRow]] = defaultdict(list)
    for row in rows:
        grouped[row.family].append(row)

    families = [
        _RootDebtFamily(
            total_weight=sum(row.dependents for row in family_rows),
            root_count=len(family_rows),
            family=family,
            roots=tuple(sorted(family_rows, key=lambda row: (-row.dependents, row.name))),
        )
        for family, family_rows in grouped.items()
    ]
    return tuple(
        sorted(
            families,
            key=lambda family: (
                -family.total_weight,
                -family.root_count,
                family.family,
            ),
        )
    )


def _large_project_files(
    repo_root: Path | None = None,
    threshold: int = 700,
) -> tuple[tuple[str, int], ...]:
    root = repo_root or Path(gpu_stack.__file__).resolve().parent.parent
    roots = (Path(gpu_stack.__file__).resolve().parent, root / "tests")
    out: list[tuple[str, int]] = []
    for scan_root in roots:
        if not scan_root.exists():
            continue
        for path in sorted(scan_root.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            line_count = len(path.read_text(encoding="utf-8").splitlines())
            if line_count >= threshold:
                out.append((path.relative_to(root).as_posix(), line_count))
    return tuple(out)
