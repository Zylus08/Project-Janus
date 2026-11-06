# Project Janus v0.57 — Neural Integration Design & Feasibility Specification

**Milestone:** Project Janus v0.57  
**Document Classification:** Architectural Specification & ML Systems Design  
**Author:** Principal ML Systems Architect & C++17 Search Systems Engineer  
**Date:** 2026-11-06  
**Target Engine:** Janus Classical Baseline C1 (Frozen N5 Search Architecture)  
**Objective:** Formulate the smallest viable, reproducible neural integration interface for the first Janus ML prototype (v0.58).

---

## 1. Context & Motivation

Project Janus was established to determine whether learned representations can improve chess decision-making beyond an established classical baseline. Through milestones v0.50 through v0.56, we successfully engineered a high-throughput native C++17 bitboard search engine with:
- Bitboard state representation, pin-aware legal move generation, and Zobrist hashing.
- MVV-LVA, killer-move (2-slot), and butterfly history quiet move ordering.
- Late Move Reductions (LMR) with 10 strict safety invariants.
- 1M-entry transposition table with depth-preferred aging and normalized mate scores.
- Handcrafted static piece-square evaluation.

We have now reached the qualification boundary of classical search heuristics. Diminishing returns in handcrafted tuning necessitate evaluating learned representations. However, deep reinforcement learning (AlphaZero-style MCTS) or large autoregressive transformers require multi-GPU clusters and produce massive inference latencies (>10ms/eval) that are incompatible with alpha-beta search on consumer CPUs.

Our mission is to specify the **smallest, most reproducible, and scientifically rigorous** bridge between Janus's native C++17 search core and a learned representation.

---

## 2. Comparative Evaluation of Candidate Architectural Paradigms

| Architectural Criterion | Option A: Full Neural Value Evaluation | Option B: Neural Move Policy Ordering | Option C: Hybrid Value Evaluation |
| :--- | :--- | :--- | :--- |
| **Model Type** | Value Network: $f_\theta(s) \to v \in [-1, 1]$ | Policy Network: $f_\theta(s) \to \mathbf{p} \in \mathbb{R}^{1968}$ | Dual Value Network / Residual Value |
| **Search Integration Point** | Replaces `native_evaluate(b)` at leaf nodes | Replaces/augments move ordering before $\alpha\beta$ loop | Blends `native_evaluate(b)` with $f_\theta(s)$ |
| **Expected Call Frequency** | 1.0–2.0 million calls/sec (every leaf node) | 50,000–100,000 calls/sec (internal nodes only) | 1.0–2.0 million calls/sec (every leaf node) |
| **Per-Inference CPU Budget** | $< 0.5\ \mu\text{s}$ (strict SIMD/NNUE required) | $5.0–15.0\ \mu\text{s}$ (manageable on CPU) | $< 0.5\ \mu\text{s}$ (strict SIMD/NNUE required) |
| **Inference Engine Footprint** | Custom INT8/FP32 SIMD matrix kernel or ONNX | Lightweight MLP or compact CNN | Custom SIMD kernel or ONNX |
| **Training Data Requirement** | 10M–100M labeled positions (FEN + eval/result) | 1M–5M grandmaster game positions (FEN + move) | 10M–50M labeled positions |
| **Search Regression Risk** | **Extreme** (eval oscillation, horizon traps) | **Minimal** (search tree preservation guaranteed) | **High** (blending weight instability) |
| **Alpha-Beta Correctness** | Preserved (as long as bounds are consistent) | **100% Guaranteed** (reordering only; 0 moves pruned) | Preserved |
| **Fallback on Inference Failure** | Critical failure; cannot evaluate leaves | **Trivial** (fall back to classical MVV-LVA/Killers) | Trivial (fall back to handcrafted eval) |

---

## 3. Recommended Architectural Choice for Janus Prototype 1: Option B (Neural Move Policy Ordering) with Option C Roadmap

### 3.1 Primary Recommendation: Neural Move Policy Ordering (Option B)
For the initial machine learning prototype in Project Janus (v0.58), we formally select **Option B: Neural Move Policy Ordering**.

### 3.2 Scientific & Engineering Justification:
1. **Zero Tactical Risk / Complete Search Safety:**
   - In alpha-beta minimax search, altering the static evaluation function changes minimax values, node evaluations, and cutoff semantics. A flawed static evaluation blunders instantly.
   - In contrast, move ordering **never changes the game-theoretic minimax value of a node** (assuming identical search depth without aggressive pruning). Improving move ordering only changes the *order* in which branches are explored.
   - If the policy network proposes a brilliant candidate move first, alpha-beta produces a beta-cutoff on Move 1, massively pruning the subtree.
   - If the policy network predicts poorly or inference fails, the existing classical killer and history heuristics provide an instantaneous, zero-cost safety net.
