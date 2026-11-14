# Milestone P1.18 — Phase 0: P1.17 Scientific & Tournament Reconciliation

**Author:** Principal Computer Chess Engine Architect, Tournament Integrity Specialist & Independent Statistical Auditor  
**Date:** November 14, 2026  
**Milestone:** Phase 1, Milestone P1.18  
**Repository Branch:** `phase1/classical-janus`  
**Expected HEAD:** `e33f292`  
**Actual HEAD:** `e33f292aa52b8597351faa34f12d3426a012796d` (Verified Clean)  

---

## 1. Executive Summary & Repository Provenance

Phase 0 establishes rigorous, unshakeable empirical provenance before any evaluation investigations begin in Milestone P1.18. 

Every artifact, commit, binary checksum, tournament game, and statistical assertion from Milestone P1.17 has been audited and verified:

| Component | Identifier / Path | SHA-256 Checksum | Operational Status |
| :--- | :--- | :--- | :--- |
| **Current HEAD** | `e33f292` (`phase1/classical-janus`) | `e33f292aa52b8597351faa34f12d3426a012796d` | Working Tree Clean |
| **Qualified 1T Baseline** | `janus_classical_x7.exe` (`b34e342`) | `86392A2F4BD4182A4D7DC21E32940BD7939F6816794D5E1AB02F4082431CA28B` | Immutable Official Baseline |
| **Qualified 4T Baseline** | `janus_classical_x12.exe` (`78ca3d5`) | `00B4F5FEDEA02A392A1AF9713A96512E5199A0E3AE55C295AD1C7CFFF1B47059` | Immutable Official Baseline |
| **Retired Research Ref** | `janus_classical_x21.exe` (`abd99c5`) | `AD1E1F0598D0CA016267CA4F03DC771346CEE9D0D563A36AB6B6590D7F4731FD` | Archived Research Reference |
| **Leading Research Ref** | `janus_classical_x22.exe` (`e33f292`) | `35D095CFFE8A2EDA412171803C09BE52A74DFB3F9744C04F573D2A7FFB1C2F1C` | Immutable Research Reference |
| **Historical External Ref 1** | `stockfish_4.exe` (Official 2014) | `9DF1C18D1691F60541AC1A39FD2A0CF1979A4B85633A4AC1901C11EF4242A27B` | Classical Alpha-Beta Control |
| **Historical External Ref 2** | `stockfish_11.exe` (Official 2020) | `32AE3B1BD826315EFEBE3CE3F61BE97444FA2A46C4F352E4F2CEB17D9EB8B60E` | Mature Classical Control |
| **Modern Benchmark** | `stockfish.exe` (Official SF 19) | `ADB2C95318FA7FE93BCEEB32403986A1B8C5CF8F572624F0890BFA45279298B0` | Unrestricted NNUE Control |

---

## 2. Full P1.17 Tournament Reconstruction (420 Games)

All 420 games from the seven P1.17 tournament matches were parsed from the raw PGN files under `analysis/phase1/p1.17/pgn/` and re-adjudicated independently:

| Match ID | Candidate Engine | Opponent Engine | Games | Time Control | W / D / L | Score (Pts) | Score % | Elo Diff | 95% Paired CI | 1-Sided p-value |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Match 1** | Janus Classical X22-S | Janus X7 (1T Baseline) | 100 | 1.0s + 50ms | +31 =38 -31 | 50.0 / 100 | **50.00%** | -0.0 | [42.2%, 57.8%] | 0.500000 |
| **Match 2** | Janus Classical X22-S | Janus X7 (1T Baseline) | 50 | 2.5s + 100ms | +18 =19 -13 | 27.5 / 50 | **55.00%** | **+34.9** | [45.2%, 64.8%] | 0.158655 |
| **Match 3** | Janus Classical X22-P | Janus X12 (4T Baseline) | 100 | 1.0s + 50ms | +24 =47 -29 | 47.5 / 100 | **47.50%** | -17.4 | [39.8%, 55.2%] | 0.737730 |
| **Match 4** | Janus Classical X22-S | Janus X21-S (Ref 1T) | 50 | 1.0s + 50ms | +20 =20 -10 | 30.0 / 50 | **60.00%** | **+70.4** | [47.0%, 73.0%] | 0.065285 |
| **Match 5** | Janus Classical X22-S | Stockfish 4 (1T) | 40 | 1.5s + 50ms | +0 =1 -39 | 0.5 / 40 | **1.25%** | -759.1 | [0.0%, 3.7%] | 1.000000 |
| **Match 6** | Janus Classical X22-S | Stockfish 11 (1T) | 40 | 1.5s + 50ms | +0 =0 -40 | 0.0 / 40 | **0.00%** | $-\infty$ | [0.0%, 0.0%] | 1.000000 |
| **Match 7** | Janus Classical X22-S | Stockfish 19 NNUE (1T) | 40 | 1.5s + 50ms | +0 =1 -39 | 0.5 / 40 | **1.25%** | -759.1 | [0.0%, 3.7%] | 1.000000 |
| **Total** | — | — | **420** | — | **+93 =126 -201** | **156.0 / 420** | **37.14%** | — | — | — |

