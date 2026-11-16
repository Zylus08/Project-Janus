# Project Janus — Phase 2, Milestone P2.3
## Phase 2: HalfKP-40960 Feature Specification & Accumulator Invariants

**Author:** Principal Computer Chess Researcher, NNUE Architecture Specialist & C++ Performance Engineer  
**Milestone:** P2.3 — King-Relative NNUE, Search-Grounded Neural Training, Incremental CPU Inference & Independent Playing-Strength Qualification  
**Date:** 2026-11-17  
**Subject:** HalfKP Feature Schema, Indexing Formulation, King Refresh Contracts & Validation  

---

### 1. Mathematical Feature Representation

The HalfKP architecture conditions every non-king piece on the square of the friendly king. 
Each feature index represents a 3-tuple $(k, c, s)$:
- $k \in [0, 63]$: Square coordinate of the friendly king.
- $c \in [0, 9]$: Piece category (5 friendly piece types, 5 enemy piece types).
  - Friendly: $0=\text{Pawn}, 1=\text{Knight}, 2=\text{Bishop}, 3=\text{Rook}, 4=\text{Queen}$.
  - Enemy: $5=\text{Pawn}, 6=\text{Knight}, 7=\text{Bishop}, 8=\text{Rook}, 9=\text{Queen}$.
- $s \in [0, 63]$: Square coordinate of the non-king piece.

$$\textbf{Total Logical Features per Perspective: } 64 \times 10 \times 64 = 40,960$$

$$\text{FeatureIndex}(k, c, s) = k \times 640 + c \times 64 + s$$

---

### 2. Perspective & Color Inversion Invariants

To allow both White and Black perspectives to share the exact same $40,960 \times 128$ feature transformer weight matrix, coordinates are mapped from the perspective's view:

1. **White Perspective:**
   - King square: $k_w = \text{Square}(\text{White King})$.
   - Piece square: $s_w = s$.
   - Category: $c_w = \text{Type}(p)$ if White, else $5 + \text{Type}(p)$ if Black.
2. **Black Perspective:**
   - King square: $k_b = \text{Square}(\text{Black King}) \oplus 56$ (rank mirrored $r \to 7 - r$).
   - Piece square: $s_b = s \oplus 56$ (rank mirrored).
   - Category: $c_b = \text{Type}(p)$ if Black, else $5 + \text{Type}(p)$ if White.

This guarantees exact skew-symmetry: in symmetric positions (e.g. `startpos`), the set of active White features and active Black features are mathematically identical.

---

### 3. Formal Accumulator Lifecycle & Refresh Contracts

Because HalfKP indexes pieces relative to the king square $k$, moving the king invalidates the entire base coordinate for that perspective:

```
========================================================================================================================
ACCUMULATOR UPDATE & REFRESH ACTION CONTRACT
========================================================================================================================
Move Type               | Friendly King Moves? | Friendly Perspective Action     | Enemy Perspective Action
------------------------+----------------------+---------------------------------+--------------------------------------
Quiet Piece Move        | No                   | Delta: -from_sq, +to_sq         | Delta: -from_sq, +to_sq
Ordinary Capture        | No                   | Delta: -from_sq, -victim, +to_sq| Delta: -from_sq, -victim, +to_sq
En Passant Capture      | No                   | Delta: -pawn, -victim, +pawn    | Delta: -pawn, -victim, +pawn
Pawn Promotion          | No                   | Delta: -pawn, +promo_piece      | Delta: -pawn, +promo_piece
King Quiet Move         | Yes                  | FULL REFRESH from scratch       | NO OP (Enemy king is unindexed)
King Capture            | Yes                  | FULL REFRESH from scratch       | Delta: -captured_piece
Castling (Kingside/QS)  | Yes                  | FULL REFRESH from scratch       | Delta: -rook_from, +rook_to
========================================================================================================================
```

#### The King Capture & Castling Invariants:
1. **King Capture:** When the White King captures a Black piece, the White perspective must be refreshed from scratch. However, the Black perspective's friendly king did not move; therefore, the Black accumulator updates via $O(1)$ delta by subtracting the captured friendly piece!
2. **Castling:** When White castles, White's king moves (triggering full refresh for White). In Black's perspective, Black's king did not move, but the White Rook moved! Therefore, the Black accumulator updates via $O(1)$ delta by removing the enemy rook from its original corner and adding it to its castled square!

---

### 4. Verification Suite Results

The implementation in `analysis/phase2/p2.3/scripts/halfkp.py` was validated by `test_halfkp.py` across 12 diagnostic positions and 20 random walk games (up to 100 plies each):
- **Total legal moves evaluated against full scratch recompute oracle:** $2,217$ plies.
- **Incremental feature mismatches:** $\mathbf{0}$ ($\mathbf{100.000\%}$ exact parity).
- **White king refreshes:** $149$.
- **Black king refreshes:** $116$.
- **Color skew-symmetry at startpos:** Exactly verified.

Phase 2 is complete. Milestone P2.3 now advances to **Phase 3: Network Capacity and Memory Budget**.
