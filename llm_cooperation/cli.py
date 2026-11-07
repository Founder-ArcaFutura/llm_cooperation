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
@click.option("--scenarios-path", default=None, help="Path to scenarios JSON file.")
@click.option("--bank", type=click.Choice(["pilot", "expanded", "phase0b", "utility-matched", "phase1", "dose-response"]), default=None, help="Convenience bank selector.")
@click.option("--calibration-path", default=None, help="Path to calibration JSON file to audit.")
def cmd_audit_items(scenarios_path: Optional[str], bank: Optional[str] = None, calibration_path: Optional[str] = None):
    """Audit scenario balance, length, and permutation counterbalancing."""
    from llm_cooperation.items.audit import audit_calibration
    from llm_cooperation.items.audit_phase1 import audit_phase1_bank
    from llm_cooperation.items.dose_response_bank import audit_dose_response_bank

    target_path = scenarios_path
    if target_path is None:
        if bank == "phase1":
            target_path = "data/scenarios_phase1_prospective.json"
        elif bank in ("phase0b", "utility-matched"):
            target_path = "data/scenarios_phase0b_utility_matched.json"
        elif bank == "expanded":
            target_path = "data/scenarios_v1_expanded.json"
        elif bank == "dose-response":
            target_path = "data/scenarios_dose_response_exploratory.json"
        else:
            target_path = "data/scenarios.json"

    if bank == "phase1" or "phase1" in target_path.lower():
        success, flags = audit_phase1_bank(target_path)
    elif bank == "dose-response" or "dose_response" in target_path.lower():
        try:
            success = audit_dose_response_bank(target_path)
            click.echo("Dose-response bank counts, factorial, controls, option lengths, and counterbalancing passed.")
        except (AssertionError, KeyError, TypeError, ValueError) as exc:
            success = False
            click.echo(f"Dose-response bank audit failed: {exc}")
    else:
        success = audit_scenarios(target_path)

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
@click.option("--bank", type=click.Choice(["pilot", "expanded", "phase0b", "utility-matched", "phase1", "dose-response"]), default=None, help="Convenience bank selector.")
@click.option("--scenarios-path", default=None, help="Custom path to scenarios JSON file (defaults to data/scenarios.json or bank choice).")
@click.option("--split", type=click.Choice(["exploratory", "confirmatory", "all"]), default=None, help="Dataset split execution filter. In Phase 0B, defaults to 'exploratory'. Evaluating 'confirmatory' or 'all' requires authorization.")
@click.option("--authorize-confirmatory", is_flag=True, default=False, help="Explicit authorization flag required to evaluate the held-out confirmatory split.")
@click.option("--authorize-phase1-run", is_flag=True, default=False, help="Explicit authorization flag required to evaluate Phase 1 bank once frozen.")
@click.option("--output-dir", "-o", default="results", help="Directory to save raw results.")
@click.option("--precision", default="bfloat16", type=click.Choice(["bfloat16", "float16", "float32"]))
@click.option("--device", default="auto", help="Device map (e.g. 'auto', 'cuda', 'cpu').")
@click.option("--mock", is_flag=True, default=False, help="Run with mock predictions without loading model weights.")
@click.option("--seed", default=42, help="Random seed for mock generator.")
@click.option("--prompt-mode", default="standard_plaintext", type=click.Choice(["standard_plaintext", "openassistant"]), help="Prompt format mode.")
def cmd_run(model, revision, bank, scenarios_path, split, authorize_confirmatory, authorize_phase1_run, output_dir, precision, device, mock, seed, prompt_mode):
    """Run behavioural evaluation."""
    is_phase0b = False
    is_phase1 = False
    target_path = "data/scenarios.json"
    if bank == "phase1":
        target_path = "data/scenarios_phase1_prospective.json"
        is_phase1 = True
    elif bank in ("phase0b", "utility-matched"):
        target_path = "data/scenarios_phase0b_utility_matched.json"
        is_phase0b = True
    elif bank == "expanded":
        target_path = "data/scenarios_v1_expanded.json"
    elif bank == "pilot":
        target_path = "data/scenarios.json"
    elif bank == "dose-response":
        target_path = "data/scenarios_dose_response_exploratory.json"

    if scenarios_path is not None:
        target_path = scenarios_path
        if "phase1" in target_path.lower():
            is_phase1 = True
        elif "phase0b" in target_path.lower():
            is_phase0b = True

    # Default split logic
    effective_split = split
    if is_phase0b and effective_split is None:
        effective_split = "exploratory"

    # Confirmatory split authorization guard for Phase 0B
    if effective_split in ("confirmatory", "all") and is_phase0b and not authorize_confirmatory:
        raise click.ClickException(
            f"CONFIRMATORY SPLIT GUARD: Executing held-out confirmatory partition in Phase 0B "
            f"requires explicit scientific authorization (--authorize-confirmatory). "
            f"Phase 0B defaults to '--split exploratory' to protect confirmatory held-out isolation."
        )

    try:
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
            authorize_phase1_run=authorize_phase1_run,
        )
    except (PermissionError, ValueError, FileNotFoundError) as e:
        raise click.ClickException(str(e))


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


