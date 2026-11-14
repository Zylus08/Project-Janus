# Milestone P1.20 Architectural Decision Gate

## 1. Decision Statement & Governing Constraints

Based on the forensic investigations across Phases 0 through 6, the independent statistical audit panel and classical chess engine architects formally select:

### **SELECTED INTERVENTION: OPTION B — DYNAMIC PASSED-PAWN ARCHITECTURE (CONNECTED & SUPPORTED PASSERS)**

### Permitted Scope & Exclusions:
1. **Single Intervention Invariant:** Exactly **one** architectural intervention is authorized for Milestone P1.20: **Connected and Supported Passed Pawns**.
2. **Strict Non-ML Charter:** No neural networks, NNUE, offline coefficient fitting, SPSA, or Texel tuning. All coefficients are manually documented from classical chess geometry.
3. **Explicit Exclusions:**
   - Singular Extensions (S1) are **EXCLUDED**.
   - ProbCut (P1) is **EXCLUDED**.
   - Multi-Cut (C1) is **EXCLUDED**.
   - King-file exposure / attack-route modifications are **EXCLUDED**.
   - Simultaneous bundling of multiple evaluation families is **EXCLUDED**.
4. **Foundation Invariant:** The intervention must be built directly on top of the certified **Janus Classical X22 (`e33f292`)** source foundation. Rejected Candidate X24 remains archived and unpromoted.

---

## 2. Epistemological Justification for Option B

### 2.1 The Failure of Static Negative Penalties
Milestones P1.18 and P1.19 established that adding static penalties for structural defects (backward pawns: $-10\text{ mg} / -15\text{ eg}$; king-file exposure: $-15$ to $-40\text{ mg}$) produces passivity and tactical fragility:
- Backward-pawn penalties caused the engine to tie down rooks to defend weak pawns rather than seeking active counterplay.
- At slower time controls ($3.0\text{s} + 100\text{ms}$), deeper search trees discovered that passive defense cannot hold active endgames, causing Candidate X24 to collapse to $37.0\%$ against Baseline X7 ($p = 0.0129$).

### 2.2 Why Connected Passed Pawns Address the Root Cause
1. **Active Forward Ambition:** Unlike backward-pawn penalties (which restrict play), connected passed pawn bonuses reward aggressive forward advancement and pawn coordination.
2. **Endgame Parity with Baseline X7:** In Match 4, Baseline X7 dominated endgames by marching connected passed pawns that Janus Classical X22 and X24 undervalued. Rewarding connected passers ensures that Janus Classical values pawn rolling formations correctly.
3. **Pawn-Hash Zero-Overhead Caching:**
   - Because passed pawn connectivity depends strictly on pawn bitboards, the entire calculation is executed inside `evaluate_pawns()`.
   - The result is cached in the 64K-entry direct-mapped pawn hash table, resulting in **$0.0\%$ search throughput penalty** ($+13.58\%$ eval speedup maintained).

---

## 3. Detailed Specification of the Architectural Intervention

### 3.1 Feature Formulation
In `evaluate_pawns(const NativeBoard* b, int mg[2], int eg[2])`:
For each passed pawn on square $sq$ (file $f$, rank $r$):
1. **Connected Passed Pawn Bonus:**
   - If there is another friendly passed pawn on an adjacent file ($f-1$ or $f+1$) within $\pm 1$ rank of $sq$:
     - Midgame Bonus: $+20\text{ cp}$
     - Endgame Bonus: $+35\text{ cp}$
   - If both pawns are on the 5th, 6th, or 7th rank:
     - Midgame Bonus: $+30\text{ cp}$
     - Endgame Bonus: $+55\text{ cp}$
2. **Supported Passed Pawn Bonus:**
   - If the passed pawn is directly defended from behind by a friendly pawn (pawn on $sq - 7$ or $sq - 9$ for White; $sq + 7$ or $sq + 9$ for Black):
     - Midgame Bonus: $+15\text{ cp}$
     - Endgame Bonus: $+25\text{ cp}$

### 3.2 Runtime Controls & Test Invariants
- Controllable via runtime option: `UCI_ConnectedPawns` (type `check`, default `true`).
- When `UCI_ConnectedPawns` is set to `false`, the engine must revert to bitwise parity with Reference X22.
- Pawn cache invalidation: Mode toggle must invoke `clear_pawn_table()`.
- Anti-symmetry invariant: Must pass 100% color inversion symmetry ($\text{eval}(W) \equiv -\text{eval}(B)$).
