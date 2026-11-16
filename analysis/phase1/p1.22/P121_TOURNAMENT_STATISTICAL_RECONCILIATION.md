# P1.21 TOURNAMENT STATISTICAL RECONCILIATION & FORENSIC AUDIT REPORT
**Milestone:** Phase 1, Milestone P1.22 — Phase 0  
**Repository:** `E:\ChessXML\project-janus-phase1`  
**Branch:** `phase1/classical-janus`  
**Audit Target:** All 8 Matches (500 Games, 250 Opening Pairs) from P1.21 Tournament Battery (`analysis/phase1/p1.21/pgn/*.pgn`)  
**Auditor:** Principal Computer Chess Architect & Independent Statistical Auditor  
**Date:** 2026-11-16  

---

## 1. Executive Summary

During the initial phase of Milestone P1.22, a forensic re-examination of the complete 500-game tournament battery from Milestone P1.21 was conducted. This audit was triggered by the observation that in all P1.21 matches, the reported pentanomial distributions exhibited non-zero values only in the first three bins, while the fourth and fifth bins were universally zero (e.g., `[26, 16, 8, 0, 0]`).

Re-parsing the raw PGN game records and inspecting the tournament controller script (`analysis/phase1/p1.21/tests/run_p121_tournaments.py`) revealed two critical implementation defects in the P1.21 experimental harness:

1. **Defective Pentanomial Binning Function:**  
   The harness calculated normalized pair scores $s \in [0.0, 1.0]$ (where $s = \frac{\text{pair\_points}}{2.0}$), and then called `int(round(s * 2.0))`.  
   Because Python's `round()` uses round-half-to-even:
   - Pair points $0.0$ ($LL$, $s=0.0$) and $0.5$ ($LD$, $s=0.25 \to 0.5$) both rounded to `0`.
   - Pair points $1.0$ ($DD$ and $WL$, $s=0.5 \to 1.0$) rounded to `1`.
   - Pair points $1.5$ ($WD$, $s=0.75 \to 1.5$) and $2.0$ ($WW$, $s=1.0 \to 2.0$) both rounded to `2`.
   - Bins `3` and `4` were strictly unreachable ($N_3 \equiv 0, N_4 \equiv 0$). What was reported as a 5-bin pentanomial was in reality a collapsed 3-bucket distortion where 0.0 and 0.5 were merged into bin 0, and 1.5 and 2.0 were merged into bin 2.

2. **PGN Termination & Referee Scoring Defect:**  
   In the game loop of `run_p121_tournaments.py`, games terminated when `board.is_game_over(claim_draw=True)` returned `True`. In `python-chess`, this method flags threefold repetition claims via `board.can_claim_threefold_repetition()`. However, the subsequent post-loop header assignment block checked `elif board.is_repetition(3):`, which requires the repetition to be strictly present in the move history without a claim pending, resulting in `False`.  
   Consequently, every game terminating via threefold repetition had its PGN result left as `*` with an empty termination tag.  
   Crucially, the result tabulation logic evaluated:
   ```python
   s1 = 1.0 if g1["result"] == "1-0" else (0.5 if g1["result"] == "1/2-1/2" else 0.0)
   ```
   Because `g["result"]` was `*`, **all 38 threefold-repetition draws across the 500 games were scored as 0.0 (Candidate Losses)**. This systematically depressed the candidate's reported scores, winning percentages, and Elo ratings across all matches.

This document establishes the mathematically rigorous, authoritative reconciliation of the P1.21 tournament battery. All 500 games have been replayed and re-adjudicated according to FIDE rules and `python-chess` board invariants.

---

## 2. Forensic Breakdown of Tournament Defects

### 2.1 The Pentanomial Calculation Collapse
In standard computer chess statistics (e.g., Cutechess, fastchess, SPRT), a pentanomial distribution partitions mini-matches of 2 games (White and Black from the same opening) by Candidate pair points:
- Bin 0: $0.0$ points ($LL$: 0 wins, 0 draws, 2 losses)
- Bin 1: $0.5$ points ($LD$: 0 wins, 1 draw, 1 loss)
- Bin 2: $1.0$ points ($DD$ or $WL$: 0 wins, 2 draws, 0 losses OR 1 win, 0 draws, 1 loss)
- Bin 3: $1.5$ points ($WD$: 1 win, 1 draw, 0 losses)
- Bin 4: $2.0$ points ($WW$: 2 wins, 0 draws, 0 losses)

