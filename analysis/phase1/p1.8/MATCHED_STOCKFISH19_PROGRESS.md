# PROJECT JANUS — PHASE 1, MILESTONE P1.8
## Matched Stockfish 19 Benchmark & Progress Qualification Report

### 1. Executive Summary & Experimental Controls

In accordance with Milestone P1.8 specifications, an independent, matched-resource benchmark was executed between **Janus Classical X13** and official **Stockfish 19** (`sf_19`, source commit `edb0d9d`).

#### Experimental Controls
- **Resource Parity**: Exactly 4 search threads assigned to each engine (`Threads = 4`).
- **Transposition Table**: 32 MB hash allocated to each engine (`Hash = 32`).
- **Time Control**: 2.0 seconds base + 50 milliseconds increment per move.
- **Opening Corpus**: 20 independent openings (40 paired games with alternating colors) drawn from `independent_openings_v056.json`.
- **Syzygy Configuration**: Deterministic endgame tablebases were strictly disabled (`SyzygyPath <empty>`) for both engines to isolate pure search and evaluation capabilities.
- **Stockfish Configuration**: Unrestricted production build with default neural evaluation network (`nn-1a298aa575a0.nnue`) fully active.
- **Janus Configuration**: Strictly classical, non-ML handcrafted evaluation (E10) with thread-local L2 cache resident pawn hash and 64B packed transposition table.

---

### 2. Empirical Benchmark Results

| Metric | Janus Classical X13 (4T) | Stockfish 19 (4T, NNUE) |
| :--- | :---: | :---: |
| **Wins** | 0 | 38 |
| **Draws** | **2** | 2 |
| **Losses** | 38 | 0 |
| **Total Score** | **1.0 / 40 (2.50%)** | **39.0 / 40 (97.50%)** |
| **Elo Difference** | **-636.4 Elo** | **+636.4 Elo** |
| **95% Wilson Score Interval** | **[0.0044, 0.1288]** | [0.8712, 0.9956] |
| **95% Elo Confidence Interval** | **[-940.8, -332.1]** | [+332.1, +940.8] |
| **Paired Student's $t$-statistic** | **$t = -27.6064$ ($df = 19$)** | — |
| **$p$-value (Two-Tailed)** | **$p < 10^{-6}$** | — |
| **Total Match Elapsed Time** | 71.53 seconds | 71.53 seconds |

---

### 3. Historical Progression Against Unrestricted Stockfish 19

| Milestone | Candidate Engine | Eval Type | Threads | Score vs. SF19 | Win % | 95% Wilson Score Upper Bound | Performance Indication |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **P1.6** | Janus Classical X11 | Classical E10 | 4T | 0W – 0D – 40L | 0.00% | 0.0877 | Total tactical breakdown under lock contention |
| **P1.7** | Janus Classical X12 | Classical E5 | 4T | 0W – 0D – 40L | 0.00% | 0.0877 | Parallel search recovered, 0/40 due to evaluation deficit |
| **P1.8** | **Janus Classical X13** | **Classical E10** | **4T** | **0W – 2D – 38L** | **2.50%** | **0.1288** | **First scoring milestone (+1.0 pt, 2 draws as Black)** |

---

### 4. Qualitative Analysis of Drawn Games

Both draws occurred with **Janus Classical X13 playing as Black against Stockfish 19 as White**:

#### Game 1: Pair 1, Game 2 — English Anglo-Scandinavian (`1/2-1/2`)
- **Opening**: `1. c4 c6 2. Nf3 d5 3. e3 Nf6`
- **Dynamic**: Stockfish 19 pushed for space on the kingside and queenside. Candidate X13 accurately evaluated king shelter and maintained pawn island symmetry.
- **Endgame Transition**: X13 liquidated minor pieces into a symmetrical rook and pawn endgame, reaching a dead drawn position that satisfied the 50-move rule / threefold repetition condition.

#### Game 2: Pair 5, Game 2 — English Symmetrical 3.Nf3 (`1/2-1/2`)
- **Opening**: `1. c4 c5 2. Nc3 Nc6 3. Nf3 Nf6`
- **Dynamic**: Stockfish 19 attempted a central breakthrough with $d4$. X13 utilized safe mobility evaluation to trade knights on $d4$ and maintain control over the central $d$- and $e$-files.
- **Endgame Transition**: The position distilled into an opposite-colored bishop and rook endgame where Stockfish was unable to make progress.

---

### 5. Remaining Structural Deficit Breakdown

While securing 2 draws against unrestricted Stockfish 19 represents genuine classical progress, a 636-Elo gap remains. The primary technical contributors are:
1. **High-Order Positional Synergy**: Stockfish's NNUE network evaluates non-linear piece interactions (e.g., bishop pair harmonized with advanced rook outpost) with zero search overhead. In contrast, classical evaluation terms must approximate these with linear bitboard scans.
2. **Evaluation Weight Calibration**: X13's evaluation weights were handcrafted. Without automated numerical tuning (such as SPSA on grandmaster game corpora), hand-tuned parameters inevitably contain systematic valuation biases.
3. **Endgame Horizon Limitations**: Without endgame tablebases (Syzygy), X13 must compute complex 5- and 6-piece tablebase wins and draws from scratch, whereas Stockfish uses deep tactical pruning that indirectly relies on end-game clarity.

---

### 6. Primary Artifacts

- **Match SF PGN**: [`analysis/phase1/p1.8/pgn/x13_4t_vs_sf19_4t.pgn`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.8/pgn/x13_4t_vs_sf19_4t.pgn) (40 games).
- **Raw Evidence Data**: `analysis/phase1/p1.8/raw/x13_vs_sf19_raw.json`.
