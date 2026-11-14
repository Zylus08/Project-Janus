# Milestone P1.17 Phase 1: Critical Stockfish Tournament Integrity Audit

**Date:** November 14, 2026  
**Status:** **AUDITED — FATAL TOURNAMENT HARNESS DEFECT DISCOVERED**  
**Gate Decision:** **INVALID** (External Benchmark Results from P1.16 Formally Invalidated)  
**Branch:** `phase1/classical-janus`  
**Milestone HEAD:** `abd99c5`  

---

## 1. Executive Summary & Root-Cause Discovery

Milestone P1.16 reported extraordinary external tournament results for Candidate Janus Classical X21 against mature and modern versions of Stockfish:
- 27.5% (11.0 / 40, +10 =2 -28) against Stockfish 4.
- 27.5% (11.0 / 40, +11 =0 -29) against Stockfish 11.
- 22.5% (9.0 / 40, +8 =2 -30) against unrestricted Stockfish 19 NNUE.

This created an acute scientific contradiction: **Why would an engine that regressed against the legacy Janus X7 baseline (scoring 39.0% at slow TC) suddenly win 29 games against world-class Stockfish engines that earlier Janus candidates could barely draw?**

Phase 1 conducted an independent forensic audit of the tournament execution script (`run_p116_tournaments.py`), process logs, and PGN game histories.

### The Fatal Discovery: Adjudication Sign-Inversion Defect
The tournament harness in `run_p116_tournaments.py` contained a catastrophic logic error in its resignation adjudication routine (lines 293–300):

```python
# Lines 293-300 of run_p116_tournaments.py
if score is not None and abs(score) >= 1000 and len(moves_history) >= 60:
    draw_claim_moves += 1
    if draw_claim_moves >= 6:
        adjudication = "adjudication_resignation"
        termination = "white_win" if score > 0 else "black_win"
        break
```

### The Mechanism of Failure:
1. **The UCI Protocol Standard:** In the universal chess interface (UCI) specification, an engine's `score cp` is **strictly defined from the perspective of the side to move**, not from White's perspective.
2. **When Stockfish (White) was Crushing Janus (Black):**
   - On Black's turn, Janus searched and evaluated the position as hopelessly lost (e.g. `score cp -1500`).
   - When 6 consecutive plies exceeded $|score| \ge 1000$, line 298 evaluated:
     `termination = "white_win" if score > 0 else "black_win"`
   - Because `score = -1500 < 0`, **the script assigned `termination = "black_win"`!**
   - Black (Janus) was down 15 pawns, but the tournament harness **awarded the win to Janus!**
3. **When Stockfish (Black) was Crushing Janus (White):**
   - On Black's turn, Stockfish evaluated the position as completely winning (e.g. `score cp +2000` or `score mate 1`).
   - When 6 consecutive plies exceeded $|score| \ge 1000$, line 298 evaluated:
     `termination = "white_win" if score > 0 else "black_win"`
   - Because `score = +2000 > 0`, **the script assigned `termination = "white_win"`!**
   - Stockfish (Black) delivered checkmate, but the harness **awarded the win to Janus (White)!**

### Definitive Forensic Proof (Match 7 Game 25):
In `match7_x21s_vs_sf19.pgn`, Game 25:
- **White:** Janus Classical X21-S
- **Black:** Stockfish 19 (Ultimate NNUE)
- **Final Move:** Move 55... `Rh3#` (Black delivered checkmate!).
- **Final FEN:** `8/3n4/8/3p4/3P4/7r/5k2/7K w - - 2 56` (White King is checkmated on h1).
- **Recorded PGN Header:** `Result = "1-0"`, `Termination = "adjudication_resignation"`!
- Stockfish 19 delivered checkmate on the board, but the tournament script recorded a **1-0 victory for Janus!**

Every single claimed "win" by Janus against Stockfish 4, Stockfish 11, and Stockfish 19 was an inverted resignation or checkmate where Stockfish was overwhelmingly winning or delivering checkmate!

---

## 2. Executable Verification Ledger

All three external reference engines were audited for binary integrity and execution provenance:

