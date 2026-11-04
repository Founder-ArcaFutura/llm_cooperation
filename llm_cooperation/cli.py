"""Unified CLI entry point for the LLM cooperation experiment harness."""

from typing import Optional
import click
from pathlib import Path

from llm_cooperation.items.audit import audit_scenarios
from llm_cooperation.harness.runner import run_experiment
from llm_cooperation.analysis.pipeline import analyze_results


@click.group()
def main():
    """LLM Cooperation: Pretrained Strategy-Selection Harness and Analysis."""
    pass


@main.command("audit-items")
@click.option("--scenarios-path", default="data/scenarios.json", help="Path to scenarios JSON file.")
@click.option("--calibration-path", default=None, help="Path to calibration JSON file to audit.")
def cmd_audit_items(scenarios_path: str, calibration_path: Optional[str] = None):
    """Audit scenario balance, length, and permutation counterbalancing."""
    from llm_cooperation.items.audit import audit_calibration
    success = audit_scenarios(scenarios_path)
    if calibration_path:
        calib_success = audit_calibration(calibration_path)
        success = success and calib_success
    if not success:
        raise click.ClickException("Item audit failed.")


@main.command("calibrate")
@click.option("--model", "-m", required=True, help="Hugging Face model identifier or mock name.")
@click.option("--calibration-path", default="data/calibration_bank.json", help="Path to calibration JSON file.")
@click.option("--revision", default=None, help="Specific commit SHA or branch revision.")
@click.option("--output-dir", "-o", default="results", help="Directory to save raw results.")
@click.option("--precision", default="bfloat16", type=click.Choice(["bfloat16", "float16", "float32"]))
@click.option("--device", default="auto", help="Device map (e.g. 'auto', 'cuda', 'cpu').")
@click.option("--mock", is_flag=True, default=False, help="Run with mock predictions without loading model weights.")
@click.option("--seed", default=42, help="Random seed for mock generator.")
@click.option("--prompt-mode", default="standard_plaintext", type=click.Choice(["standard_plaintext", "openassistant"]), help="Prompt format mode.")
def cmd_calibrate(model, calibration_path, revision, output_dir, precision, device, mock, seed, prompt_mode):
    """Run diagnostic multiple-choice calibration evaluation."""
    from llm_cooperation.harness.runner import run_calibration
    out_path, summary = run_calibration(
        model_name=model,
        calibration_path=calibration_path,
        output_dir=output_dir,
        revision=revision,
        precision=precision,
        device=device,
        mock=mock,
        seed=seed,
        prompt_mode=prompt_mode,
    )
    click.echo(f"Calibration completed: Status={summary['status']}, Output={out_path}")


@main.command("run")
@click.option("--model", "-m", required=True, help="Hugging Face model identifier or mock name.")
@click.option("--revision", default=None, help="Specific commit SHA or branch revision.")
@click.option("--bank", type=click.Choice(["pilot", "expanded", "phase0b", "utility-matched"]), default=None, help="Convenience bank selector ('pilot', 'expanded', or 'utility-matched' / 'phase0b').")
@click.option("--scenarios-path", default=None, help="Custom path to scenarios JSON file (defaults to data/scenarios.json or bank choice).")
@click.option("--split", type=click.Choice(["exploratory", "confirmatory", "all"]), default=None, help="Dataset split execution filter. In Phase 0B, defaults to 'exploratory'. Evaluating 'confirmatory' or 'all' requires authorization.")
@click.option("--authorize-confirmatory", is_flag=True, default=False, help="Explicit authorization flag required to evaluate the held-out confirmatory split.")
@click.option("--output-dir", "-o", default="results", help="Directory to save raw results.")
@click.option("--precision", default="bfloat16", type=click.Choice(["bfloat16", "float16", "float32"]))
@click.option("--device", default="auto", help="Device map (e.g. 'auto', 'cuda', 'cpu').")
@click.option("--mock", is_flag=True, default=False, help="Run with mock predictions without loading model weights.")
@click.option("--seed", default=42, help="Random seed for mock generator.")
@click.option("--prompt-mode", default="standard_plaintext", type=click.Choice(["standard_plaintext", "openassistant"]), help="Prompt format mode.")
def cmd_run(model, revision, bank, scenarios_path, split, authorize_confirmatory, output_dir, precision, device, mock, seed, prompt_mode):
    """Run Phase 0 or Phase 0B behavioural evaluation."""
    is_phase0b = False
    target_path = "data/scenarios.json"
    if bank in ("phase0b", "utility-matched"):
        target_path = "data/scenarios_phase0b_utility_matched.json"
        is_phase0b = True
    elif bank == "expanded":
        target_path = "data/scenarios_v1_expanded.json"
    elif bank == "pilot":
        target_path = "data/scenarios.json"

    if scenarios_path is not None:
        target_path = scenarios_path
        if "phase0b" in target_path.lower():
            is_phase0b = True

    # Default split logic
    effective_split = split
    if is_phase0b and effective_split is None:
        effective_split = "exploratory"

    # Confirmatory split authorization guard
    if effective_split in ("confirmatory", "all") and is_phase0b and not authorize_confirmatory:
        raise click.ClickException(
            f"CONFIRMATORY SPLIT GUARD: Executing held-out confirmatory partition in Phase 0B "
            f"requires explicit scientific authorization (--authorize-confirmatory). "
            f"Phase 0B defaults to '--split exploratory' to protect confirmatory held-out isolation."
        )

    run_experiment(
        model_name=model,
        scenarios_path=target_path,
        output_dir=output_dir,
        revision=revision,
        precision=precision,
        device=device,
        mock=mock,
        seed=seed,
        prompt_mode=prompt_mode,
        split_filter=effective_split if effective_split != "all" else None,
    )


@main.command("analyze")
@click.argument("results_path", type=click.Path(exists=True))
@click.option("--output-dir", "-o", default="reports", help="Directory to output reports and figures.")
@click.option("--bootstrap-samples", "-b", default=2000, help="Number of scenario-cluster bootstrap samples.")
def cmd_analyze(results_path, output_dir, bootstrap_samples):
    """Analyze raw experimental outputs and generate reports."""
    analyze_results(
        results_path=results_path,
        output_dir=output_dir,
        num_bootstraps=bootstrap_samples,
    )


@main.command("compare-models")
@click.argument("results_paths", nargs=-1, required=True, type=click.Path(exists=True))
@click.option("--output-dir", "-o", default="reports", help="Directory to output comparison report.")
@click.option("--bootstrap-samples", "-b", default=2000, help="Number of scenario-cluster bootstrap samples.")
def cmd_compare_models(results_paths, output_dir, bootstrap_samples):
    """Generate cross-model comparison report separating base models and post-trained comparators."""
    from llm_cooperation.analysis.pipeline import compare_models
    out_file = compare_models(
        results_paths=list(results_paths),
        output_dir=output_dir,
        num_bootstraps=bootstrap_samples,
    )
    click.echo(f"Saved cross-model comparison report to {out_file}")


if __name__ == "__main__":
    main()
