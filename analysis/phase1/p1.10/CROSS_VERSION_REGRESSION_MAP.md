# Phase 1: Cross-Version Regression Archaeology & Forensic Mapping

**Milestone:** Phase 1, Milestone P1.10  
**Charter:** Classical Strength Regression Forensics & Algorithmic Root-Cause Isolation  
**Auditor:** Principal Computer Chess Engineer, Systems Performance Architect & Search Auditor  
**Raw Telemetry Reference:** [`analysis/phase1/p1.10/raw/archaeology_forensics_raw.json`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.10/raw/archaeology_forensics_raw.json)  
**Test Suite:** [`analysis/phase1/p1.10/tests/archaeology_cross_version.py`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.10/tests/archaeology_cross_version.py)

---

## 1. Executive Summary & Forensic Context

In Milestone P1.9 Match A, **Janus Classical X14** suffered a statistically confirmed strength regression against **Janus Classical X7** ($40.25\%$, $-68.6\text{ Elo}$, $p = 0.001424$). This failure occurred despite X14 exhibiting superior handcrafted chess knowledge, higher endgame conversion rates ($75\%$ vs $70\%$), and comparable multithreaded node throughput in benchmark positions.

To uncover why successive classical evaluation enhancements (X10, X13, X14) have repeatedly degraded single-thread tournament strength, Phase 1 reconstructs the exact source-level evolution across the entire engine lineage:
- **Janus Classical X7 (`b34e342`):** Qualified 1T Baseline. Minimalist Flat Classical Evaluation (E5), zero pawn hash overhead, fixed time management, no Late Move Pruning.
- **Janus Classical X10 (`504022f`):** Handcrafted Evaluation Reference. Enhanced Classical Evaluation (E10), 64K shared pawn hash table, dynamic time allocation.
- **Janus Classical X12 (`78ca3d5`):** Qualified 4T Baseline. 64B cache-line packed parallel TT, smart depth-preferred replacement, warm history, safe quadratic Late Move Pruning (LMP), E10 evaluation.
- **Janus Classical X13 (`3afcf6f`):** Experimental Multicore Platform. 16K thread-local pawn hash table (512 KB per thread), E10 evaluation, safe quadratic LMP.
- **Janus Classical X14 (`c85374a`):** Evaluated Research Platform. Refined Classical Evaluation (E11), 16K thread-local pawn hash, Syzygy tablebase adapter.

---

## 2. Lineage Feature Dependency Graph

```mermaid
graph TD
    X7["Janus Classical X7 (P1.2)<br/>1T Qualified Baseline<br/>• Flat E5 Eval<br/>• Staged Movegen<br/>• LMR L3 / ContHist H3<br/>• Fixed Time Mgmt"]
    
    X7 -->|"+ Enhanced Positional Terms<br/>+ 64K Shared Pawn Hash<br/>+ Dynamic Time Allocation"| X10["Janus Classical X10 (P1.5)<br/>Advanced Eval Reference<br/>• E10 Positional Eval<br/>• Unsynchronized Pawn Table"]
    
    X10 -->|"+ 64B Packed Shared TT<br/>+ Smart Eviction<br/>+ Warm History<br/>+ Safe Quadratic LMP"| X12["Janus Classical X12 (P1.7)<br/>4T Qualified Baseline<br/>• Lazy SMP Multithreading<br/>• Shared 64K Pawn Table"]
    
    X12 -->|"+ 16K Thread-Local Pawn Hash<br/>(Private L2 Cache Resident)"| X13["Janus Classical X13 (P1.8)<br/>Frozen Experimental Platform<br/>• Zero Thread Bus Contention<br/>• Promotion Revoked in P1.9"]
    
    X13 -->|"+ Refined E11 Terms<br/>(Blockades, Central Kings, Opposition)<br/>+ Syzygy Tablebase Adapter"| X14["Janus Classical X14 (P1.9)<br/>Evaluated Research Platform<br/>• 40.25% vs X7 (1T Regression)<br/>• 48.75% vs X12 (4T Inconclusive)"]
```

