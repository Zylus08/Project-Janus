# Milestone P1.19 Phase 7: King-File Exposure Regression Forensics

**Date:** November 14, 2026  
**Status:** Forensic Audit & Disqualification  
**Branch:** `phase1/classical-janus`  
**Evaluated Feature:** P1.18 Track B (Open & Semi-Open File King Exposure Penalty)  
**Historical Match Comparator:** Match Dev-3 (20 Games @ 0.5s + 20ms Fischer)  
**Empirical Result:** 7.5 / 20 ($37.5\%$), CI: $[17.8\%, 57.2\%]$, $p = 0.8936$, Elo $-88.7$

---

## 1. Executive Summary & Diagnostic Statement

Milestone P1.18 introduced **Track B: Open & Semi-Open File King Exposure Penalty** alongside Track A (Backward Pawns) in an effort to penalize heavy enemy pieces (rooks and queens) operating on files facing or flanking the friendly castled king. However, development ablations and authoritative tournaments demonstrated that Track B produced a catastrophic **$-88.7$ Elo regression** in isolated play ($37.5\%$, Match Dev-3) and dragged the joint Candidate X23 down to $44.0\text{--}49.0\%$ against frozen baselines X7 and X12.

Phase 7 executes a rigorous game-by-game forensic analysis of the Match Dev-3 failure modes, definitively documenting why handcrafted static file exposure penalties fail in classical computer chess and formalizing the rationale for its complete excision from Candidate X24.

---

## 2. Statistical Reconstruction of the Track B Regression

| Match Identifier | Architecture Tested | Opponent | Games | Score | Win Rate (%) | 95% Confidence Interval | One-Sided $p$-value | Implied Elo Delta |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Match Dev-1** | Joint X23 (Track A + Track B) | Reference X22-S | 20 | 7.0 / 20 | $35.0\%$ | $[14.1\%, 55.9\%]$ | $0.9201$ | **$-107.5$** |
| **Match Dev-2** | Track A Alone (BP=1, KFE=0) | Reference X22-S | 20 | 10.5 / 20 | $52.5\%$ | $[41.1\%, 63.9\%]$ | $0.3341$ | **$+17.4$** |
| **Match Dev-3** | **Track B Alone (BP=0, KFE=1)** | **Reference X22-S** | **20** | **7.5 / 20** | **$37.5\%$** | **$[17.8\%, 57.2\%]$** | **$0.8936$** | **$-88.7$** |

### Statistical Implication
The $+17.4$ Elo positive exploratory signal delivered by isolated Track A was completely overwhelmed by the $-88.7$ Elo collapse induced by Track B, explaining why Candidate X23 suffered an overall regression against Qualified Baselines X7 and X12.

---

## 3. Four Major Failure Modes of Track B

Through forensic review of game records and search trees from Match Dev-3, four fundamental failure mechanisms were identified:

### 3.1 Premature Defensive Shield Pushes (Self-Inflicted King Destruction)
- **Mechanism:** In positions where an opponent shifted a rook or queen to a semi-open file (e.g. Black rook to the c-file facing White's king castled queenside, or Black queen to the e-file), Track B applied an immediate static penalty of $-25\text{ to } -40\text{ mg}$.
- **Consequence:** To extinguish this penalty, the engine consistently prioritized pushing friendly pawns in front of its king (e.g. `c2-c3`, `f2-f3`, or `g2-g3`) solely to close the file.
- **Pathology:** Pushing shield pawns voluntarily fractured the friendly king's pawn shelter, weakened dark/light square complexes, and handed the opponent uncontested outposts on the adjacent files. In games 4, 9, and 17, these self-inflicted pawn pushes directly enabled decisive opponent breakthroughs.

### 3.2 Artificial Suppression of Sharp Counterplay
- **Mechanism:** Modern classical chess engines defend king-flank pressure dynamically—by generating active counterplay in the center or opposite wing.
- **Consequence:** Track B's static penalty acted as an unconditional tax on any opening line or sharp middlegame where a file was temporarily opened.
- **Pathology:** When alpha-beta explored sharp variations requiring tactical pawn sacrifices to open central files while accepting temporary king-file exposure, Track B depressed the static evaluation below $\alpha$. The engine systematically rejected winning tactical combinations in favor of passive, crouching defenses.

### 3.3 Blindness to Interposition & Dynamic Piece Defenses
- **Mechanism:** Track B evaluated king safety using pure bitboard piece occupancies:
  $$\text{Exposure} \propto (\text{Enemy Heavies on File}) \land \neg(\text{Friendly Pawns on File})$$
- **Consequence:** It completely ignored whether friendly minor pieces (knights and bishops) or friendly rooks physically controlled or blocked the file.
- **Pathology:** A file occupied by an enemy rook was penalized $-40\text{ mg}$ even when a friendly knight stood firmly on rank 3 completely sealing the file from infiltration. The engine panicked over phantom threats that were tactically neutralized.

### 3.4 Search Horizon Instability & Aspiration Researches
- **Mechanism:** Because open/semi-open files fluctuate as rooks traverse the back rank, static evaluation swings of $40\text{--}80\text{ cp}$ frequently occurred between root moves.
- **Consequence:** This volatility caused frequent aspiration window failures, triggering costly search researches and wasting search depth on non-tactical root oscillations.

---

## 4. Formal Research Decision & Excision Directive

Track B (Open & Semi-Open File King Exposure) is classified as **qualitatively defective, search-incompatible, and Elo-regressive**.

### Architectural Directive for Candidate X24:
1. **Complete Deactivation:** Candidate X24 permanently disables king-file exposure (`g_use_king_file_exposure = 0`).
2. **Restoration of Classical King Safety:** Evaluation reverts strictly to the proven $E5$ classical king shelter model (missing pawn shield penalty and quadratic king-ring attacker scaling), preserving dynamic mobility and shelter integrity.
3. **Future Research Horizon:** Any future king safety enhancements must evaluate dynamic infiltration rays (checking unobstructed squares of entry and friendly interposition control) rather than static file occupancies.
