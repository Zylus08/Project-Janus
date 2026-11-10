# Project Janus — Phase 1, Milestone P1.5
## Classical Evaluation Refinements & Handcrafted Mathematical Formulations

**Author:** Principal Computer Chess Engineer, C++17 Performance Architect, Classical Chess Evaluation Researcher, Search-Time Optimization Specialist, and Statistical Experimental Auditor  
**Lineage:** Janus Classical X  
**Incumbent Baseline:** Janus Classical X7 (`b34e342`)  
**Proposed Candidate:** Janus Classical X10  
**Source Implementation:** `engine/classical_x/janus_classical_x.cpp`  
**Date:** November 2026  
**Governing Rule 1:** Strictly Non-ML (Zero neural networks, zero NNUE, zero learned weights, zero offline-fitted models)

---

### 1. Executive Summary & Design Principles

Milestone P1.5 delivers a major handcrafted overhaul of the Janus classical evaluation function, transitioning from X7's E5 evaluation to **Candidate X10's E10 evaluation architecture**.

All terms adhere strictly to non-ML computer chess engineering principles:
1. **Zero Learned Weights:** Every constant is manually chosen based on classical chess principles and validated through ablation.
2. **Computational Boundedness:** All operations execute via bitwise bitboard arithmetic, population counts (`popcount64`), and $O(1)$ lookups.
3. **Exact Color Symmetry:** Every term is evaluated symmetrically for White and Black via square mirroring (`sq ^ 56`) or color-relative ranks.
4. **Mate Score Invariance:** Evaluator output is bounded within $[-10000, +10000]$ cp, ensuring zero interference with mate distance detection ($> 25000$ cp).

---

### 2. Module E1' — Pawn Structure Refinement

The pawn structure module addresses five structural weaknesses identified in the Phase 2 Failure Atlas:

#### A. Candidate Passed Pawns
- **Definition:** A pawn that is not yet passed (enemy pawns exist on adjacent files ahead of it), but has no enemy pawn on its own file, and the count of friendly supporting pawns on adjacent files is $\ge$ the count of opposing enemy pawns:
  $$\text{FrontSpan}(f) \cap \text{Pawns}_{\text{enemy}} = \emptyset \quad \land \quad \text{popcount}(\text{AdjPawns}_{\text{friendly}}) \ge \text{popcount}(\text{AdjPawns}_{\text{enemy}})$$
- **Bonus:** Awarded $50\%$ of the corresponding passed pawn bonus for its current rank:
  $$\Delta_{\text{candidate}}(r) = \frac{\text{PASSED\_PAWN\_BONUS}[r]}{2}$$

#### B. Backward Pawns
- **Definition:** A pawn on square $s$ (rank $r$, file $f$) where:
  1. The immediate stop square $s_{\text{stop}} = s + 8$ (for White) is attacked by an enemy pawn.
  2. Zero friendly pawns exist on adjacent files at or behind rank $r$ to support its advance.
- **Penalty:** $-10$ MG / $-15$ EG.

#### C. Pawn Islands
- **Definition:** The number of disjoint contiguous file clusters occupied by friendly pawns:
  $$I = \text{CountDisjointClusters}(\text{OccupiedFiles})$$
- **Penalty:** $-8 \times (I - 1)$ MG / $-12 \times (I - 1)$ EG for each island beyond the initial cluster.

#### D. Connected & Supported Passed Pawns
- **Connected Passer:** Friendly pawn on adjacent file within $\pm 1$ rank $\implies +15$ MG / $+25$ EG.
- **Supported Passer:** Defended directly by friendly pawn attack ray $\implies +15$ MG / $+25$ EG.

---

### 3. Module E2' — King Safety Refinement

The king safety engine addresses the massive queenless evaluation pathologies discovered in Phase 2:

#### A. Queen Presence Scaling
- In X7, quadratic king attack danger was computed even when queens were exchanged, causing severe panic in symmetrical queenless positions (`POS_27`, `POS_28`).
- **X10 Formulation:** Let $Q_{\text{enemy}} = \text{popcount}(\text{Queens}_{\text{enemy}})$.
  $$\text{KingDanger} = \begin{cases} 0 & \text{if } Q_{\text{enemy}} == 0 \\ \min(200, 2 \times \text{AttackUnits}^2) \times \frac{Q_{\text{enemy}}}{2} & \text{if } Q_{\text{enemy}} > 0 \end{cases}$$