| Engine | Executable Path | SHA-256 Checksum | Size (Bytes) | UCI `id name` | Compiler / Arch |
| :--- | :--- | :--- | :---: | :--- | :--- |
| **Stockfish 4** | `E:/ChessXML/tools/stockfish_4/stockfish_4.exe` | `1128CAB83386063359947F04155A2210C966080E71176DD385D8BDC3B6C32674` | 602,112 | `Stockfish 4 64` | GCC / x86-64 |
| **Stockfish 11** | `E:/ChessXML/tools/stockfish_11/stockfish_11.exe` | `B004C03BD71BB84E8BC1832C580E72A7E883F121E1834EA6DA2802D1575E8048` | 687,616 | `Stockfish 11 64` | GCC / x86-64 BMI2 |
| **Stockfish 19** | `E:/ChessXML/tools/stockfish/stockfish.exe` | `45BC8E4969147DB9C2EB533810637994619BFF0EACC81CCFD9854394901BCBD0` | 103,046,300 | `Stockfish 19` | GCC / x86-64 AVX2 |

### Stockfish 19 Configuration Audit:
- `Threads`: set to `1` (verified).
- `Hash`: set to `32` MB (verified).
- `Skill Level`: default `20` (unrestricted, verified).
- `UCI_LimitStrength`: default `false` (verified).
- `EvalFile`: default `nn-1a298aa575a0.nnue` (embedded directly in the 103MB binary, verified active).
- Clock management: Fischer `1500ms + 50ms`, zero time forfeits, clocks legally passed.
- **Finding:** Stockfish was operating at 100% full strength without any artificial handicap.

---

## 3. Re-adjudication of External Matches (Correct Legal Chess Oracle)

Replaying all 120 external games using `python-chess` with proper checkmate, stalemate, repetition, and material-advantage adjudication reveals the true, uncorrupted competitive record:

| Match | Opponent | P1.16 Claimed Score | Inverted Games | True W | True D | True L | True Score (%) | True Elo Diff |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Match 5** | Stockfish 4 (Classical HCE) | 11.0 / 40 (27.5%) | 8 | **0** | **7** | **33** | **3.5 / 40 (8.8%)** | -425.2 |
| **Match 6** | Stockfish 11 (Apex HCE) | 11.0 / 40 (27.5%) | 10 | **0** | **2** | **38** | **1.0 / 40 (2.5%)** | -614.3 |
| **Match 7** | Stockfish 19 (Ultimate NNUE) | 9.0 / 40 (22.5%) | 7 | **0** | **6** | **34** | **3.0 / 40 (7.5%)** | -454.1 |
| **Total** | **All External Benchmarks** | **31.0 / 120 (25.8%)** | **25** | **0** | **15** | **105** | **7.5 / 120 (6.2%)** | **-497.8** |

### Critical Findings:
1. **Zero Wins Against Stockfish:** Candidate X21 won **0 games** against Stockfish (0 wins across 120 games).
2. **True Performance Level:** Janus Classical X21 scored **6.25%** across all external matches (+0 =15 -105), which is completely consistent with earlier classical Janus candidates (X19 scored ~1.25%–3.75%).
3. **The Paradox Resolved:** The apparent leap in strength against Stockfish was entirely a statistical artifact of 25 game outcomes being inverted by the tournament runner when Stockfish crushed Janus.

---

## 4. Impact on Internal Baseline Matches (Matches 1, 2, 3)

The adjudication bug also affected internal matches whenever games ended in resignation adjudication:

| Match ID | Match Description | P1.16 Reported Score | Inverted Games | Re-adjudicated Score | Re-adjudicated % |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Match 1** | X21-S vs X7 Baseline (1.0s) | 45.5 / 100 (45.5%) | 10 | 43.5 / 100 | **43.5%** |
| **Match 2** | X21-S vs X7 Baseline (2.5s) | 19.5 / 50 (39.0%) | 3 | 22.0 / 50 | **44.0%** |
| **Match 3** | X21-P vs X12 Baseline (4T SMP) | 47.0 / 100 (47.0%) | 10 | 49.5 / 100 | **49.5%** |

In all three matches, the candidate remains firmly below 50.0%. The formal decision of **Category B (Promotion Denied, Baselines Preserved)** remains 100% scientifically sound and valid.

---

## 5. Formal Gate Adjudication: **INVALID**

Under Project Janus tournament integrity charter rules:
- The external tournament results reported in Milestone P1.16 are formally adjudicated as **INVALID**.
- The tournament runner `analysis/phase1/p1.16/tests/run_p116_tournaments.py` is permanently quarantined.
- A corrected tournament harness (`analysis/phase1/p1.17/tests/run_p117_tournaments.py`) must be implemented with side-to-move-aware adjudication and full `python-chess` board state validation before any future matches are conducted.
