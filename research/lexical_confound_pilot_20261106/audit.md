# Automatic token-length and overlap audit

Source: 124 scenarios, 54 families; pinned Qwen tokenizer 8faed761d45a263340a0528343f099c05c9a4323.

| Strategy | Mean action tokens |
|---|---:|
| COOPERATE | 16.895 |
| INDEPENDENT | 13.145 |
| COMPETE_EXPLOIT | 14.081 |
| DISENGAGE | 14.258 |

Naturally inverted original quartets: 0.

| Length-distribution pair | Histogram overlap (0–1) |
|---|---:|
| COOPERATE:INDEPENDENT | 0.234 |
| COOPERATE:COMPETE_EXPLOIT | 0.290 |
| COOPERATE:DISENGAGE | 0.427 |
| INDEPENDENT:COMPETE_EXPLOIT | 0.645 |
| INDEPENDENT:DISENGAGE | 0.726 |
| COMPETE_EXPLOIT:DISENGAGE | 0.774 |

Six-fold family-held-out baseline diagnostics (equal family weight at reporting):

- length_only: 0.561
- lexical_only: 0.970

Lexical features include meaningful strategy vocabulary; high performance is not proof of a spurious confound.
Histogram overlap does not establish within-scenario equivalence. All original counts are retained in audit.json.

Selected: 12 families, 32 scenarios, 12 domains.
Feasibility selection uses metadata/text only and enriches for usable existing candidate lengths. It is not representative sampling.

Complete-family coverage BEFORE semantic review:

- length: 9 families (template_015, template_016, template_022, template_024, template_031, template_035, template_046, template_048, template_053)
- ablation: 12 families (template_002, template_015, template_016, template_022, template_024, triad_01, template_031, template_035, template_046, template_048, template_053, triad_03)
- meaning: 4 families (template_015, template_022, template_046, template_048)
- content: 1 families (template_053)

All candidates remain quarantined. No new model inference or accepted semantic equivalence.
Article deletion is strongly strategy-asymmetric. Partial panels explicitly leave unavailable actions unchanged.
No balanced all-strategy ablation result or general paraphrase robustness claim is licensed by these partial panels.
Scaling recommendation: review the bounded length and targeted-ablation pilot; do not scale the corpus.
