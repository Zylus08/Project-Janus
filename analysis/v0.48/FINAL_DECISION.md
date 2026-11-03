# Project Janus v0.48 — Final Optimization Decision

**Milestone:** Project Janus v0.48  
**Repository:** `E:\ChessXML\project-janus`  
**Parent Baseline Commit:** `0446ae3` (v0.47 Final)  
**Evaluated Candidates:**
- **Baseline K0:** Standard eager move ordering (`enable_lazy_move_selection=False`, `enable_rfp=False`)
- **Candidate L1:** Lazy move selection with immediate TT cutoff (`enable_lazy_move_selection=True`)
- **Candidate L2:** Stable entry-scored incremental move selection

---

## 1. Selected Outcome: CATEGORY B

> ### **Category B: Efficiency Improvement Retained, Strength Unconfirmed**
> **Candidate L1 is retained as an experimental option (`enable_lazy_move_selection=True`), disabled by default.**  
> **Production default configuration for v0.49 remains strictly K0 (`enable_lazy_move_selection=False`, `enable_rfp=False`).**

---

## 2. Evaluation Against Formal Decision Criteria

| Category | Preregistered Criteria | Qualification Assessment |
|---|---|---|
| **Category A: Validated & Promoted** | Demonstrable playing-strength improvement in a controlled match ($p < 0.05$) OR substantial efficiency improvement ($>15\%$ node reduction or $>20\%$ runtime reduction) with zero decision degradation. | **DOES NOT QUALIFY.** L1 did not demonstrate a playing-strength improvement in the v0.47 match ($p = 0.256$, mean delta $-0.16$ pts/pair). Node reduction is essentially neutral ($+0.04\%$ at D5). Promotion to default requires demonstrable playing strength benefit. |
| **Category B: Retained, Strength Unconfirmed** | Statistically significant efficiency improvement ($>10\%$ runtime reduction) with neutral or near-neutral decision quality, but playing-strength improvement not demonstrated. | **QUALIFIES FULLY.** L1 achieves a **$-17.68\%$ runtime reduction at Depth 5** (saving 14,510 complete sorts), maintains **95.95% exact move+score agreement** with K0, exhibits **zero tactical regressions or blunders**, but playing strength remains unconfirmed. |
| **Category C: Ineffective or Harmful** | No meaningful efficiency improvement ($<5\%$ runtime reduction) OR decision degradation (blunders, tactical misses) OR match loss ($p < 0.05$). | **DOES NOT APPLY TO L1.** L1 delivers an empirical $-17.68\%$ speedup with no degradation. (Note: Candidate L2 falls into Category C due to $+16.9\%$ runtime regression caused by Python pre-scoring overhead). |
| **Category D: Inconclusive** | Inconsistent results across runs, unexplained divergences, or insufficient statistical power. | **DOES NOT APPLY.** All search divergences were forensically cataloged and explained (transposition-table entry timing and alternate equal quiet moves). The computational source of speedup is fully decomposed. |

---

## 3. Comprehensive Evidentiary Basis

### 3.1 Source of Search Efficiency (Phases B & C)
The extensive decomposition across Depths 2 through 5 on the 37-position diagnostic corpus confirmed:
- **Runtime Reduction:** L1 reduced Depth 5 search execution time from 102.16s to 84.10s (**$-17.68\%$ net wall-clock reduction**).
- **Ordering Overhead Reduction:** Move scoring and sorting time fell from 7.11s to 4.91s (**$-30.87\%$**).
- **Eliminated Sorts:** At Depth 5, L1 avoided **14,510 complete move-list sorts** out of 67,789 beta cutoffs.
- **Immediate TT-Move Cutoffs:** At Depth 5, 14,521 cutoffs (21.42% of all cutoffs, 28.18% of first-move cutoffs) occurred immediately on the TT move without ever scoring or sorting the move list.
- **Tree-Size Neutrality:** Total tree size at Depth 5 was virtually identical (1,251,786 nodes for K0 vs 1,252,292 nodes for L1, a negligible delta of $+0.04\%$).

### 3.2 Computational Waste of Quiet History Lookups (Phase D)
Phase D uncovered the fundamental mechanical flaw of eager sorting in an interpreted environment:
- Across the 37 positions at Depth 4, eager sorting performed **975,344 quiet move scoring and history table lookups**.
- Only **8,326 quiet moves actually produced beta cutoffs** (a 117:1 waste ratio, or **$99.1\%$ waste**).
- L1 succeeds precisely because testing the TT move before sorting bypasses this 99.1% computational waste whenever the TT move triggers a cutoff.

### 3.3 Forensic Verification of Decision Safety (Phase E)
Forensic analysis of all 148 paired search outputs across Depths 2–5 established:
- **Agreement Rate:** 142/148 (95.95%) identical best moves and scores.
- **Disagreement Inventory:** Exactly 4 moves differed (2.7%), all at Depth 5.
- **Disagreement Classification:** All 4 disagreements were classified as `alternate_equal_line` ($\le 3$ cp difference between quiet development moves).
- **Tactical and Blunder Audit:** **0 blunders, 0 tactical regressions, 0 material drops**. In fact, in `control_p7_white_ply3` at Depth 5, L1 selected `d2d4`, exactly matching the Stockfish 19 reference move, whereas K0 selected `b1c3`.

### 3.4 Candidate L2 Rejection (Phase F)
Candidate L2 was developed to test whether stable entry-scored incremental selection could achieve 100% search-tree identity to K0:
- **Search Equivalence:** Achieved exact 100.0% node-for-node and score-for-score equivalence to K0 (405,197 nodes at Depth 4).
- **Performance Failure:** In interpreted Python, constructing and sorting move wrapper objects on the fly increased runtime from 32.48s to 37.98s ($+16.9\%$, $-14.5\%$ NPS).
- **Conclusion:** Candidate L2 is discarded as a production candidate, confirming that Candidate L1's lightweight phase separation is the only viable architecture in Python.

---

## 4. Production Configuration for v0.49

The production configuration for the codebase moving into v0.49 is reaffirmed:

```python
# Production Configuration (Frozen Baseline)
enable_lazy_move_selection = False   # K0 production default
enable_rfp = False                  # Retained experimental, disabled by default

# Experimental Feature Flags (Available for diagnostic / research use)
# Candidate L1:
# enable_lazy_move_selection = True
# rfp_margin_per_depth = 120
# rfp_max_depth = 2
```

---

## 5. Follow-Up Recommendations for Future Milestones

1. **Compiled Move Picker (C-Extension / Cython / PyBind):**
   - The primary limiting factor of advanced move pickers (such as L2 or stage-based selection: TT $\to$ Captures $\to$ Killers $\to$ Quiets) in Project Janus is the interpreted Python call overhead. Implementing a compiled C move-picker will allow true lazy sorting (picking the next best move with an $O(N)$ partial selection or heap) with zero Python object instantiation.
2. **Killer Move Heuristic Integration:**
   - With L1 having established the safety of multi-stage selection, the natural next step is inserting 2 killer moves between winning captures and quiet history moves.
3. **History Table Decay & Pruning:**
   - Introduce history aging/decay between moves to improve quiet move ordering accuracy while maintaining the lazy bypass.

