"""Unified CLI entry point for the LLM cooperation experiment harness."""

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
def cmd_audit_items(scenarios_path: str):
    """Audit scenario balance, length, and permutation counterbalancing."""
    success = audit_scenarios(scenarios_path)
    if not success:
        raise click.ClickException("Scenario audit failed.")


@main.command("run")
@click.option("--model", "-m", required=True, help="Hugging Face model identifier or mock name.")
@click.option("--revision", default=None, help="Specific commit SHA or branch revision.")
@click.option("--scenarios-path", default="data/scenarios.json", help="Path to scenarios JSON file.")
@click.option("--output-dir", "-o", default="results", help="Directory to save raw results.")
@click.option("--precision", default="bfloat16", type=click.Choice(["bfloat16", "float16", "float32"]))
@click.option("--device", default="auto", help="Device map (e.g. 'auto', 'cuda', 'cpu').")
@click.option("--mock", is_flag=True, default=False, help="Run with mock predictions without loading model weights.")
@click.option("--seed", default=42, help="Random seed for mock generator.")
@click.option("--prompt-mode", default="standard_plaintext", type=click.Choice(["standard_plaintext", "openassistant"]), help="Prompt format mode.")
def cmd_run(model, revision, scenarios_path, output_dir, precision, device, mock, seed, prompt_mode):
    """Run Phase 0 behavioural evaluation on 96 presentations."""
    run_experiment(
        model_name=model,
        scenarios_path=scenarios_path,
        output_dir=output_dir,
        revision=revision,
        precision=precision,
        device=device,
        mock=mock,
        seed=seed,
        prompt_mode=prompt_mode,
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
