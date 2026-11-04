# Project Janus v0.51 — Preregistered Match Protocol: Native N2 vs Python K0

## 1. Preregistration Timestamp & Status
- **Milestone:** Project Janus v0.51
- **Status:** **FROZEN PRIOR TO MATCH LAUNCH**
- **Preregistration Date:** 2026-11-04
- **Repository:** `E:\ChessXML\project-janus`
- **Branch:** `v0.3-benchmark-harness`
- **Baseline Git Commit:** `238b85b`

---

## 2. Experimental Engine Configurations & Cryptographic Registry

### Candidate Engine: Native N2 Standalone UCI Engine
- **Binary Path:** `analysis/v0.51/native/janus_native_engine.exe`
- **Binary SHA-256:** `0611bc59e52073d07b0092b183e6a373783a9e4e6a679177b02ceb4a9900fb9b`
- **Source Path:** `analysis/v0.51/native/janus_native.cpp`
- **Source SHA-256:** `8e719e9b8613c71a96eb5cf2eff4643e1070d6fba6c02df3c2ae7ac5681d0d0e`
- **Configuration:** C++17 bitboard engine, 1M-entry TT, iterative deepening, quiescence search with delta pruning, in-tree repetition tracking, Fischer clock management.

### Reference Engine: Production Baseline Python K0
- **Implementation Path:** `src/janus/search.py`
- **Configuration:** `JanusSearch(enable_lazy_move_selection=False, enable_rfp=False)`
- **Orchestration Layer:** Python 3.13.2 64-bit with `python-chess` board state.

### Reference Engine (Diagnostic Verification): Stockfish 19
- **Binary Path:** `../tools/stockfish/stockfish.exe`
- **Binary SHA-256:** `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0`

---

## 3. Opening Suite & Match Architecture

- **Opening Suite File:** `analysis/v0.51/corpus/openings_v051_100.json`
- **Opening Suite SHA-256:** `2f929719ab8377e1682b3c37c6b93c762a8898bca9284aa3797db936391aca3b`
- **Total Openings:** 100 distinct ECO-balanced opening positions.
- **Match Design:**
  * Exactly 100 opening pairs = **200 games total**.
  * Pair symmetry: For each opening, Game A is played with N2 White vs K0 Black; Game B is played with K0 White vs N2 Black.
  * Engine process lifecycle: A fresh native process is spawned for each match session or paired match run.
- **Time Control:** Fixed Fischer time control: **3.0 seconds initial time + 0.10 seconds (100 ms) increment per move** ($3\text{s} + 100\text{ms}$).
  Matches the historical SF1320 benchmark conditions established in v0.43.

---

## 4. Game Adjudication Policy

1. **Checkmate & Stalemate:** Standard FIDE rules.
2. **Threefold Repetition:** Adjudicated as a draw immediately upon occurrence or claim.
3. **Fifty-Move Rule:** Adjudicated as a draw when `halfmove_clock >= 100`.
4. **Seventy-Five-Move Rule:** Automatic immediate draw.
5. **Insufficient Material:** Bare kings (K vs K), K+N vs K, K+B vs K, and K+B vs K+B on same-color squares adjudicated as draw immediately.
6. **Move Horizon Adjudication:** If a game reaches 200 plies (100 moves) without checkmate or material advantage $> 500$ cp, adjudicated as draw.
7. **Timeout / Illegal Move Policy:**
   * Any engine exceeding its clock time forfeits the game.
   * Any engine emitting an illegal move forfeits the game.

---

## 5. Statistical Methodology

All match statistics will be computed using paired analysis:
1. **Score Metrics:**
   $$\text{Score \%} = \frac{W + 0.5 \times D}{N} \times 100\%$$
2. **Paired Opening Deltas:**
   $$\Delta_i = S_{N2, i} - S_{K0, i} \quad \text{for pair } i \in \{1, \dots, 100\}$$
   where $S_{N2, i}$ is N2's score in pair $i$ (out of 2.0 points).
3. **Hypothesis Testing:**
   - Null Hypothesis $H_0$: $\mu_\Delta = 0$ (N2 and K0 have identical playing strength).
   - Alternative Hypothesis $H_1$: $\mu_\Delta \ne 0$.
   - Two-tailed paired Student's t-test and 95% Pair-Bootstrap Confidence Interval (10,000 resamples).
4. **Elo Difference:**
   $$\Delta \text{Elo} = -400 \times \log_{10}\left(\frac{1}{P} - 1\right)$$

