# PROJECT JANUS — PHASE 1, MILESTONE P1.9
## Phase 1: 240-Position Generalized Chess Failure Atlas

### 1. Executive Summary & Methodology

Milestone P1.8's preliminary 24-position failure analysis forced complex chess decisions into single-cause categories and asserted that static evaluation (F1: 58.3%) and endgame horizon (F6: 25.0%) accounted for 83.3% of all engine losses. Phase 1 of Milestone P1.9 constructs a comprehensive, provenance-tracked **240-position Generalized Failure Atlas** to rigorously test whether these conclusions hold across a realistic, diverse chess landscape.

#### Experimental Design
- **Total Corpus Size**: Exactly 240 independent, deduplicated positions drawn from historical match turning points, standard test suites, tactical regressions, and canonical endgame databases.
- **16 Core Strategic Categories**: Open middlegames, closed pawn chains, strategic pawn breaks, opposite-side castling, exposed kings, quiet defenses, isolated queen's pawns (IQP), backward pawns, connected passers, rook endgames, minor-piece endgames, pure pawn endgames, queenless middlegames, zugzwang & fortresses, promotion races, and tactically forced sequences.
- **Partitioning & Clustering**: Clustered by source game/event into **120 Development (DEV)** and **120 Held-Out (HELD_OUT)** positions to prevent evaluation leakage.
- **Multi-Engine Evaluation**: Every position was evaluated under matched 350 ms conditions across **Janus Classical X7 (1T)**, **Janus Classical X10 (1T)**, **Janus Classical X12 (4T)**, **Janus Classical X13 (4T)**, and **Stockfish 19 (4T)**.

---

### 2. Empirical Failure Distribution Across 240 Positions

| Category ID | Description | Total Count | % of All Failures | DEV Set (120) | Held-Out Set (120) | Key Attribution Mechanism |
| :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| **SOLVED** | Correct move matches solution or Stockfish 19 best move | **24** | *10.0% of total* | 14 | 10 | Tactical accuracy & clear positional moves |
| **F7** | **Interacting / Multi-Cause** | **137** | **63.4%** | **69** | **68** | Complex interplay of positional evaluation and search dynamics |
| **F1** | **Static Evaluation Error / Positional Blindness** | **55** | **25.5%** | **27** | **28** | Misjudged pawn structure, king shelter, or piece coordination |
| **F6** | **Endgame Knowledge / Horizon Error** | **21** | **9.7%** | **8** | **13** | Theoretical draw/win mishandled (Lucena, Philidor, key squares) |
| **F3** | **Selective Pruning Error** | **3** | **1.4%** | **2** | **1** | Excessive LMR/LMP pruning on non-obvious candidate defenses |
| **F2** | **Search Horizon / Tactical Miss** | **0** | **0.0%** | 0 | 0 | Tactical sequences at moderate depth adequately searched |
| **F4** | **Time Allocation Failure** | **0** | **0.0%** | 0 | 0 | Equalized under fixed per-move budget |
| **F5** | **Parallel Search Interference** | **0** | **0.0%** | 0 | 0 | 0 non-deterministic root regressions observed |
| **TOTAL** | **Atlas Totals** | **240** | **100.0%** | **120** | **120** | **Total Failures: 216 / 240 (90.0%)** |

---

### 3. Key Scientific & Architectural Takeaways

#### Finding 1: Dominance of Interacting Multi-Cause Failures (F7: 63.4%)
The primary empirical finding of the expanded atlas is that **forcing engine failures into mutually exclusive single-cause categories is methodologically flawed**:
- In 63.4% of positions (137 / 216 failures), the discrepancy between Janus Classical and Stockfish 19 cannot be attributed purely to static evaluation or purely to search horizon.
- Rather, a slightly biased evaluation score (e.g. overvaluing material over king pressure by 40 cp) distorts the search tree, causing aspiration windows to fail high/low on inferior branches, which in turn leads to late move reductions on the critical defensive moves.

#### Finding 2: Static Evaluation (F1: 25.5%) Remains the Leading Single Cause
Among identifiable single-cause failures, **Static Evaluation (F1)** is overwhelmingly the most prevalent (55 positions, 25.5% of failures):
- **Pawn Structure Vulnerabilities**: Candidate X13 frequently underestimates the weakness of backward pawns on open files (e.g., $d6$ in the Sicilian/King's Indian) and overestimates candidate passers that can be easily blockaded by minor pieces.
- **King Safety Imbalances**: While E10 introduced king attack units, it scales attacks symmetrically and lacks awareness of open diagonals toward an uncastled king or pawn storm momentum under opposite-side castling.

#### Finding 3: Endgame Knowledge Horizon (F6: 9.7%)
Endgame outcome errors account for 21 failures (9.7%):
- In pure pawn and rook endgames (Lucena, Philidor, key squares, distant opposition), classical alpha-beta search without tablebases cannot foresee outcomes 20–30 plies deep where material does not change.
- This directly confirms the necessity of Phase 3 (Deterministic Syzygy Tablebase Integration) to provide exact, zero-search endgame oracles.

#### Finding 4: Stability of Parallel Search (F5: 0.0%)
Consistent with P1.7 and P1.8, parallel search interference (F5) was 0.0%. The 64B cache-line packed transposition table and root arbitration architecture operate with zero thread-induced regressions.

---

### 4. Primary Deliverables & Raw Telemetry

- **Curated Atlas JSON**: [`analysis/phase1/p1.9/corpus/generalized_failure_atlas_240.json`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.9/corpus/generalized_failure_atlas_240.json) (240 positions, 120 DEV / 120 HELD-OUT).
- **Raw Evaluation Data**: [`analysis/phase1/p1.9/raw/generalized_failure_atlas_raw.json`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.9/raw/generalized_failure_atlas_raw.json) (Complete engine-by-engine metrics).

