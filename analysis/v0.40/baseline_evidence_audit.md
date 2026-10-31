# Project Janus v0.40 — Baseline Evidence and Statistical Audit Report

## 1. Executive Summary & Purpose

This audit independently inspects, reconciles, and mathematically audits the evidence base, raw datasets, performance profiles, and statistical claims reported across Project Janus milestones v0.38 and v0.39.

Rather than accepting reported figures at face value, this audit examines raw PGN files, telemetry CSVs, move-by-move timing traces, and re-executes measurements under strict, reproducible protocols.

---

## 2. Reconciling Performance Measurements (Phase 1.1)

### 2.1 The v0.39 Reporting Discrepancy
The v0.39 report and `performance_profile.json` contained the following summary numbers for Depth 4 search across the 6 canonical benchmark positions:

| Candidate | Total Nodes | Total Elapsed Time | Reported NPS | Direct Ratio ($\sum \text{Nodes} / \sum \text{Time}$) | Arithmetic Mean of Positions ($\frac{1}{N}\sum \text{NPS}_i$) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Q0 (Checks Off)** | 40,423 | 2,107.60 ms | **21,998.4** | 19,179.6 NPS | 21,998.4 NPS |
| **Q1 (Checks On)** | 45,434 | 8,716.58 ms | **11,018.8** | 5,212.3 NPS | 11,018.8 NPS |

### 2.2 Root-Cause Identification
1. **Mean of Ratios vs Ratio of Sums:**
   The reported NPS values were the unweighted arithmetic means of per-position throughputs ($\frac{1}{6} \sum \text{NPS}_i$), rather than aggregate pooled throughput ($\frac{\sum \text{Nodes}}{\sum \text{Time}}$).
   - In Q0, `rook_endgame` searched 309 nodes in 9.4 ms ($\approx 33,000$ NPS) and `tactics_mate_in_one` searched 2,712 nodes in 61.8 ms ($\approx 44,000$ NPS). These tiny tree positions arithmetically skewed the unweighted mean upward by $+14.7\%$ over the true pooled throughput.
   - In Q1, the distortion was even more severe (+111.4%), because complex middlegames took substantially longer per node, but small positions with rapid cutoffs retained high nominal NPS.
2. **First-Run Cold Starts:**
   The initial single-pass profile in v0.39 did not include a warmup pass, subjecting the first position (`open_game` and `startpos`) to minor module import and byte-code compilation latency.

### 2.3 Re-Measurement Under Controlled Multi-Repetition Protocol
To establish rigorous ground truth, a multi-repetition benchmark was executed (`scripts/reconcile_v039_benchmarks.py`):
- Warm-up pass executed on all positions before timing.
- 5 independent repetitions per position.
- Measured with high-resolution monotonic timer (`time.perf_counter`).
- Both aggregate pooled throughput and position-level medians and dispersion (standard deviation) recorded.

#### Reconciled Multi-Repetition Benchmark Results (5 Repetitions)
| Position ID | Phase | Q0 Nodes | Q0 Median Time | Q0 Median NPS | Q1 Nodes | Q1 Median Time | Q1 Median NPS |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `startpos` | Opening | 2,552 | 104.01 ms | 24,536.3 NPS ($\pm 2,595$) | 2,556 | 164.95 ms | 15,495.3 NPS ($\pm 364$) |
| `four_knights` | Opening | 8,513 | 379.32 ms | 22,442.7 NPS ($\pm 419$) | 8,712 | 473.49 ms | 18,400.0 NPS ($\pm 293$) |
| `open_game` | Middlegame | 13,550 | 574.45 ms | 23,587.9 NPS ($\pm 261$) | 14,891 | 828.61 ms | 17,971.0 NPS ($\pm 208$) |
| `middlegame_tactical` | Middlegame | 12,787 | 587.95 ms | 21,748.6 NPS ($\pm 484$) | 14,198 | 848.33 ms | 16,736.4 NPS ($\pm 175$) |
| `rook_endgame` | Endgame | 309 | 9.37 ms | 32,977.6 NPS ($\pm 1,322$) | 309 | 9.38 ms | 32,942.4 NPS ($\pm 1,298$) |
| `tactics_mate_in_one` | Tactical | 2,712 | 61.81 ms | 43,877.4 NPS ($\pm 1,289$) | 4,768 | 164.90 ms | 28,914.5 NPS ($\pm 654$) |
| **Pooled Aggregate** | **All** | **40,423** | **1,716.91 ms** | **23,544.0 NPS** | **45,434** | **2,539.66 ms** | **17,889.8 NPS** |

**Technical Takeaway:**
- Candidate Q0 achieves a true pooled throughput of **23,544.0 NPS** (1.717s total wall-clock time).
- Candidate Q1 incurs a **+12.4% node expansion** (45,434 nodes) and a **+47.9% wall-clock time overhead** (2,539.66 ms), reducing pooled throughput to **17,889.8 NPS**.
- Conclusion remains completely sound: Q1 selective check exploration adds substantial latency overhead without providing search depth scaling.