@main.command("analyze-dose-response")
@click.argument("results_path", type=click.Path(exists=True))
@click.option("--output-dir", "-o", default="reports/dose_response", help="Directory for dose-response outputs.")
@click.option("--bootstrap-samples", "-b", default=2000, type=int, help="Template-family bootstrap resamples.")
def cmd_analyze_dose_response(results_path, output_dir, bootstrap_samples):
    """Analyze a dose-response run and write machine-readable and Markdown reports."""
    import json
    from llm_cooperation.analysis.metrics import load_run_results, aggregate_by_scenario, audit_position_bias
    from llm_cooperation.analysis.dose_response import analyze_payoff_dose_response

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    metadata, records = load_run_results(results_path, validate=True)
    aggregates = aggregate_by_scenario(records)
    result = analyze_payoff_dose_response(aggregates, n_bootstraps=bootstrap_samples)
    valid_letter_rate = (
        sum(bool(r.get("is_valid_letter", False)) for r in records) / len(records)
        if records else 0.0
    )
    position_bias = audit_position_bias(records) if records else {k: 0.0 for k in "ABCD"}
    summary_path = out / "dose_response_summary.json"
    summary_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    report_path = out / "dose_response_report.md"
    sens = result["payoff_sensitivity"]
    eq = result["equal_utility_baseline"]
    interactions = result["interactions"]
    choice_slope_display = (
        "not estimable (no usable COOPERATE/INDEPENDENT choice cells)"
        if sens["choice_slope"] is None else f"{sens['choice_slope']:.4f}"
    )
    report_path.write_text(
        "# Payoff dose-response analysis\n\n"
        f"- Run: `{metadata.get('run_id', 'unknown')}` (`mock={metadata.get('mock', False)}`)\n"
        f"- Template families: {result['num_templates_analyzed']}\n"
        f"- Generated-letter validity (format diagnostic): {valid_letter_rate:.4f}\n"
        f"- Forced-choice position distribution (A/B/C/D): {position_bias}\n"
        f"- Equal-utility COOPERATE minus INDEPENDENT choice rate: {eq['choice_diff_mean']:.4f}\n"
        f"- Equal-utility log probability difference: {eq['log_prob_diff_mean']:.4f}\n"
        f"- Payoff sensitivity in COOPERATE share among COOPERATE/INDEPENDENT: {choice_slope_display}\n"
        f"- COOPERATE/INDEPENDENT indifference crossover (delta U): {sens['crossover_threshold_delta_u']}\n"
        f"- Partner-benefit modulation: {interactions['partner_benefit_modulation']}\n"
        f"- Reciprocity modulation: {interactions['reciprocity_modulation']}\n\n"
        "These exploratory estimates describe forced-choice outputs and do not establish an intrinsic preference or causal pretraining mechanism.\n",
        encoding="utf-8",
    )
    click.echo(f"Dose-response report: {report_path}")
    click.echo(f"Dose-response summary: {summary_path}")


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


@main.group("contrastive-mapping")
def cmd_contrastive_mapping():
    """Exploratory one-shot contrastive representation-mapping experiment."""
    pass


@cmd_contrastive_mapping.command("prepare")
@click.option("--output", "-o", required=True, help="Directory for prepared prompt dataset.")
@click.option("--bank", default="data/scenarios_phase0b_utility_matched.json", help="Scenario bank path.")
@click.option("--discovery-fraction", type=float, default=0.5, help="Fraction of families for discovery.")
@click.option("--seed", type=int, default=42, help="Deterministic partition seed.")
@click.option("--smoke", is_flag=True, default=False, help="Prepare small subset for smoke test.")
def cmd_cm_prepare(output, bank, discovery_fraction, seed, smoke):
    """Prepare single-action contrastive prompts and manifests."""
    from llm_cooperation.mechanistic.contrastive_mapping import prepare
    import json
    res = prepare(output, bank_path=bank, discovery_fraction=discovery_fraction, seed=seed, smoke=smoke)
    click.echo(json.dumps(res, indent=2))


