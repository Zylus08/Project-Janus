# Phase 4: Architecture Decision Record (Milestone P1.11)

**Milestone:** Phase 1, Milestone P1.11  
**Charter:** Classical Search Architecture Decision, Counterfactual Pruning Verification & Competitive Strength Recovery  
**Architect:** Principal Computer Chess Engineer & C++17 Search Architect  
**Status:** **APPROVED & RECORDED**  
**Selected Direction:** **DIRECTION A — Evaluation-Aware Pruning Safety & History-Dampened LMR**  
**Target Candidate Engine:** Janus Classical X16 (X16-S on 1T, X16-P on 4T)  

---

## 1. Problem Statement & Empirical Justification

Across Milestones P1.8, P1.9, and P1.10, adding handcrafted classical evaluation terms and parallel search throughput failed to produce statistically significant playing-strength gains against frozen baselines X7 and X12.

The forensic investigations of Phases 1, 2, and 3 revealed the exact mechanical cause:
1. **The LMR Over-Pruning Defect (Phase 2):**
   - The counterfactual pruning audit proved that Late Move Reductions (LMR) caused a staggering **$33.33\%$ move disagreement rate** (13 / 39 positions).
   - In quiet defensive and king-safety positions (`DEF_01`, `DEF_02`, `KNG_03`, `END_04`), standard LMR reduced critical defensive refutations (such as castling to safety `e1g1` or king-opposition pawn pushes `d4d5`) by $R \ge 2$, prematurely abandoning winning or saving branches in favor of speculative attacks.
2. **Evaluation–Pruning Disconnect (Phase 3):**
   - When evaluation terms E10/E11 are added, static score volatility expands by $\pm 48\text{ cp}$.
   - Existing alpha-beta pruning mechanisms (RFP and LMR) operate blindly on depth and move index, ignoring whether the position is improving or deteriorating relative to previous plies.

---

## 2. Direction Candidates Evaluated

| Direction Option | Architectural Mechanism | Empirical Support | Implementation Complexity | Correctness Risk | Selected? |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **A: Evaluation-Aware Pruning Safety** | History-dampened LMR + Improving-flag modulated RFP/LMR | **CRITICAL** (Phase 2 proved 33.3% LMR & 15.4% RFP errors) | Low (pure algorithmic) | Minimal | **SELECTED** |
| **B: Search-Bound Reliability** | Re-tune TT bound replace/aspiration windows | Low (TT collision rate $< 2.4\%$) | Moderate | Low | Not selected |
| **C: Lightweight Evaluation** | Strip terms back to Flat E5 | Contradicted by Phase 3 (E15 is stable & solved `DEV_12`) | Low | Low | Not selected |
| **D: Root Search Reliability** | Completed-iteration time extension | Moderate | Low | Low | Secondary |
| **E: Low-Level Optimization** | SIMD movegen / TT layout rewrite | Redundant (X15 already achieved 1.73M NPS, +17% over X12) | High | Moderate | Not selected |
| **F: No Justified Intervention** | Abort candidate development | Contradicted by clear Phase 2 evidence | None | None | Not selected |

---

## 3. The Selected Architecture: Direction A Specification

Direction A introduces **Evaluation-Aware Pruning Safety (EAPS)** into the search pipeline of Janus Classical X16 without introducing any neural or machine-learning dependencies:

### 3.1 The "Improving" Search Flag
- In `alpha_beta_search`, define:
  $$\text{improving} = (\text{ply} \ge 2) \land (\text{in\_check} == \text{false}) \land (\text{static\_eval} > \text{eval\_stack}[\text{ply} - 2])$$
- If the current position is **not improving**, the side to move is under pressure or in a deteriorating position. In this state:
  1. **RFP Safety:** Reverse Futility Pruning margin is expanded:
     $$\text{Margin}_{\text{effective}} = \text{Margin}_{\text{base}} + (\text{improving} ? 0 : 40 \times d)$$
     This prevents premature fail-high cutoffs when the position is slipping.
  2. **LMR Safety:** Quiet move reductions are dampened:
     $$R_{\text{effective}} = \max(0, R_{\text{base}} - (\text{improving} ? 0 : 1))$$
     This guarantees that defensive refutations are searched deeper when under threat.

### 3.2 Continuation-History Dampened LMR
- Quiet moves possessing strong positive continuation history from the previous 1-ply or 2-ply ancestor moves receive an additional $-1$ ply reduction dampening:
  $$\text{if } (\text{conthist\_score} > 1500) \implies R = \max(0, R - 1)$$
- Conversely, moves with negative continuation history and low butterfly history receive $+1$ ply reduction.

### 3.3 Strict Isolation & Testability
- The entire Direction A mechanism is controlled via the new UCI option:
  `option name UCI_PruningSafety type check default true`
- When set to `false`, the engine reproduces Candidate X15 bit-for-bit, providing an exact, zero-overhead baseline control for confirmatory ablations.

---

## 4. Preregistered Implementation Invariants

1. **Strictly Non-ML:** Zero learned weights, zero SPSA, zero neural evaluation. All dampening offsets are discrete integer ply adjustments ($\pm 1$ ply).
2. **Zero Memory Allocation:** Uses existing search stack entries `eval_stack[MAX_SEARCH_PLY]` with zero dynamic memory allocation.
3. **Thread Safety:** Uses thread-local history and evaluation stacks; zero cross-thread locking.
4. **Deterministic Reproducibility:** 100% deterministic at 1 thread.

