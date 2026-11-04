# Project Janus v0.50 — Architectural Recommendation & Final Decision

## 1. Decision Outcome

**Selected Category: Category B — Native Core Feasible, Further Work Required Before Transition**

---

## 2. Formal Justification

### 2.1 Criteria Evaluation Matrix

| Criterion | Requirement for Category A | Requirement for Category B | v0.50 Measured Empirical Result | Status |
|---|---|---|---|---|
| **Throughput Improvement** | >10x speedup vs Python K0 | >5x speedup vs Python K0 | **19.4x to 51.3x wall-clock speedup** (353k-648k NPS vs 5.1k-21.6k NPS) | **EXCEEDS CATEGORY A** |
| **Depth 5 Move Agreement** | >90% agreement | >70% agreement | **78.4% (29 / 37 positions identical)** | **SATISFIES CATEGORY B** |
| **Tactical Regression Pass Rate** | 100% parity / zero regression | Parity on core tactical motifs | **100% parity at Depth 4 (50.0% vs 50.0%) and Depth 5 (41.7% vs 41.7%)**; N2 solved stalemate avoidance (`tac_11`) where K0 failed | **EXCEEDS CATEGORY B** |
| **Board-State & Rule Precision** | 100% exact | 100% exact | **100.0% FEN round-trip, check detection, legal move generation (42,041 moves), and 18/18 standard Perft suites passed** | **EXCEEDS CATEGORY A** |
| **Heuristic Parity** | Complete parity | Acceptable with identified gaps | Move ordering differences (quiet tie-breaks) and delta pruning margins cause minor divergences at depth 5 | **SATISFIES CATEGORY B** |

### 2.2 Detailed Scientific Rationale
1. **Order-of-Magnitude Acceleration Validated**:
   N2 delivers an undeniable computational breakthrough for Project Janus:
   - Move generation executes at **15.0–16.1 Million NPS** (~800x faster than python-chess).
   - End-to-end alpha-beta search executes at **350,000 to 650,000 NPS**, completing depth 5 searches in 10.12s natively versus 195.99s in Python K0 (**19.4x faster**).
   - In fixed-time searches, N2 searches 2.0+ ply deeper than Python K0 at every budget tier (reaching Depth 5.27 at 500ms vs Depth 3.27 in K0).
2. **Move Agreement Convergence**:
   Move agreement between K0 and N2 increases steadily with depth:
   - Depth 1: 43.2%
   - Depth 2: 59.5%
   - Depth 3: 64.9%
   - Depth 4: 70.3%
   - Depth 5: **78.4%**
   The remaining 21.6% divergence at Depth 5 stems primarily from quiet move evaluation symmetries (scores within 5–15 cp) where different move generation enumeration orders break ties differently.
3. **Prudence in Production Transition**:
   Category A requires >90% agreement. Promoting N2 to the sole production default prematurely would violate Janus's strict empirical gating principles. By classifying this outcome under **Category B**, Project Janus preserves Python K0 as the immutable reference baseline while advancing N2 as an experimental native core.

---

## 3. Transition Roadmap for v0.51

To advance from Category B to full Category A production replacement in v0.51:
1. **Full UCI Protocol Bridge in C++**:
   Integrate full UCI command processing (`uci`, `isready`, `position fen/moves`, `go wtime/btime/movetime/depth`) directly into the native binary, eliminating Python IPC overhead during matches.
2. **Threefold Repetition & Path History**:
   Add a 1,024-ply game history stack to N2 for exact threefold repetition detection across the entire game.
3. **Static Exchange Evaluation (SEE)**:
   Implement native bitboard SEE to prune losing captures in quiescence search and order winning captures ahead of equal captures.
4. **Controlled Gauntlet Validation vs Stockfish 19 & Python K0**:
   Run a 200-game match between Python K0 and Native N2 under standard time controls to measure empirical Elo gains from native search depth.

