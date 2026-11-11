# Exploratory choice-set intervention

This reruns the draft Phase 1 bank in two separately prompted conditions, with identical stems and original option text. Four-option uses the original four cyclic orders; three-option removes COOPERATE and uses all six orders of the remaining strategies. Each model receives 600 independent prompts (60 × 10). No previous inference results are substituted. Each prompt records both greedy generated text with strict isolated-letter validation and a forced-choice positional score: first-token logits for the available letters, conditional probabilities, and the highest-scoring letter and strategy. Exact prompt-boundary tokenization must yield distinct single tokens for all available letters; otherwise the positional score is null and the generated response is still recorded. Token IDs and the chosen space/no-space continuation are recorded. Raw outputs, mappings, prompts, revisions and bank hash are retained. A partially completed run is stored on Modal volume `llm-coop-results` under `choice_set/<run_id>/rows.jsonl` and committed after each scenario. Completed runs also download to `results/choice_set/<run_id>/`.

The launcher covers the twelve Phase 1 protocol base models, the Qwen instruct comparator, and the Pythia SFT comparator from the recent CLM study. Some checkpoints require Hugging Face gated access. To use the existing Modal secret named `huggingface-secret`, pass `-UseHuggingFaceSecret`. Failed models are reported and the launcher continues; rerun selected models with `-Models @('model/id', 'model/id')`.

The summaries separately count valid generated letters and valid positional scores, and report invalid responses, letter frequencies, strategy frequencies, and scenarios with the same strategy across every order for both measures. Inspect these before interpreting strategy percentages: fixed-letter behavior produces balanced strategy totals under counterbalancing. Counts are repeated presentations, not independent scenarios; cluster uncertainty by template, and compare partner and control strata separately. The three-option bank has no independent calibration suite in this harness, and order consistency alone does not establish comprehension. Four- and three-option prompts differ in option count and label instruction as well as cooperation availability; changes do not isolate a mechanism or eliminate wording, utility, or positional effects. This is an exploratory intervention on an already exposed, unreviewed draft, not the preregistered prospective replication.

Run from repository root in PowerShell:

```powershell
.\scripts\run_choice_set.ps1 -UseHuggingFaceSecret
```

For a selected subset:

```powershell
.\scripts\run_choice_set.ps1 -Models @('EleutherAI/pythia-12b-deduped', 'founder-arcafutura/pythia-12b-exploratory-20261022', 'Qwen/Qwen2.5-3B') -UseHuggingFaceSecret
```

The two measures are computed on the same prompt: positional scoring chooses the highest-probability permitted letter even if unconstrained generation is invalid. Their disagreement and their separate validity rates are useful diagnostics. Conditional probabilities sum to one within the available letter set and are not unconditional probabilities or evidence of understanding.

## Optional fourth alternative

`-Mode all` runs the original four-option condition, the three-option condition, and the `four_neutral` replacement condition (840 presentations per model). `-Mode replacement-only` runs only the replacement condition (240 per model), so already completed conditions need not be repeated. The default `standard` runs the original two conditions (600 per model). The 14-model cohort and both output measures are unchanged.

```powershell
.\scripts\run_choice_set.ps1 -Mode all
.\scripts\run_choice_set.ps1 -Mode replacement-only
```

The replacement occupies the original cooperation option's position in each of the four matched cyclic orders. Original noncooperative choices and the stem are unchanged. The 30 new alternative texts are shared by each human/AI pair and stored in `data/choice_set_neutral_replacements.json`; their SHA-256 is recorded in replacement-run metadata. The text is newly drafted and unreviewed: neutrality, distinctness, feasibility, payoff equivalence, and absence of partner effects are not established. Some alternatives introduce a new action or unspecified equipment, so they need not be equally attractive or equivalent to any existing option. The cooperative option is removed but cooperative information in the stem remains. The neutral-replacement comparison is exploratory and does not isolate lexical overlap.