@cmd_contrastive_mapping.command("run")
@click.option("--plan", required=True, help="Prepared plan directory.")
@click.option("--output", "-o", required=True, help="Output directory for activations.")
@click.option("--model", default="Qwen/Qwen2.5-1.5B", help="Target model identifier.")
@click.option("--revision", default="8faed761d45a263340a0528343f099c05c9a4323", help="Target model revision SHA.")
@click.option("--authorize-inference", is_flag=True, default=False, help="Authorize actual model inference.")
@click.option("--mock", is_flag=True, default=False, help="Run mock synthetic passes without GPU.")
def cmd_cm_run(plan, output, model, revision, authorize_inference, mock):
    """Run model inference and capture residual-stream activations."""
    from llm_cooperation.mechanistic.contrastive_mapping import run_inference
    import json
    res = run_inference(
        plan_dir=plan,
        output_dir=output,
        model_id=model,
        revision=revision,
        authorize=authorize_inference,
        mock=mock,
    )
    click.echo(json.dumps(res, indent=2))


@cmd_contrastive_mapping.command("analyze")
@click.option("--run-dir", required=True, help="Run directory with activations.")
@click.option("--prompts", required=True, help="Path to prompts.jsonl.")
@click.option("--output", "-o", required=True, help="Output directory for reports.")
@click.option("--n-boot", type=int, default=1000, help="Bootstrap resamples.")
def cmd_cm_analyze(run_dir, prompts, output, n_boot):
    """Analyze contrastive geometry on captured activations."""
    from llm_cooperation.mechanistic.contrastive_mapping import analyze_contrastive_mapping
    analyze_contrastive_mapping(run_dir=run_dir, prompts_path=prompts, output_dir=output, n_boot=n_boot)
    click.echo(f"Analysis completed. Report written to {output}")


@cmd_contrastive_mapping.command("smoke-test")
@click.option("--output", "-o", required=True, help="Output directory for smoke test artifacts.")
def cmd_cm_smoke(output):
    """Run complete mock end-to-end smoke test including failure mode assertions."""
    from llm_cooperation.mechanistic.contrastive_mapping import (
        DEFAULT_REVISION,
        prepare,
        run_inference,
        analyze_contrastive_mapping,
    )
    import json
    out_p = Path(output)
    plan_dir = out_p / "plan"
    run_dir = out_p / "run"
    analysis_dir = out_p / "analysis"
    click.echo("1. Preparing smoke plan...")
    prepare(plan_dir, smoke=True)
    click.echo("2. Running mock inference...")
    run_inference(plan_dir, run_dir, mock=True)
    click.echo("3. Analyzing contrastive representations...")
    analyze_contrastive_mapping(run_dir, plan_dir / "prompts.jsonl", analysis_dir, n_boot=200)

    click.echo("4. Verifying fail-closed assertions on corrupted inputs...")
    manifest_p = run_dir / "manifest.json"
    tampered_manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    tampered_manifest["model_revision"] = "badrevision0000000000000000000000000000000"
    manifest_p.write_text(json.dumps(tampered_manifest), encoding="utf-8")
    try:
        analyze_contrastive_mapping(run_dir, plan_dir / "prompts.jsonl", analysis_dir / "bad")
        raise AssertionError("Tampered manifest failed to raise ValueError")
    except ValueError:
        click.echo("  ✓ Detected tampered manifest")
    finally:
        tampered_manifest["model_revision"] = DEFAULT_REVISION
        manifest_p.write_text(json.dumps(tampered_manifest), encoding="utf-8")

    click.echo(f"Smoke test succeeded! Reports generated at {analysis_dir}")




