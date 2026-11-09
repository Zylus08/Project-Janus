# PROJECT JANUS — PHASE 1, MILESTONE P1.0
## Classical Evaluation Gap Analysis: Handcrafted Terms vs. Stockfish 19

**Status:** COMPLETE & AUDITED  
**Date:** 2026-11-09  
**Auditor / Principal Engineer:** Principal Computer Chess Engineer & Systems Architect  
**Corpus:** Standard 50-Position Evaluation Suite ([`corpus/standard_50_evaluation_suite.json`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.0/corpus/standard_50_evaluation_suite.json))  
**Raw Test Telemetry:** [`raw/classical_evaluation_gap_raw.json`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.0/raw/classical_evaluation_gap_raw.json)  
**Evaluator Audited:** Janus Classical C1 Native (`NativeEngine::evaluate()`, C++17)  
**Reference Engine:** Stockfish 19 (Unrestricted NNUE Evaluator, Single Thread, 64 MB TT)  

---

## 1. Executive Summary

Janus Classical Baseline C1 relies entirely on an elementary handcrafted evaluation function composed of:
1. **Material Values:** Standard piece weights ($P=100, N=320, B=330, R=500, Q=900, K=20000$).
2. **Piece-Square Tables (PST):** Static $8 \times 8$ positional bonuses interpolated linearly across game phase ($0 \le \text{phase} \le 24$).
3. **Castling Bonus:** A static flat bonus of $+15\text{ cp}$ if castled.

**Every other classical chess evaluation feature is completely absent.**

When benchmarked across the 50 standardized diagnostic positions against Stockfish 19, the average evaluation error is **132.48 cp**, with catastrophic errors exceeding **288 cp** in king attack positions and **184 cp** in closed structures.

```
+----------------------------------------------------------------------------------------------------+
|                                EVALUATION ERROR BY CHESS REGIME                                    |
+----------------------+---------------------------+-------------------------------------------------+
| Category             | Mean Absolute Error vs SF | Primary Evaluative Blindspot                     |
+----------------------+---------------------------+-------------------------------------------------+
| King Attack (KATK)   | 288.00 cp                 | Zero king shelter, open file, or attacking terms |
| Defensive / Mate     | 233.60 cp                 | Inability to measure king zone vulnerability    |
| Closed Structures    | 184.00 cp                 | Zero pawn chain, blockade, or outpost awareness |
| Endgame (ENDG)       | 169.20 cp                 | Zero passed pawn distance or opposition terms   |
| Tactical Scenarios   |  95.40 cp                 | Over-reliance on brute-force qsearch resolution |
| Candidate Decisions  |  37.00 cp                 | Superficial static piece-placement preference   |
| Open Games           |  35.80 cp                 | Lack of open-file and rook-on-7th bonuses       |
| Quiet Positional     |  17.20 cp                 | Coincidental balance of material and basic PST  |
+----------------------+---------------------------+-------------------------------------------------+
| OVERALL AVERAGE      | 132.48 cp                 | Missing ~12 major classical evaluation families |
+----------------------+---------------------------+-------------------------------------------------+
```

---

## 2. Granular Gap Decomposition: The Missing Evaluation Families

In classical computer chess (pre-NNUE Stockfish 11/12, Crafty, Fruit, Rebel), strong handcrafted evaluation consists of approximately 12–15 distinct evaluation terms. C1 implements only **2 of them** (Material and PST).

### 2.1 Missing Family 1: Mobility & Piece Activity
- **Stockfish Classical Approach:** Counts the number of safe destination squares (squares not attacked by enemy pawns or defended pieces) for Knights, Bishops, Rooks, and Queens. A piece with restricted mobility incurs severe penalties.
- **Janus C1 Status:** **Completely Absent (0% implemented).** A bishop trapped behind its own locked pawns (`CLSD_04`) receives the exact same PST score as an active bishop dominating open diagonals.

### 2.2 Missing Family 2: Pawn Structure Nuances
- **Stockfish Classical Approach:**
  - *Passed Pawns:* Evaluates passed pawns based on rank, whether they are protected by another pawn, whether they are outside or connected, and distance from the kings.
  - *Pawn Weaknesses:* Penalties for doubled pawns (stacked on same file), isolated pawns (no friendly pawns on adjacent files), backward pawns, and over-advanced pawn chains.
- **Janus C1 Status:** **Completely Absent (0% implemented).** C1 treats an isolated doubled backward pawn on rank 2 identically to a connected passed pawn on rank 6, distinguishing them solely by their static rank bonus in the PST.

