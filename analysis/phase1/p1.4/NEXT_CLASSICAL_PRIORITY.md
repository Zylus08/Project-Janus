# Project Janus — Phase 1, Milestone P1.4
## Strategic Architecture & Next Classical Engineering Priority (Milestone P1.5)

**Author:** Principal Computer Chess Engineer, C++17 Performance Architect, Search Algorithm Researcher, Statistical Experimentalist, and Independent Reproducibility Auditor  
**Lineage:** Janus Classical X  
**Current Qualified Classical Baseline:** Janus Classical X7 (`b34e342`)  
**Target Milestone:** Phase 1, Milestone P1.5  
**Date:** November 2026  
**Governing Rule 1:** Strictly Non-ML (Zero neural evaluation, zero NNUE, zero learned weights, zero offline-fitted models)

---

### 1. Strategic Context & Motivation

Milestone P1.4 definitively established the fundamental bottleneck currently capping the playing strength of Janus Classical X:
- **Search selectivity is limited by evaluation accuracy.** Introducing verification-search selectivity (such as Singular Extensions) before the evaluation function possesses sufficient positional discernment imposes an unacceptable nominal depth tax without yielding positive Elo.
- **Move ordering has reached a plateau under current evaluation.** The Countermove Heuristic successfully recovered +42.1 Elo over X8, bringing Candidate X9 to statistical parity with Baseline X7 (48.50%, $p = 0.5755$), but could not surpass X7 because both engines rely on the same basic Handcrafted Evaluation (E5: material + piece-square tables + basic pawn structure).
- **Stockfish 19's overwhelming superiority stems from positional knowledge.** While Janus searches 12–15 plies at blitz time controls, it suffers from severe positional blindness: it misjudges passed pawn potential, permits damaging pawn storms against its king, misplaces rooks on closed files, and undervalues piece coordination.

Therefore, **Milestone P1.5 must pivot directly to Classical Evaluation Expressiveness (E6) and Dynamic Time Management**, rather than introducing further unconstrained selective search extensions.

---

### 2. Primary Engineering Focus 1: Handcrafted Evaluation Expressiveness (E6)

The current classical evaluation function (E5) uses simple tapered evaluation based on material counts and basic $8 \times 8$ Piece-Square Tables (PST) with rudimentary pawn penalties. Milestone P1.5 will introduce four fully classical, non-ML positional evaluation modules:

#### A. Bitboard-Accelerated Passed Pawn Evaluation
- **Passed Pawn Mask Generation:** Precompute forward-span and adjacent-file bitboard masks `passed_pawn_mask[color][square]`. A pawn is passed if `(their_pawns & passed_pawn_mask[color][square]) == 0`.
- **Rank-Advancement Scaling:** Grant non-linear rank advancement bonuses that sharply escalate as pawns reach the 5th, 6th, and 7th ranks:
  $$\text{Bonus}(r) = W_{\text{passed}}[r] \quad (r \in [4, 7])$$
- **Protected & Connected Passed Pawns:** Award substantial additional bonuses if a passed pawn is defended by a friendly pawn or supported abreast on an adjacent file.
- **King Proximity to Passed Pawns:** In the endgame phase, scale passed pawn values based on the distance of both the friendly and enemy kings:
  $$\Delta_{\text{king}} = (\text{ChebyshevDist}(K_{\text{enemy}}, \text{sq}) \times 2) - \text{ChebyshevDist}(K_{\text{friendly}}, \text{sq})$$

#### B. King Safety, Pawn Shelter & Storm Evaluation
- **Pawn Shield Bitboards:** Evaluate the 3 squares immediately in front of the castled king (e.g., $f2/g2/h2$ for White kingside). Deduct penalties for missing shield pawns or advanced pawns (e.g., $h3$ creating a hook).
- **Enemy Pawn Storm Detection:** Detect approaching enemy pawns on files adjacent to the friendly king, penalizing opened files and forward enemy pawn advances.
- **Virtual Queen Attack Zones:** Count the number and weight of attacking enemy pieces directing mobility or checks into the $3 \times 3$ perimeter surrounding the king.