In `run_p121_tournaments.py`:
```python
def calc_pentanomial(pair_scores):
    p = [0, 0, 0, 0, 0]
    for s in pair_scores:
        idx = int(round(s * 2.0))
        p[idx] += 1
    return p
```
Because `pair_scores` was appended with `(s1 + s2) / 2.0`, the variable `s` took values in $\{0.0, 0.25, 0.50, 0.75, 1.00\}$. Multiplying by 2.0 produced $\{0.0, 0.5, 1.0, 1.5, 2.0\}$. Rounding half to even mapped $0.5 \to 0$ and $1.5 \to 2$, completely extinguishing bins 3 and 4.

### 2.2 The Threefold Repetition Draw Corruption
Replaying each of the 38 games marked with `*` confirmed that 100% of them reached legitimate threefold repetition positions where `board.can_claim_threefold_repetition()` was `True`.  
Because the harness treated `*` as `0.0`, Candidate X26 suffered an artificial deduction of 19.0 total points (38 half-points converted to full losses).

Specifically:
- **Match 1 (vs X22-S Fast):** 7 games had `*` (all 3-fold repetitions). True score: 42.5/100 (42.5%), not 39.0/100 (39.0%).
- **Match 2 (vs X22-S Slow):** 5 games had `*` (all 3-fold repetitions). True score: 21.0/50 (42.0%), not 18.5/50 (37.0%).
- **Match 3 (vs X7 Fast):** 10 games had `*` (all 3-fold repetitions). True score: 47.5/100 (47.5%), not 42.5/100 (42.5%).
- **Match 4 (vs X7 Slow):** 7 games had `*` (all 3-fold repetitions). True score: 22.0/50 (44.0%), not 18.5/50 (37.0%).
- **Match 5 (vs X12 Fast SMP):** 7 games had `*` (all 3-fold repetitions). True score: 41.0/100 (41.0%), not 37.5/100 (37.5%).
- **Match 6 (vs Stockfish 4 Blitz):** 1 game had `*` (Game 29 was a threefold repetition draw!). True score: 0.5/40 (1.25%), not 0.0/40 (0.0%).
- **Match 7 (vs Stockfish 11 Blitz):** 1 game had `*` (Game 20 was a threefold repetition draw!). True score: 0.5/40 (1.25%), not 0.0/40 (0.0%).
- **Match 8 (vs Stockfish 19 NNUE):** 0 games had `*` (all 20 decisive losses). True score: 0.0/20 (0.0%).

---

## 3. Authoritative Reconciled Match Results

The following table presents the authoritative, fully audited results across all 8 matches.

| Match ID | Opponent / Condition | Games (Pairs) | P1.21 Reported (W-D-L, %) | Authoritative (W-D-L, %) | Repaired '*' Draws | Authoritative Elo | Paired 95% CI | Paired SE | Two-Tailed p-value |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **M1** | Ref X22-S Fast (5s+0.05s) | 100 (50) | 20-38-42 (39.0%) | **20-45-35 (42.5%)** | 7 | -52.5 | [34.7%, 50.3%] | 0.0399 | p = 0.0603 |
| **M2** | Ref X22-S Slow (15s+0.15s) | 50 (25) | 12-13-25 (37.0%) | **12-18-20 (42.0%)** | 5 | -56.1 | [28.8%, 55.2%] | 0.0673 | p = 0.2343 |
| **M3** | Base X7 Fast (5s+0.05s) | 100 (50) | 23-39-38 (42.5%) | **23-49-28 (47.5%)** | 10 | -17.4 | [40.9%, 54.1%] | 0.0337 | p = 0.4581 |
| **M4** | Base X7 Slow (15s+0.15s) | 50 (25) | 8-21-21 (37.0%) | **8-28-14 (44.0%)** | 7 | -41.9 | [34.5%, 53.5%] | 0.0485 | p = 0.2158 |
| **M5** | Base X12 Fast (4T SMP) | 100 (50) | 15-45-40 (37.5%) | **15-52-33 (41.0%)** | 7 | -63.2 | [35.3%, 46.7%] | 0.0292 | p = 0.0021 |
| **M6** | Stockfish 4 Blitz (3s+0.03s) | 40 (20) | 0-0-40 (0.0%) | **0-1-39 (1.25%)** | 1 | -759.1 | [0.0%, 3.7%] | 0.0125 | p < 0.0001 |
| **M7** | Stockfish 11 Blitz (3s+0.03s) | 40 (20) | 0-0-40 (0.0%) | **0-1-39 (1.25%)** | 1 | -759.1 | [0.0%, 3.7%] | 0.0125 | p < 0.0001 |
| **M8** | Stockfish 19 NNUE Blitz | 20 (10) | 0-0-20 (0.0%) | **0-0-20 (0.0%)** | 0 | -inf | [0.0%, 0.0%] | 0.0000 | p < 0.0001 |
| **Total** | **All 8 Matches** | **500 (250)** | **78-156-266 (31.2%)** | **78-194-228 (35.0%)** | **38** | — | — | — | — |

