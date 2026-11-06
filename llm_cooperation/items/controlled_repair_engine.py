"""Conservative offline controlled-bank feasibility search.

Only explicit whole-phrase changes are permitted. These are candidates for human
review, not proofs of semantic or grammatical equivalence.
"""
import itertools
import re
from difflib import SequenceMatcher

STRATEGIES = ('COOPERATE', 'INDEPENDENT', 'COMPETE_EXPLOIT', 'DISENGAGE')
BANKS = ('A', 'B', 'C')
RULES = (('through the shared', 'via the shared'),
         ('based solely on', 'solely based on'),
         ('via VHF radio', 'over VHF radio'))
WORD = re.compile(r'[a-z0-9]+', re.I)
BAD = re.compile(r'\b(?:according in order to|in order to to|the the|an early docking access)\b', re.I)


def grammatical_screen(text):
    return bool(text and text[0].isupper() and text.endswith('.') and not BAD.search(text))


def variants(text):
    """Return original and single explicitly enumerated context-bound edits."""
    result = {text}
    for a, b in RULES:
        for source, dest in ((a, b), (b, a)):
            if source in text:
                result.add(text.replace(source, dest, 1))
    return sorted(x for x in result if grammatical_screen(x))


def valid_rewrite(original, candidate):
    return candidate in variants(original)


def jaccard_similarity(a, b):
    x, y = set(WORD.findall(a.lower())), set(WORD.findall(b.lower()))
    return len(x & y) / len(x | y) if x | y else 0.0


def collision(a, b):
    return any(a[s].strip().casefold() == b[s].strip().casefold() or
               jaccard_similarity(a[s], b[s]) > .85 for s in STRATEGIES)


def measure(tokenizer, stem, options):
    actions = {s: len(tokenizer.encode(options[s].strip(), add_special_tokens=False)) for s in STRATEGIES}
    prompts = {s: len(tokenizer.encode(f'{stem.strip()}\n\nAction: {options[s].strip()}\nDecision:', add_special_tokens=False)) for s in STRATEGIES}
    return actions, prompts


def quartets(tokenizer, stem, options):
    pools = [variants(options[s]) for s in STRATEGIES]
    outcomes = []
    for texts in itertools.product(*pools):
        candidate = dict(zip(STRATEGIES, texts))
        if len(set(texts)) != 4:
            continue
        a, p = measure(tokenizer, stem, candidate)
        if max(a.values())-min(a.values()) <= 1 and max(p.values())-min(p.values()) <= 1:
            outcomes.append(candidate)
    return outcomes


def select_joint(fixed, choices, originals=None):
    """Exhaustively maximize completed banks, then minimize edits, deterministically."""
    originals = originals or {}
    banks = [b for b in BANKS if b not in fixed]
    best, best_score = {}, None
    def visit(i, selected):
        nonlocal best, best_score
        if i == len(banks):
            count = len(selected)
            edits = sum(sum(v[s] != originals.get(b, v)[s] for s in STRATEGIES) for b,v in selected.items())
            distance = sum(sum(1-SequenceMatcher(None, originals.get(b,v)[s], v[s]).ratio() for s in STRATEGIES) for b,v in selected.items())
            tie = tuple((b, tuple(selected[b][s] for s in STRATEGIES)) for b in sorted(selected))
            score = (-int(len(fixed)+count == 3), -count, edits, distance, tie)
            if best_score is None or score < best_score:
                best, best_score = dict(selected), score
            return
        b = banks[i]
        visit(i+1, selected)
        for q in choices.get(b, []):
            if any(collision(q, x) for x in itertools.chain(fixed.values(), selected.values())):
                continue
            selected[b] = q
            visit(i+1, selected)
            del selected[b]
    visit(0, {})
    return best
