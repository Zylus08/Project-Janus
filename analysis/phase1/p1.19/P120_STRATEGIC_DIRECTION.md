# Strategic Direction for Milestone P1.20: Advanced Search Pruning & Dynamic Classical Evaluation

## 1. Executive Summary & Context

Milestones P1.18 and P1.19 rigorously evaluated classical pawn structure (backward pawns) and naive king-file exposure under strictly controlled non-ML conditions.
- Milestone P1.18 demonstrated that combining backward pawns with naive king-file exposure produced severe regression (-59.5 Elo).
- Milestone P1.19 established that cleanly isolating backward pawns recovered +28.1 Elo, eliminating king-safety blunders, but isolated backward pawns still failed to produce positive Elo gains at fast time controls (48.0%, -13.9 Elo) and suffered severe regression at slow time controls (37.0%, -92.5 Elo, $p = 0.0129$).
- Consequently, **Candidate X24 was rejected (Category C)**, and **Reference X22 (`e33f292`)** remains the active foundation for future research.

Milestone P1.20 must break out of the static penalty paradigm and focus on **dynamic, search-aligned classical evaluation** and **selective search tree deepening**.

---

## 2. Core Strategic Pillars for Milestone P1.20

### Pillar 1: Connected Passed Pawns & Candidate Passer Topology
- **Current Limitation:** In Janus Classical X22 and X24, passed pawns receive identical bonuses regardless of whether they are isolated, backward-supported, or connected. In endgames, isolated passed pawns are easily blockaded and rounded up by opposing rooks.
- **P1.20 Objective:**
  - Leverage the 64K pawn hash table to classify passed pawns into three distinct categories:
    1. *Connected Passed Pawns*: Adjacent passed pawns that defend each other or can advance in tandem (+30 mg / +50 eg bonus).
    2. *Protected Passed Pawns*: Passed pawns supported from behind by a friendly pawn (+20 mg / +35 eg bonus).
    3. *Candidate Passed Pawns*: Unopposed pawns with a flank majority that can force a breakthrough.
  - Zero search-time overhead: All calculations execute inside `evaluate_pawns()` and are cached in the direct-mapped pawn table.

### Pillar 2: Dynamic King Safety Zone (Attacking Piece Weighting)
- **Current Limitation:** Naive open-file penalties (Track B) failed because they penalized the king's file even when the opponent possessed no pieces capable of attacking.
- **P1.20 Objective:**
  - Implement a classical 12-square King Danger Zone.
  - Count the number of enemy attackers aiming at the king zone.
  - Compute a quadratic attacker score:
    $$\text{KingDanger} = \frac{(\text{AttackerWeightSum})^2}{100}$$
  - Only penalize king exposure when the opponent has at least two attacking minor/major pieces threatening the shelter.

### Pillar 3: Trapped & Dominated Piece Detection
- **Current Limitation:** In matches against Stockfish 4 and 11, Janus frequently conceded piece activity by allowing minor pieces to become trapped on the edge behind enemy pawn chains.
- **P1.20 Objective:**
  - Detect trapped bishops on a7/b8/h7/g8 dominated by enemy pawns on b6/c7/g6/f7.
  - Detect trapped knights on a8/h8 with zero legal moves.
  - Impose an immediate penalty ($-80\text{ cp}$) to ensure the search avoids these dead-end positions.

### Pillar 4: Selective Search Pruning (Singular Extensions or ProbCut)
- **Current Limitation:** Search depth remains limited to 8–10 plies at 1.0s, leaving the engine vulnerable to tactical shots discovered by deeper historical references.
- **P1.20 Objective:**
  - Investigate **Singular Extensions (S1)**: When a TT move exceeds the second-best move by a significant margin ($\ge 30\text{ cp}$ at depth $\ge 8$), extend the search by 1 ply.
  - Investigate **ProbCut (P1)**: In tactical positions with shallow null-move cutoffs, prune non-competitive branches to deepen critical PV lines.

---

## 3. Baselines & Experimental Controls for P1.20

| Engine Identifier | Version / Commit | Architectural Role | Checksum |
| :--- | :--- | :--- | :--- |
| **Janus Classical X7** | Commit `b34e342` | Qualified 1T Strength Baseline | `86392A2F4BD4182A...` |
| **Janus Classical X12** | Commit `78ca3d5` | Qualified 4T Strength Baseline | `00B4F5FEDEA02A39...` |
| **Janus Classical X22** | Commit `e33f292` | Active Research Reference | `35D095CFFE8A2EDA...` |
| **Janus Classical X24** | Milestone P1.19 | Historical Control (Track A Isolated) | `D8BE5521B91A353C...` |
| **Stockfish 4** | 2014 Classical | Historical External Benchmark | `1128CAB833860633...` |
| **Stockfish 11** | 2020 Classical | Mature External Benchmark | `B004C03BD71BB84E...` |
| **Stockfish 19** | NNUE | Ultimate SOTA Benchmark | `45BC8E4969147DB9...` |

---

## 4. Mandatory Milestone Protocol for P1.20

1. **Strict Charter Adherence:** No neural networks, NNUE, learned parameters, SPSA, or Texel tuning.
2. **Atomic Verification:** Each feature must be tested independently before combination.
3. **Multi-TC Battery:** All candidates must pass both blitz (1.0s + 50ms) and slow time control (3.0s + 100ms) with zero degradation.
4. **Adversarial Harness Certification:** The 15-case referee suite must be executed prior to any tournament games.
5. **Single Atomic Commit:** Milestone conclusion must occur on branch `phase1/classical-janus` with zero remote git push.
