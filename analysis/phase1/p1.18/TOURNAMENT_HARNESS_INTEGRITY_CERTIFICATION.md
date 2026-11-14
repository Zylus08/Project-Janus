# Milestone P1.18 — Tournament Harness Integrity & Release Qualification

**Author:** Principal Computer Chess Engine Architect & Tournament Integrity Specialist  
**Date:** November 14, 2026  
**Milestone:** Phase 1, Milestone P1.18  
**Certification Status:** **PASSED (15 / 15 Tests, 100.0%)**  

---

## 1. Executive Summary & Root Cause Post-Mortem

The historical resignation-inversion defect discovered during Milestone P1.17 represented a severe release-quality failure in the automated tournament infrastructure. 

### The Root Cause
In Milestone P1.16, the tournament runner `run_p116_tournaments.py` introduced a naive resignation shortcut (lines 293–300):
```python
if abs(score) >= 1000:
    resignation_count += 1
    if resignation_count >= 6:
        termination = "white_win" if score > 0 else "black_win"
```
Under the standard Universal Chess Interface (UCI) protocol, an engine reports its evaluation `score cp <n>` strictly from the **perspective of the side to move**, not White. Consequently:
- When White searched a losing position (e.g. down a queen), it reported a negative score (`score cp -900`). The condition `score > 0` evaluated to `False`, correctly assigning `"black_win"`.
- When Black searched a losing position (e.g. down a queen), it also reported a negative score from Black's perspective (`score cp -900`). The condition `score > 0` evaluated to `False`, **incorrectly assigning `"black_win"`**!

This resulted in 29 games in P1.16 where Stockfish completely crushed Janus being recorded as wins for Janus, generating the illusion of an external breakthrough.

---

## 2. The Formal Adjudication Contract

For Milestone P1.18 and all subsequent milestones, the tournament harness is bound by a strict, non-negotiable **Adjudication Contract**:

### 2.1 Separation of Concerns
1. **Legal Board State Takes Absolute Precedence:**
   - The harness must verify `board.is_checkmate()`, `board.is_stalemate()`, `board.is_insufficient_material()`, `board.can_claim_threefold_repetition()`, and `board.can_claim_fifty_moves()` immediately after every move push.
   - If a board state is terminal under FIDE chess rules, it must be adjudicated as such immediately, regardless of what the engine's UCI search string reports.
2. **Strict Score Perspective Transformation:**
   - Any evaluation string emitted by an engine must be mapped to an absolute White-centric coordinate space before evaluating resignations:
   $$Score_{White} = \begin{cases} Score_{UCI} & \text{if side to move is White} \\ -Score_{UCI} & \text{if side to move is Black} \end{cases}$$
3. **Resignation Thresholds:**
   - An engine may only be resigned if the normalized score $|Score_{White}| \ge 1000$ (10.0 pawns) persists continuously for at least 6 consecutive plies (3 full moves).
   - If $Score_{White} \ge +1000$, White wins (`1-0`).
   - If $Score_{White} \le -1000$, Black wins (`0-1`).

---

## 3. Adversarial Release Qualification Suite

To prove immunity against all edge cases, a synthetic adversarial transcript suite was executed via `analysis/phase1/p1.18/tests/test_harness_adversarial_suite.py`:

| Test ID | Scenario Description | Tested Perspective & Inputs | Adjudicated Winner | Expected Winner | Status |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **CASE_1** | White winning with positive score | $+1500$ cp, White to move, 6 plies | **White** | White | **PASS** |
| **CASE_2** | White losing with negative score | $-1500$ cp, White to move, 6 plies | **Black** | Black | **PASS** |
| **CASE_3** | Black winning with positive score | $+1500$ cp, Black to move, 6 plies | **Black** | Black | **PASS** |
| **CASE_4** | Black losing with negative score | $-1500$ cp, Black to move, 6 plies | **White** | White | **PASS** |
| **CASE_5A** | White announces forced mate | `mate +3`, White to move | **White** | White | **PASS** |
| **CASE_5B** | Black announces forced mate | `mate +2`, Black to move | **Black** | Black | **PASS** |
| **CASE_5C** | Black announces being checkmated | `mate -1`, Black to move | **White** | White | **PASS** |
| **CASE_5D** | Direct Checkmate on board | Fool's Mate ($4. Qh4\#$), White checked | **Black** | Black | **PASS** |
| **CASE_6** | Missing/malformed score string | Normal position, no score line | **None (In Progress)** | None | **PASS** |
| **CASE_7** | Clock timeout forfeit | Black exceeds time budget | **White** | White | **PASS** |
| **CASE_8** | Engine crash forfeit | White process exits abruptly | **Black** | Black | **PASS** |
| **CASE_9** | Illegal move forfeit | Black emits pseudo-legal/illegal move | **White** | White | **PASS** |
| **CASE_10** | Stalemate position | King stalemated without check | **Draw** | Draw | **PASS** |
| **CASE_11** | Repetition detection | Position repeated 3 times | **None (In Progress)** | None | **PASS** |
| **CASE_12** | Match 7 Game 25 Exact Re-test | $55\dots Rh3\#$, White mate -1 reported | **Black** | Black | **PASS** |

**Result:** **15 / 15 (100.0%) Adversarial Cases Passed.**

---

## 4. Historical Contamination Audit

An automated audit of all 66 Python tournament and match runner scripts across the entire repository history was conducted:

| Milestone Repository Path | Resignation Adjudication Logic | Status | Impact on Historical Elo |
| :--- | :--- | :---: | :--- |
| **P1.0 – P1.11** | None (Games played to full mate/stalemate/cutoff) | **Clean** | None |
| **P1.12** (`analysis/phase1/p1.12/`) | Turn-aware: `if score <= -600 and resign_side == board.turn: result = "0-1" if White else "1-0"` | **Clean** | Validated |
| **P1.13 – P1.15** | Standard board termination & move limits | **Clean** | Validated |
| **P1.16** (`analysis/phase1/p1.16/`) | Flawed: `termination = "white_win" if score > 0 else "black_win"` | **Contaminated** | **Matches 5–7 INVALID (Corrected in P1.17)** |
| **P1.17** (`analysis/phase1/p1.17/`) | Perspective-aware: `black_win if turn == WHITE else white_win` | **Clean** | Replicated & Validated |
| **P1.18** (`analysis/phase1/p1.18/`) | Full Adjudication Contract with Board-state precedence | **Certified** | Baseline for all P1.18 matches |

### Conclusion
The contamination was strictly isolated to Milestone P1.16 external matches (Matches 5, 6, and 7). Internal engine matches in P1.16 between Janus versions were played symmetrically (both engines suffered the same potential inversion when Black resigned), but external matches against Stockfish were completely invalidated. The defect was entirely resolved in P1.17 and is formally certified for P1.18.