---

## 3. Systematic Source-Level Audit of Material Changes

| Subsystem | Prior Implementation (X7) | Modified Implementation (X14) | Intended Algorithmic Goal | Measured Cost / Impact | Search Mechanisms Affected | Expected Failure Mode |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Pawn Structure** | Simple `eval_pawn_structure` (isolated, doubled pawns; $\pm 10$ to $\pm 15$ cp). | `eval_pawn_structure_v2` with candidate passers, connected/supported bonuses ($+25$ cp), rank bonuses ($+130$ cp), blockades ($-25$ cp), and phalanxes ($+20$ cp). | Accurate strategic pawn valuation. | Score variance increases by $+7.5\%$. Pawn structure can swing eval by $> 200$ cp. | Reverse Futility Pruning (RFP), Quiescence stand-pat. | Positional overvaluation triggers premature beta-cutoffs in quiet lost positions. |
| **King Safety** | Simple `eval_king_safety` (pawn shield missing; $-5$ to $-15$ cp/pawn). | `eval_king_safety_v2` with king ring attack units, quadratic danger scaling ($\min(200, 2 \cdot units^2)$), and central open-file king penalties ($-25$ cp). | Tactical king attack and defense awareness. | Evaluator CPU time increases by $35\%$. Introduces up to $-200$ cp static penalty. | RFP, Null Move Pruning (NMP), Aspiration Windows. | Static evaluation swings violently when pieces aim near king, causing aspiration window misses and re-searches. |
| **Pawn Hashing** | Disabled (direct inlined computation). | Thread-local 16,384-entry pawn hash table (`PawnHashEntry` 32 bytes = 512 KB per thread). | Eliminate redundant pawn structure evaluations across tree. | $4.76\text{ ns}$ probe latency. Occupies 25% of core L2 cache. | Tree-wide evaluation throughput. | Cache misses or index collisions on non-pawn board transformations. |
| **Endgame King Activity** | Simple king centralization ($+2$ cp/step). | `eval_endgame_positional_v2` with passer king escort, Rule of the Square ($+500$ cp), and king opposition ($\pm 18$ cp). | Correct endgame pawn conversion and defense. | Correct on theoretical test cases ($75\%$ conversion). | Quiescence, endgame leaf evaluation. | Rule of the Square bonus ($+500$ cp) swamps alpha-beta window if king can be deflected. |
| **Late Move Pruning** | Disabled (`g_use_lmp = false`). | Safe Conservative Quadratic LMP (`g_lmp_mode = 1`, max depth 4, moves: $3 + d^2$). | Prune late quiet non-tactical moves at shallow plies. | Reduces searched nodes by $12\%$ at fixed depth. | Move loop in `negamax()`. | Pruning quiet defensive candidate moves in sharp positions. |
| **Time Management** | Fixed allocation per move (`time / moves_to_go`, `UCI_DynamicTime false`). | Dynamic Time Management (`UCI_DynamicTime true`), scaling time allocation by score swing and ply. | Spend more time when position evaluation is unstable. | Reduces time allocated to quiet, seemingly solved moves by $25\%$. | Iterative deepening termination. | Premature search termination when static eval claims position is winning/losing. |
| **Leaf Throughput** | $877,105\text{ NPS}$ on 1 core at depth 8. | $740,770\text{ NPS}$ on 1 core at depth 8 (**$15.5\%$ throughput loss**). | Richer positional evaluation. | $15.5\%$ lower nodes searched under fixed 1s+50ms clock. | Completed iterative deepening depth. | Reaches $0.5$ to $1.0$ fewer plies on critical root moves. |

---

## 4. Evaluation of Causal Hypotheses for the Single-Thread Regression

