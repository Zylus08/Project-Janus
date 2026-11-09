# Project Janus Phase 1 — Milestone P1.0
## Reproducible Engine Benchmark Protocol Specification

**Milestone:** P1.0  
**Program:** Classical Engine Supremacy Program (Phase 1)  
**Role:** Independent Engine Testing Auditor & Systems Architect  
**Subject Opponents:** Janus Classical Baseline C1 vs Official Stockfish 19 (Unrestricted)  
**Date:** 2026-11-09  
**Deliverable:** `analysis/phase1/p1.0/BENCHMARK_PROTOCOL.md`  

---

## 1. Executive Protocol Objectives

This document establishes the permanent, preregistered testing protocol for evaluating **Project Janus Classical engines** against **unrestricted Stockfish 19**.

To prevent artificial victories and ensure scientific validity, all benchmarks must adhere to the following principles:
1. **Zero Handicapping of Stockfish:** Stockfish 19 must execute with `UCI_LimitStrength=false`, maximum normal skill (`Skill Level=20`), and its default embedded NNUE network active.
2. **Symmetric Resource Allocation:** Both engines are allocated identical single-thread CPU execution (`Threads=1`) and identical transposition table memory (`Hash=64` MB).
3. **Balanced Opening Pairs:** Every opening from the independent master corpus is contested twice, with engines alternating White and Black pieces from the exact same starting FEN.
4. **Standard FIDE Adjudication:** Game termination is arbitrated externally via python-chess (Checkmate, Stalemate, Threefold Repetition, 50-move rule, Insufficient material, Time forfeit).

---

## 2. Standardized Opponent Engine Configurations

```text
+---------------------------------------------------------------------------------------------------+
| JANUS CLASSICAL C1 PRODUCTION SETTINGS                                                            |
+---------------------------------------------------------------------------------------------------+
Binary Path:         analysis/v0.56/native/janus_native_engine.exe
Hash:                a4f9d9d18b549d29b2e6740ac90d90d39167d92d3846b95fc0c4f5b966add83f
Threads:             1 (Single-threaded native loop)
Hash Size:           64 MB (1,048,576 entries)
UCI Options:
  UseKillerOrdering  = true
  UseHistoryOrdering = true
  UsePVS             = false
  UseLMR             = true (MinDepth=3, MoveThreshold=4, BaseReduction=1)
  UseSEEOrdering     = false
  UseSEEInQuiescence = false

+---------------------------------------------------------------------------------------------------+
| UNRESTRICTED STOCKFISH 19 REFERENCE SETTINGS                                                      |
+---------------------------------------------------------------------------------------------------+
Binary Path:         E:/ChessXML/tools/stockfish/stockfish.exe
Hash:                45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0
Threads:             1 (Single-threaded search)
Hash Size:           64 MB
Ponder:              false
MultiPV:             1
Skill Level:         20
UCI_LimitStrength:   false (Unrestricted)
UCI_Elo:             N/A (Disabled)
EvalFile:            nn-1a298aa575a0.nnue (Active default NNUE)
SyzygyPath:          <empty> (Tablebases disabled unless symmetrically provided)
```

---

## 3. Benchmark Tiers & Time Controls

```
+---------------------------------------------------------------------------------------------------+
| BENCHMARK TIERS AND TIME CONTROL SPECIFICATIONS                                                    |
+---------------------------------------------------------------------------------------------------+
| Tier Name                   | Time Control           | Opening Corpus             | Game Count     |
+---------------------------------------------------------------------------------------------------+
| Tier 1: Primary Blitz       | 3.0s base + 100ms inc  | independent_openings_v056  | 20-100 games   |
| Tier 2: Slower Diagnostic   | 15.0s base + 100ms inc | independent_openings_v056  | 10-40 games    |
| Tier 3: Fixed Depth Match   | Depth 6-8 per move     | Standard Suite (50 pos)    | 50-100 games   |
| Tier 4: Fixed Nodes Match   | 200,000 nodes per move | Standard Suite (50 pos)    | 50-100 games   |
+---------------------------------------------------------------------------------------------------+
```

### Time Allocation Rules:
- Under Fischer clocking ($T_{\text{base}} + T_{\text{inc}}$), engines receive their base clock at move 1 and gain the increment after each move.
- Timeouts: If an engine's clock reaches $\le 0\text{ ms}$ and elapsed move time exceeds available budget, the game is immediately adjudicated as a time forfeit loss.

---

## 4. Telemetry Schema & Archival Standards

### 4.1 PGN Tag Specifications
Every game played by the benchmark harness must record standard headers:
```pgn
[Event "Janus Phase 1 Benchmark (3.0s+0.1s)"]
[Site "Local Host"]
[Date "2026.11.09"]
[Round "1"]
[White "Janus Classical Baseline C1"]
[Black "Stockfish 19"]
[Result "0-1"]
[ECO "A10"]
[Opening "English Anglo-Scandinavian"]
[Termination "CHECKMATE"]
```
Moves in the PGN must include standard clock and evaluation comments:
`10. d4 [%eval +0.25] [%clk 0:00:02.850] 10... exd4 [%eval -0.30] [%clk 0:00:02.910]`

### 4.2 Raw JSON Schema
Each tournament outputs a structured JSON artifact containing:
- `summary`: total games, WDL counts, points scored, score percentage, Elo delta estimate, and PGN filepath.
- `games`: array of individual games with full move lists, ply-by-ply nodes, search depths, NPS, evaluation scores, and move latencies.

---

## 5. Statistical Rigor & Elo Estimations

- **Paired Scoring:** Games are analyzed as paired trials ($n$ opening pairs = $2n$ games). Score difference per pair $D_i = S_{A,\text{White}} + S_{A,\text{Black}} - 1.0 \in \{-1.0, -0.5, 0.0, +0.5, +1.0\}$.
- **Bootstrap Confidence Intervals:** 10,000 bootstrap resamples clustered at the opening-pair level.
- **Statistical Significance:** Paired two-tailed Student's t-test and Wilcoxon signed-rank test. A strength delta is declared statistically significant only if $p < 0.05$ and the 95% CI does not span zero.
- **Bounded Samples:** Small sample matches ($N \le 40$ games) are designated as **gap characterization diagnostics**, and must not be cited as certified ratings.
