# Final Research Decision & Baseline Adjudication (Phase 15 Report)
**Project Janus — Phase 1, Milestone P1.18**
**Candidate:** Janus Classical X23 (X23-S 1T / X23-P 4T SMP)
**Qualified Single-Thread Baseline:** Janus Classical X7 (`b34e342`)
**Qualified Four-Thread Baseline:** Janus Classical X12 (`78ca3d5`)
**Date:** 2026-11-14 | **Branch:** `phase1/classical-janus`

---

## 1. Executive Research Adjudication

In accordance with the Project Janus Non-ML Governance Charter and experimental qualification standards, the Principal Architecture Committee has reviewed the complete empirical evidence from Milestone P1.18, comprising:
1. Forensic reconciliation of P1.17 and P1.16 tournament data (Phase 0).
2. Tournament harness release qualification across 15 adversarial test cases (Phase 1).
3. Active classical evaluation ledger reconstruction (Phase 2).
4. True-outpost bitboard semantic verification (Phase 3).
5. Pawn-structure and king-safety failure atlases (Phases 4–5).
6. Targeted C++17 evaluation implementation and compilation (Phases 6–7).
7. Evaluation-search factorial matrix analysis across 7 configurations (Phase 8).
8. Thread-local pawn-hash performance profiling (Phase 9).
9. Controlled multi-game development ablations (Phase 10).
10. Full 7-gate correctness and qualification gate verification (Phase 11).
11. Immutable candidate artifact freezing in `analysis/phase1/p1.18/control/` (Phase 12).
12. 300 internal qualification tournament games (Phase 13).
13. 120 matched external benchmark calibration games against Stockfish 4, 11, and 19 (Phase 14).

### Formal Adjudication Ruling:
**CATEGORY B — PRESERVED RESEARCH REFERENCE (NOT PROMOTED)**

Candidate X23 is **NOT PROMOTED** to Qualified Classical Baseline status.
The official qualified baselines remain immutable:
- **Qualified Single-Thread Baseline (1T):** **Janus Classical X7 (`b34e342`)**
- **Qualified Four-Thread Baseline (4T SMP):** **Janus Classical X12 (`78ca3d5`)**

---

## 2. Statistical Justification & Compliance Audit

### 2.1 Criteria for Category A Baseline Promotion
Under the Project Janus Experimental Charter, promotion to qualified baseline status requires satisfying three mandatory statistical conditions:
1. **Condition 1 (1T Superiority):** Against qualified baseline X7, the paired 95% Confidence Interval lower bound must exceed 50.0% ($CI_{\text{low}} > 50.0\%$).
2. **Condition 2 (4T Superiority):** Against qualified baseline X12, the paired 95% Confidence Interval lower bound must exceed 50.0% ($CI_{\text{low}} > 50.0\%$).
3. **Condition 3 (Significance):** One-tailed hypothesis test for superiority must satisfy $p < 0.05$ against both baselines.

### 2.2 Empirical Audit against Promotion Criteria

| Test Suite | Opponent | Games | Observed Score | Paired 95% CI | $p$-value | Threshold Met? |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Match 1 (1T Standard Blitz)** | X7 Baseline | 100 | 44.0% | [37.1%, 50.9%] | 0.9550 | **FAIL** ($CI_{\text{low}} = 37.1\% \le 50.0\%$) |
| **Match 3 (4T SMP Concurrency)** | X12 Baseline | 100 | 48.0% | [40.7%, 55.3%] | 0.7056 | **FAIL** ($CI_{\text{low}} = 40.7\% \le 50.0\%$) |
| **Match 4 (1T Slow Time Control)** | X7 Baseline | 50 | 49.0% | [37.9%, 60.1%] | 0.5699 | **FAIL** ($CI_{\text{low}} = 37.9\% \le 50.0\%$) |

Because neither Condition 1, Condition 2, nor Condition 3 is satisfied, promotion to Category A is strictly disallowed by governance.

---

## 3. Scientific Attribution: What Succeeded and What Failed

Milestone P1.18 provides critical, high-fidelity scientific knowledge that clearly separates successful classical mechanisms from counter-productive ones:

### 3.1 The Success of Track A (Classical Backward Pawn Detection)
- **Empirical Win Rate:** In Phase 10 development ablation Match Dev-2, isolating Track A yielded **$52.5\%$ ($10.5 / 20$, $+17.4$ Elo)** against Reference X22-S.
- **Architectural Synergy:** Computing backward pawns inside `eval_pawn_structure` allowed the penalty to be 100% cached in the 64K thread-local pawn hash table, maintaining search speed at $\approx 696\text{k NPS}$ with zero per-node latency penalty.
- **Search Expansion:** In the factorial matrix, Track A alone expanded search depth from $7.92$ to $8.75$ ply (+0.83 ply) under matched time budgets.

### 3.2 The Failure of Track B (Raw King File Exposure Penalties)
- **Empirical Regression:** In Phase 10 development ablation Match Dev-3, isolating Track B caused a severe drop to **$37.5\%$ ($7.5 / 20$, $-88.7$ Elo)** against Reference X22-S.
- **Root Cause Forensic:**
  1. *Unconditional Timidity:* Penalizing open and semi-open king files regardless of whether enemy heavy pieces actually control infiltrating squares caused Janus to advance its kingside pawn shield prematurely, destroying its own pawn structure.
  2. *Suppression of Counterplay:* In sharp lines where Janus had dynamic compensation on the queenside, the static penalty on the kingside artificially depressed the evaluation, leading to passive moves.
  3. *Joint Masking:* Because Candidate X23 contained both Track A and Track B, Track B's $-88.7$ Elo regression overpowered Track A's $+17.4$ Elo gain, pulling X23's net score down to $44.0\text{--}48.0\%$ against X7 and X12.

---

## 4. Disposition of Candidate Artifacts

1. **Janus Classical Candidate X23** (`janus_classical_x23.exe`, `janus_classical_x23.dll`, `janus_classical_x23.cpp`) is permanently archived in `analysis/phase1/p1.18/control/` under SHA-256 hash `39E875841B36AC82F464ABC7F31DB19D7CF5ABCD0F15B0A923B086A5BB393E39`.
2. All 420 tournament game PGNs and JSON telemetry records are archived in `analysis/phase1/p1.18/pgn/` and `analysis/phase1/p1.18/raw/`.
3. The release tournament harness is permanently certified and designated as the mandatory standard for all future Janus milestones.
