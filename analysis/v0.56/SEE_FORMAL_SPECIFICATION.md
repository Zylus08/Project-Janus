# Project Janus v0.56 — Native Static Exchange Evaluation Formal Specification

**Milestone:** v0.56  
**Architect:** Principal Chess Engine Architect & C++17 Search Systems Engineer  
**Date:** 2026-11-05  
**Component:** `janus_see(...)` Native C++17 Engine Function  
**Classification:** Formal Algorithmic Specification  

---

## 1. Objective and Theoretical Model

Static Exchange Evaluation (SEE) computes the expected material outcome of a capture or sequence of recaptures on a single target square under optimal play by both sides, assuming neither player is forced to recapture if doing so would lose material.

SEE evaluates material changes only. It does not perform a full tree search, positional evaluation, or checkmate detection.

### 1.1 Valuation Scale
SEE adheres strictly to Janus's established midgame piece evaluation scale (`MG_PIECE_VALUES`):
- **Pawn:** 100 centipawns
- **Knight:** 320 centipawns
- **Bishop:** 335 centipawns
- **Rook:** 500 centipawns
- **Queen:** 900 centipawns
- **King:** 20,000 centipawns (sentinel value)

---

## 2. Mathematical Exchange Model

Given a board state $B$ and an initial candidate move $m = (\text{from}, \text{to}, \text{flag}, \text{promo})$:

1. **Initial Gain Vector:**
   Let $d = 0$.
   $$\text{gain}[0] = V(\text{victim}) + \Delta V_{\text{promo}}$$
   where:
   - For en passant: $V(\text{victim}) = 100$, and the captured pawn on $(\text{to\_file}, \text{from\_rank})$ is removed.
   - For standard captures: $V(\text{victim})$ is the value of the enemy piece on $\text{to}$.
   - For promotions: $\Delta V_{\text{promo}} = V(\text{promo\_piece}) - V(\text{pawn})$.
   - The initial piece on $\text{to}$ becomes $P_0 = (\text{flag} == \text{promo} \ ? \ \text{promo\_piece} : \text{moving\_piece})$.

2. **Occupancy & Piece Tracking:**
   $$\text{occupied} = (\text{occupied}_{\text{initial}} \setminus \{\text{from}\}) \cup \{\text{to}\}$$
   $$\text{active\_mask} = \text{occupied}_{\text{initial}} \setminus \{\text{from}\}$$
   If en passant, the en passant square $\text{ep\_sq}$ is removed from both $\text{occupied}$ and $\text{active\_mask}$.

3. **Alternating Recapture Loop:**
   For $d = 1, 2, \dots, D_{\max}$ (with $D_{\max} = 32$):
   - Determine current side to move: $\text{cur\_side} = (\text{initial\_side} + d) \bmod 2$.
   - Find all attackers of $\text{to}$ for $\text{cur\_side}$ under the current $\text{occupied}$ and $\text{active\_mask}$.
   - Iterate through attacker piece types in ascending value order:
     $$\text{PAWN} \prec \text{KNIGHT} \prec \text{BISHOP} \prec \text{ROOK} \prec \text{QUEEN} \prec \text{KING}$$
   - Select the least valuable legal attacker $S_{\text{att}}$ of type $T_{\text{att}}$:
     - **King Legality Constraint:** The King may only recapture if $\text{to}$ is not attacked by the opponent after removing the piece on $\text{to}$ ($\text{occupied} \setminus \{\text{to}\}$).
     - **Pin Legality Constraint:** An attacker $S_{\text{att}}$ pinned to its King cannot recapture unless $\text{to}$ lies along the pin ray between the pinner and the King.
   - If no legal attacker exists for $\text{cur\_side}$, the exchange sequence terminates.
   - Otherwise:
     $$\text{gain}[d] = V(P_{d-1}) - \text{gain}[d-1]$$
     If a pawn recaptures onto rank 0 or rank 7, it promotes to Queen:
     $$\text{gain}[d] \leftarrow \text{gain}[d] + (V(\text{Queen}) - V(\text{Pawn}))$$
     $$P_d = \text{Queen}$$
     Otherwise, $P_d = T_{\text{att}}$.
     - Update state:
       $$\text{occupied} \leftarrow \text{occupied} \setminus \{S_{\text{att}}\}$$
       $$\text{active\_mask} \leftarrow \text{active\_mask} \setminus \{S_{\text{att}}\}$$

4. **Minimax Backward Pass:**
   Both players only recapture if doing so improves their net material standing:
   $$\text{For } d = D_{\text{final}} \text{ down to } 1:$$
   $$\text{gain}[d - 1] = -\max(-\text{gain}[d - 1], \text{gain}[d])$$
   The final net material gain for the side initiating move $m$ is $\text{gain}[0]$.

---

## 3. Corner Cases & Correctness Invariants

1. **X-Ray / Battery Revealing:**
   When a front piece departs $S_{\text{att}}$, its bit is cleared from $\text{occupied}$. Subsequent iterations query sliding attacks using the updated $\text{occupied}$ bitboard, automatically revealing rook, bishop, or queen batteries behind the departed piece.
2. **Absolute Pins:**
   A piece pinned to its King is prevented from recapturing off the pin ray. In Janus bitboards, this is verified by checking whether an enemy slider attacks the friendly King through $\text{temp\_occ} = (\text{occupied} \setminus \{S_{\text{att}}\}) \cup \{\text{to}\}$ with enemy slider on $\text{to}$ removed.
3. **King Encroachment:**
   A King cannot capture on a defended square under any circumstances.
4. **Promotion Material:**
   Both initial promotion captures and subsequent pawn promotions upon recapture on the back rank are evaluated at Queen value ($+800\text{ cp}$).
5. **Zero Allocation:**
   All temporary vectors ($\text{gain}[32]$, attacker bitboards) use fixed-size stack arrays without heap allocation.
6. **No Board Mutation:**
   `janus_see` takes `const NativeBoard* b` and never mutates board state, Zobrist keys, history, or TT.

---

## 4. Integration into Candidate N7 Move Scoring

When `UseSEEOrdering=true`:
1. **Winning Captures ($\text{SEE} > 0$):**
   Scored in $[100,000, 100,050]$, ordered by MVV-LVA (or $\text{SEE}$ score).
2. **Equal Captures ($\text{SEE} == 0$):**
   Scored at $95,000$, above Killer Move 1 ($90,000$).
3. **Losing Captures ($\text{SEE} < 0$):**
   Demoted to $[20,000 + \text{SEE}]$, below Killer Move 2 ($80,000$) and high history moves, but above unranked quiet moves ($0$).
4. **Non-Pruning Invariant:**
   All legal captures remain eligible for search. No captures are discarded.
