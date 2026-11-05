# Audit Report: Controlled Strategy Scenario Banks

## 1. Within-Scenario Length Balance

| Bank | Mean Token Span | Std Token Span | Min Span | Max Span | Mean Word Span | Mean Char Span |
| --- | --- | --- | --- | --- | --- | --- |
| Original | 4.58 | 1.61 | 2 | 11 | 3.41 | 23.93 |
| Bank A | 2.15 | 1.93 | 0 | 9 | 2.73 | 22.48 |
| Bank B | 2.79 | 2.79 | 0 | 13 | 3.02 | 24.74 |
| Bank C | 2.54 | 2.32 | 0 | 10 | 2.91 | 24.33 |

## 2. Strategy-Level Action Token Lengths

| Bank | Strategy | Mean Tokens | Std Tokens | Min Tokens | Max Tokens |
| --- | --- | --- | --- | --- | --- |
| Original | COOPERATE | 16.89 | 1.78 | 13 | 24 |
| Original | INDEPENDENT | 13.14 | 1.41 | 10 | 17 |
| Original | COMPETE_EXPLOIT | 14.08 | 1.42 | 11 | 18 |
| Original | DISENGAGE | 14.26 | 1.96 | 11 | 19 |
| Bank A | COOPERATE | 16.77 | 1.81 | 15 | 24 |
| Bank A | INDEPENDENT | 14.97 | 0.69 | 10 | 17 |
| Bank A | COMPETE_EXPLOIT | 15.18 | 0.58 | 15 | 18 |
| Bank A | DISENGAGE | 15.36 | 1.14 | 14 | 19 |
| Bank B | COOPERATE | 16.84 | 1.82 | 15 | 24 |
| Bank B | INDEPENDENT | 14.97 | 0.69 | 10 | 17 |
| Bank B | COMPETE_EXPLOIT | 15.29 | 0.68 | 15 | 18 |
| Bank B | DISENGAGE | 14.82 | 2.61 | 4 | 19 |
| Bank C | COOPERATE | 16.69 | 1.83 | 15 | 24 |
| Bank C | INDEPENDENT | 14.97 | 0.69 | 10 | 17 |
| Bank C | COMPETE_EXPLOIT | 15.14 | 0.50 | 15 | 18 |
| Bank C | DISENGAGE | 14.94 | 2.22 | 5 | 19 |

## 3. Cross-Bank Lexical Diversity and Phrasing Overlap

| Comparison | Total Pairs | Exact Text Matches | Mean Word Jaccard Similarity |
| --- | --- | --- | --- |
| Original_vs_Bank A | 496 | 235 | 0.920 |
| Original_vs_Bank B | 496 | 144 | 0.846 |
| Original_vs_Bank C | 496 | 144 | 0.849 |
| Bank A_vs_Bank B | 496 | 288 | 0.902 |
| Bank A_vs_Bank C | 496 | 288 | 0.903 |
| Bank B_vs_Bank C | 496 | 288 | 0.903 |

## 4. Strategy Vocabulary and N-Gram Frequencies

### Original
- **COOPERATE**:
  - Common words: with (100), the (72), a (62), an (62), human (60), automated (57)
  - Common bigrams: "a human" (60), "an automated" (55), "with a" (48), "with an" (48), "through the" (12)
- **INDEPENDENT**:
  - Common words: your (122), independently (74), on (42), using (42), local (26), standard (22)
  - Common bigrams: "independently using" (38), "on your" (28), "independently on" (16), "using your" (14), "according to" (12)
- **COMPETE_EXPLOIT**:
  - Common words: to (110), your (48), the (32), all (28), of (24), priority (18)
  - Common bigrams: "ahead of" (16), "claim exclusive" (8), "to finish" (8), "of others" (8), "at maximum" (8)
- **DISENGAGE**:
  - Common words: and (96), the (52), in (28), until (26), suspend (24), postpone (22)
  - Common bigrams: "and postpone" (18), "and defer" (12), "from the" (12), "shut down" (12), "until the" (10)

### Bank A
- **COOPERATE**:
  - Common words: with (100), the (72), a (62), an (62), human (60), automated (41)
  - Common bigrams: "a human" (60), "with a" (48), "with an" (48), "an automated" (41), "through the" (12)
- **INDEPENDENT**:
  - Common words: your (128), independently (74), as (70), planned (68), exactly (46), on (42)
  - Common bigrams: "as planned" (68), "exactly as" (40), "independently using" (38), "on your" (28), "your own" (16)
- **COMPETE_EXPLOIT**:
  - Common words: to (110), your (48), of (44), ahead (36), the (32), others (28)
  - Common bigrams: "ahead of" (36), "of others" (28), "your own" (18), "in order" (16), "order to" (16)
- **DISENGAGE**:
  - Common words: and (96), until (72), the (52), next (32), in (30), shift (26)
  - Common bigrams: "until next" (24), "next shift" (24), "until later" (22), "and postpone" (18), "and defer" (12)

### Bank B
- **COOPERATE**:
  - Common words: with (100), the (72), a (64), human (60), an (60), automated (41)
  - Common bigrams: "a human" (60), "with a" (48), "with an" (48), "an automated" (41), "through the" (12)
- **INDEPENDENT**:
  - Common words: your (120), independently (74), as (70), planned (68), exactly (54), on (42)
  - Common bigrams: "as planned" (68), "exactly as" (40), "independently using" (38), "on your" (28), "exactly for" (14)
- **COMPETE_EXPLOIT**:
  - Common words: to (110), your (48), of (44), ahead (36), the (32), others (28)
  - Common bigrams: "ahead of" (36), "of others" (28), "in order" (16), "order to" (16), "your own" (16)
- **DISENGAGE**:
  - Common words: and (92), until (78), the (52), later (38), in (26), pause (24)
  - Common bigrams: "until later" (38), "and postpone" (16), "until next" (14), "next shift" (14), "from the" (12)

### Bank C
- **COOPERATE**:
  - Common words: with (100), the (72), a (62), an (62), human (60), automated (39)
  - Common bigrams: "a human" (60), "with a" (48), "with an" (48), "an automated" (39), "through the" (12)
- **INDEPENDENT**:
  - Common words: your (120), independently (74), as (66), planned (64), exactly (48), on (42)
  - Common bigrams: "as planned" (64), "independently using" (38), "exactly as" (34), "on your" (28), "exactly for" (14)
- **COMPETE_EXPLOIT**:
  - Common words: to (110), your (48), of (44), ahead (36), first (34), the (32)
  - Common bigrams: "ahead of" (36), "of others" (28), "your own" (18), "in order" (16), "order to" (16)
- **DISENGAGE**:
  - Common words: and (94), until (62), the (52), in (26), later (26), postpone (22)
  - Common bigrams: "until later" (26), "and postpone" (16), "shut down" (14), "from the" (12), "until the" (10)
