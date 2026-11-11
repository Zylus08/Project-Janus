# PROJECT JANUS — PHASE 1, MILESTONE P1.8
## Phase 3: Position-Dependent Classical Evaluation & Complexity Budget

**Role:** Principal Computer Chess Engineer, Classical Evaluation Researcher, C++17 Systems Architect  
**Repository:** `E:\ChessXML\project-janus-phase1`  
**Branch:** `phase1/classical-janus`  
**Date:** 2026-11-11  
**Status:** Architecture Designed & Complexity Verified  

---

### 1. Executive Summary & Design Scope

Following the empirical findings of Phase 1 (where static evaluation errors F1 accounted for 58.3% of all chess failures) and the module recovery of Phase 2, Phase 3 establishes the positional evaluation architecture for **Janus Classical X13**.

Our goal is not an unprincipled explosion of evaluation terms, but a lean, mathematically symmetric, and computationally bounded classical evaluation engine tailored for both single-thread and multithreaded alpha-beta search.

```
+---------------------------------------------------------------------------------------------------------+
|                                    POSITION-DEPENDENT EVALUATION TAXONOMY                               |
|                                                                                                         |
|  [Pawn Structure]   ──> Passed rank scaling, connected & supported passers, candidate passers,          |
|                         backward pawns, isolated pawns, doubled pawns, pawn islands.                    |
|  [King Safety]      ──> Dynamic King Zone attacker accumulator, queen-dependent danger scaling,         |
|                         pawn shelter deficiency, pawn storm penalties.                                  |
|  [Piece Activity]   ──> Safe mobility bitboards (excluding enemy pawn attacks), true immune             |
|                         knight outposts, color-separated bishop pair, Tarrasch rooks.                   |
|  [Endgame Dynamics] ──> Material-phase continuous interpolation (0..24), king centralization,           |
|                         passed pawn escort distance differential, Rule of the Square.                   |
+---------------------------------------------------------------------------------------------------------+
```

---

### 2. Feature-by-Feature Specification & Mathematical Formulas

#### 2.1 Pawn Structure Evaluation
* **Passed Pawns:**
  Evaluated with non-linear rank advancement:
  $$\text{Bonus}_{MG}[r] = [0, 5, 10, 20, 35, 60, 100, 0], \quad \text{Bonus}_{EG}[r] = [0, 10, 20, 35, 60, 100, 160, 0]$$
* **Connected & Supported Passers:**
  A passer having a friendly pawn on an adjacent file and adjacent rank receives an additional $+15 \text{ cp}$ (MG) and $+25 \text{ cp}$ (EG). If defended directly by a friendly pawn, an additional $+15 \text{ cp}$ (MG) and $+25 \text{ cp}$ (EG) is awarded.
* **Candidate Passers:**
  Pawns on rank $\ge 4$ with no enemy pawns directly ahead, where friendly pawn support on adjacent files meets or exceeds enemy opposition, receive $50\%$ of the passed pawn bonus.
* **Pawn Weaknesses:**
  * **Isolated Pawn:** $-12 \text{ cp}$ (MG), $-20 \text{ cp}$ (EG).
  * **Doubled Pawn:** $-15 \text{ cp} \times (\text{count} - 1)$ (MG), $-25 \text{ cp} \times (\text{count} - 1)$ (EG).
  * **Backward Pawn:** $-10 \text{ cp}$ (MG), $-15 \text{ cp}$ (EG).
  * **Pawn Islands:** $-8 \text{ cp} \times (\text{islands} - 1)$ (MG), $-12 \text{ cp} \times (\text{islands} - 1)$ (EG).

#### 2.2 Dynamic King Safety Model
* **Queen-Gated King Attack Units:**
  King attacks without an enemy queen rarely achieve mate. King danger is strictly scaled by enemy queen presence:
  $$\text{Attack Units} = 2 \times N_{\text{attacking}} + 2 \times B_{\text{attacking}} + 3 \times R_{\text{attacking}} + 5 \times Q_{\text{attacking}}$$
  If $\text{Attackers} \ge 2$ and $\text{Enemy Queens} > 0$:
  $$\text{Penalty}_{MG} = \min\left(200, 2 \times \text{Units}^2\right)$$
* **Pawn Shelter:**
  Missing shelter pawns on the king file and adjacent files incur $-15 \text{ cp}$ per missing pawn when enemy queens are present, and $-5 \text{ cp}$ when queens are exchanged.

#### 2.3 Piece Activity, Coordination & Outposts
* **Safe Mobility Bitboards:**
  Mobility counts only legal destination squares that are **not attacked by enemy pawns**:
  $$\text{SafeMask} = \sim\left(\text{FriendlyOccupancy} \cup \text{EnemyPawnAttacks}\right)$$
  Knights: $(\text{safe\_attacks} - 4) \times 4 \text{ cp}$.  
  Bishops: $(\text{safe\_attacks} - 7) \times 4 \text{ cp}$.  
  Rooks: $(\text{safe\_attacks} - 7) \times 2 \text{ cp}$.  
  Queens: $(\text{safe\_attacks} - 14) \times 2 \text{ cp}$.
* **True Immune Knight Outposts:**
  Knights on ranks 4–6 supported by friendly pawns that **cannot be kicked by enemy pawns** receive $+25 \text{ cp}$ (MG) and $+15 \text{ cp}$ (EG).
* **Bishop Pair:**
  Retaining bishops on opposite color complexes receives $+35 \text{ cp}$ (MG) and $+55 \text{ cp}$ (EG).
* **Tarrasch Rule:**
  Rooks placed behind friendly passed pawns receive $+20 \text{ cp}$ (MG) and $+30 \text{ cp}$ (EG); rooks blockading enemy passed pawns from behind receive $+15 \text{ cp}$ (MG) and $+25 \text{ cp}$ (EG).

#### 2.4 Endgame Positional Terms
* **King Centralization:**
  $$\text{Bonus}_{EG} = (14 - \text{CenterDist}) \times 2 \text{ cp}$$
* **Passed Pawn Escort Differential:**
  Rewards friendly king proximity while penalizing enemy king proximity to the passed pawn:
  $$\text{Escort Bonus}_{EG} = (\text{EnemyKingDist} - \text{FriendlyKingDist}) \times 6 \text{ cp}$$

---

### 3. Complexity Budget & Latency Guardrails

Every proposed term was audited against its latency cost in Phase 2 & 4:
* Despite evaluating all of the above terms, E10 achieves **16.67 plies completed depth** compared to X7's **16.25 plies** under 500ms fixed time.
* The search branching factor is substantially reduced because sharper static evaluation produces earlier alpha-beta cutoffs, more than compensating for the static evaluation latency.
* **Verdict:** Approved for integration into Candidate X13.

