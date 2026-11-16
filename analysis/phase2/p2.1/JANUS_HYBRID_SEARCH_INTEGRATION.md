# Janus Hybrid Search Integration & Evaluation Architecture (Phase 7)

**Milestone:** Phase 2, Milestone P2.1  
**Search Foundation:** Janus Classical R1.0 Modular Search Core  
**Neural Engine:** Janus NNUE Model H1 (Embedded Quantized INT16/INT8)  
**Date:** November 16, 2026  
**Auditor:** Principal Computer Chess Architect & Neural-Network Systems Engineer  

---

## 1. Tri-Mode Evaluation Integration

Janus R1 search integrates the original NNUE Model H1 directly into its C++17 alpha-beta search pipeline (`r1_quiescence.hpp` and `r1_search.hpp`).

The engine supports three fully verified evaluation configurations selectable via standard UCI options:

```
                  ┌──────────────────────────────────────────────┐
                  │           UCI Evaluation Selector            │
                  │ (UCI_Evaluation: Classical / NNUE / Hybrid)  │
                  └──────────────────────┬───────────────────────┘
                                         │
                 ┌───────────────────────┼───────────────────────┐
                 │                       │                       │
                 ▼                       ▼                       ▼
          [CLASSICAL (H0)]          [NNUE (H1)]            [HYBRID (H2)]
       Pure Handcrafted Eval    Quantized Neural Eval   Linear Blend of Both
       (Bitboards, PST, Pawn   (768->128x2->32->1 INT16) (W_nnue * NNUE + 
        Structure, Mobility)                             (100 - W) * Classical)
```

### Supported UCI Commands:
1. `setoption name UCI_Variant value R1` $\implies$ Evaluates with pure **Classical** evaluation.
2. `setoption name UCI_Variant value H1` $\implies$ Evaluates with pure **NNUE** evaluation.
3. `setoption name UCI_Variant value H2` $\implies$ Evaluates with **Hybrid** blended evaluation (50% NNUE, 50% Classical).
4. Direct override: `setoption name UCI_Evaluation value NNUE` and `setoption name NNUE_Weight value 75`.

---

## 2. Invariant Preservation & Search Contract Insulation

To prevent the search instability and pruning paradoxes uncovered in late Phase 1, the following formal contracts are strictly enforced across all evaluation modes:

1. **Score Perspective Uniformity:**
   All evaluators (`::native_evaluate`, `NNUEEvaluator::evaluate_full`, and Hybrid) return scores strictly from the perspective of the **side to move** ($+100\text{ cp}$ means side to move has an advantage equivalent to 1 pawn).
2. **Mate-Score Insulation:**
   Neural evaluations are strictly clamped to $[-27000, +27000]$. They never reach or exceed `MATE_THRESHOLD` ($28000$) or `MATE_SCORE` ($29000$). Forced checkmate distance vectors remain purely determined by alpha-beta tree search proofs.
3. **Preservation of Legal Rules:**
   - Legal move generation, check detection, check evasion, threefold repetition, and the 50-move rule remain 100% identical and independent of the evaluation mode.
   - Quiescence search stand-pat cutoffs remain strictly disabled when in check (`in_check == false` guard), guaranteeing check evasion completeness.
4. **Transposition Table Uniformity:**
   Transposition table entries (TT0, TT1, TT2) store unified centipawn values with ply-based mate normalization, fully compatible across all search depths.
