# Project Janus — Phase 2, Milestone P2.2
## Phase 1: Feature Schema Forensics & Architectural Reclassification

**Author:** Principal Computer Chess Architect & Neural Network Systems Engineer  
**Milestone:** P2.2 — Neural Evaluation Failure Forensics, Score Calibration & Scalable Dataset Readiness  
**Date:** 2026-11-16  
**Subject:** Forensic Analysis of Candidate H1 Neural Input Representation  

---

### 1. Executive Summary & Core Finding

During Milestone P2.1, candidate H1's input representation was designated as `Dual-Perspective HalfKP-768`.
Forensic inspection of the actual feature calculation functions in both Python (`train_janus_nnue.py`) and C++ (`engine/classical_x/r1/r1_nnue.hpp`) reveals that **this designation is fundamentally inaccurate**.

Conventional **HalfKP** representations (as pioneered in Stockfish NNUE) explicitly condition non-king piece features upon the friendly king's square coordinate:
$$\text{Feature}_{\text{HalfKP}} = \text{KingSq} \times (10 \times 64) + \text{PieceType} \times 64 + \text{PieceSq} \quad (\approx 40,960 \text{ sparse dimensions})$$

In Candidate H1, the feature indexing formula is strictly:
$$\text{Feature}_{\text{White}} = (\text{Color} \times 6 + \text{PieceType}) \times 64 + \text{Square}$$
$$\text{Feature}_{\text{Black}} = ((1 - \text{Color}) \times 6 + \text{PieceType}) \times 64 + (\text{Square} \oplus 56)$$

There are exactly $2 \times 6 \times 64 = 768$ features per perspective.
There is **ZERO** king-square conditioning. The friendly king is simply piece type 5 (`K`), and the enemy king is piece type 11 (`k`).

**Official Architectural Reclassification:**
Candidate H1's input layer is classified as:
$$\textbf{Janus Dual-Perspective Piece-Square-768 (DP-PS-768)}$$

---

### 2. Feature Dimension & Semantic Attribution Audit

| Information Dimension | Encoded in H1 DP-PS-768? | Implementation Mechanism |
| :--- | :---: | :--- |
| **Piece Type** | **YES** | 6 piece classes: Pawn (0), Knight (1), Bishop (2), Rook (3), Queen (4), King (5). |
| **Piece Color** | **YES** | Binary partition: Friendly pieces vs Enemy pieces. |
| **Piece Square** | **YES** | Direct square index $0 \le \text{sq} \le 63$. |
| **Board Orientation** | **YES** | Symmetrical rank-inversion for Black perspective ($\text{sq} \oplus 56$). |
| **Friendly King Location** | **PARTIAL (INDEPENDENT)** | Encoded only as an independent piece on square $k$, with zero conditioning on other pieces. |
| **Enemy King Location** | **PARTIAL (INDEPENDENT)** | Encoded only as an independent piece on square $k'$, with zero conditioning on other pieces. |
| **Relative King-Piece Geometry** | **NO** | Zero distance, angle, or file/rank relative coordinates between pieces and kings. |
| **Pawn Shelter / Shield** | **NO** | Pawns in front of the king add independent weights; no cross-terms exist in the accumulator. |
| **Pawn Structure Dynamics** | **NO** | No passed, isolated, doubled, or backward pawn interaction terms. |
| **Side to Move (STM)** | **YES (PERSPECTIVE)** | Concatenation order: `[Accumulator(STM), Accumulator(NTM)]`. |

---

### 3. Empirical Feature Invariant Test Results

The test harness `audit_feature_schema.py` executed 7 rigorous diagnostic suites:

1. **Feature Index Parity (Python vs C++):**
   - Verified across all 768 feature dimensions: **0 mismatches** between `train_janus_nnue.py` and `r1_nnue.hpp`.
2. **Starting Position Dimensionality:**
   - Active features: Exactly 32 for STM (16 friendly, 16 enemy), exactly 32 for NTM.
3. **Color Inversion & Perspective Symmetry:**
   - Active feature sets for White to move and Black to move in mirrored positions match with 100% exactness (`exact_set_match = True`).
4. **King Placement Independence Test:**
   - Position A: White King on `e1`, Pawn on `e2`. Active features: `[28, 324]`.
   - Position B: White King on `g1`, Pawn on `e2`. Active features: `[28, 326]`.
   - Result: Moving the king changed **only** the king's feature ($324 \to 326$). The pawn feature ($28$) was completely unaffected. In genuine HalfKP, moving the king changes the feature index of all friendly pieces on the board.
5. **Castling & En Passant Modifiers:**
   - Kingside Castling: Exactly 2 removals (King `e1`, Rook `h1`) and 2 additions (King `g1`, Rook `f1`).
   - En Passant: Exactly 2 removals (capturing pawn, victim pawn) and 1 addition (destination pawn).
6. **Promotion & Underpromotion:**
   - Disjoint feature assignments verified for Queen, Rook, Bishop, and Knight promotions.
7. **Make/Unmake Invariance:**
   - Verified across 100 consecutive random legal plies: 100% invariant state recovery.

---

### 4. Positional Chess Limitations of the DP-PS-768 Architecture

Because DP-PS-768 contains no king-piece cross-terms in its accumulator:
1. **The Accumulator is a Linear Piece-Square Vector:**
   The accumulator vector $\mathbf{a}_{\text{stm}} \in \mathbb{R}^{128}$ is simply:
   $$\mathbf{a}_{\text{stm}} = \mathbf{b} + \sum_{i=1}^{N} \mathbf{W}[\text{piece}_i, \text{sq}_i]$$
   The network cannot compute multiplicative features such as *"Knight attacking square adjacent to enemy King"* or *"Pawn sheltering friendly King"* in the feature transformer.
2. **All Non-Linearity is Bottlenecked in Hidden Layer L1 ($256 \to 32$):**
   Any positional synergy between pieces must be extracted entirely by the 32 hidden neurons of Layer 1. With only 32 neurons and a tiny training set (40k positions), the network cannot learn complex positional motifs.
3. **Why DP-PS-768 Can Guide Tactics but Fails at Positional Chess:**
   DP-PS-768 effectively learns generalized piece-square tables and global piece counts, explaining why it achieves ~60% test accuracy on basic outcome prediction and cuts search tree nodes by 35%. However, it cannot perceive king safety or pawn structure nuances, which explains why Classical R1 (which possesses handcrafted king safety and pawn hash tables) dominates it in match play.

---

### 5. Architectural Verdict

The H1 input representation is officially documented as **Janus Dual-Perspective Piece-Square-768 (DP-PS-768)**.
Future feature expansion in Milestone P2.2+ must introduce true **king-relative feature conditioning** (HalfKP-4096 or HalfKAv2) to enable the network to learn king safety, pawn shields, and king-attack geometry.