### 2.3 Missing Family 3: King Safety & Shelter
- **Stockfish Classical Approach:**
  - Evaluates the pawn shield in front of the castled king (e.g., $f2/g2/h2$ or $f7/g7/h7$). Penalizes missing shield pawns or advanced pawns (e.g., $h3$ creating a hook).
  - Calculates King Attack Units: weights attacking enemy pieces (Knight = 2, Bishop = 2, Rook = 3, Queen = 5) and multiplies by the number of attacks against squares in the $3 \times 3$ king zone.
  - Evaluates open and semi-open files directed at the enemy king.
- **Janus C1 Status:** **Completely Absent.** C1 only awards $+15\text{ cp}$ if the king has executed the castling move. If the pawns in front of the king are completely obliterated, C1 still awards the full $+15\text{ cp}$ castling bonus!

### 2.4 Missing Family 4: Piece Coordination & Combinations
- **Bishop Pair Bonus:** In open and semi-open positions, holding both bishops yields a proven statistical advantage of $+35\text{ to }+50\text{ cp}$. C1 has zero bishop pair bonus.
- **Rooks on Open & Semi-Open Files:** Placing a rook on an open file ($+20\text{ cp}$) or semi-open file ($+10\text{ cp}$), or doubled on the 7th rank ($+40\text{ cp}$). C1 has zero file-occupancy terms.
- **Knight Outposts:** Knights anchored on ranks 4, 5, or 6 that are defended by a friendly pawn and cannot be driven away by an enemy pawn. C1 has zero outpost terms.

### 2.5 Missing Family 5: Endgame Specialized Knowledge
- **King Centralization:** As game phase approaches endgame, the king must activate and march toward the center or toward passed pawns. C1 has a static king endgame PST, but lacks dynamic proximity terms.
- **Rook Behind Passed Pawn (Tarrasch Rule):** Positioning rooks behind friendly or enemy passed pawns. C1 has zero terms.
- **Unstoppable Passed Pawn Detection / Rule of the Square:** Knowing when a pawn cannot be caught by the opposing king without searching 12 plies. C1 has zero terms.

---

## 3. The Static-to-Search Evaluation Shift

In `raw/classical_evaluation_gap_raw.json`, we analyzed the shift between C1's static evaluation (`NativeEngine::evaluate()`) and its final search evaluation (`score_cp` after Depth 7 alpha-beta):

$$\Delta_{\text{shift}} = |\text{Score}_{\text{search}} - \text{Score}_{\text{static}}|$$

### Findings:
1. **Defensive / Tactical Positions:** The average shift is **5,738.8 cp** in mating positions and **28.0 cp** in tactical positions. C1's static evaluation has zero horizon perception; it relies entirely on the search tree to realize that a king is in mortal danger.
2. **Quiet & Closed Positions:** The average shift is tiny (**6.0 cp to 7.0 cp**). Because C1's search tree does not understand pawn structure or mobility, depth 7 search does not alter the static assessment. The engine remains blissfully ignorant of its strategic deterioration.

---

## 4. Evaluation Performance vs. Expressiveness Trade-Off

In Milestone P1.0 profiling:
- **C1 Static Evaluation Speed:** **104.2 nanoseconds per evaluation** (approximately 9.6 million raw evaluations per second on a single thread).
- **CPU Time Share:** Static evaluation consumed only **7.4% of total search CPU time** ($406.2\text{ ms}$ out of $5,499.7\text{ ms}$), whereas move generation consumed **84.3%**.

### Strategic Implication:
C1's evaluation is ultra-fast, but that speed is largely wasted because the search engine is choked by move generation and tree explosion. 
We can afford to enrich the handcrafted evaluation function with:
- Bitboard-based pawn structure tables (passed pawns, isolated pawns, pawn chains),
- King safety zone counters,
- Mobility calculations via magic bitboards,
- Bishop pair and outpost terms.

Adding these terms will increase static evaluation time from $\sim 104\text{ ns}$ to $\sim 250\text{ ns}$, which is still well within the acceptable budget (under 15% of search time) while dramatically improving move choice and tree pruning.

---

## 5. Compliance with Project Janus Rule 1

> [!IMPORTANT] Pure Classical Supremacy Architecture
> In strict compliance with **Rule 1 (Strictly Non-ML)**, the Phase 1 Classical evaluation modernization will **not** incorporate:
> - Neural networks or NNUE inference,
> - Learned weight matrices or tensor runtimes,
> - Reinforcement learning or self-play policy networks.
> 
> Instead, Project Janus will engineer an advanced **Handcrafted Classical Evaluation (HCE)** engine. Parameters will be tuned using the classical **Texel's Tuning Method** (logistic regression over millions of quiet positions from historical grandmaster play and classical engine games), preserving full transparency, determinism, and pure algorithmic supremacy.

