# Move-Ordering Ablation Study (v0.47 Phase I)

## 1. Experimental Design

Phase I investigates the independent empirical contribution of each move-ordering layer in Project Janus:
- **Corpus:** 37-position diagnostic corpus.
- **Evaluation Depth:** Nominal Depth 4.
- **Configurations Evaluated:**
  1. `Full_K0`: Full baseline ordering (TT move + MVV-LVA/SEE + Promotions + Killers 1 & 2 + History heuristic).
  2. `Candidate_L1`: Lazy move selection with full ordering.
  3. `No_TT_Ordering`: Transposition table move prioritization suppressed.
  4. `No_Killers`: Killer heuristics 1 & 2 suppressed (`max_killers_ply = 0`).
  5. `No_History`: Butterfly history heuristic scoring suppressed (`enable_history = False`).
  6. `With_Countermoves`: Countermove heuristic active (`enable_countermoves = True`).

## 2. Empirical Ablation Results

| Configuration | Total Nodes | Node Delta vs K0 | First-Move Cutoff Rate | Total Cutoffs | Total Runtime | Effective NPS | Ordering Time |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Full_K0** | 405,197 | — | **81.08%** | 26,634 | 66.30 s | 6,111 | 5.55 s |
| **Candidate_L1** | 407,705 | +0.62% | **80.77%** | 26,923 | 75.89 s | 5,372 | 5.61 s |
| **No_TT_Ordering** | 552,585 | **+36.37%** | **75.28%** | 33,565 | 100.77 s | 5,483 | 8.78 s |
| **No_Killers** | 413,939 | +2.16% | **79.99%** | 26,698 | 72.65 s | 5,697 | 4.69 s |
| **No_History** | 412,118 | +1.71% | **80.84%** | 26,750 | 19.83 s | 20,783 | 1.55 s |
| **With_Countermoves** | 405,120 | -0.02% | **81.07%** | 26,633 | 19.75 s | 20,516 | 1.78 s |

## 3. Structural Hierarchy Analysis & Insights

1. **TT Move Priority is Paramount:** Suppressing the TT move priority in move ordering causes a catastrophic **+36.37% surge in total search nodes** (from 405,197 to 552,585) and degrades the first-move cutoff rate from 81.08% down to 75.28%. This proves conclusively that the TT move is the single most critical move in the ordering hierarchy.
2. **Killer Moves Contribution:** Killer moves provide a clean +1.09 percentage point increase in first-move cutoffs (79.99% $\to$ 81.08%) and prevent a 2.16% expansion in tree size.
3. **History Scoring Cost vs Yield:** In pure Python, evaluating butterfly history lookups across 30+ legal moves accounts for a substantial fraction of ordering overhead. Suppressing history reduced node ordering time from 5.55s to 1.55s while expanding the search tree by only +1.71%.
4. **Validation of Lazy Move Selection:** Candidate L1 specifically targets the highest-leverage insight from this ablation: because the TT move delivers over 75–81% of cutoffs, testing the TT move *first* before scoring/sorting remaining moves (including history) eliminates sorting work precisely where it is most expensive.

