# Project Janus v0.51.1 — Game Termination Forensics & FIDE Adjudication Audit

## 1. Overview & Verification Scope

The v0.51 match report categorized all 200 game outcomes into four termination types:
- 96 White checkmates
- 86 Black checkmates
- 9 fivefold repetitions
- 9 "150-ply horizon" draws

Every game was independently audited against the FIDE Laws of Chess using `python-chess`. The comprehensive record is saved in [`analysis/v0.51.1/raw/termination_audit.csv`](file:///e:/ChessXML/project-janus/analysis/v0.51.1/raw/termination_audit.csv).

---

## 2. Checkmate Adjudication Verification (182 Games)

For all 182 purported checkmate games:
1. The final board state was tested with `board.is_checkmate()`.
2. The side to move was confirmed to be in check with zero legal evasions.
3. The winner declared in the PGN header was verified against the mating side.

**Audit Findings:**
- **White Checkmates:** Exactly **96 / 96 (100.0%)** verified as true FIDE checkmates.
- **Black Checkmates:** Exactly **86 / 86 (100.0%)** verified as true FIDE checkmates.
- **False Checkmates / Resignation Anomalies:** **Zero.** Every single win in the match was decided on the physical board by checkmate.

---

## 3. Fivefold Repetition Adjudication (9 Games)

Under FIDE Article 9.6.1, a game is drawn automatically if a position has occurred at least five times, without requiring a claim by either player.

Replay analysis of the 9 games labeled `draw_fivefold_repetition` confirmed:
- Games 67, 72, 87, 107, 114, 124, 134, 141, and 167 all reached identical board state hashes (including side to move, castling rights, and en passant availability) $\ge 5$ times.
- In each case, `board.is_fivefold_repetition()` returned `True`.
- **Classification:** **Class A — Valid Automatic FIDE Draw.**

---

## 4. The 150-Ply Adjudication Forensics

### 4.1 Problem Statement
A common ambiguity in chess engine testing is the distinction between:
- **Game Plies:** Total half-moves played in the game from move 1 (e.g. 150 plies = 75 full moves).
- **Halfmove Clock (`halfmove_clock`):** Number of half-moves since the last pawn move or capture, governing the FIDE 50-move and 75-move rules.

The v0.51 report classified 9 games as `draw_max_plies_horizon`. The audit investigated whether these 9 games represented valid FIDE draws or an artificial tournament controller ceiling.

### 4.2 Forensic Ledger of the 9 Horizon Games

| Game ID | Pair ID | Opening ID | N2 Role | Final Plies | Final `halfmove_clock` | Last Pawn/Cap Ply | Plies Since Reset | `can_claim_50` | `is_75_moves` | Material Imbalance at Ply 150 | Audit Classification |
|:---:|:---:|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|:---:|
| **18** | 9 | `v043_p09_petrov` | Black | 150 | **53** | 97 | 53 | False | False | K0 $+1400\text{ cp}$ vs N2 Bare King | **Class C** |
| **21** | 11 | `v043_p11_sicilian_kan` | White | 150 | **22** | 128 | 22 | False | False | K0 $+1800\text{ cp}$ vs N2 Bare King | **Class C** |
| **73** | 37 | `v043_p37_queens_indian` | White | 150 | **1** | 149 | 1 | False | False | N2 $+630\text{ cp}$ vs K0 Bare King | **Class C** |
| **88** | 44 | `gruenfeld_defense` | Black | 150 | **2** | 148 | 2 | False | False | N2 $+1070\text{ cp}$ vs K0 $K+B$ | **Class C** |
| **121** | 61 | `sicilian_dragon` | White | 150 | **1** | 149 | 1 | False | False | N2 $+2000\text{ cp}$ vs K0 Bare King | **Class C** |
| **123** | 62 | `sicilian_accelerated_dragon` | White | 150 | **28** | 122 | 28 | False | False | K0 $+900\text{ cp}$ vs N2 Bare King | **Class C** |
| **133** | 67 | `caro_kann_tartakower` | White | 150 | **32** | 118 | 32 | False | False | N2 $+720\text{ cp}$ vs K0 Rook | **Class C** |
| **148** | 74 | `english_four_knights` | Black | 150 | **0** | 150 | 0 | False | False | N2 $+1920\text{ cp}$ vs K0 Bare King | **Class C** |
| **186** | 93 | `bogo_indian_nimzowitsch` | Black | 150 | **8** | 142 | 8 | False | False | K0 $+420\text{ cp}$ (Endgame) | **Class C** |

### 4.3 Root Cause Analysis & Protocol Divergence
1. **Source Code Location:**
   In `analysis/v0.51/tests/run_preregistered_match.py`:
   - Line 108: `max_plies: int = 150`
   - Lines 136–194: Loop terminates unconditionally after 150 plies.
   - Lines 195–203:
     ```python
     if result_str == "*":
         outcome = board.outcome(claim_draw=True)
         if outcome:
             result_str = outcome.result()
             termination = f"draw_{outcome.termination.name.lower()}"
         else:
             result_str = "1/2-1/2"
             termination = "draw_max_plies_horizon"
     ```
2. **Protocol Discrepancy:**
   In `analysis/v0.51/MATCH_PREREGISTRATION.md` Section 4.6, the preregistered text stated:
   > *"Move Horizon Adjudication: If a game reaches 200 plies (100 moves) without checkmate or material advantage $> 500$ cp, adjudicated as draw."*

   The tournament runner used **150 plies** instead of 200 plies, and did not evaluate the $> 500\text{ cp}$ material clause before assigning a draw.
3. **FIDE Non-Equivalence:**
   None of these 9 games satisfied FIDE Article 9.2 (50-move claim) or Article 9.6.2 (75-move mandatory draw). Their `halfmove_clock` ranged from 0 to 53.

### 4.4 Material Bias & Counterfactual Impact
Did truncating these games at 150 plies artificially inflate N2's score?
- **In 5 of the 9 games (Games 73, 88, 121, 133, 148):** N2 held an overwhelming material advantage ($+630\text{ cp}$ to $+2000\text{ cp}$) with K0 reduced to a bare king or minor piece. Truncation **cost N2 five potential wins**, awarding K0 an unearned half-point in each game.
- **In 3 of the 9 games (Games 18, 21, 123):** K0 had a massive material advantage against N2's bare king, but K0's shallow search depth (Depth 2–3) was unable to coordinate checkmate against N2's evasion moves within 50+ plies.
- **In 1 game (Game 186):** K0 was up a minor exchange in an endgame.

As proven in the statistical sensitivity analysis (Phase 3), whether these 9 games are excluded entirely ($96.43\%$ score) or awarded 100% to K0 ($91.75\%$ score), **N2 remains decisively superior with $p < 10^{-40}$**.

---

## 5. Gate 2 Finding

**Gate 2 Status: PASSED WITH FORMAL CORRECTION.**  
- 182 / 182 checkmates are independently verified FIDE checkmates.
- 9 / 9 fivefold repetitions are independently verified FIDE Article 9.6.1 automatic draws.
- The 9 "150-ply horizon" draws are formally classified as **Class C — Controller-Imposed Horizon Adjudications**, correcting the narrative that conflated game plies with FIDE move counters.
- The protocol discrepancy (150 plies vs preregistered 200 plies) is documented and proven to have zero material effect on the tournament outcome.