#### C. Piece Activity & Structural Coordination
- **Rooks on Open & Semi-Open Files:** Award bonuses for rooks situated on files with no pawns (open file) or only enemy pawns (semi-open file).
- **Connected Rooks:** Award a coordination bonus when two rooks share a rank or file with zero intervening pieces.
- **Knight Outposts:** Identify outpost squares on ranks 4, 5, and 6 that cannot be attacked by enemy pawns and are defended by a friendly pawn.
- **Bishop Pair Bonus:** Provide a persistent endgame bonus for retaining both bishops against knight pairs or bishop-and-knight configurations.

---

### 3. Primary Engineering Focus 2: Dynamic Time Management

Under the current fixed time allocation scheme, Janus allocates a static slice of its remaining clock:
$$t_{\text{target}} = \frac{t_{\text{remaining}}}{N_{\text{moves\_to\_go}}} + \text{inc}$$

This uniform allocation is severely sub-optimal:
1. **Easy Move Waste:** In forced recapture sequences, single legal responses, or obvious book positions, the engine expends its full target time instead of moving instantly.
2. **Critical Position Starvation:** In positions where the best move changes repeatedly across successive iterative deepening plies (move instability) or the root evaluation drops precipitously, the engine terminates search prematurely due to a rigid hard clock cap.

#### Milestone P1.5 Time Management Architecture:
- **Move Stability Factor ($F_{\text{stab}}$):** If the best move at the root remains unchanged across the last 3 iterative deepening depths, scale down the time budget: $F_{\text{stab}} \in [0.6, 1.0]$. If the best move fluctuates, expand the budget: $F_{\text{stab}} \in [1.0, 1.8]$.
- **Score Swing Factor ($F_{\text{swing}}$):** If the root score drops by $> 50$ cp between depth $d$ and $d-1$, allocate up to $2.0\times$ extra time to resolve the tactical emergency.
- **One-Legal-Move Fast Path:** If root move generation yields only 1 legal move, exit immediately at depth 1 in $< 1\text{ ms}$.

---

### 4. Primary Engineering Focus 3: Safe Shallow Pruning (LMP & History Pruning)

To offset any computational overhead introduced by the richer E6 evaluation function, P1.5 will incorporate shallow, non-verification pruning mechanisms:
- **Late Move Pruning (LMP):** At shallow depths ($d \le 3$), after searching a threshold number of quiet moves ($N_{\text{LMP}}(d) = 3 + 3 \times d^2$), prune remaining quiet moves in the move loop.
- **History Pruning:** At $d \le 3$, prune quiet moves whose accumulated history score falls below a negative threshold (e.g., $H < -2000 \times d$).

Unlike Singular Extensions, LMP and History Pruning involve **zero verification searches** and execute in $O(1)$ time, thereby saving tree nodes and directly boosting nominal search depth.

---

### 5. Preregistered Milestone P1.5 Experimental Protocol

1. **Baseline Control:** Janus Classical X7 (`b34e342`) remains the frozen control engine.
2. **Incremental Ablations:**
   - E6.1: Passed Pawn masks & advancement evaluation.
   - E6.2: King safety pawn shelters & enemy pawn storms.
   - E6.3: Rooks on open files & piece coordination.
   - TM1: Dynamic time management with move stability scaling.
   - SP1: Late Move Pruning & History Pruning.
3. **Correctness Qualification:** 12/12 Perft suites must pass bit-exact; UCI protocol compliance verified; zero memory leaks or dangling pointers.
4. **Preregistered Promotion Gate:**
   - A candidate engine (Janus Classical X10) will be promoted to the baseline registry if and only if it achieves a **statistically significant victory** against Baseline X7 in a 200-game match (100 opening pairs at 1.0s + 50ms):
     $$\text{Score} > 50.0\%, \quad p < 0.05 \text{ (paired } t\text{-test)}.$$
5. **Stockfish 19 Benchmark:** Execute a matched 40-game tournament (20 opening pairs at 2.0s + 50ms) to measure external defensive resistance and draw conversion rate against unrestricted Stockfish 19.

---

### 6. Summary

Milestone P1.4 demonstrated that search heuristics cannot overcome the physical horizon imposed by clock constraints when evaluation is shallow. By enriching Janus's positional evaluation function (E6), deploying dynamic time allocation, and trimming hopeless quiet branches via LMP, Milestone P1.5 will establish the positional foundation required to achieve genuine classical supremacy.

**Sign-off:**  
Principal Computer Chess Engineer & Independent Experimental Auditor.