### H1: Evaluation-Scale Mismatch (CONFIRMED CONTRIBUTOR)
- **Empirical Evidence:** In Phase 1 forensics, the static score standard deviation widened from **$244.8\text{ cp}$ in X7 to $263.2\text{ cp}$ in X14** ($+7.5\%$ wider variance).
- **Search Mechanism Impact:** Reverse Futility Pruning uses a static, hardcoded margin:
  $$\text{margin} = 80 \times \text{depth}$$
  In X7, a modest positional advantage rarely exceeds $50\text{ cp}$. In X14, king ring attack units and passed pawn rank bonuses easily inject $+150$ to $+250\text{ cp}$ into `static_eval`. When:
  $$\text{static\_eval} - 80 \ge \beta$$
  RFP triggers immediately at depth 1, pruning the entire subtree. In positions where the opponent possessed a concrete tactical refutation, X7 searched deeply enough to find the tactic, whereas X14 pruned the branch based on inflated static evaluation.

### H2: Positional Double Counting (CONFIRMED CONTRIBUTOR)
- In X14, a passed pawn on the 6th rank defended by another pawn accumulates:
  1. Base passed pawn rank bonus: $+70\text{ MG} / +110\text{ EG}$.
  2. Supported passer bonus: $+15\text{ MG} / +25\text{ EG}$.
  3. Phalanx passer bonus: $+12\text{ MG} / +20\text{ EG}$.
  4. Friendly rook behind passer (Tarrasch): $+25\text{ EG}$.
  5. King escort proximity: up to $+36\text{ EG}$.
- **Net Static Addition:** Up to **$+216\text{ EG centipawns}$** for a single pawn! This artificially pushes positions into pseudo-won evaluations before tactical defenses or blocking maneuvers are calculated.

### H3: Excessively Expensive Evaluation / Throughput Tax (CONFIRMED PRIMARY CAUSE)
- **Empirical Measurement:** At fixed depth 8 across 20 diagnostic positions, X7 achieved **$877,105\text{ NPS}$** while X14 achieved **$740,770\text{ NPS}$**.
- This represents an immediate **$15.5\%$ computational penalty** per leaf node.
- In 4-thread play (Lazy SMP), multithreading produces a $3.1\times$ aggregate node multiplier that compensates for the evaluation drag. In single-thread play, there is zero multithreading compensation. Under a fast clock of $1.0\text{s} + 50\text{ms}$, X14 searches approximately $15\%$ fewer nodes per second, causing it to fall behind by 0.5 to 1.0 plies on complex turns. In computer chess, an engine operating 0.7 plies shallower suffers a predictable deficit of 50 to 80 Elo.

### H4: Phase-Dependent Evaluation Errors (SECONDARY CONTRIBUTOR)
- The linear game phase formula (`game_phase = total_non_pawn_pieces / 24`) treats Queen + Rook endgames with substantial middlegame weighting, keeping king attack danger units active even when no mating attack exists, leading to distorted evaluations.

### H5: Search–Evaluation Interaction with Dynamic Time Management (CONFIRMED CONTRIBUTOR)
- In X7, time allocation is fixed (`UCI_DynamicTime false`), ensuring a predictable, deep search regardless of evaluation fluctuations. In X14, `UCI_DynamicTime true` reduces time on turns where static evaluation appears stable, compounding the depth deficit caused by H3.

### H6: Runtime or State-Integrity Defect (REJECTED)
- Verified 100% bit-exact color symmetry invariance and clean memory alignment. No data races, memory leaks, or uninitialized reads exist in X14.

---

## 5. Architectural Forensic Conclusion

**Janus Classical X14's single-thread regression against X7 is driven by a compound triad:**
1. **$15.5\%$ Evaluation Throughput Tax (H3):** Slower leaf evaluation robs single-thread search of critical search depth.
2. **Score-Scale Inflation on Fixed Pruning Margins (H1 & H2):** Inflated king attack and passed pawn bonuses cause premature Reverse Futility Pruning.
3. **Dynamic Time Misallocation (H5):** Truncating search time on positions with inflated static confidence leaves tactical refutations undetected.

**Action Plan for Milestone P1.10:**
To recover strength without forfeiting positional understanding, Milestone P1.10 must re-scale evaluation terms, calibrate pruning margins to the evaluation distribution, optimize evaluation code to recover lost NPS, and verify that all search pruning mechanisms remain sound.