2. **Computational Feasibility on Standard CPU:**
   - Static evaluation is called at every single leaf node in both main search and quiescence search ($> 1,500,000$ calls/sec in Janus N5). Evaluating a multi-layer neural network 1.5 million times per second on a single CPU core without specialized INT8 assembly (such as Stockfish's hand-crafted AVX-512 NNUE kernels) causes a catastrophic $100\times$ collapse in NPS.
   - Move ordering is evaluated **only at internal nodes** (depth $\ge 1$), which occur at roughly $1/20\text{th}$ to $1/30\text{th}$ the frequency of leaf evaluations ($\sim 50,000$ calls/sec).
   - Furthermore, we can restrict policy inference strictly to shallow horizons or root/PV nodes, keeping total CPU inference overhead $< 10\%$.
3. **Training Data Accessibility & Ground Truth Quality:**
   - Supervised training data for policy prediction is abundant, clean, and unambiguous: grandmaster move selections from the Lichess Elite or FIDE Master databases provide millions of high-quality (board state $\to$ played move) pairs.
   - Value evaluation requires noisy game results or expensive Stockfish self-play depth-search evaluations.
4. **Clean Factorial Ablation Design:**
   - Evaluating `UseNeuralPolicyOrdering=true` vs `UseNeuralPolicyOrdering=false` under the exact same frozen N5 engine provides an airtight, isolated experimental test of learned representation quality.

---

## 4. Mandatory Interface & Tensor Encoding Specification

### 4.1 Input Tensor: HalfKP-Inspired 12-Plane Bitboard Representation
To maximize native bitboard efficiency and eliminate runtime overhead, the input tensor is extracted directly from the engine's internal `NativeBoard` bitboards (`uint64_t pieces[2][6]`):

- **Tensor Shape:** $[1, 14, 8, 8]$ (or flat $[1, 896]$ floating-point / INT8 tensor).
- **Channels 0–5:** White pieces ($P, N, B, R, Q, K$). Each channel is an $8 \times 8$ binary bitboard.
- **Channels 6–11:** Black pieces ($P, N, B, R, Q, K$).
- **Channel 12:** Side to move ($1.0$ if White, $0.0$ if Black across all 64 squares).
- **Channel 13:** Auxiliary state:
  - Squares 0–3: Castling rights (White K, White Q, Black K, Black Q).
  - Square 4: En passant square file (normalized $0.0 - 1.0$, or $0.0$ if none).
  - Square 5: Fifty-move rule halfmove counter (normalized $/ 100.0$).
  - Remaining squares: $0.0$.

### 4.2 Perspective Canonicalization (Side-to-Move Invariance)
To halve model parameter requirements, the tensor is always oriented from the perspective of the side to move:
- If Black to move, flip the board vertically ($r \to 7 - r$) and swap White and Black piece planes.
- Output move coordinates are inverted accordingly upon inference return.

### 4.3 Output Policy Vector
- **Policy Vector Dimension:** Flat $\mathbb{R}^{4096}$ (from-square $[0..63] \times$ to-square $[0..63]$) or standard $\mathbb{R}^{1968}$ (all legal move combinations including promotions).
- For prototype simplicity, the from-to encoding is used:
  $$\text{Index}(m) = \text{from\_sq} \times 64 + \text{to\_sq} \quad (\text{range: } [0, 4095])$$
- Softmax is applied only across **legal moves** generated by `native_generate_legal_moves`:
  $$\pi(m_i) = \frac{\exp(z_{\text{index}(m_i)})}{\sum_{j \in \text{Legal}} \exp(z_{\text{index}(m_j)})}$$

### 4.4 Move Scoring Integration Hierarchy
In `score_move_for_ordering`, when `UseNeuralPolicyOrdering=true`:
1. **Transposition Table Move:** $10,000,000$ (Unchanged)
2. **Promotions:** $800,000 - 900,000$ (Unchanged)
3. **Winning Captures ($\text{SEE} > 0$):** $100,000 + \text{MVV-LVA}$
4. **Neural Policy Priority:** For non-losing moves, policy score scaled to $[20,000, 70,000]$:
   $$\text{Score}(m) = 20,000 + \text{int}(50,000 \times \pi(m))$$
5. **Killer Moves:** $90,000 / 80,000$ (Superseded only if neural confidence $> 0.80$)
6. **Losing Captures:** $< 20,000$
7. **History Heuristic:** $< 16,384$
8. **Unscored Quiets:** $0$

### 4.5 Determinism & Error Fallback
- **Inference Failure Fallback:** If inference fails (missing model weights, tensor allocation failure, NaN detection), the search core logs a warning and immediately falls back to the classical N5 ordering heuristic without interrupting search.
- **Deterministic Inference:** Floating-point thread race conditions are avoided by single-thread inference or pre-allocated per-thread model contexts. Fixed weights and greedy argmax guarantee $100\%$ reproducible move selections.
- **Model Versioning:** Models will be stored under `models/` with SHA-256 manifests and embedded architecture metadata.

