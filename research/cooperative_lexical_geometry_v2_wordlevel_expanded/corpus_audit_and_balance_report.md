# Cooperative Lexical Geometry v2 Word-Level Expanded Corpus

## Scientific Audit and Corpus Balance Report

### 1. Overview and Core Research Question
The core question addressed by this research infrastructure is:
> **Have we produced a sufficiently large, semantically matched, genuinely word-level multilingual corpus to test whether cooperation exhibits excess lexical coherence beyond ordinary semantic similarity?**

**Answer:**
We have successfully expanded the word-level corpus from 24 pilot concepts to **200 fully balanced, structurally audited, dictionary-backed concepts** (50 concepts each across *cooperation*, *competition*, *independent action*, and *neutral activity*) across 5 languages (**English, French, Mandarin Chinese, Japanese, and Arabic**).

However, **the corpus is NOT YET ready for confirmatory embedding inference** because native fluent human speaker review remains outstanding across Arabic, Chinese, French, and Japanese. Automated checks, dictionary definitions, and morphological parses establish necessary structural and lexical defensibility, but do not substitute for native adjudication of nuanced pragmatic polysemy.

---

### 2. Maximum Defensible Cohort Size: Analysis and Determination
While the nominal target was 150 concepts per category (600 total across 4 categories):
1. **Linguistic Bottleneck across 5 Diverse Typological Families:**
   Finding 150 distinct single lexical words for *independent action* and *cooperation* that:
   - Are strictly single orthographic lexical words in all 5 languages (no multi-word phrases, no hyphens, no idioms);
   - Are non-synonymous (avoiding packing one category with near-synonyms while another spans broad concepts);
   - Share comparable frequency bands, parts of speech (primarily abstract action nouns / masdars), and semantic breadth;
   is linguistically impossible without severe translation strain, archaic or artificial lexicalization, or multi-word compositional phrases (e.g. Arabic "عدم تدخل" for non-intervention, French "diviser pour régner", Chinese "单打独斗").
2. **Defensible Threshold:**
   At **50 concepts per category (200 concepts total, 1,000 language-word tokens)**, each category retains rich subdomains without resorting to dubious translations or compositional phrasing. Expanding beyond 50 concepts per category in *independent action* introduces severe synonym dilution (repeating subtle variations of "solitude" or "isolation"). Thus, **50 items per category is the maximum defensible cohort size** under strict single-word matching constraints.

---

### 3. Wordhood Criteria across Typologically Diverse Languages
- **English (`en`):** Single unhyphenated orthographic word, primary nominal lemma (e.g., `cooperation`, `trust`, `sovereignty`).
- **French (`fr`):** Single orthographic token without spaces or hyphens (e.g., `coopération`, `vigie`, `neutralisme`; hyphenated terms like `non-intervention` or `avant-poste` were explicitly rejected).
- **Mandarin Chinese (`zh`):** Lexicalized 2-character (or 1-character) morpheme compound recognized as an atomic lexical entry in standard lexicography (CC-CEDICT, *Contemporary Chinese Dictionary* / 现代汉语词典), e.g., `合作`, `主权`, `隐居`.
- **Japanese (`ja`):** Recognized single unsegmented lexical noun (kango or wago) in standard dictionaries (*Daijirin*, *Kojien*, JMDict), e.g., `協力`, `自主`, `妥結`.
- **Arabic (`ar`):** Single uncompounded morphological lexical word (verbal noun / *masdar* or abstract noun) derived from a triconsonantal or quadriconsonantal root, without clitic prepositions or multi-word genitive constructs (*idafa*), e.g., `تعاون`, `سيادة`, `انشقاق`.

---

### 4. Corpus Balance and Subdomain Coverage

| Category | Total Concepts | Pilot Items | Confirmatory Items | Subdomain Breadth | Mean Char Length (EN/FR/ZH/JA/AR) |
|---|---|---|---|---|---|
| **Cooperation** | 50 | 6 | 44 | 10 subdomains (collective action, social trust, normative exchange, group cohesion, resource sharing, alliance structure, deliberative agreement, conflict resolution, prosocial benevolence, supportive action) | 8.98 / 9.24 / 2.00 / 2.04 / 4.86 |
| **Competition** | 50 | 6 | 44 | 7 subdomains (rivalrous contest, exploitative extraction, hegemonic control, market exclusion, deceptive maneuver, antagonistic dispute, predatory harm) | 8.10 / 8.26 / 2.00 / 2.14 / 4.68 |
| **Independent** | 50 | 6 | 44 | 5 subdomains (self-determination, spatial isolation, individual agency, seclusion boundary, detachment boundary) | 9.80 / 9.92 / 2.08 / 2.22 / 5.12 |
| **Neutral** | 50 | 6 | 44 | 7 subdomains (empirical inquiry, quantitative assessment, physical process, information processing, resource handling, systematic arrangement, material production) | 10.06 / 10.44 / 2.00 / 2.04 / 4.94 |

---

### 5. Protection Against Selection Bias
1. **Preservation of the Pilot:** The original 24-concept pilot corpus remains unmodified in `research/cooperative_lexical_geometry_v2_wordlevel/`.
2. **Explicit Provenance Cohorts:** Every concept in the expanded corpus is tagged with `cohort: 'pilot'` (24 concepts) or `cohort: 'confirmatory'` (176 concepts), enabling isolated analysis and preventing retrospective cherry-picking.
3. **No Model Inference Run:** In strict compliance with scientific governance, **no embedding models (E5, BGE-M3, LaBSE) were executed on this candidate cohort**, preserving clean hypothesis testing.

---

### 6. Outstanding Limitations and Gate Criteria for Confirmatory Run
Before initiating confirmatory model inference:
1. **Native Fluent Speaker Adjudication:** Human native speakers of French, Mandarin Chinese, Japanese, and Arabic must review each candidate word against its concept gloss for naturalness and register appropriateness.
2. **Polysemy and Frequency Calibration:** While dictionary definitions confirm nominal equivalence, empirical corpus frequencies (e.g. from SUBTLEX, Google Books Ngrams, or ArTenTen) should be documented to check for frequency-driven embedding artifacts.
3. **Formal Freeze Verification:** Verify cryptographic hashes in `frozen_manifest.json` against `lexicon.json` before feeding embeddings into the inferential pipeline.


### 7. Corrective Adjudications
- **CP25 (espionage):** Chinese label updated from agent noun  (spy) to standard activity noun  (espionage / intelligence work).
- **CP43 (ambush):** Japanese label updated from agent noun  (concealed troops) to standard action noun  (ambush attack).
- **CP48 (vendetta):** Arabic label corrected to restore the hamza  (blood revenge / feud) distinguishing it from the verb . Japanese label refined from generic  (struggle / conflict) to specific  (blood revenge / vendetta).
- **Verification Provenance Relabeling:** To prevent overstating verification claims prior to independent fluent speaker review, status tags are explicitly calibrated as  and .
