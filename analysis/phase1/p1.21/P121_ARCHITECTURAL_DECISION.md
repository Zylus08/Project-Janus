# Milestone P1.21: Architectural Decision Gate & Targeted Intervention Selection

**Milestone:** Phase 1, Milestone P1.21 (Search–Evaluation Decoupling, Pruning Reliability & Classical Architecture Decision Gate)  
**Deliverable:** `analysis/phase1/p1.21/P121_ARCHITECTURAL_DECISION.md`  
**Phase:** Phase 8 — Architectural Decision Gate  
**Repository:** `E:\ChessXML\project-janus-phase1`  
**Branch:** `phase1/classical-janus`  
**Decision Gate Status:** **OPTION A SELECTED (Verified RFP Correctness Repair)**  

---

## 1. Executive Summary & Decision

Across Phases 0 through 7 of Milestone P1.21, the Janus Classical architecture was subjected to forensic decompilation, counterfactual pruning audits, static evaluation perturbations, depth-dependent reliability profiling, shallow exact reference verification, and search-cost attribution.

### Core Empirical Discoveries Governing the Decision:
1. **Search-Code Identity:** The source diff between X22 (correctness reference), X24 (P1.19), and X25 (P1.20) proved that search algorithms, move ordering, pruning, and time management are **$100\%$ bitwise identical**. All behavioral divergence was caused strictly by static evaluation interaction with search pruning.
2. **Reverse Futility Pruning Contract Defects:** As established in Phase 2, Janus's current Reverse Futility Pruning (RFP) implementation suffers from four structural contract defects:
   - **Absence of Non-PV Guard:** RFP prunes unconditionally at PV nodes where $\beta - \alpha > 1$, prematurely truncating principal variation lines and corrupting root PV telemetry.
   - **Absence of TT Write:** When $\text{StaticEval} - \text{Margin} \ge \beta$, the function executes `return static_eval;` without writing a `TT_LOWER` bound to the Transposition Table. This deprives parent and sibling nodes of cutoff transposition bounds, triggering repeated subtree re-searches and TT thrashing.
   - **TT Upper-Bound Conflict:** RFP ignores existing TT entries where $\text{flag} == \text{TT\_UPPER}$ and $\text{score} < \beta$, overriding deep branch proof that the position fails low.
   - **Pure Pawn Endgame Zugzwang Vulnerability:** RFP lacks a non-pawn material guard, pruning in K+P endgames where quiet moves can be catastrophic zugzwangs.
3. **Massive Pruning Volume:** Phase 7 proved that RFP is responsible for **$41.6\%\text{–}73.2\%$ of all search cutoffs** in tactical and semi-open middlegame positions ($11,000\text{–}14,000$ cutoffs per depth 8 search). Consequently, defects in RFP compromise a massive fraction of Janus's game tree.
4. **Zero Minimax Flaws:** Phase 6 proved that Janus's underlying minimax recursion is $100\%$ sound, bug-free, and invariant.

### The Decision:
**Option A (Verified Reverse Futility Pruning Correctness Repair)** is formally selected as the single targeted architectural intervention for Candidate X26. Options B, C, D, and E are formally evaluated and dispositioned below.

---

## 2. Systematic Evaluation of Candidate Architectural Options

### Option A: Verified RFP Correctness Repair — **SELECTED**
- **Hypothesis:** Repairing the four structural defects in the RFP contract will eliminate tactical discovery latency, prevent TT bound thrashing, restore PV node integrity, and stabilize search tree volume across static evaluation variations without altering positional evaluation weights.
- **Evidence Base:**
  - Phase 2 proved the mathematical and programmatic contract defects.
  - Phase 3 showed that defective RFP delayed tactical discovery of winning piece sacrifices (`CF_T3`).
  - Phase 7 demonstrated that RFP handles up to $73.2\%$ of all cutoffs.
- **Scope of Change:** Targeted search modification within `negamax()` restricted solely to the RFP decision block; zero changes to evaluation terms.
- **Verdict:** **APPROVED FOR IMPLEMENTATION (Phase 9).**

---

### Option B: Evaluation-Aware Pruning Compatibility — **REJECTED AS REDUNDANT**
- **Hypothesis:** Dynamically scale pruning margins based on static evaluation confidence, piece activity, or pawn structure tension.
- **Evaluation:** Introducing dynamic, adaptive pruning margins based on complex positional factors increases heuristic coupling. Phase 4 and 5 proved that Janus already suffers from excessive search-evaluation coupling. Layering heuristic margin scaling on top of a structurally defective RFP contract would obscure root causes and violate the mandate for minimal, targeted interventions.
- **Verdict:** **REJECTED.**

---

### Option C: Selectivity Efficiency Correction (LMR / LMP Adjustments) — **REJECTED**
- **Hypothesis:** Adjust Late Move Reduction (LMR) tables or Late Move Pruning (LMP) cutoffs to curb search tree expansion.
- **Evaluation:** Phase 7 telemetry revealed that move ordering is exceptionally strong ($82.5\%\text{–}97.2\%$ first-move cutoffs) and LMR re-searches are within normal ranges ($< 15\%$). LMR and LMP are not the source of search volatility. Altering LMR tables would risk introducing tactical blunders without addressing the verified RFP defects.
- **Verdict:** **REJECTED.**

---