@main.command("audit-controlled-banks")
@click.option(
    "--bank-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path("data/controlled_strategy_banks_v1"),
    help="Directory containing controlled banks A, B, C.",
)
@click.option(
    "--output-report",
    type=click.Path(file_okay=True, dir_okay=False, path_type=Path),
    default=Path("data/controlled_strategy_banks_v1/audit_report.md"),
    help="Path to markdown output report.",
)
def cmd_audit_controlled_banks(bank_dir: Path, output_report: Path):
    """Audit length-matching and lexical diversity of controlled strategy banks."""
    from llm_cooperation.items.audit_controlled_banks import (
        compute_bank_metrics,
        compute_cross_bank_diversity,
    )
    from llm_cooperation.items.controlled_banks import load_phase0b_scenarios

    orig_scenarios = load_phase0b_scenarios()
    click.echo(f"Loaded {len(orig_scenarios)} authoritative Phase 0B scenarios.")

    banks = {"Original": orig_scenarios}
    bank_files = {
        "Bank A": bank_dir / "bank_a_length_matched.json",
        "Bank B": bank_dir / "bank_b_lexically_diversified.json",
        "Bank C": bank_dir / "bank_c_independent_replication.json",
    }

    for name, path in bank_files.items():
        if path.exists():
            import json
            with path.open("r", encoding="utf-8") as f:
                d = json.load(f)
                scs = d.get("scenarios", d) if isinstance(d, dict) else d
                banks[name] = scs
                click.echo(f"Loaded {len(scs)} scenarios from {name} ({path.name}).")
        else:
            click.echo(f"Notice: {name} not found at {path}")

    metrics = {name: compute_bank_metrics(scs) for name, scs in banks.items()}
    diversity = compute_cross_bank_diversity(banks)

    click.echo("Summary of Within-Scenario Token Spans (Max - Min Tokens):")
    for name, m in metrics.items():
        ts = m["token_spans"]
        click.echo(f"  {name:10s}: Mean {ts['mean']:.2f} (std={ts['std']:.2f}, min={ts['min']}, max={ts['max']})")

    md_lines = [
        "# Audit Report: Controlled Strategy Scenario Banks",
        "",
        "## 1. Within-Scenario Length Balance",
        "",
        "| Bank | Mean Token Span | Std Token Span | Min Span | Max Span | Mean Word Span | Mean Char Span |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for name, m in metrics.items():
        ts = m["token_spans"]
        ws = m["word_spans"]
        cs = m["char_spans"]
        md_lines.append(
            f"| {name} | {ts['mean']:.2f} | {ts['std']:.2f} | {ts['min']} | {ts['max']} | {ws['mean']:.2f} | {cs['mean']:.2f} |"
        )

    md_lines.extend([
        "",
        "## 2. Strategy-Level Action Token Lengths",
        "",
        "| Bank | Strategy | Mean Tokens | Std Tokens | Min Tokens | Max Tokens |",
        "| --- | --- | --- | --- | --- | --- |",
    ])
    for name, m in metrics.items():
        for strat, s_stat in m["action_tokens"].items():
            md_lines.append(
                f"| {name} | {strat} | {s_stat['mean']:.2f} | {s_stat['std']:.2f} | {s_stat['min']} | {s_stat['max']} |"
            )

    md_lines.extend([
        "",
        "## 3. Cross-Bank Lexical Diversity and Phrasing Overlap",
        "",
        "| Comparison | Total Pairs | Exact Text Matches | Mean Word Jaccard Similarity |",
        "| --- | --- | --- | --- |",
    ])
    for comp, d_stat in diversity.items():
        md_lines.append(
            f"| {comp} | {d_stat['total_action_pairs']} | {d_stat['exact_matches']} | {d_stat['mean_word_jaccard_similarity']:.3f} |"
        )

    md_lines.extend([
        "",
        "## 4. Strategy Vocabulary and N-Gram Frequencies",
        "",
    ])
    for name, m in metrics.items():
        md_lines.append(f"### {name}")
        for strat in ["COOPERATE", "INDEPENDENT", "COMPETE_EXPLOIT", "DISENGAGE"]:
            top_w = ", ".join(f"{w} ({c})" for w, c in list(m["top_words"][strat].items())[:6])
            top_bg = ", ".join(f"\"{bg}\" ({c})" for bg, c in list(m["top_bigrams"][strat].items())[:5])
            md_lines.append(f"- **{strat}**:")
            md_lines.append(f"  - Common words: {top_w}")
            md_lines.append(f"  - Common bigrams: {top_bg}")
        md_lines.append("")

    output_report.parent.mkdir(parents=True, exist_ok=True)
    output_report.write_text("\n".join(md_lines), encoding="utf-8")
    click.echo(f"Audit report written to {output_report}")


if __name__ == "__main__":
    main()
