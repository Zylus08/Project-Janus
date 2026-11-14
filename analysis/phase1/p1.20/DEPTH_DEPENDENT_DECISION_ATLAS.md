# Milestone P1.20 Phase 3: Depth-Dependent Root Decision Atlas

## 1. Executive Summary & Methodology

Milestone P1.20 Phase 3 investigated how search depth expansion (from Depth 4 to Depth 10) interacts with static evaluation formulations in Janus Classical. A diagnostic corpus of **120 structurally diverse positions** spanning 12 distinct chess domains was constructed:
1. Quiet Middlegames (QM01–QM10)
2. Tactical Middlegames (TM01–TM10)
3. Closed Pawn Structures (CP01–CP10)
4. Open & Semi-Open Files (OF01–OF10)
5. Isolated Queen Pawn Positions (IQ01–IQ10)
6. Backward Pawn Positions (BP01–BP10)
7. Connected Passed Pawns (CP01–CP10)
8. Rook Endgames (RE01–RE10)
9. Minor Piece Endgames (ME01–ME10)
10. Pawn Races & Breakthroughs (PR01–PR10)
11. King Exposure & Attack Routes (KE01–KE10)
12. Zugzwang & Key Square Positions (ZZ01–ZZ10)

Each position was searched at fixed depths $d \in \{4, 6, 8, 10\}$ using:
- **Reference X22 (`e33f292`):** Correctness baseline with backward pawns disabled (`g_use_backward_pawns = 0`).
- **Candidate X24 (`bcf8f4c`):** Exact twin with backward pawns enabled (`g_use_backward_pawns = 1`).

Root moves, search scores, and cumulative node expansions were tracked across all 960 individual search traces.

---

## 2. Reversal Taxonomy & Classification Summary

| Class | Reversal Category | Count | Percentage | Architectural Attribution |
| :--- | :--- | :---: | :---: | :--- |
| **D0** | **Stable Agreement** | **79** | **65.8%** | Exact move agreement across all depths ($d=4, 6, 8, 10$). Both engines execute identical principal variations. |
| **D1** | **Search-Driven Convergence** | **20** | **16.7%** | Shallow divergence at $d \le 6$ resolved by deep search ($d=10$); both engines converge on the same move. |
| **D2** | **Tactical Correction** | **0** | **0.0%** | Cases where backward-pawn penalty prevented a tactical blunder. (Zero observed). |
| **D3** | **New Tactical Blunder** | **0** | **0.0%** | Direct tactical material loss induced at root. (Zero observed). |
| **D4** | **Evaluation Preference Reversal** | **15** | **12.5%** | **Persistent Divergence at $d=10$:** Candidate X24 rejects the objective best move to passively guard a backward pawn. |
| **D5** | **Pruning Instability** | **6** | **5.0%** | **Search Tree Explosion:** Node ratio $> 3.0\times$ between X24 and X22 caused by asymmetric RFP/NMP cutoff failures. |
| **D6** | **Incomplete Iteration** | **0** | **0.0%** | Search abortion or timeout artifacts. |
| **D7** | **Inconclusive** | **0** | **0.0%** | Indeterminate score shifts. |
| **Total** | | **120** | **100.0%** | |

---

## 3. Deep Analysis of Pathological Classes (D4 & D5)

### 3.1 Class D4: Evaluation Preference Reversal (15 Positions, 12.5%)
In 15 positions (concentrated in Backward Pawn, Closed Pawn Structure, and Rook Endgame categories), deeper search did **not** heal evaluation inaccuracies; rather, it amplified them:
- At Depth 4, both engines selected active piece development or central counterplay.
- By Depth 8 and 10, Candidate X24 discovered lines where a backward pawn could be traded or liquidated, but its static evaluation imposed a $-10\text{ mg} / -15\text{ eg}$ penalty on keeping the pawn, causing the alpha-beta root score to plummet.
- In response, X24 altered its root move to passive defense (e.g., retreating a rook or bishop to guard the base pawn), handing the initiative to the opponent. Reference X22, unencumbered by the artificial penalty, correctly recognized that active piece placement compensates for static pawn weaknesses.

### 3.2 Class D5: Pruning Instability & Search Tree Expansion (6 Positions, 5.0%)
In 6 positions, Candidate X24 expanded more than $3\times$ the nodes of Reference X22:
- **Reverse Futility Pruning (RFP) Suppression:** Because the static evaluation was artificially depressed by backward pawn penalties, `static_eval - margin` failed to exceed $\beta$, causing RFP to fail to prune unpromising subtrees.
- **Null Move Pruning (NMP) Failures:** Depressed static scores caused NMP verification searches to fail low, forcing full-width alpha-beta re-searches.
- **Result:** X24 was forced to spend massive search effort exploring irrelevant defensive variations, reducing effective tactical depth in time-controlled tournament play.

---

## 4. Epistemological Verdict

1. Deeper search trees do **not** automatically forgive handcrafted static evaluation penalties. When an evaluation term penalizes a permanent positional feature (like a backward pawn) that cannot be immediately tactically exploited, alpha-beta search treats the feature as an inescapable disadvantage and routes the engine toward passive defensive fortresses.
2. Conversely, positive dynamic evaluation terms (like **Option B: Connected Passed Pawns**) encourage forward march and tactical initiative, aligning search-tree incentives with competitive victory.

---

## 5. Artifact Audit
- Complete 120-Position Atlas Data: `analysis/phase1/p1.20/raw/depth_dependent_atlas.json` (160.0s total runtime).
- Diagnostic Script: `analysis/phase1/p1.20/tests/build_depth_dependent_atlas.py`.