### Option D: Root Decision or Time-Management Repair — **REJECTED**
- **Hypothesis:** Modify root move stability thresholds or time-allocation curves to compensate for longer time-control score degradation.
- **Evaluation:** While X24 suffered from time-allocation inefficiencies due to eval-driven node inflation, Phase 1 confirmed that time management algorithms in X22, X24, and X25 are identical. Search-tree inflation at fixed depth is the root cause of time trouble, not the clock manager. Fixing root time allocation would merely treat the symptom while leaving search tree corruption intact.
- **Verdict:** **REJECTED.**

---

### Option E: No Incremental Change (Direct Architectural Redesign Proposal) — **DEFERRED TO PHASE 16**
- **Hypothesis:** Abandon all incremental search modifications and immediately declare Phase 1 classical development complete, pivoting directly to a clean-sheet search redesign.
- **Evaluation:** Prematurely pivoting without repairing known, verified implementation defects in the search contract would represent unscientific engineering. A rigorous research program must test whether fixing identified contract bugs restores strength to the classical engine before declaring the classical search paradigm exhausted. If Candidate X26 fails independent qualification despite the Option A repair, the empirical basis for the Phase 16 Architectural Pivot Decision will be irrefutable.
- **Verdict:** **DEFERRED TO PHASE 16 AS CONTINGENCY.**

---

## 3. Technical Specification of Option A (RFP Correctness Repair)

The intervention will be implemented in `engine/classical_x/janus_classical_x.cpp` under the search variant identifier `X26` (controlled via `UCI_SearchVariant = "X26"` and `UCI_RfpRepair = true`).

### 3.1 Mathematical & Algorithmic Contract Repairs

#### Defect 1: Non-PV Guard (PV Node Immunity)
- **Current Defective Code:**
  ```cpp
  if (!in_check && depth <= 3 && std::abs(beta) < MATE_BOUND) {
      int rfp_margin = g_rfp_margin_per_depth * depth;
      if (static_eval - rfp_margin >= beta) {
          g_telemetry_rfp_cutoffs++;
          return static_eval;
      }
  }
  ```
- **Option A Specification:**
  RFP must only execute at Cut/Null-Window nodes ($\beta - \alpha == 1$). Pruning at PV nodes ($\beta - \alpha > 1$) violates alpha-beta minimax invariants and causes PV truncation.
  ```cpp
  bool is_pv_node = (beta - alpha > 1);
  if (!is_pv_node && !in_check && depth <= 3 && std::abs(beta) < MATE_BOUND)
  ```

#### Defect 2: Transposition Table Bound Recording
- **Current Defective Code:**
  Function executes `return static_eval;` without updating the Transposition Table.
- **Option A Specification:**
  Before returning `static_eval`, record a `TT_LOWER` entry in the transposition table with the current `depth` and `static_eval` (clamped to prevent mate score corruption).
  ```cpp
  if (t_thread_id == 0) {
      TTEntry* tte = &g_tt[b->zobrist_key & (TT_SIZE - 1)];
      tte->key = b->zobrist_key;
      tte->score = static_eval;
      tte->depth = (uint8_t)depth;
      tte->flag = TT_LOWER;
      tte->best_move = 0;
  }
  return static_eval;
  ```

#### Defect 3: TT Upper-Bound Conflict Invalidation
- **Option A Specification:**
  If a valid transposition table entry for the current position already exists with `tte->depth >= depth`, `tte->flag == TT_UPPER`, and `tte->score < beta`, the subtree is already proven to fail low. In this circumstance, static evaluation over-optimism must not trigger an RFP cutoff.
  ```cpp
  if (tt_hit && (tt_entry.flag == TT_UPPER) && tt_entry.score < beta) {
      // Inhibit RFP: TT upper bound proves position fails low
  }
  ```

#### Defect 4: Zugzwang & Non-Pawn Material Guard
- **Option A Specification:**
  In pure king-and-pawn endgames, quiet positions frequently contain zugzwang where any move deteriorates the position. RFP must be inhibited when the moving side has no non-pawn material.
  ```cpp
  uint64_t my_non_pawns = b->pieces[us][KNIGHT] | b->pieces[us][BISHOP] | 
                          b->pieces[us][ROOK]   | b->pieces[us][QUEEN];
  if (my_non_pawns == 0) {
      // Inhibit RFP: Risk of zugzwang in pure pawn endgame
  }
  ```

---

## 4. Phase 9 & Phase 10 Execution Plan

1. **Phase 9: Implementation:**
   - Update `engine/classical_x/janus_classical_x.cpp` with the Option A RFP contract repair.
   - Add UCI options: `UCI_RfpRepair` (default true under Variant X26).
   - Recompile `janus_classical_x.exe` and `janus_classical_x.dll`.
2. **Phase 10: Controlled Ablations:**
   - Execute a 4-way factorial ablation matrix across diagnostic batteries:
     - **B0:** Legacy RFP (X22/X25 baseline).
     - **B1:** B0 + Non-PV Guard.
     - **B2:** B1 + TT Lower Bound Storage.
     - **B3 (Full X26):** B2 + TT Conflict Guard + Non-Pawn Material Guard.
3. **Phase 11: Correctness & Harness Verification:**
   - Run Perft 1–5, legal move checks, and 15-case referee integrity suite.
4. **Phase 12–14: Candidate Qualification:**
   - Freeze candidate `janus_classical_x26.exe`.
   - Run independent match qualification against X22, X7, and X12 at fast and slow time controls.
   - Run external calibration against Stockfish 4, Stockfish 11, and Stockfish 19 NNUE.

---

## 5. Formal Approval

The Principal Computer Chess Engine Architect, C++17 Search Engineer, and Statistical Experimentalist hereby ratify **Option A** as the governing technical path for Milestone P1.21.
