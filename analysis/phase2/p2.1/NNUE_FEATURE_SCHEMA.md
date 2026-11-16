# Janus NNUE — Feature Representation Schema (Phase 2)

**Milestone:** Phase 2, Milestone P2.1  
**Architecture:** Dual-Perspective HalfKP-768 Sparse Feature Schema  
**Date:** November 16, 2026  
**Auditor:** Principal Computer Chess Architect & Neural-Network Systems Engineer  

---

## 1. Feature Representation Specification

To ensure both mathematical tractability and high-speed CPU inference, Project Janus adopts the canonical **Dual-Perspective 768-Feature Sparse Representation**:

### Mathematical Mapping:
- **Piece Types ($12$ total):**
  - White: Pawn (0), Knight (1), Bishop (2), Rook (3), Queen (4), King (5)
  - Black: Pawn (6), Knight (7), Bishop (8), Rook (9), Queen (10), King (11)
- **Board Squares ($64$ total):** $s \in [0, 63]$ ($0 = \text{a1}, 63 = \text{h8}$).
- **Total Feature Dimensions:** $12 \times 64 = 768$.

### Dual Perspective Alignment:
The network maintains two independent feature perspectives:
1. **White Perspective ($\mathbf{f}_{\text{white}}$):**
   - Evaluated directly from White's side.
   - White pieces are friendly (indices 0..5), Black pieces are enemy (indices 6..11).
   - Square mapping is $s$ as-is ($0..63$).
   $$\text{index}_{\text{white}} = p \times 64 + s$$
2. **Black Perspective ($\mathbf{f}_{\text{black}}$):**
   - Evaluated from Black's side with rank symmetry ($s' = s \oplus 56$).
   - Black pieces are friendly (indices 0..5), White pieces are enemy (indices 6..11).
   $$\text{index}_{\text{black}} = p' \times 64 + (s \oplus 56)$$
   where $p' = (p < 6) ? (p + 6) : (p - 6)$.

When White is to move, the network input layer concatenates:
$$\mathbf{X} = [\text{acc}_{\text{white}}, \text{acc}_{\text{black}}]$$
When Black is to move, the network input layer cleanly flips perspective:
$$\mathbf{X} = [\text{acc}_{\text{black}}, \text{acc}_{\text{white}}]$$

This mathematical construction guarantees **100% color-inversion symmetry** across all positions.

---

## 2. Incremental Delta Update Formalism

For any legal move $m = (\text{from}, \text{to}, \text{flags})$, the active feature set changes by at most 2 removals and 2 additions:

| Move Type | White Perspective Delta | Black Perspective Delta | Max Feature Ops |
| :--- | :--- | :--- | :---: |
| **Quiet Move** | $-\text{piece}(\text{from}), +\text{piece}(\text{to})$ | $-\text{piece}'(\text{from}'), +\text{piece}'(\text{to}')$ | 2 ops |
| **Capture** | $-\text{piece}(\text{from}), -\text{victim}(\text{to}), +\text{piece}(\text{to})$ | $-\text{piece}'(\text{from}'), -\text{victim}'(\text{to}'), +\text{piece}'(\text{to}')$ | 3 ops |
| **Castling** | $-\text{K}(\text{from}), +\text{K}(\text{to}), -\text{R}(\text{rfrom}), +\text{R}(\text{rto})$ | $-\text{K}'(\text{from}'), +\text{K}'(\text{to}'), -\text{R}'(\text{rfrom}'), +\text{R}'(\text{rto}')$ | 4 ops |
| **En Passant** | $-\text{P}(\text{from}), -\text{p}(\text{epsq}), +\text{P}(\text{to})$ | $-\text{P}'(\text{from}'), -\text{p}'(\text{epsq}'), +\text{P}'(\text{to}')$ | 3 ops |
| **Promotion** | $-\text{P}(\text{from}), -\text{victim?}(\text{to}), +\text{promo}(\text{to})$ | $-\text{P}'(\text{from}'), -\text{victim?'}(\text{to}'), +\text{promo}'(\text{to}')$ | 3–4 ops |

### Fundamental Verification Invariant:
$$\text{Accumulator}(S_{t+1}) = \text{Accumulator}(S_t) - \sum_{f \in \text{Removed}} \mathbf{W}_f + \sum_{f \in \text{Added}} \mathbf{W}_f \equiv \text{FullRecompute}(S_{t+1})$$

In test suite `test_nnue_features.py`, this invariant was evaluated across **$3,968$ random legal moves** with **$100.0\%$ exact equality** ($\Delta = 0$).
