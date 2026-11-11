"""Continuation-likelihood cooperation assay.

Scores the conditional log-probability of complete action descriptions
given scenario context, without requiring instruction-following or
forced-choice letter responses.

Primary measurement:
    log P(a | s) = sum_i log P(t_i | s, t_{<i})

This module is a complementary evaluation to the forced-choice harness.
It does NOT replace or modify the existing forced-choice runner.
"""
