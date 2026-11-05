# Four-strategy real-model findings

This interpretation accompanies [`four_strategy_report.md`](four_strategy_report.md), the full machine-generated layerwise report, and [`four_strategy_report.json`](four_strategy_report.json), which contains every layer's metrics, confusion matrices, projections, permutation results, and geometry. The two PNGs show the layerwise probe scores and strategy geometry.

## Data and procedure

The source is the completed, non-mock `Qwen/Qwen2.5-1.5B` run at revision `8faed761d45a263340a0528343f099c05c9a4323`. Before analysis, all 496 activation archives were checked against the 497-entry evidence index (prompt inventory plus activations); all hashes matched. The prompt file matched the prepared full-run inventory exactly. Every tensor was finite and shaped `[28, 1536]`. The data contain 124 scenarios, 54 template/triad families, and 24 domains. Evaluation used 27 held-out families and 12 held-out domains; all four action labels from a scenario remained together, and no family crossed either split.

For each scenario and layer, the four strategy vectors were centered by subtracting their within-scenario mean. The classifier selected regularization using grouped discovery-only folds. Intervals resampled held-out families or domains as clusters. The domain-direction analysis gives each discovery domain equal weight. The length control fits a discovery-only ridge regression from within-scenario centered word and character counts to activations, then evaluates on residualized activations. It controls linear activation associations with these two counts, not action vocabulary or semantic content.

## Main findings

The four presented action descriptions are highly linearly distinguishable across both held-out scenario families and held-out domains. Across layers, family-held-out balanced accuracy ranges from **0.812 to 1.000**; strict domain-held-out balanced accuracy ranges from **0.885 to 0.993**, with domain macro-F1 from **0.855 to 0.993**. Per-vector unit normalization still gives **0.875 to 0.992** domain-held-out balanced accuracy, so rising activation magnitude alone does not explain the effect. After the word/character adjustment, four-class balanced accuracy ranges from **0.548 to 0.895**; it is **0.879 at layer 18** and **0.883 at layer 22**. Across 100 within-scenario permutations, the layerwise null means range from **0.246 to 0.257** in the family split and **0.245 to 0.253** in the domain split, around the four-class chance level of 0.25.

Cross-domain direction consistency is positive for every strategy at every layer before length adjustment: each strategy's held-out-domain direction-alignment pointwise 95% cluster interval excludes zero at all 28 layers. This is direct evidence that the scenario-centered strategy geometry generalizes across the bank's held-out domains. After length adjustment, the result is asymmetric. The COOPERATE alignment means fall from **0.433–0.760** (raw) to **0.012–0.226**; INDEPENDENT retains **0.332–0.532**, COMPETE_EXPLOIT **0.215–0.491**, and DISENGAGE **0.225–0.526**. Thus COOPERATE remains classifiable, but its pooled mean residual direction is much more sensitive to linear length-related activation signal than the other three. At some mid-to-late layers the adjusted COOPERATE direction still aligns positively across domains, although its cosine is considerably smaller.

Action descriptions are not length-matched: COOPERATE averages **13.75 words / 101.4 characters**, compared with INDEPENDENT at **10.61 / 83.0**, COMPETE_EXPLOIT at **11.39 / 82.4**, and DISENGAGE at **11.05 / 79.9**. The large attenuation of COOPERATE's mean-direction cosine after adjustment is therefore material. The adjusted classifier remaining well above chance shows that the whole four-class geometry is not reducible to a linear function of word and character count alone. It does not rule out effects of wording, tokenization, syntax, or other prompt features.

## Candidate layers

As an exploratory follow-up screen, layers were flagged when all four strategies had pointwise 95% cluster-interval lower bounds above zero for both length-adjusted held-out-domain alignment and projection margin, and length-adjusted four-class balanced accuracy was at least 0.85. This yields **layers 17–19 and 21–23**. Representative layers 18 and 22 show near-ceiling family-held-out results and strong domain-held-out results:

| Layer | Family balanced accuracy (95% cluster CI) | Domain balanced accuracy (95% cluster CI) | Domain macro-F1 (95% cluster CI) | Length-adjusted balanced accuracy | Unit-normalized balanced accuracy |
|---:|---:|---:|---:|---:|---:|
| 18 | 1.000 [1.000, 1.000] | 0.979 [0.948, 1.000] | 0.978 [0.946, 1.000] | 0.879 | 0.976 |
| 22 | 1.000 [1.000, 1.000] | 0.990 [0.969, 1.000] | 0.989 [0.967, 1.000] | 0.883 | 0.992 |

At both layers, each strategy's one-versus-rest AUROC rounds to **1.000**. At layer 18, the domain confusion matrix (rows/columns ordered COOPERATE, INDEPENDENT, COMPETE_EXPLOIT, DISENGAGE) is `[[62,0,0,0],[0,60,2,0],[2,1,59,0],[0,0,0,62]]`. At layer 22 it is `[[62,0,0,0],[0,62,0,0],[2,0,60,0],[0,0,0,62]]`.

The strategy directions are not orthogonal. Their effective rank is about **2.87 at layer 18** and **2.91 at layer 22**, near the maximum rank of three imposed by four-way scenario-centering. At layer 18, for example, COOPERATE's direction cosine is −0.276 with INDEPENDENT, −0.653 with COMPETE_EXPLOIT, and −0.565 with DISENGAGE; several other pairwise relationships are weak or positive. The full cosine matrix at every layer is in the JSON.

Layers **18 and 22** are reasonable candidates for follow-up because the four-class performance remains high after the simple length adjustment and the held-out directions satisfy the exploratory criterion. The broader flagged set should be retained when planning follow-up; selecting only the best layers after inspection would add selection bias. These are candidate layers for mechanistic investigation, not localization claims. A measurable signal at saved layer 0 does not show that its representation originates there.

## Interpretation and limits

The evidence supports reproducible, domain-general linear information about which of these four action descriptions was presented. COOPERATE is distinguishable in the raw representation and remains highly decodable after the measured length adjustment, while its mean residual direction is more length-sensitive than the other three. INDEPENDENT, COMPETE_EXPLOIT, and DISENGAGE also have strong and, after this adjustment, generally more stable domain-aligned mean directions. All four must be interpreted together: their centered means occupy a shared, nonorthogonal, approximately three-dimensional subspace.

There are 12 held-out domains and 27 held-out families. Bootstrap intervals are pointwise, not adjusted for scanning 28 layers and four strategies; the candidate rule is post hoc and exploratory. The lexical adjustment covers only linear effects of two simple length counts, not lexical identity or semantic equivalence. A single pretrained model, prompt format, scenario bank, and frozen set of action descriptions cannot establish generalization to other phrasings or tasks. Linear decodability does not show model preference, use during action selection, or distinct causal decision mechanisms.
