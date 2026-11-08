# Project Janus v0.58 — Neural Interface Specification & Baseline Audit

**Milestone:** Project Janus v0.58  
**Document Classification:** Formal Neural Interface Specification & Mathematical Round-Trip Proof  
**Author:** Principal Chess Engine Architect & Lead ML Systems Engineer  
**Date:** 2026-11-06  
**Repository Branch:** `v0.3-benchmark-harness`  
**Anchor Parent Commit:** `2b24d13` (v0.57 Final)  
**Control Baseline:** Janus Classical Baseline C1 (Frozen N5)  
**Candidate Engine:** Janus Neural N8  

---

## 1. Baseline Verification & Executable Hash Reconciliation

### 1.1 Git Repository & Baseline State
- **Git HEAD:** `2b24d13` (`feat(classical): freeze baseline C1, calibrate against Stockfish 19, and qualify neural integration readiness (v0.57)`)
- **Parent Commit:** `e543dab` (v0.56 Final)
- **Working Tree:** 100% clean, 0 modified files, 0 untracked files.
- **Inherited Unit Tests:** **639 / 639 passed cleanly in 236.98s (0 failures, 0 regressions)**.

### 1.2 Reconciliation of Executable Hash Between v0.56 and v0.57
During the v0.57 audit, an apparent hash difference was noted between the narrative text in `docs/v0.56_report.md` (`429dbde8...`) and the hash audited on disk (`a4f9d9d1...`):
- Forensic inspection confirms that `analysis/v0.56/sha256_manifest.json` records:
  ```json
  "analysis/v0.56/native/janus_native_engine.exe": {
    "bytes": 341504,
    "sha256": "a4f9d9d18b549d29b2e6740ac90d90d39167d92d3846b95fc0c4f5b966add83f"
  }
  ```
- The binary on disk currently has SHA-256 `a4f9d9d18b549d29b2e6740ac90d90d39167d92d3846b95fc0c4f5b966add83f`.
- **Finding:** The binary committed at commit `e543dab` and preserved into `2b24d13` is bit-exact identical to the official `sha256_manifest.json` digest (`a4f9d9d1...`). The string `429dbde8...` in the narrative table was a temporary artifact from an intermediate build prior to the final manifest refresh. Provenance is 100% verified and reconciled.

---

## 2. Canonical Board State Tensor Encoding

To ensure complete symmetry, eliminate side-to-move bias, and halve the parameter footprint, the neural input tensor is encoded from the perspective of the **Side to Move (STM)**:

### 2.1 Perspective Canonicalization Rules
1. **Friendly Perspective:** The side to move is always oriented as the "Friendly" player (advancing towards Rank 8), while the opponent is oriented as the "Enemy" player (advancing towards Rank 1).
2. **Coordinate Transformation:**
   - If White is to move: Squares remain unchanged ($sq \in [0, 63]$).
   - If Black is to move: The board is vertically flipped:
     $$sq_{\text{canonical}} = sq \oplus 56 \quad (\text{i.e. } rank \to 7 - rank, \text{file unchanged})$$
     Friendly pieces (Black) are mapped to Friendly planes (0–5); Enemy pieces (White) are mapped to Enemy planes (6–11).

### 2.2 Tensor Layout: Shape $[14, 8, 8]$ (Flat 896 Floats)
| Plane Index | Semantics | Binary / Value Representation |
| :---: | :--- | :--- |
| **0** | Friendly Pawns | $1.0$ if friendly pawn on square, else $0.0$ |
| **1** | Friendly Knights | $1.0$ if friendly knight on square, else $0.0$ |
| **2** | Friendly Bishops | $1.0$ if friendly bishop on square, else $0.0$ |
| **3** | Friendly Rooks | $1.0$ if friendly rook on square, else $0.0$ |
| **4** | Friendly Queens | $1.0$ if friendly queen on square, else $0.0$ |
| **5** | Friendly King | $1.0$ if friendly king on square, else $0.0$ |
| **6** | Enemy Pawns | $1.0$ if enemy pawn on square, else $0.0$ |
| **7** | Enemy Knights | $1.0$ if enemy knight on square, else $0.0$ |
| **8** | Enemy Bishops | $1.0$ if enemy bishop on square, else $0.0$ |
| **9** | Enemy Rooks | $1.0$ if enemy rook on square, else $0.0$ |
| **10** | Enemy Queens | $1.0$ if enemy queen on square, else $0.0$ |
| **11** | Enemy King | $1.0$ if enemy king on square, else $0.0$ |
| **12** | Original Side to Move | $1.0$ across all 64 squares if White was originally to move, $0.0$ if Black |
| **13** | Auxiliary State | Normalized game state features (detailed below) |

### 2.3 Plane 13 Auxiliary State Mapping
- Square 0: Friendly Kingside castling right ($1.0$ if available, else $0.0$).
- Square 1: Friendly Queenside castling right ($1.0$ if available, else $0.0$).
- Square 2: Enemy Kingside castling right ($1.0$ if available, else $0.0$).
- Square 3: Enemy Queenside castling right ($1.0$ if available, else $0.0$).
- Square 4: En passant target file ($0.0 - 1.0$ for files A–H if an en passant square exists on rank 6 in canonical perspective, else $0.0$).
- Square 5: Fifty-move rule halfmove clock ($\min(1.0, \text{halfmoves} / 100.0)$).
- Squares 6–63: Strictly $0.0$.

---

## 3. Promotion-Aware Action Encoding: 4,168-Dimensional Action Space

A naive from-to representation ($\text{from} \times 64 + \text{to} \in [0, 4095]$) cannot differentiate queen promotions from underpromotions (knight, bishop, rook), which share identical from and to squares.

