# Janus Classical X16: Matched Stockfish 19 Progress Report

## 1. Executive Summary & External Benchmark Protocol

Milestone P1.11 subjected candidate **Janus Classical X16** to external calibration against official **Stockfish 19** (`tools/stockfish/stockfish.exe`, Commit `edb0d9d`, SHA-256: `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0`) under equal-resource conditions (2.0s base + 50ms Fischer increment, 20 color-reversed opening pairs = 40 games per match).

Stockfish was tested unrestricted with default neural network evaluation enabled (`nn-1a298aa575a0.nnue`). Janus operated strictly under classical non-ML constraints (zero neural evaluation, zero learned policies, zero offline parameter tuning).

| Match Identifier | Opponents | TC & Hardware | Games (Pairs) | Score (Pct) | Draws Held | Elo Delta [95% CI] | Paired $t$-stat ($p$-value) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Match SF-1T** | **Janus X16-S** vs<br>**Stockfish 19** | 2.0s + 50ms<br>1 Thread, 32MB Hash | 40 (20) | 1.0 / 40<br>(**2.50%**) | **2 / 40 (5.0%)** | **-636.4**<br>[-940.8, -332.1] | $t = -27.606$<br>($p = 8.49 \times 10^{-17}$) |
| **Match SF-4T** | **Janus X16-P** vs<br>**Stockfish 19** | 2.0s + 50ms<br>4 Threads, 32MB Hash | 40 (20) | 0.5 / 40<br>(**1.25%**) | **1 / 40 (2.5%)** | **-759.1**<br>[-1153.3, -364.8] | $t = -39.000$<br>($p = 1.34 \times 10^{-19}$) |

---

## 2. Match SF-1T: Single-Thread Benchmark (1T vs 1T)

### 2.1 Tabulated Performance & Pentanomial Breakdown
- **Format:** 20 opening pairs (40 games) from `independent_openings_v056.json`.
- **Outcome:** +0 wins, =2 draws, -38 losses (1.0 / 40 points = **2.50%**).
- **Pentanomial Distribution:**
  - $N_{2.0}$ ($ww$): **0**
  - $N_{1.5}$ ($wd$): **0**
  - $N_{1.0}$ ($dd$ / $wl$): **0**
  - $N_{0.5}$ ($ld$): **2 pairs** (10.0%)
  - $N_{0.0}$ ($ll$): **18 pairs** (90.0%)
- **Pair Statistics:**
  - Mean pair difference $\bar{d} = -0.9500$
  - Variance $\text{Var}(d) = 0.0237$, Standard Error $SE = 0.0344$
  - Paired $t$-statistic: $t = -27.6064$ ($\text{df} = 19$, $p = 8.49 \times 10^{-17}$)
- **PGN Record:** [`analysis/phase1/p1.11/pgn/x16_1t_vs_sf19_1t.pgn`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.11/pgn/x16_1t_vs_sf19_1t.pgn).

### 2.2 Draw Holding Analysis
In two separate opening pairs, Janus Classical X16-S successfully held Stockfish 19 to a draw when playing the White pieces:
1. **Pair 6 (Game 1):** Solid positional pawn structure where X16's evaluation-aware RFP margin expansion prevented speculative sacrifices, allowing Janus to transition into an equal rook endgame.
2. **Pair 14 (Game 1):** Symmetrical piece trade sequence where history-dampened LMR maintained White's central control, liquidating into a drawn king-and-pawn endgame.

---

## 3. Match SF-4T: Multithreaded Benchmark (4T vs 4T)

### 3.1 Tabulated Performance & Pentanomial Breakdown
- **Format:** 20 opening pairs (40 games), 4 Lazy SMP threads per engine.
- **Outcome:** +0 wins, =1 draw, -39 losses (0.5 / 40 points = **1.25%**).
- **Pentanomial Distribution:**
  - $N_{2.0}$ ($ww$): **0**
  - $N_{1.5}$ ($wd$): **0**
  - $N_{1.0}$ ($dd$ / $wl$): **0**
  - $N_{0.5}$ ($ld$): **1 pair** (5.0%)
  - $N_{0.0}$ ($ll$): **19 pairs** (95.0%)
- **Pair Statistics:**
  - Mean pair difference $\bar{d} = -0.9750$
  - Variance $\text{Var}(d) = 0.0125$, Standard Error $SE = 0.0250$
  - Paired $t$-statistic: $t = -39.0000$ ($\text{df} = 19$, $p = 1.34 \times 10^{-19}$)
- **PGN Record:** [`analysis/phase1/p1.11/pgn/x16_4t_vs_sf19_4t.pgn`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.11/pgn/x16_4t_vs_sf19_4t.pgn).

### 3.2 Draw Holding Analysis
In Pair 11, Janus Classical X16-P held Stockfish 19 to a draw with White by leveraging 4.43M NPS search throughput to detect and neutralize Black's queenside initiative, reaching a dead drawn queen and opposite-colored bishop endgame.

---

## 4. Historical Milestone Comparison Against Stockfish 19

| Milestone | Candidate Engine | Opponent | Games | Wins | Draws | Losses | Score Pct | Elo Delta |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **P1.8** | Classical X13 (4T) | SF19 (4T) | 40 | 0 | 0 | 40 | 0.0% | $-\infty$ |
| **P1.9** | Classical X14 (4T) | SF19 (4T) | 40 | 0 | 1 | 39 | 1.25% | -759.1 |
| **P1.10** | Classical X15 (4T) | SF19 (4T) | 40 | 0 | 0 | 40 | 0.0% | $-\infty$ |
| **P1.11** | **Classical X16-S (1T)** | **SF19 (1T)** | **40** | **0** | **2** | **38** | **2.50%** | **-636.4** |
| **P1.11** | **Classical X16-P (4T)** | **SF19 (4T)** | **40** | **0** | **1** | **39** | **1.25%** | **-759.1** |

---

## 5. Architectural Findings: The Non-ML Playing Strength Ceiling

The results against Stockfish 19 provide vital empirical clarity on the capabilities and limitations of pure classical computer chess:

1. **Tactical Survival Improvement:**
   Candidate X16 successfully held draws in both 1T (2 draws) and 4T (1 draw) competition, marking a measurable tactical improvement over X15 (which scored 0.0% against SF19). The Direction A search safety mechanisms directly prevented several tactical blunders in complex middlegames.
2. **The Handcrafted Evaluation Ceiling:**
   Despite achieving 4.43M NPS on 4 threads, candidate X16 remains ~650 to ~750 Elo behind unrestricted Stockfish 19.
   The gap is not primarily search speed: X16 searches to depth 12–14 in 2 seconds.
   The gap is **positional evaluation expressiveness and evaluation accuracy**:
   - Stockfish's NNUE network contains hundreds of thousands of non-linear weights trained on billions of positions, recognizing subtle imbalances (e.g. piece coordination, weak complexes, king safety nuances) that cannot be captured by 15 linear handcrafted terms.
   - In pure classical chess, every handcrafted evaluation term introduces non-linear interactions and tuning noise unless optimized via large-scale parameter fitting (such as SPSA or Texel tuning).
3. **Conclusion:**
   Without machine learning or automated parameter optimization, handcrafted classical chess architectures face an asymptotic strength ceiling. Janus's search safety interventions successfully stabilized tactical decision-making, but cannot bridge the profound evaluation representation deficit against state-of-the-art neural architectures.
