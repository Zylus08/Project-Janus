# Project Janus — Phase 1 Milestone P1.1
## Phase 1.2 Classical Engineering Prioritization & Algorithmic Roadmap

**Milestone:** P1.1 $\to$ P1.2 Transition  
**Engine Lineage:** Janus Classical X  
**Governing Paradigm:** Strictly Non-ML (Zero NN, Zero NNUE, Zero Learned Weights)  
**Parent Anchor:** `bbadf8f` / `7b526a0`  
**Date:** November 2026  
**Auditor:** Principal Computer Chess Engineer & Systems Architect  

---

## 1. Executive Summary

Milestone P1.1 successfully modernized Janus Classical X's core search infrastructure:
- Staged Move Generation (`MovePicker`) delivered a **3.18x wall-clock speedup** and boosted NPS from 1.28M to 4.27M.
- Quiescence SEE filtering pruned **34.3% of search nodes** with 0 tactical blunders.
- Conservative Null-Move Pruning ($R=3$) slashed **61.6% of search nodes** with verified zugzwang safety.
- Reverse Futility Pruning reduced nodes by **38.8%** at depths 1–3 with 96% move agreement.
- Aspiration Windows ($\delta = 25\text{ cp}$) provided a clean **13.3% node reduction** with 100% move fidelity.
- Together, Variant `X6` achieved an **84.36% node reduction, a 10.52x speedup**, and expanded fixed-time search horizons by **+3.36 plies**.

Building upon these verified search foundations, Milestone P1.2 will focus on:
1. **Advanced Pruning & Reductions (Search Tier 2)**
2. **Move Ordering Architecture (Heuristic Tier 2)**
3. **Classical Handcrafted Evaluation Modernization (Evaluation Tier 1)**

---

## 2. High-Impact Candidates for P1.2 Prioritization

### Priority 1: Continuation History & Butterfly History Ordering
- **Rationale:** P1.0 audit revealed that move ordering quality directly governs alpha-beta efficiency. Currently, Janus Classical X uses a single 2D history table `g_history_table[2][64][64]`.
- **Proposed Architecture:**
  - Introduce **Continuation History** (`1-ply` and `2-ply` previous move indexing).
  - Add **Capture History** separate from quiet history.
  - Implement aging decay or bonus/penalty scaling based on search depth ($b(d) = d^2$).
- **Expected Impact:** Improves move ordering accuracy, increasing first-move cutoff rate from 80.4% to >88%, saving 20–30% additional nodes.

### Priority 2: History-Dependent Late Move Reductions (LMR) Modernization
- **Rationale:** Janus currently implements static logarithmic LMR ($R = 1 + \dots$) for moves after index 4.
- **Proposed Architecture:**
  - Condition reduction depth on history score: reduce poor quiet moves by $R + 1$, and reduce good quiet moves by $R - 1$ or $R = 0$.
  - Protect tactical moves (checks, tactical threats) from reduction.
- **Expected Impact:** Deeper search horizons (+0.8 to +1.2 plies) without increasing tactical blunder risk.

### Priority 3: Classical Evaluation Modernization (King Safety & Mobility)
- **Rationale:** Under Governing Rule 1 (Strictly Non-ML), playing strength against modern engines requires high-fidelity positional guidance. Janus's classical evaluation is currently simple Piece-Square Tables (PST) + material.
- **Proposed Architecture:**
  - **King Safety:** Attack unit counting based on attacking pieces around the king ring (3x3 zone), pawn shield integrity, and open king files.
  - **Piece Mobility:** Fast bitboard population count for pseudo-legal squares accessible to knights, bishops, and rooks, with precomputed mobility bonus curves.
  - **Pawn Structure:** Isolated pawns, doubled pawns, backward pawns, and passed pawn rank advancement bonuses with king proximity.
- **Expected Impact:** Direct positional judgment enhancement against intermediate and grandmaster-level positions.

### Priority 4: Principal Variation Search (PVS) & Singular Extensions
- **Rationale:** Once aspiration windows and staged movegen are active, PVS with null-window scout searches ($[\alpha, \alpha+1]$) on all moves after the first can be safely integrated.
- **Proposed Architecture:**
  - Full PVS with TT best-move first.
  - Singular Extensions: extend singular moves by 1 ply when TT move dominates all alternatives by a wide margin ($> 30\text{ cp}$).
- **Expected Impact:** Sharp tactical resilience in complex middlegame complications.

---

## 3. P1.2 Research & Engineering Roadmap

| Phase | Milestone Objective | Target Deliverable | Risk Assessment |
| :---: | :--- | :--- | :--- |
| **P1.2.1** | Continuation History & Advanced Move Ordering | `analysis/phase1/p1.2/MOVE_ORDERING_REPORT.md` | Low — pure selectivity, 0 rule risks |
| **P1.2.2** | History-Aware LMR & Tactical Extensions | `analysis/phase1/p1.2/DYNAMIC_LMR_REPORT.md` | Medium — requires tactical regression suite |
| **P1.2.3** | Handcrafted Evaluation Modernization (King Safety, Mobility) | `analysis/phase1/p1.2/HANDCRAFTED_EVAL_REPORT.md` | Medium — must preserve 20M+ NPS movegen speed |
| **P1.2.4** | Parameter Optimization (Texel Tuning / SPSA on classical weights) | `analysis/phase1/p1.2/EVAL_PARAMETER_TUNING.md` | Low — deterministic gradient/SPSA tuning |
| **P1.2.5** | Strength Qualification Tournament vs C1 & SF19 Progress | `analysis/phase1/p1.2/P1_2_STRENGTH_QUALIFICATION.md` | Low — preregistered automated harness |

---

## 4. Phase 1 Acceptance Criteria for Production Default Promotion

To supersede Classical C1 as the frozen default engine:
1. **Strength Margin:** $\ge +250\text{ Elo}$ over Classical C1 in paired tournament matches (95% CI lower bound $> +200\text{ Elo}$).
2. **Perft & Correctness:** 100% ground-truth agreement across standard perft suites.
3. **Statistical Soundness:** Minimum 200 paired tournament games across stratified openings.
4. **Zero ML Dependencies:** Source and binaries strictly free of neural networks or learned models.

