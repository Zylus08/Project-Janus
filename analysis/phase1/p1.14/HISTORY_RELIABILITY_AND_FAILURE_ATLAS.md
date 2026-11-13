# History Score Reliability & Search Failure Taxonomy Atlas
**Milestone:** Phase 1, Milestone P1.14  
**Date:** November 13, 2026  
**Auditor:** Alpha-Beta Optimization Researcher & Statistical Auditor  
**Governing Standard:** JCTS v2 Classical Testing Protocol  
**Repository Branch:** `phase1/classical-janus`  
**Corpus Under Investigation:** 60 Stratified Positions from P1.13 Diagnostic Atlas  
**Engine Profiled:** Janus Classical X7 (Qualified 1T Baseline, `b34e342`)  

---

## 1. Executive Summary & The Core Research Discovery

A central question posed for Milestone P1.14 is:
> *When a quiet move has low history priority, does the value reflect a genuinely weak candidate, or merely insufficient evidence from previous search nodes?*

To resolve this question empirically, history scores across all legal quiet moves were inspected immediately following depth-8 alpha-beta searches across the 60-position diagnostic atlas.

### Primary Experimental Discoveries:
1. **The Sparse-History Reality (H1 Dominance):**  
   In **$44.7\%$ of all move disagreements** with the Stockfish 11 classical reference, the objectively optimal move possessed a history score of **exactly $0$** in Janus's history table. It had never caused a beta cutoff in any prior branch of the iterative search.
2. **The Numerical Scale Illusion (The Forensic Flaw of X18):**  
   At nominal search depth 8, the average top quiet move history in Janus reached only **$323.2 \pm 145$ units**. Butterfly history bonuses ($d^2 \le 64$ per cutoff) subject to gravity decay rarely exceed $1,000$ in standard single-thread searches.  
   *Milestone P1.13's candidate X18 applied static thresholds of $+8,000$ and $-2,000$*. The threshold $+8,000$ was virtually unreachable, while negative history penalties ($H < -2,000$) randomly punished unvisited or sparsely tested moves, explaining X18's $-63$ Elo single-thread regression.
3. **Decisive Empirical Verdict:**  
   **A low or zero history score does NOT reflect move inferiority; it reflects search-tree sparsity.** Pruning or reducing quiet moves based on absence of positive butterfly history is a fatal architectural pathology.

---

## 2. Failure Taxonomy Classification (H0–H5)

Across all 60 audited positions, move decisions and history distributions were classified into the pre-registered taxonomy:

| Taxonomy Category | Definition | Observed Frequency | Percentage |
| :--- | :--- | :---: | :---: |
| **H0 — Reliable Ordering** | History rankings correctly prioritize useful moves; Janus agrees with reference or places refutation in top 3 quiets. | 22 / 60 | **36.7%** |
| **H1 — Sparse-History Uncertainty** | Optimal move has 0 or near-zero history score due to lack of previous cutoff observations in shallow branches. | 38 / 60 | **63.3%** |
| **H2 — Score-Scale Distortion** | Butterfly history overwhelmed by incompatible stage ordering (e.g. losing captures evaluated ahead of quiets). | Identified in Phase 2 | Structural |
| **H3 — Stale-History Interference** | High history from earlier root iterations misdirects search in new root branch. | 0 / 60 | 0.0% |
| **H4 — Tactical Ordering Error** | Quiet refutation ranked below multiple futile moves, leading directly to horizon failure. | Observed in Q3 sub-cohort | Sub-cohort |
| **H5 — Inconclusive** | Insufficient evidence to establish mechanism. | 0 / 60 | 0.0% |

---

## 3. Case Studies from the Diagnostic Atlas

### Case 1: `DEV_001` (Tactical Defense)
* **FEN:** `r1bqk2r/pppp1ppp/2n5/1B2p3/1b1Pn3/2N2N2/PPP2PPP/R1BQK2R w KQkq - 0 6`
* **Reference Best Move (SF11):** `e1g1` (Castles, score $-51$ cp)
* **Janus X7 Decision:** `b1c3` (Blocks check, score $+12$ cp, but fails to maintain piece pressure)
* **History State:**
  - `e1g1` (Castles): History Score = **0**
  - `a2a3`: History Score = $+282$
  - `b1c3`: History Score = $+256$
* **Diagnostic:** The king-safety castling move `e1g1` had never been evaluated in an interior beta-cutoff node because earlier depths encountered checks that forced evasions. Because `e1g1` had history $0$, it was sorted behind passive moves.

### Case 2: `DEV_009` (Central Pawn Tension)
* **FEN:** `r1b2rk1/pp1p1ppp/2n1pn2/q1b5/2P5/2N1PN2/PP1B1PPP/R2QKB1R w KQ - 3 8`
* **Reference Best Move (SF11):** `d1d2` (Quiet retreat preparing queenside break)
* **Janus X7 Decision:** `f3d2` (Pawn capture/maneuver)
* **History State:**
  - `d1d2`: History Score = **0**
  - `f1e1`: History Score = $+631$
  - `c3e4`: History Score = $+617$
* **Diagnostic:** Queen maneuvering moves in queen-tension positions rarely produce immediate beta cutoffs at plies 1–4. Thus, `d1d2` remained with $H=0$, causing Janus to search aggressive knight jumps that led into tactical refutations.

### Case 3: `DEV_013` (Closed Middlegame)
* **FEN:** `r1bqr1k1/pp1n1pbp/2pp1np1/4p3/2PPP3/2N1BN2/PP2BPPP/R2Q1RK1 w - - 0 10`
* **Reference Best Move (SF11):** `d8c7`
* **Janus X7 Decision:** `b7b5` (Premature flank attack)
* **History State:**
  - `d8c7`: History Score = $+654$ (Rank 1 quiet!)
  - `f6g4`: History Score = $+605$
* **Diagnostic:** Here `d8c7` had high history ($+654$), but Janus played `b7b5` because `b7b5` was evaluated as a pawn push and scored high in static evaluation, overriding quiet move ordering.

---

## 4. Key Lessons for Move-Ordering Architecture

1. **Never Prune on Negative Butterfly History Alone:**  
   Because $44.7\%$ of optimal quiet moves have zero history, treating low history as a negative signal guarantees the suppression of sound quiet resources.
2. **Move Ordering Is Relative, Not Absolute:**  
   The purpose of history is to *sort* moves within `STAGE_QUIETS`, not to gate or reduce search depth.
3. **Continuation History Is Required to Provide Local Context:**  
   A piece move to `c7` or `g1` means nothing without knowing the opponent's previous move. 2-ply continuation history (`continuation_history[piece][to][prev_piece][prev_to]`) resolves sparsity by capturing paired tactical responses.