---

## 4. Decomposed Pair Subcategories & Authoritative Pentanomial Distributions

Every pair has been classified into the six canonical mutual outcomes:
- **LL** ($0.0$ pts): Candidate loses both games.
- **LD** ($0.5$ pts): Candidate draws one, loses one.
- **DD** ($1.0$ pts): Candidate draws both games.
- **WL** ($1.0$ pts): Candidate wins one, loses one (split pair).
- **WD** ($1.5$ pts): Candidate wins one, draws one.
- **WW** ($2.0$ pts): Candidate wins both games.

### 4.1 Authoritative Pair Subcategories Table

| Match ID | Total Pairs | LL (0.0) | LD (0.5) | DD (1.0) | WL (1.0) | WD (1.5) | WW (2.0) | Points Sum Check |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **M1** (vs X22-S Fast) | 50 | 8 | 12 | 15 | 7 | 3 | 5 | $0(8) + 0.5(12) + 1.0(22) + 1.5(3) + 2.0(5) = 42.5$ pts (Exact) |
| **M2** (vs X22-S Slow) | 25 | 5 | 9 | 2 | 1 | 5 | 3 | $0(5) + 0.5(9) + 1.0(3) + 1.5(5) + 2.0(3) = 21.0$ pts (Exact) |
| **M3** (vs X7 Fast) | 50 | 1 | 19 | 10 | 7 | 10 | 3 | $0(1) + 0.5(19) + 1.0(17) + 1.5(10) + 2.0(3) = 47.5$ pts (Exact) |
| **M4** (vs X7 Slow) | 25 | 3 | 6 | 8 | 2 | 6 | 0 | $0(3) + 0.5(6) + 1.0(10) + 1.5(6) + 2.0(0) = 22.0$ pts (Exact) |
| **M5** (vs X12 Fast) | 50 | 4 | 17 | 14 | 8 | 7 | 0 | $0(4) + 0.5(17) + 1.0(22) + 1.5(7) + 2.0(0) = 41.0$ pts (Exact) |
| **M6** (vs Stockfish 4) | 20 | 19 | 1 | 0 | 0 | 0 | 0 | $0(19) + 0.5(1) + 1.0(0) + 1.5(0) + 2.0(0) = 0.5$ pts (Exact) |
| **M7** (vs Stockfish 11) | 20 | 19 | 1 | 0 | 0 | 0 | 0 | $0(19) + 0.5(1) + 1.0(0) + 1.5(0) + 2.0(0) = 0.5$ pts (Exact) |
| **M8** (vs Stockfish 19) | 10 | 10 | 0 | 0 | 0 | 0 | 0 | $0(10) + 0.5(0) + 1.0(0) + 1.5(0) + 2.0(0) = 0.0$ pts (Exact) |
| **Total** | **250** | **69** | **65** | **49** | **25** | **31** | **11** | **Total Candidate Points: 175.0 / 500 (35.0%)** |

### 4.2 Verified Pentanomial Distributions

To eliminate any convention ambiguity, both ascending ($[0.0, 0.5, 1.0, 1.5, 2.0]$) and descending ($[2.0, 1.5, 1.0, 0.5, 0.0]$) representations are explicitly documented:

