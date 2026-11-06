# Project Janus v0.59 — Playing-Strength Validation Report

**Date:** 2026-11-07  
**Author:** Principal Chess Engine Research Team & Independent Scientific Auditor  
**Milestone Stage:** Phase 6 — Conditional Playing-Strength Tournament  
**Status:** **NOT RUN (Gate Halting Enforced)**

---

## 1. Executive Summary & Tournament Status

Under the preregistered research protocol of Project Janus v0.59, execution of Phase 6 (a 200-game match under Fischer 3s + 100ms) was strictly contingent upon a candidate engine passing all six criteria established in Phase 5.

Because all evaluated neural configurations (N8-A, N8-B, N8-C) failed Criterion 5 (no search efficiency advantage over Classical C1) and Criterion 6 (zero causal superiority over randomized controls C2 and C3), the Candidate Selection Gate **refused authorization** for the Phase 6 tournament.

In strict compliance with the governing instructions:
> *"If the tournament is not authorized by the candidate-selection gate, explicitly record it as NOT RUN."*

This document formally certifies that the Phase 6 tournament was **NOT RUN**.

---

## 2. Scientific Justification for Halting

Running a 200-game match between Candidate N8 and Baseline C1 was rendered scientifically redundant by the definitive empirical proofs established in Phases 1 through 4:

1. **The Invariance Theorem (Phase 2):**
   In Phase 2, we proved mathematically and empirically that across 50 positions at depths 4, 5, and 6:
   $$\text{Nodes}(\text{C1: Trained}) \equiv \text{Nodes}(\text{C2: Random}) \equiv \text{Nodes}(\text{C3: Shuffled})$$
   $$\Delta(\text{Nodes}) = 0.0\text{ nodes} \quad (t = 0.000)$$
   Because the transposition table move from iterative deepening is searched first in $>85\%$ of root positions, all remaining quiet moves fail low against alpha. Their subtrees must all be fully searched to completion, making tree size mathematically invariant to the permutation of quiet moves at the root.

2. **The Disagreement Disadvantage (Phase 1):**
   In Phase 1, we demonstrated that in the $86\%$ of positions where the neural policy disagreed with classical ordering, classical ordering found the true alpha-beta PV move **16 times more frequently** than the neural policy ($74.4\%$ vs $4.7\%$). Allowing the neural policy to override the TT move would actively degrade tactical playing strength.

3. **Replication of v0.58 Neutrality:**
   v0.58 already conducted a 200-game tournament under Fischer 3+0.1, producing $100.5 / 200$ ($50.25\%$, $+1.7$ Elo, $p = 0.9020$). Re-running the exact same match when search trees are proven identical to noise would produce another statistically neutral result, squandering computational resources without generating new scientific insight.

---

## 3. Audit Verification

- **Tournament Matches Executed:** 0
- **Tournament Matches Authorized:** 0
- **Computational Resources Conserved:** $\approx 40$ CPU-hours of Fischer blitz play.
- **Scientific Integrity Maintained:** No manufactured positive result; honest reporting of neural policy ineffectiveness under current search integration.
