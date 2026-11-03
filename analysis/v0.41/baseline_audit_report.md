# Project Janus v0.41 — Baseline Integrity & Discrepancy Audit Report

**Date:** 2026-11-01  
**Auditor:** Senior Chess Engine Research Engineer, Statistical Validation Lead, and Independent Audit Engineer  
**Starting Commit:** `8424f1d` (`8424f1da8ed639064639c0f1b36ca1bb38d56ab5`)  
**Branch:** `v0.3-benchmark-harness`  
**Host Environment:** AMD64 Windows 11 (Python 3.13.2, python-chess 1.11.2)  
**External Benchmark:** Stockfish 19 (`E:\ChessXML\tools\stockfish\stockfish.exe`, SHA-256: `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0`)

---

## 1. Baseline Verification & Starting State

Before introducing modifications, the repository working tree was inspected and verified clean:
- **HEAD Commit:** `8424f1d` (*"docs(v0.40): comprehensive milestone report and decision framework"*).
- **Working Tree:** Pristine, no untracked or unstaged files.
- **Test Suite Status:** 437 tests passing in 216.0 s (`tests/` discover).
- **Default Engine Configuration:**
  - Full tapered evaluation with pawn structure, rook files, castled and uncastled king safety enabled (`CONFIG_V034_TAPERED`).
  - Capture-only quiescence search (Q0).
  - Arm C adaptive Fischer time management (3,000 ms + 100 ms).
  - Transposition table: 200,000 entries, always-replace policy.
  - Reverse Futility Pruning: **DISABLED** by default (`enable_rfp = False`).
  - Move Ordering Heuristics (Candidate ORD1): **DISABLED** by default (`enable_countermoves = False`, `enable_history_malus = False`).

---

## 2. Comprehensive Forensic Audit of v0.40 Claims

### 2.1 Throughput Arithmetic: Ratio-Mean vs Pooled Aggregate NPS
- **Historical Claim in v0.39:** Reported Q0 throughput as 21,998 NPS vs Q1 as 11,018 NPS. However, calculated $\frac{\sum \text{Nodes}}{\sum \text{Time}}$ gave 19,179 vs 5,212 NPS.
- **Audit Findings:** The discrepancy is fully resolved. v0.39 averaged the per-position NPS ratios ($\frac{1}{N}\sum \text{NPS}_i$), which heavily overweights tiny endgame subtrees (33k–44k NPS). The pooled throughput ($\frac{\sum \text{Nodes}}{\sum \text{Time}}$) is the statistically sound metric:
  - **Q0 Pooled NPS:** **23,544.0 NPS** (1.717 s total search time).
  - **Q1 Pooled Throughput:** **17,889.8 NPS** (2.540 s total search time, +47.9% time overhead).
  - **Conclusion:** Q0 is empirically faster by 31.6% in throughput and cuts total search latency by 32.4%.

### 2.2 Repetition Claim Handling in Quiescence
- **Historical Claim in v0.40:** Removing `can_claim_threefold_repetition()` from `_quiescence` preserves draw-claim correctness because moves in capture-only quiescence are irreversible.
- **Forensic Audit:** While intra-qsearch cyclic loops are physically impossible across captures and promotions, **positions entering quiescence from preceding game history can already be eligible for a 3-fold repetition claim**.
  - Neither `_negamax` (line 731) nor `_quiescence` (line 642) checked `can_claim_threefold_repetition()` or `is_repetition(3)`. They only checked `is_fivefold_repetition()`.
  - When a game history reaches a 3-fold repetition, the side to move entering quiescence evaluated static material (e.g. down a Queen = -900 cp) and completely skipped the draw claim (0 cp).
  - **Action in v0.41:** Remediate the call path using `board.is_repetition(3)` (0.18 $\mu\text{s}$ latency) to guarantee 100% draw-claim recognition without degrading search throughput.

### 2.3 The Reverse Futility Pruning (RFP) Qualification Gap
- **Audit Findings:** The v0.40 executive summary stated "GATES A-D PASSED", yet the detailed RFP report (`analysis/v0.40/reverse_futility_experiment.md`) classified Gate D as `RETAIN AS EXPERIMENTAL COMPONENT (DEFERRED DEFAULT ENABLING)` because **no playing-strength match was executed for Candidate RFP**.
- **Qualification Gap Confirmed:** In v0.40, Candidate RFP was evaluated through Gate A (implementation audit), Gate B (7 correctness tests), and Gate C (fixed-position profiling showing -18.22% nodes), but Gate D (strength match against Stockfish 19 Elo 1320) was **deferred**.
- **Action in v0.41:** Execute the preregistered 50-game controlled paired match for Candidate RFP against Stockfish 19 Elo 1320 to resolve Gate D empirically.

### 2.4 Statistical Terminology: Inconclusive vs Equivalence
- **Audit Findings:** The v0.40 report described Candidate K1 (46.0% vs 45.0% K0, $p = 0.9231$) and Candidate ORD1 (45.0% vs 45.0% K0, $p = 1.0000$) as establishing "statistical equivalence".
- **Statistical Correction:** In classical null-hypothesis significance testing (NHST), failing to reject $H_0$ ($p > 0.05$) does **not** prove that two configurations are equivalent; it only indicates that the test was unable to detect a statistically significant difference within a 50-game sample ($\pm 14\%$ uncertainty interval).
- **Formal Definition:** To establish equivalence, a practical equivalence margin $\Delta_{\text{equiv}} = \pm 10\%$ must be preregistered under Two One-Sided Tests (TOST). The v0.41 report will use precise terminology: **statistically inconclusive / no detectable difference at $N=50$**.

---

## 3. Plan for Milestone v0.41

1. **Phase 1:** Resolve the RFP Qualification Gap by running the 50-game match for Candidate `rfp`.
2. **Phase 2:** Qualify Candidate `ord1` through 4-way profiling and empirical match analysis.
3. **Phase 3:** Reassess K1 under the TOST statistical framework.
4. **Phase 4:** Trace and repair the repetition draw claim call path in `_negamax` and `_quiescence`.
5. **Phase 5:** Effective-depth and tactical reliability diagnostics across 16 benchmark positions.
6. **Phase 6:** Harness integrity verification and clean-room audit.

