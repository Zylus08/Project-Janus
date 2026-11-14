# Future Classical Evaluation Research & Architectural Roadmap

## 1. Principles of Non-ML Classical Evaluation Architecture

Project Janus operates under a strict, non-negotiable charter: **strictly non-ML classical computer chess**. Zero neural networks, NNUE, offline model fitting, SPSA, or Texel tuning are permitted. All evaluation functions must be derived from first-principles chess geometry, material balances, piece-square tables, and human grandmaster understanding.

Milestones P1.16 through P1.19 provide fundamental empirical lessons on how handcrafted classical evaluation terms behave in modern alpha-beta search engines.

---

## 2. Lessons from P1.18 and P1.19 Evaluation Experiments

### 2.1 The "Piecemeal Handcrafted Term" Trap
In Milestone P1.18, two features were added simultaneously:
- Track A: Backward pawns ($-10\text{ mg} / -15\text{ eg}$)
- Track B: King-file exposure ($-20\text{ mg} / -5\text{ eg}$)
This combination resulted in severe competitive regression (Match Dev-3: 41.5%, -59.5 Elo).

In Milestone P1.19, Track A was cleanly isolated and audited. The results across 570 authoritative games demonstrate:
1. **Isolated Track A is Non-Harmful at Blitz (48.0%), but Regressive at Slow TC (37.0%):**
   - At fast time controls (0.5s–1.0s), backward pawn penalties neither significantly hurt nor help ($p > 0.50$).
   - At slow time controls (3.0s + 100ms), search depth increases to 11–13 plies. At this depth, static evaluation penalties for backward pawns cause the engine to reject tactical sacrifices, dynamic counterplay, and active rook endgames in favor of defending structurally weak but tactically irrelevant pawns.
2. **Static Penalties Suppress Tactical Dynamism:**
   - Classical engines derive playing strength primarily from piece activity, line clearance, and tactical initiative. Penalizing static pawn defects without verifying whether the opponent can actually exploit the weakness creates "ghost fears" that cripple the engine's ambition.

### 2.2 The Success of the 64K Direct-Mapped Pawn Hash Table
While the backward-pawn term itself did not produce Elo gains, the **64K pawn-structure hash table architecture** introduced in P1.18 and verified in P1.19 is a major engineering breakthrough:
- **100% Cache Invariance:** $\text{eval}(B)_{\text{warm}} \equiv \text{eval}(B)_{\text{cold}} \equiv \text{eval}(B)_{\text{disabled}}$ (0/500 mismatches).
- **Evaluation Speedup:** Measured raw evaluation latency dropped from $1374.3\text{ ns}$ to $1187.7\text{ ns}$ (+13.58% acceleration).
- **Search Throughput:** Search NPS expanded by +52% in pawn-heavy positions, providing headroom for more sophisticated classical pawn-structure calculations.

---

## 3. High-Priority Classical Evaluation Research Targets for P1.20+

Future milestones should avoid isolated negative penalties and focus on positive incentives that align with search dynamics:

### 3.1 Connected & Supported Passed Pawns
- **Weakness in X24:** Candidate X24 rewards passed pawns uniformly by rank, but treats isolated passed pawns and connected passed pawns identically.
- **Proposed Feature:** Introduce connected passed pawn bonuses (pawns on adjacent files that protect each other or can advance in tandem) and candidate passers (pawns with no opposing pawns on their file and a majority on adjacent files).
- **Pawn-Hash Caching:** Passed pawn topology is static with respect to piece moves and should be computed entirely within `evaluate_pawns()` and stored in the 64K pawn hash table.

### 3.2 Dynamic King Safety & Attacking Piece Weights
- **Lesson of Track B:** Static file penalties ($-20\text{ cp}$ for an open file near the king) fail because they punish the king even when the opponent has zero heavy pieces capable of infiltrating the file.
- **Proposed Feature:** Implement a classical "Attacking King Zone" model:
  - Define a 12-square king zone (the 8 surrounding squares plus 4 forward squares).
  - Count the number and types of enemy pieces attacking squares in the king zone (e.g. Knight = 2 pts, Bishop = 2 pts, Rook = 3 pts, Queen = 5 pts).
  - Apply king safety penalties non-linearly only when the attacking score exceeds a threshold (e.g. $\ge 2$ attackers).

### 3.3 Trapped & Dominated Piece Detection
- In Match 5 vs Stockfish 4, Janus frequently allowed its bishops or rooks to be entombed behind pawn chains (e.g. bishop on a7 blocked by b6/c7).
- Adding classical trapped piece penalties will prevent catastrophic positional concessions that currently escape standard mobility evaluation.

### 3.4 Piece-Pawn Endgame Interaction
- King proximity to passed pawns: implementing the "Square of the King" rule for pawn endgames and bonus for king advancement in front of passed pawns.
- Rook behind passed pawns (Tarrasch rule): rewarding rooks placed on the same file behind friendly or enemy passed pawns.

---

## 4. Methodological Protocol for Future Evaluation Milestones

To prevent the diagnostic confusion that arose in P1.16–P1.18, all future classical evaluation milestones must adhere to this five-stage protocol:
1. **Isolated Implementation:** Each evaluation term must be isolated behind an independent UCI option and toggleable without code churn.
2. **Pawn-Hash Coherence:** Any pawn-derived term must be computed inside the pawn hash calculation, with automatic table invalidation on mode switches.
3. **Generalization Atlas & Search Interaction Audit:** 100 held-out positions and diagnostic search trees must be evaluated before running tournaments.
4. **Adversarial Harness Verification:** The 15-case adversarial referee test must pass 100% to guarantee zero score-inversion or adjudication corruption.
5. **Slow TC Verification:** Any proposed candidate must be tested at both fast blitz (1.0s + 50ms) and slow time control (3.0s + 100ms) to ensure no deep-search degradation occurs.