| Match ID | Opponent | P1.21 Corrupted Raw | Authoritative Ascending [LL, LD, 1.0, WD, WW] | Authoritative Descending [WW, WD, 1.0, LD, LL] |
|:---|:---|:---:|:---:|:---:|
| **M1** | Ref X22-S Fast | `[26, 16, 8, 0, 0]` | `[8, 12, 22, 3, 5]` | `[5, 3, 22, 12, 8]` |
| **M2** | Ref X22-S Slow | `[15, 4, 6, 0, 0]` | `[5, 9, 3, 5, 3]` | `[3, 5, 3, 9, 5]` |
| **M3** | Base X7 Fast | `[22, 17, 11, 0, 0]` | `[1, 19, 17, 10, 3]` | `[3, 10, 17, 19, 1]` |
| **M4** | Base X7 Slow | `[12, 8, 5, 0, 0]` | `[3, 6, 10, 6, 0]` | `[0, 6, 10, 6, 3]` |
| **M5** | Base X12 Fast | `[26, 18, 6, 0, 0]` | `[4, 17, 22, 7, 0]` | `[0, 7, 22, 17, 4]` |
| **M6** | Stockfish 4 Blitz | `[20, 0, 0, 0, 0]` | `[19, 1, 0, 0, 0]` | `[0, 0, 0, 1, 19]` |
| **M7** | Stockfish 11 Blitz | `[20, 0, 0, 0, 0]` | `[19, 1, 0, 0, 0]` | `[0, 0, 0, 1, 19]` |
| **M8** | Stockfish 19 NNUE Blitz | `[10, 0, 0, 0, 0]` | `[10, 0, 0, 0, 0]` | `[0, 0, 0, 0, 10]` |

---

## 5. Verification of Mathematical Invariants

All individual matches and aggregated totals satisfy the following mathematical identity invariants:
1. **Total Pair Partition Identity:**
   $$N_{\text{pairs}} = N_{LL} + N_{LD} + N_{DD} + N_{WL} + N_{WD} + N_{WW}$$
   *(Verified: $8+12+15+7+3+5 = 50$, $5+9+2+1+5+3 = 25$, etc.)*
2. **Total Candidate Points Identity:**
   $$\text{Points} = 0.0 \cdot N_{LL} + 0.5 \cdot N_{LD} + 1.0 \cdot (N_{DD} + N_{WL}) + 1.5 \cdot N_{WD} + 2.0 \cdot N_{WW} = W + 0.5 \cdot D$$
   *(Verified exactly across all 8 matches without floating point divergence)*
3. **Decomposed W-D-L Invariant:**
   $$W = 2 \cdot N_{WW} + N_{WD} + N_{WL}$$
   $$D = 2 \cdot N_{DD} + N_{WD} + N_{LD}$$
   $$L = 2 \cdot N_{LL} + N_{LD} + N_{WL}$$
   *(Verified: in M1, $W = 2(5) + 3 + 7 = 20$; $D = 2(15) + 3 + 12 = 45$; $L = 2(8) + 12 + 7 = 35$; Total games = 100)*

---

## 6. Scientific Implications for Milestone P1.22

1. **Re-evaluation of Candidate X26:**  
   While Candidate X26 remains inferior to Baseline X7 (-17.4 Elo fast, -41.9 Elo slow) and Reference X22 (-52.5 Elo fast, -56.1 Elo slow), its true performance is significantly less catastrophic than originally reported in P1.21. In fast time control vs X7, X26 scored 47.5% (23-49-28), drawing 49 out of 100 games and losing by only 5 games, rather than the reported 42.5% with 38 losses.
2. **Draw Resilience vs Historical Reference Engines:**  
   Candidate X26 managed a legitimate threefold repetition draw against Stockfish 4 in blitz (Game 29: 43 plies) and against Stockfish 11 in blitz (Game 20: 54 plies). In P1.21, both matches were reported as 0-40 whitewashes. While Stockfish 4 and 11 completely outclass X26 (+759 Elo advantage), X26 demonstrated tactical hold capability in two specific openings.
3. **Tournament Controller Hardening Requirement for R1:**  
   Milestone P1.22's testing scripts must never rely on `board.is_repetition(3)` after loop exit without checking `board.can_claim_threefold_repetition()`, and pentanomial accumulators must be indexed directly by integer pair points $\in \{0, 1, 2, 3, 4\}$ or explicit outcome keys (`LL`, `LD`, `DD`, `WL`, `WD`, `WW`).

The authoritative reconciled dataset is committed at:
`analysis/phase1/p1.22/raw/p121_tournament_reconciliation.json`.