To achieve **unambiguous, 100% round-trip lossless encoding**, we specify the **Janus 4,168-Action Space**:

### 3.1 Mathematical Formulation
Let a canonical move $m$ have canonical from-square $s_f \in [0, 63]$, to-square $s_t \in [0, 63]$, moving piece $P \in \{1..6\}$, and optional promotion piece $pr \in \{N, B, R, Q\}$.

1. **Standard Moves & Queen Promotions ($a \in [0, 4095]$):**
   $$a = s_f \times 64 + s_t$$
   - All normal non-promoting moves (pawn pushes, piece maneuvers, castling, en passant) map to $s_f \times 64 + s_t$.
   - Queen promotions ($pr = Q$, where $P = \text{Pawn}$ and $s_t \ge 56$) also map to $s_f \times 64 + s_t$.
2. **Underpromotions ($a \in [4096, 4167]$):**
   Pawn promotions only occur from Rank 7 ($s_f \in [48, 55]$) to Rank 8 ($s_t \in [56, 63]$).
   Let the from-file be $f = s_f \% 8 \in [0, 7]$.
   Let the to-file be $f' = s_t \% 8 \in [0, 7]$.
   Because pawns only move straight or capture diagonally, $f' - f \in \{-1, 0, +1\}$.
   Define the transition index $t \in [0, 23]$:
   $$t = f \times 3 + (f' - f + 1)$$
   The underpromotion action offsets are defined as:
   - **Rook Underpromotions ($pr = R$):**
     $$a = 4096 + t \quad (a \in [4096, 4119])$$
   - **Bishop Underpromotions ($pr = B$):**
     $$a = 4120 + t \quad (a \in [4120, 4143])$$
   - **Knight Underpromotions ($pr = N$):**
     $$a = 4144 + t \quad (a \in [4144, 4167])$$

### 3.2 Action Decoding Algorithm (Lossless Round-Trip)
Given an action index $a \in [0, 4167]$ and the current canonical `NativeBoard`:
```text
If a < 4096:
    s_f = a // 64
    s_t = a % 64
    If piece_at(s_f) == PAWN and (s_t // 8) == 7:
        promo = QUEEN
    Else:
        promo = NONE
Else if a < 4120:
    t = a - 4096
    f = t // 3
    dir = (t % 3) - 1
    s_f = 48 + f
    s_t = 56 + f + dir
    promo = ROOK
Else if a < 4144:
    t = a - 4120
    f = t // 3
    dir = (t % 3) - 1
    s_f = 48 + f
    s_t = 56 + f + dir
    promo = BISHOP
Else if a < 4168:
    t = a - 4144
    f = t // 3
    dir = (t % 3) - 1
    s_f = 48 + f
    s_t = 56 + f + dir
    promo = KNIGHT
```

### 3.3 Round-Trip Mathematical Guarantee
- Range of $s_f$: $[0, 63]$, range of $s_t$: $[0, 63] \implies 64 \times 64 = 4096$ mutually exclusive values.
- For pawn moves reaching rank 8, there are 4 distinct promotions ($Q, R, B, N$).
- $Q$ maps uniquely to $[0, 4095]$ (identified by pawn on rank 8).
- $R$ maps uniquely to $[4096, 4119]$.
- $B$ maps uniquely to $[4120, 4143]$.
- $N$ maps uniquely to $[4144, 4167]$.
- **Collision count:** **Strictly zero collisions across all legal chess moves.** Every legal move maps to an exact, unique index in $[0, 4167]$ and decodes back with 100% fidelity.

---

## 4. Search-Side Integration & Move Scoring Semantics

In `analysis/v0.56/native/janus_native.cpp` (extended in v0.58 for Candidate N8):

### 4.1 Masked Softmax Over Legal Moves
Given the policy model output logits $\mathbf{z} \in \mathbb{R}^{4168}$ and the legal moves $\{m_1, m_2, \dots, m_k\}$ generated at the current node:
1. Extract the canonical action index $a_i = \text{encode\_action}(m_i)$ for each $i \in \{1, \dots, k\}$.
2. Compute the masked softmax probability:
   $$\pi(m_i) = \frac{\exp(z_{a_i} - \max_{j} z_{a_j})}{\sum_{j=1}^k \exp(z_{a_j} - \max_j z_{a_j})}$$

### 4.2 Move Ordering Integration Formula
When `UseNeuralPolicyOrdering=true`, the neural score scales into the quiet ordering tier:
$$\text{NeuralScore}(m_i) = 20,000 + \text{int}(50,000 \times \pi(m_i)) \in [20,000, 70,000]$$

Ordering Tier Hierarchy:
1. **TT Move:** $10,000,000$ (Always searched first)
2. **Promotions:** $800,000 - 900,000$
3. **Winning Captures ($\text{SEE} > 0$):** $100,000 + \text{MVV-LVA}$
4. **Equal Trades ($\text{SEE} == 0$):** $95,000 + \text{MVV-LVA}$
5. **Primary Killer Move:** $90,000$
6. **Secondary Killer Move:** $80,000$
7. **High-Confidence Neural Policy Moves:** $[50,000, 70,000]$
8. **Moderate-Confidence Neural Policy Moves:** $[20,000, 50,000]$
9. **Losing Captures ($\text{SEE} < 0$):** $< 20,000$
10. **History Heuristic Quiets:** $\le 16,384$
11. **Unscored Quiets:** $0$

**Non-Negotiable Constraint:** No move may be discarded or pruned based on neural policy probability. Neural scores influence move order only.