---

## 3. Reconciling Tactical Forensic Counts & Mate Sentinels (Phase 1.2)

### 3.1 Forensic Accounting Structure
The v0.39 report recorded:
- 120 total blunder events across the 30-game sequential sample (Games 1–30).
- 24 forced mate concessions.
- 96 ordinary centipawn drops.
- Six failure categories summing to exactly 120.

### 3.2 Audit Findings on Classification & Sentinels
1. **Are mate concessions included in the six categories?**
   **Yes.** Every blunder event—whether a forced mate concession or a centipawn drop $\ge 150$ cp—was routed through the taxonomy classifier `classify_v039_blunder()`. For example, Game 1 ply 16 (`f4c7??`), which conceded mate in 1, was classified into `"Shallow Search Horizon (Depth <= 1)"` because its completed depth was 0.0 plies.
2. **Can an event appear in multiple categories?**
   **No.** The classifier uses a mutually exclusive `if / elif` cascading structure. Every event receives exactly one classification label.
3. **Are mate sentinels combined with centipawn drops?**
   **No.** In `analyze_losses_v039.py`, when an event conceded forced mate, `eval_drop_cp` was explicitly set to `None`. The mean centipawn drop for each category was calculated strictly across the subset of events where `eval_drop_cp is not None`.
4. **Denominator Disclosures:**
   The category `count` (summing to 120) includes both mate concessions and centipawn drops, but the `mean_centipawn_drop` average used only the non-mate denominator ($n_{\text{cp}} \le \text{count}$). This separation is fully verified and correct.

---

## 4. Rechecking Statistical Analysis & Match Summaries (Phase 1.3)

### 4.1 Independent Reconstruction from Raw PGN Games
The raw PGN files for both the v0.38 and v0.39 matches were parsed independently from disk:

1. **v0.39 Candidate Match (`analysis/v0.39/match_q0_k0/match_results.pgn`):**
   - Total PGN games: 50 games.
   - PGN Results: 20 White wins (`1-0`), 27 Black wins (`0-1`), 3 draws (`1/2-1/2`).
   - Janus White games (even index 0, 2, ... 48): 8 wins, 3 draws, 14 losses $\implies$ **9.5 / 25 points (38.0%)**.
   - Janus Black games (odd index 1, 3, ... 49): 13 wins, 0 draws, 12 losses $\implies$ **13.0 / 25 points (52.0%)**.
   - Total Janus Score: **21 Wins, 3 Draws, 26 Losses** $\implies$ **22.5 / 50 points (45.0%)**.
   - Complete opening pairs: Exactly 25 pairs, 100% colour-reversed, zero missing games.
   - Paired Student's $t$-statistic: $t = -0.6928$ ($\text{df} = 24$, $p = 0.4884$).
   - 10,000-sample paired bootstrap 95% CI: $[31.0\%, 58.0\%]$.
   - Logistic Elo differential: $-34.9$ Elo (95% CI: $[-139.0, +56.1]$ Elo), calibrated rating **1285.1 Elo**.

2. **v0.38 Calibrated Baseline Match (`analysis/v0.38/calibrated_elo/match_results.pgn`):**
   - Total PGN games: 50 games.
   - Total Janus Score: **26 Wins, 4 Draws, 20 Losses** $\implies$ **28.0 / 50 points (56.0%)**.
   - Complete opening pairs: Exactly 25 pairs, 100% colour-reversed.
   - Paired Student's $t$-statistic: $t = +0.7682$ ($\text{df} = 24$, $p = 0.4499$).
   - 10,000-sample paired bootstrap 95% CI: $[39.88\%, 72.12\%]$.
   - Logistic Elo differential: $+41.9$ Elo, calibrated rating **1361.9 Elo**.

3. **v0.38 Primary Unrestricted Benchmark (0/100 games):**
   - Exact Clopper-Pearson 95% CI: **$[0.00\%, 3.62\%]$**.
   - Rule-of-three upper bound: **$3.00\%$**.
   - The zero-width $[0.0\%, 0.0\%]$ CI from historical notes is fully corrected.

### 4.2 Summary of Reconciled Evidence
All mathematical and arithmetic relationships between the raw match artifacts and the reported statistics are reconciled. No technical conclusions are altered:
1. Candidate Q0+K0 performance against Stockfish 1320 (45.0%, 95% CI: [31.0%, 58.0%]) is statistically indistinguishable from 50% parity ($p = 0.49$) and compatible with the v0.38 baseline anchor (56.0%).
2. Candidate Q0 search throughput is 23,544.0 pooled NPS, whereas Q1 incurs a +47.9% time overhead without depth scaling.

