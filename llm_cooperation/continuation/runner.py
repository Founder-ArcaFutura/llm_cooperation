"""Runner for the continuation-likelihood cooperation assay.

Orchestrates scenario loading, prefix construction, continuation scoring,
and result serialization. Integrates with existing Phase 1 holdout guards.

This runner is entirely separate from the forced-choice runner in
llm_cooperation/harness/runner.py. It does not modify or depend on
the forced-choice evaluation path beyond the shared scenario schema.
"""

import hashlib
import json
import os
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from llm_cooperation.items.schema import ScenarioBank, StrategyType, Scenario
from llm_cooperation.continuation.schema import (
    CandidateScoreResult,
    ScenarioContinuationResult,
    ContinuationRunRecord,
)
from llm_cooperation.continuation.templates import (
    build_prefix,
    ALL_TEMPLATE_IDS,
    TEMPLATE_BY_ID,
)
from llm_cooperation.continuation.scorer import (
    score_all_strategies_for_prefix,
    score_continuation_mock,
)
from llm_cooperation.harness.runner import verify_provisional_phase1_bank

# ---------------------------------------------------------------------------
# Supported banks (mirrors modal_app.py SUPPORTED_BANKS, read-only access)
# ---------------------------------------------------------------------------
SUPPORTED_BANKS = {
    "pilot": "data/scenarios.json",
    "expanded": "data/scenarios_v1_expanded.json",
    "phase0b": "data/scenarios_phase0b_utility_matched.json",
    "utility-matched": "data/scenarios_phase0b_utility_matched.json",
    "phase1": "data/scenarios_phase1_prospective.json",
    "dose-response": "data/scenarios_dose_response_exploratory.json",
}

# Remote paths (used inside Modal containers)
REMOTE_BANK_PATHS = {
    k: f"/root/{v}" for k, v in SUPPORTED_BANKS.items()
}


