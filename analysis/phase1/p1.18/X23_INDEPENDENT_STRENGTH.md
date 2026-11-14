# Independent Playing-Strength Qualification (Phase 13 Report)
**Project Janus — Phase 1, Milestone P1.18**
**Candidate:** Janus Classical X23 (X23-S / X23-P)
**Control Baselines:** Janus Classical X7 (1T, `b34e342`) | Janus Classical X12 (4T, `78ca3d5`)
**Reference Candidate:** Janus Classical X22-S (`e33f292`)
**Harness:** Release Tournament Harness Certified in Phase 1 (100% Legal Board State Priority)
**Date:** 2026-11-14 | **Raw Data:** `analysis/phase1/p1.18/raw/p118_tournaments_raw.json`

---

## 1. Executive Summary & Regulatory Gate

To establish whether **Janus Classical Candidate X23** achieves genuine competitive playing-strength superiority over frozen qualified baselines, four independent, controlled tournament matches were executed across 300 total games under strict opening-pair symmetry using the fresh master opening corpus `independent_openings_v056.json`.

All games were monitored by the certified tournament harness. Adjudications strictly prioritized legal checkmates on board, threefold repetitions, 50-move draws, and certified non-inverted resignation evaluations.

### Qualification Criteria (Category A Promotion Standard)
Promotion to Qualified Classical Baseline requires:
1. Paired 95% Confidence Interval lower bound $CI_{\text{low}} > 50.0\%$ against Qualified Baseline X7 (1T).
2. Paired 95% Confidence Interval lower bound $CI_{\text{low}} > 50.0\%$ against Qualified Baseline X12 (4T SMP).
3. One-tailed statistical significance $p < 0.05$ against both baselines.

---

## 2. Competitive Tournament Results

| Match | Description | Format | Games | Candidate Score | Win Rate (%) | Wins | Draws | Losses | Paired 95% CI | $p$-value | Elo Difference |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Match 1** | X23-S vs X7 Baseline 1T | 50 pairs @ 1.0s + 50ms | 100 | 44.0 / 100 | 44.0% | 22 | 44 | 34 | [37.1%, 50.9%] | 0.9550 | $-41.9$ Elo |
| **Match 2** | X23-S vs X22-S Reference 1T | 25 pairs @ 1.0s + 50ms | 50 | 24.5 / 50 | 49.0% | 15 | 19 | 16 | [36.8%, 61.2%] | 0.5640 | $-6.9$ Elo |
| **Match 3** | X23-P vs X12 Baseline 4T | 50 pairs @ 1.0s + 50ms | 100 | 48.0 / 100 | 48.0% | 25 | 46 | 29 | [40.7%, 55.3%] | 0.7056 | $-13.9$ Elo |
| **Match 4** | X23-S vs X7 Baseline Slow TC | 25 pairs @ 2.5s + 100ms | 50 | 24.5 / 50 | 49.0% | 16 | 17 | 17 | [37.9%, 60.1%] | 0.5699 | $-6.9$ Elo |
| **Total** | **All Internal Qualification** | — | **300** | **141.0 / 300** | **47.0%** | **78** | **126** | **96** | — | — | — |

---

## 3. Detailed Match Analysis

### 3.1 Match 1: Candidate X23-S vs Qualified Baseline X7 (100 Games @ 1.0s + 50ms)
- **Score:** $44.0 / 100$ ($44.0\%$, $+22 =44 -34$).
- **Statistical Assessment:** Paired CI is $[37.1\%, 50.9\%]$, with $p = 0.9550$.
- **Finding:** Candidate X23-S does not achieve statistical superiority over Baseline X7 ($CI_{\text{low}} = 37.1\% \le 50.0\%$). X7 maintains a $+41.9$ Elo advantage under standard blitz time controls.
- **Root Cause Forensic:** While X23-S displayed sharp endgame technique when exploiting enemy backward pawns, Track B's king exposure penalties caused X23-S to push pawns in front of its king in Sicilian and French middlegames, allowing X7's classical piece pressure to break through on weakened outposts.

### 3.2 Match 2: Candidate X23-S vs Research Reference X22-S (50 Games @ 1.0s + 50ms)
- **Score:** $24.5 / 50$ ($49.0\%$, $+15 =19 -16$).
- **Statistical Assessment:** Paired CI is $[36.8\%, 61.2\%]$, with $p = 0.5640$.
- **Finding:** Candidate X23-S performs nearly dead-even with Reference X22-S ($-6.9$ Elo), demonstrating that the joint inclusion of Track A and Track B roughly balances out against X22-S's baseline evaluation.

### 3.3 Match 3: Candidate X23-P vs Qualified Baseline X12 (100 Games @ 1.0s + 50ms, 4T SMP)
- **Score:** $48.0 / 100$ ($48.0\%$, $+25 =46 -29$).
- **Statistical Assessment:** Paired CI is $[40.7\%, 55.3\%]$, with $p = 0.7056$.
- **Finding:** Candidate X23-P delivers a highly competitive performance against the 4T Baseline X12 ($-13.9$ Elo), with a $46\%$ draw rate and 25 decisive victories. However, the confidence interval lower bound ($CI_{\text{low}} = 40.7\%$) does not exceed $50.0\%$.

### 3.4 Match 4: Candidate X23-S vs Qualified Baseline X7 Slow TC (50 Games @ 2.5s + 100ms)
- **Score:** $24.5 / 50$ ($49.0\%$, $+16 =17 -17$).
- **Statistical Assessment:** Paired CI is $[37.9\%, 60.1\%]$, with $p = 0.5699$.
- **Finding:** Under a $2.5\times$ longer time control budget, Candidate X23-S improves from $44.0\%$ to $49.0\%$ against X7. The deeper search trees allow X23 to search through the defensive timidity induced by Track B, achieving an even $+16 =17 -17$ score.

---

## 4. Architectural Attribution & Factorial Cross-Check

The tournament findings corroborate the development ablations from Phase 10:
- **Track A (Backward Pawns Alone):** Gained $+17.4$ Elo ($52.5\%$) against X22 in Phase 10.
- **Track B (King File Exposure Alone):** Lost $-88.7$ Elo ($37.5\%$) against X22 in Phase 10.
- **Joint Candidate X23:** Scored $44.0\text{--}49.0\%$ against the frozen baselines.

The failure to promote Candidate X23 is attributable to Track B's uncalibrated positional penalties, not to search defects or backward pawn evaluation.

---

## 5. Regulatory Qualification Verdict

In accordance with the governing charter:
- Candidate X23-S failed to achieve $CI_{\text{low}} > 50.0\%$ against Baseline X7 ($37.1\%$).
- Candidate X23-P failed to achieve $CI_{\text{low}} > 50.0\%$ against Baseline X12 ($40.7\%$).

**Formal Adjudication:** Candidate X23 is **NOT PROMOTED** to Qualified Classical Baseline. It is cataloged as a **Preserved Research Reference (Category B)**.
- Single-thread Baseline remains: **Janus Classical X7 (`b34e342`)**
- Four-thread Baseline remains: **Janus Classical X12 (`78ca3d5`)**