- **Pawn Shield Scaling:** Missing shield pawn penalty is scaled down from $-15$ MG to $-5$ MG when $Q_{\text{enemy}} == 0$, allowing the king to activate safely in endgames.

#### B. Enemy Pawn Storm Detection
- For castled kings on flank files ($kf \le 2$ or $kf \ge 5$), detects advancing enemy pawns on the 3 files surrounding the king:
  $$\Delta_{\text{storm}} = -8 \times (r_{\text{storm}} - 2) \quad \text{for } r_{\text{storm}} \ge 3$$

---

### 4. Module E3' — Piece Activity & True Outposts

#### A. True Knight Outposts (Immune to Pawn Kicks)
- **Problem in X7:** Knights on ranks 4–6 received full outpost bonuses even when an enemy pawn could immediately kick them (`POS_17`, `POS_18`).
- **X10 Formulation:** A knight square $s$ (rank $r$, file $f$) is a **True Immune Outpost** iff:
  1. It is defended by a friendly pawn: $\text{AttackRay}_{\text{pawn}}(s) \cap \text{Pawns}_{\text{friendly}} \neq \emptyset$.
  2. Zero enemy pawns can ever attack $s$: $\text{ForwardAdjacentSpan}(s) \cap \text{Pawns}_{\text{enemy}} = \emptyset$.
- **Bonuses:**
  - True Immune Outpost: **$+25$ MG / $+15$ EG**.
  - Defended but kickable outpost: **$+10$ MG / $+5$ EG**.

#### B. Color-Separated Bishop Pair
- Verifies that friendly bishops occupy both light and dark squares:
  $$\text{Bishops} \cap \text{LightSquares} \neq \emptyset \quad \land \quad \text{Bishops} \cap \text{DarkSquares} \neq \emptyset \implies \mathbf{+35\text{ MG / }+55\text{ EG}}$$

#### C. Safe Queen Mobility
- Computes queen legal moves not attacked by enemy pawns:
  $$\Delta_{\text{queen\_mob}} = (\text{Mobility} - 14) \times 2 \text{ cp}$$

#### D. Rooks Behind Passed Pawns (The Tarrasch Rule)
- Friendly rook on same file behind friendly passed pawn: **$+20$ MG / $+30$ EG**.
- Friendly rook on same file behind enemy passed pawn (blockade ray): **$+15$ MG / $+25$ EG**.
- Connected rooks sharing rank or file: **$+15$ MG / $+15$ EG**.

---

### 5. Module E4' & E5' — Phase-Aware & Endgame Reasoning

#### A. Rule of the Square for Unescorted Passers
- In pure King + Pawn endgames ($\text{NonPawnMaterial} == 0$), for any passed pawn with promotion distance $D_{\text{promo}} = 7 - r_{\text{pawn}}$:
  $$D_{\text{king}} = \max(|r_{\text{king}} - 7|, |f_{\text{king}} - f_{\text{pawn}}|)$$
  If $D_{\text{promo}} < D_{\text{king}}$ (accounting for side to move):
  $$\Delta_{\text{square}} = \mathbf{+500\text{ EG (Mathematically Guaranteed Queen)}}$$

#### B. Opposite-Colored Bishops Fortress Scaling
- In simplified endgames where both sides retain only opposite-colored bishops and $\le 3$ pawns each:
  $$\text{Score}_{\text{final}} = \text{MaterialDifference} + 0.50 \times \text{PositionalDifference}$$
  This suppresses artificial win evaluations in drawing fortress positions (`POS_23`, `POS_24`).

---

### 6. Architectural Sign-Off

All equations and logic have been directly implemented in `engine/classical_x/janus_classical_x.cpp` and verified for bit-exact backward compatibility when running in `UCI_Variant X7` mode.

**Status:** Phase 3 Completed & Verified.