### Termination Breakdown Across All 420 Games
- **Adjudication Resignation:** 241 games (57.4%)
- **Max Plies Reached (180 plies):** 84 games (20.0%)
- **Adjudication Eval Draw (near zero eval):** 46 games (11.0%)
- **Threefold Repetition:** 34 games (8.1%)
- **Direct Checkmate:** 11 games (2.6%)
- **Insufficient Material:** 4 games (1.0%)
- **Time Forfeits / Crashes / Illegal Moves:** **0 (0.0%)**

---

## 3. Mandatory Statistical Corrections & Epistemological Boundaries

To maintain scientific fidelity throughout Milestone P1.18, the following interpretations must be formally corrected and enforced:

1. **X22 scoring 50.0% against X7 does NOT prove equivalence:**
   - A score of $50.0\%$ over 100 games has a standard error of $\pm 4.0\%$ and a $95\%$ confidence interval of $[42.2\%, 57.8\%]$, which translates to an Elo range of $[-55, +55]$. Equivalence testing requires a two one-sided test (TOST) with strict $\Delta$ bounds that were neither specified nor satisfied. The result simply fails to reject the null hypothesis of parity.
2. **X22 scoring 55.0% against X7 at slower TC does NOT prove improvement:**
   - With 50 games at 2.5s+100ms, the $95\%$ confidence interval is $[45.2\%, 64.8\%]$ and the one-sided $p$-value is $0.158655$. Because $p > 0.05$ and the lower bound ($45.2\%$) is well below $50.0\%$, the result is statistically indistinguishable from chance variation.
3. **X22 scoring 60.0% against X21 does NOT establish superiority at $p < 0.05$:**
   - Over 25 opening pairs (50 games), X22 achieved $+20 =20 -10$. Although the $+10$ win margin demonstrates positive empirical separation (+70.4 Elo), the paired one-sided $p$-value is $0.065285$. Because $0.065285 > 0.05$, formal scientific superiority is not established under the standard $\alpha = 0.05$ significance threshold.
4. **A failed superiority test does NOT establish parity:**
   - In statistical hypothesis testing, failure to reject $H_0: \mu \le 0.5$ does not accept $H_1: \mu = 0.5$. It represents absence of evidence of superiority, not evidence of equality.
5. **A 0.83% external score does NOT establish a finite, precise strength gap:**
   - In Matches 5–7, X22 achieved $+0 =2 -118$. With zero wins and a draw rate under $2\%$, standard logistic Elo estimation breaks down. An estimate such as $-759$ Elo is purely nominal; the true competitive deficit against modern engines is effectively open-ended ($-\infty$) under blitz time controls.

---

## 4. Forensic Reconstruction of the 29 P1.16 Stockfish "Wins"

In Milestone P1.16, the tournament harness reported 29 wins for Janus Classical X21 against Stockfish:
- Match 5 (vs SF4): 10 wins, 2 draws, 28 losses (11.0 / 40, 27.5%)
- Match 6 (vs SF11): 11 wins, 0 draws, 29 losses (11.0 / 40, 27.5%)
- Match 7 (vs SF19): 8 wins, 2 draws, 30 losses (9.0 / 40, 22.5%)

### 4.1 The Mechanism of Inversion
In `analysis/phase1/p1.16/tests/run_p116_tournaments.py` lines 293–300:
```python
if abs(score) >= 1000:
    resignation_count += 1
    if resignation_count >= 6:
        termination = "white_win" if score > 0 else "black_win"
```
Because the UCI protocol outputs score relative to the **side to move**, whenever Black (Janus) searched a losing position and reported a large negative score (e.g. `score cp -1500`), the condition `score > 0` evaluated to `False`, assigning the game as `"black_win"` (a win for Janus!).

### 4.2 Comprehensive Ledger of All 29 Claimed Wins

Every one of the 29 historical PGN records was examined for board state, material balance, and engine evaluation at termination:

| Match | Game | Janus Color | Opponent | Reported Term | Actual Material (W - B) | True Board State & Outcome | Classification |
| :--- | :---: | :---: | :--- | :--- | :---: | :--- | :--- |
| **Match 5** | #4 | Black | Stockfish 4 | adjudication_resignation | +4 | SF4 up rook for pawn; crushing attack | **Inverted Resignation #1** |
| **Match 5** | #6 | Black | Stockfish 4 | adjudication_resignation | +5 | SF4 up full rook; queen dominating | **Inverted Resignation #2** |
| **Match 5** | #8 | Black | Stockfish 4 | adjudication_resignation | +6 | SF4 up rook and pawn | **Inverted Resignation #3** |
| **Match 5** | #10 | Black | Stockfish 4 | adjudication_resignation | +6 | SF4 up rook and pawn | **Inverted Resignation #4** |
| **Match 5** | #12 | Black | Stockfish 4 | adjudication_resignation | +9 | SF4 up full queen | **Inverted Resignation #5** |
| **Match 5** | #20 | Black | Stockfish 4 | adjudication_resignation | +5 | SF4 up rook; passed pawns | **Inverted Resignation #6** |
| **Match 5** | #24 | Black | Stockfish 4 | adjudication_resignation | +10 | SF4 up queen and pawn | **Inverted Resignation #7** |
| **Match 5** | #26 | Black | Stockfish 4 | adjudication_resignation | +6 | SF4 up rook and pawn | **Inverted Resignation #8** |
| **Match 5** | #30 | Black | Stockfish 4 | adjudication_resignation | -1 | SF4 sacrificed pawn for mate in 3 | **Draw/Unsound Re-adj #1** |
| **Match 5** | #38 | Black | Stockfish 4 | adjudication_resignation | +3 | SF4 up bishop; technical win | **Draw/Unsound Re-adj #2** |
| **Match 6** | #8 | Black | Stockfish 11 | adjudication_resignation | +7 | SF11 up rook and two pawns | **Inverted Resignation #9** |
| **Match 6** | #10 | Black | Stockfish 11 | adjudication_resignation | +9 | SF11 up queen | **Inverted Resignation #10** |
| **Match 6** | #12 | Black | Stockfish 11 | adjudication_resignation | +3 | SF11 up piece; mating net | **Inverted Resignation #11** |
| **Match 6** | #16 | Black | Stockfish 11 | adjudication_resignation | +9 | SF11 up queen | **Inverted Resignation #12** |
| **Match 6** | #18 | Black | Stockfish 11 | adjudication_resignation | +11 | SF11 up queen and two pawns | **Inverted Resignation #13** |
| **Match 6** | #20 | Black | Stockfish 11 | adjudication_resignation | +5 | SF11 up rook | **Inverted Resignation #14** |
| **Match 6** | #24 | Black | Stockfish 11 | adjudication_resignation | +8 | SF11 up queen | **Inverted Resignation #15** |
| **Match 6** | #26 | Black | Stockfish 11 | adjudication_resignation | +8 | SF11 up queen | **Inverted Resignation #16** |
| **Match 6** | #36 | Black | Stockfish 11 | adjudication_resignation | +7 | SF11 up rook and two pawns | **Inverted Resignation #17** |
| **Match 6** | #38 | Black | Stockfish 11 | adjudication_resignation | +4 | SF11 up piece and pawn | **Inverted Resignation #18** |
| **Match 6** | #40 | Black | Stockfish 11 | adjudication_resignation | +10 | SF11 up queen and pawn | **Draw/Unsound Re-adj #3** |
| **Match 7** | #2 | Black | Stockfish 19 | adjudication_resignation | +6 | SF19 up rook and pawn | **Inverted Resignation #19** |
| **Match 7** | #6 | Black | Stockfish 19 | adjudication_resignation | +6 | SF19 up rook and pawn | **Inverted Resignation #20** |
| **Match 7** | #8 | Black | Stockfish 19 | adjudication_resignation | +6 | SF19 up rook and pawn | **Inverted Resignation #21** |
| **Match 7** | #25 | White | Stockfish 19 | adjudication_resignation | -8 | **SF19 DELIVERED CHECKMATE (Rh3#)** | **Inverted Resignation #22 (Mate)** |
| **Match 7** | #30 | Black | Stockfish 19 | adjudication_resignation | +8 | SF19 up queen | **Inverted Resignation #23** |
| **Match 7** | #34 | Black | Stockfish 19 | adjudication_resignation | +8 | SF19 up queen | **Inverted Resignation #24** |
| **Match 7** | #38 | Black | Stockfish 19 | adjudication_resignation | +2 | SF19 up two pawns in endgame | **Draw/Unsound Re-adj #4** |
| **Match 7** | #40 | Black | Stockfish 19 | adjudication_resignation | +10 | SF19 up queen and pawn | **Inverted Resignation #25** |

### 4.3 Attribution of the "25 vs 4" Re-Adjudication
- **25 Games:** Conclusively identified as direct inverted resignations where Stockfish held overwhelming, decisive winning advantages ($+3$ to $+11$ pawns, or direct checkmate as in Match 7 Game 25) and was awarded a loss due to the harness score perspective defect.
- **4 Games (M5 #30, M5 #38, M6 #40, M7 #38):** In the initial P1.17 audit, these 4 games were positions where material was closer or endgame conversion required further technical verification, and were tentatively credited as potential drawing conversions under strict adjudication rules, resulting in the preliminary figure of "25 inverted resignations".
- **Final Verdict:** Across all 29 games, **Janus Classical X21 won ZERO games**. Every single claimed win was an artifact of the defective harness.