def compute_file_hash(filepath: str) -> str:
    """SHA-256 hash of a file for provenance tracking."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def get_git_commit() -> Optional[str]:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, check=False,
        )
        return res.stdout.strip() if res.returncode == 0 else None
    except Exception:
        return None


def compute_rankings(
    scores: Dict[str, CandidateScoreResult],
) -> Tuple[Dict[str, int], Dict[str, int]]:
    """Compute rank-by-sum and rank-by-mean for each strategy.

    Rank 1 = highest log-probability (least negative = most probable).
    """
    strategies = list(scores.keys())
    sum_vals = {s: scores[s].sum_log_prob for s in strategies}
    mean_vals = {s: scores[s].mean_log_prob for s in strategies}

    rank_by_sum = {
        s: rank
        for rank, s in enumerate(
            sorted(strategies, key=lambda x: sum_vals[x], reverse=True), start=1
        )
    }
    rank_by_mean = {
        s: rank
        for rank, s in enumerate(
            sorted(strategies, key=lambda x: mean_vals[x], reverse=True), start=1
        )
    }
    return rank_by_sum, rank_by_mean


def build_scenario_result(
    scenario: Scenario,
    scores: Dict[str, CandidateScoreResult],
    template_id: str,
    candidate_wording_id: str,
) -> ScenarioContinuationResult:
    """Build a ScenarioContinuationResult from raw scores."""
    rank_by_sum, rank_by_mean = compute_rankings(scores)

    coop_key = StrategyType.COOPERATE.value
    indep_key = StrategyType.INDEPENDENT.value
    comp_key = StrategyType.COMPETE_EXPLOIT.value

    coop_vs_indep = None
    coop_vs_comp = None
    if coop_key in scores and indep_key in scores:
        coop_vs_indep = scores[coop_key].sum_log_prob - scores[indep_key].sum_log_prob
    if coop_key in scores and comp_key in scores:
        coop_vs_comp = scores[coop_key].sum_log_prob - scores[comp_key].sum_log_prob

    coop_rank_sum = rank_by_sum.get(coop_key, 0)
    coop_rank_mean = rank_by_mean.get(coop_key, 0)

    return ScenarioContinuationResult(
        scenario_id=scenario.id,
        partner_type=scenario.partner_type.value,
        context_type=scenario.context_type.value,
        template_id=template_id,
        candidate_wording_id=candidate_wording_id,
        domain=scenario.domain,
        split=scenario.split,
        source_type=scenario.source_type,
        scores=scores,
        rank_by_sum=rank_by_sum,
        rank_by_mean=rank_by_mean,
        coop_vs_independent_sum_delta=coop_vs_indep,
        coop_vs_compete_sum_delta=coop_vs_comp,
        coop_rank_by_sum=coop_rank_sum,
        coop_rank_by_mean=coop_rank_mean,
        coop_first_by_sum=(coop_rank_sum == 1),
        coop_first_by_mean=(coop_rank_mean == 1),
    )


def run_continuation_experiment(
    model_name: str,
    scenarios_path: str = "data/scenarios_phase1_prospective.json",
    output_dir: str = "results",
    revision: Optional[str] = None,
    precision: str = "bfloat16",
    device: str = "auto",
    mock: bool = False,
    seed: int = 42,
    template_ids: Optional[List[str]] = None,
    candidate_wording_id: str = "original",
    split_filter: Optional[str] = None,
    include_control_context: bool = False,
    control_scenario_id: Optional[str] = None,
) -> Path:
    """Run continuation-likelihood assay and save results to JSONL.

    Safety:
    - Never accesses Phase 1 confirmatory holdout (Phase 1 bank requires
      explicit authorization via existing runner guards).
    - Outputs are explicitly marked exploratory.
    - Source bank is read-only; not modified.

    Args:
        model_name: HuggingFace model identifier.
        scenarios_path: Path to scenario bank JSON.
        output_dir: Directory for output JSONL file.
        revision: Model revision SHA (for reproducibility).
        precision: 'bfloat16', 'float16', or 'float32'.
        device: 'auto', 'cuda', 'cpu'.
        mock: If True, use mock scorer without loading model weights.
        seed: Random seed for mock scorer.
        template_ids: List of template IDs to use. Defaults to all three.
        candidate_wording_id: Wording variant identifier.
        split_filter: If set, only score scenarios with this split.
        include_control_context: Score each candidate against a control scenario.
        control_scenario_id: Scenario ID to use as mismatched context.

    Returns:
        Path to output JSONL file.
    """
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(scenarios_path):
        raise FileNotFoundError(f"Scenario bank not found: {scenarios_path}")

    with open(scenarios_path, "r", encoding="utf-8") as f:
        bank_data = json.load(f)

    bank = ScenarioBank(**bank_data)
    scenarios = bank.scenarios

    # Explicit guard: refuse to run on Phase 1 bank unless it is provisional
    is_phase1 = "phase1" in Path(scenarios_path).name.lower() or any(
        getattr(s, "source_type", None) == "prospective_replication"
        or (s.template_id and s.template_id.startswith("phase1_"))
        or (s.id and s.id.startswith("phase1_"))
        for s in bank.scenarios
    )
    if is_phase1:
        if bank.status == "draft_pending_review":
            verify_provisional_phase1_bank(scenarios_path)
            print(
                "[CONTINUATION RUNNER] PHASE 1 PROVISIONAL: "
                "Scoring unadjudicated draft corpus as exploratory. "
                "NOT a confirmatory replication."
            )
        else:
            raise PermissionError(
                f"PHASE 1 HOLDOUT PROTECTION TRIGGERED: The Phase 1 bank status is '{bank.status}'. "
                "Continuation assay is currently authorized only for the provisional draft Phase 1 bank."
            )

    if split_filter:
        scenarios = [s for s in scenarios if getattr(s, "split", None) == split_filter]
        if not scenarios:
            raise ValueError(f"No scenarios match split_filter='{split_filter}'")

    if template_ids is None:
        template_ids = ALL_TEMPLATE_IDS

    for tid in template_ids:
        if tid not in TEMPLATE_BY_ID:
            raise ValueError(
                f"Unknown template_id '{tid}'. Valid: {ALL_TEMPLATE_IDS}"
            )

    # Load model (or use mock)
    model = None
    tokenizer = None
    effective_precision = precision
    model_class_name = None

    if not mock:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        torch_dtype_map = {
            "bfloat16": torch.bfloat16,
            "float16": torch.float16,
            "float32": torch.float32,
        }
        if precision not in torch_dtype_map:
            raise ValueError(f"Unsupported precision '{precision}'")

        print(f"[continuation_runner] Loading tokenizer for {model_name}...")
        tokenizer = AutoTokenizer.from_pretrained(
            model_name, revision=revision, trust_remote_code=True
        )
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        print(f"[continuation_runner] Loading model {model_name} (dtype={precision}, device={device})...")
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            revision=revision,
            torch_dtype=torch_dtype_map[precision],
            device_map=device,
            trust_remote_code=True,
        )
        model.eval()
        effective_precision = str(model.dtype).replace("torch.", "")
        model_class_name = model.__class__.__name__
        print(f"[continuation_runner] Model loaded. effective_precision={effective_precision}")

    rng = np.random.default_rng(seed=seed)

    all_scenario_results: List[ScenarioContinuationResult] = []

    # Optionally set up control scenario
    control_scenario: Optional[Scenario] = None
    if include_control_context and control_scenario_id:
        ctrl_matches = [s for s in bank.scenarios if s.id == control_scenario_id]
        if not ctrl_matches:
            raise ValueError(f"Control scenario ID '{control_scenario_id}' not found in bank")
        control_scenario = ctrl_matches[0]

    n_total = len(scenarios) * len(template_ids)
    processed = 0
    print(f"[continuation_runner] Scoring {len(scenarios)} scenarios x "
          f"{len(template_ids)} templates = {n_total} combinations "
          f"(mock={mock})...")

    for scenario in scenarios:
        strategy_continuations: Dict[StrategyType, str] = dict(scenario.options)

        for template_id in template_ids:
            prefix_text = build_prefix(scenario.stem, template_id)

            scores = score_all_strategies_for_prefix(
                model=model,
                tokenizer=tokenizer,
                prefix_text=prefix_text,
                strategy_continuations=strategy_continuations,
                model_name=model_name,
                model_revision=revision,
                precision=effective_precision,
                scenario_id=scenario.id,
                template_id=template_id,
                candidate_wording_id=candidate_wording_id,
                mock=mock,
                rng=rng,
            )

            sc_result = build_scenario_result(
                scenario=scenario,
                scores=scores,
                template_id=template_id,
                candidate_wording_id=candidate_wording_id,
            )
            all_scenario_results.append(sc_result)

            processed += 1
            if processed % 20 == 0 or processed == n_total:
                print(f"  [{processed}/{n_total}] scenarios processed...")

    # Build run metadata
    safe_name = model_name.replace("/", "_")
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    entropy = uuid.uuid4().hex[:8]
    run_id = f"clm_{safe_name}_{ts}_{entropy}"
    filename = f"{run_id}.jsonl"
    out_path = Path(output_dir) / filename

    torch_v = None
    transformers_v = None
    try:
        import torch
        torch_v = torch.__version__
    except Exception:
        pass
    try:
        import transformers
        transformers_v = transformers.__version__
    except Exception:
        pass

    run_record = ContinuationRunRecord(
        run_id=run_id,
        model_name=model_name,
        model_revision=revision,
        model_class=model_class_name or ("MockModel" if mock else None),
        tokenizer_name=model_name if not mock else None,
        effective_precision=effective_precision,
        requested_precision=precision,
        timestamp=datetime.now(timezone.utc).isoformat(),
        git_commit=get_git_commit(),
        torch_version=torch_v,
        transformers_version=transformers_v,
        scenario_bank=Path(scenarios_path).name,
        scenario_bank_hash=compute_file_hash(scenarios_path),
        num_scenarios=len(scenarios),
        templates_used=template_ids,
        wording_variants=[candidate_wording_id],
        include_control_context=include_control_context,
        control_scenario_id=control_scenario_id,
        is_confirmatory=False,
        num_scenario_results=len(all_scenario_results),
        seed=seed,
        scenario_results=all_scenario_results,
    )

    with open(out_path, "w", encoding="utf-8") as f:
        # Header line: metadata without individual results
        header = run_record.model_dump(exclude={"scenario_results"})
        f.write(json.dumps(header) + "\n")
        # One line per scenario result
        for sr in all_scenario_results:
            f.write(json.dumps(sr.model_dump()) + "\n")

    print(f"[continuation_runner] Done. Output: {out_path}")
    return out_path


def load_continuation_results(
    results_path: str,
) -> Tuple[Dict, List[Dict]]:
    """Load a continuation-likelihood results JSONL file.

    Returns:
        (metadata_dict, list_of_scenario_result_dicts)
    """
    with open(results_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        raise ValueError(f"Empty results file: {results_path}")

    metadata = json.loads(lines[0])
    records = [json.loads(line) for line in lines[1:]]
    return metadata, records
