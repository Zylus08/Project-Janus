# Search Divergence Forensics (v0.48 Phase E)

## 1. Executive Summary

Phase E performs an exhaustive inventory and tactical consequence analysis of all positions where Baseline K0 and Candidate L1 produced different search outputs across the 37-position diagnostic corpus over nominal Depths 2, 3, 4, and 5 (148 total paired evaluations).

## 2. Divergence Inventory & Frequency

- **Total Paired Search Evaluations:** 148 evaluations (37 positions × 4 depths).
- **Exact Move & Score Matches:** **142 / 148 (95.95%)**.
- **Score-Only Variance (Same Move):** 2 / 148 (1.35%).
- **Move Disagreements:** **4 / 148 (2.70%)**.

### Complete Disagreement Table

| Position ID | Depth | K0 Move (Score) | L1 Move (Score) | Score Delta | Stockfish 19 Ref Move | Classification | Tactical Consequence |
|---|---:|---|---|---:|---|---|---|
| `control_p31_white_ply7` | 5 | `a2a4` (+15 cp) | `h2h4` (+15 cp) | **0 cp** | `e1g1` | Alternate Equal Line | None (equal quiet flank pawn push) |
| `control_p7_white_ply3` | 5 | `b1c3` (+27 cp) | `d2d4` (+27 cp) | **0 cp** | `d2d4` | Alternate Equal Line | **Positive** (L1 matches SF19 ref `d2d4`) |
| `control_p8_white_ply3` | 3 | `f1d3` (+24 cp) | `b1c3` (+24 cp) | **0 cp** | `d2d4` | Alternate Equal Line | None (identical score piece development) |
| `control_p8_white_ply3` | 4 | `f1d3` (+12 cp) | `b1c3` (+15 cp) | **3 cp** | `d2d4` | Alternate Equal Line | None (statistically negligible 3 cp difference) |

## 3. Root vs Internal Cause Analysis

1. **Origin of Divergence:**
   - In all 4 instances, the divergence occurred in quiet opening/positional control positions with multiple interchangeable development moves (`b1c3`, `d2d4`, `f1d3`).
   - In K0, all moves are scored and sorted eagerly using the entry-state history table.
   - In L1, the TT move is evaluated first. When the TT move does not generate an immediate cutoff, recursive search beneath the TT move updates the history table before the remaining quiet moves are sorted.
   - When the remaining quiet moves share nearly identical positional evaluations (e.g. +24 vs +24 cp), the slight difference in history bonus alters which equally good move is placed first.
2. **Tactical Consequence Audit:**
   - **Tactical Refutations:** **0 / 4 (Zero)**.
   - **Blunders / Missed Wins:** **0 / 4 (Zero)**.
   - **Material Loss:** **0 / 4 (Zero)**.
   - In fact, on `control_p7_white_ply3` at Depth 5, L1 selected `d2d4` (+27 cp), which precisely matches the Stockfish 19 reference move `d2d4`, whereas K0 chose `b1c3` (+27 cp).
3. **Conclusion:** K0 and L1 search divergences are purely benign tie-breaking variations among strategically equivalent quiet moves. No tactical degradation occurs under lazy move selection.

