# Reverse Futility Pruning (RFP) Implementation Audit — v0.44

**Milestone:** Project Janus v0.44  
**Date:** 2026-11-03  
**Auditor:** Autonomous Senior Chess-Engine Researcher & Search Algorithm Engineer  
**Status:** COMPLETE (Gate B Validated)

---

## 1. Executive Summary

Reverse Futility Pruning (also known as Static Null Move Pruning) was introduced into Project Janus to safely prune search subtrees at frontier depths (depths 1 and 2) where the side to move already possesses a static positional advantage so substantial that failing high ($\ge \beta$) is deemed near-certain.

In the v0.43 100-opening-pair independent replication (400 games against Stockfish 19 at Elo 1320), RFP demonstrated an aggregate search-node reduction of 6.25% and an effective search depth increase of +0.12 plies. However, this search efficiency translated into a net playing score deficit:
- **Baseline K0:** 123.0 / 200 (61.50%)
- **Candidate RFP:** 119.5 / 200 (59.75%)
- **Paired delta:** $\bar{\Delta} = -0.0350$ points/pair ($t = -0.3940$, $p = 0.6528$, 95% CI $[-0.2050, +0.1400]$)

This audit establishes the formal mathematical specification, structural guards, control flow placement, and theoretical vulnerability landscape of the v0.43/v0.44 RFP implementation in `src/janus/search.py`.

---

## 2. Mathematical Decision Rule & Specification

The RFP decision logic is implemented at lines 812–828 of [`src/janus/search.py`](file:///E:/ChessXML/project-janus/src/janus/search.py#L812-L828):

```python
# Reverse Futility Pruning (RFP / Static Null Move Pruning)
if (
    self.enable_rfp
    and ply > 0
    and not in_check
    and depth <= self.rfp_max_depth
    and abs(beta) < MATE_THRESHOLD
    and abs(alpha) < MATE_THRESHOLD
    and board.halfmove_clock < 140
):
    self.rfp_considered += 1
    static_eval = evaluate_side_to_move(board, config=self.eval_config)
    rfp_margin = self.rfp_margin_per_depth * depth
    if static_eval - rfp_margin >= beta:
        self.rfp_cutoffs += 1
        self._store_tt(key, depth, beta, "lower", tt_move, ply)
        return beta, []
```

### Formal Formulation

Let:
- $d \in \{1, 2\}$ be the remaining nominal search depth (`depth <= self.rfp_max_depth`).
- $p > 0$ be the distance from the search root (`ply > 0`).
- $S(s)$ be the static positional evaluation from the perspective of the side to move at state $s$ (`evaluate_side_to_move`).
- $\beta$ be the upper bound of the current alpha-beta window.
- $M(d) = d \times M_{\text{per\_depth}}$ be the depth-scaled pruning margin, where $M_{\text{per\_depth}} = 120\text{ cp}$.
- $T_{\text{mate}} = 20000$ (`MATE_THRESHOLD`).
- $H(s)$ be the halfmove clock (`board.halfmove_clock`).

The pruning predicate $P_{\text{RFP}}(s, d, \alpha, \beta, p)$ is defined as:

$$P_{\text{RFP}} \iff (p > 0) \land (\neg \text{InCheck}(s)) \land (d \le d_{\max}) \land (|\beta| < T_{\text{mate}}) \land (|\alpha| < T_{\text{mate}}) \land (H(s) < 140) \land (S(s) - M(d) \ge \beta)$$

When $P_{\text{RFP}}$ evaluates to `True`:
1. Increment counter `rfp_cutoffs`.
2. Store lower-bound entry in transposition table: $\text{TT}[key] \leftarrow (d, \beta, \text{"lower"}, \text{tt\_move}, p)$.
3. Terminate search of the current subtree immediately and return fail-hard value $(\beta, [])$.

---

## 3. Structural Guard Audit

| Guard | Implementation | Purpose & Assessment | Correctness Verdict |
|---|---|---|---|
| **Root Protection** | `ply > 0` | Guarantees RFP never triggers at the search root. The root must always evaluate legal moves to produce a PV move. | **SOUND** |
| **Check Invalidation** | `not in_check` | Evasion moves are forced in check; static evaluation has no awareness of check evasion or checkmate. | **SOUND** |
| **Depth Horizon** | `depth <= self.rfp_max_depth` (default 2) | Limits pruning strictly to frontier plies (depth 1: margin 120 cp; depth 2: margin 240 cp). | **SOUND** |
| **Mate Bounds** | `abs(beta) < MATE_THRESHOLD and abs(alpha) < MATE_THRESHOLD` | Prevents pruning when a forced mate sequence is within or near the window. | **SOUND** |
| **Draw Rule Horizon** | `board.halfmove_clock < 140` | Prevents pruning near the 75-move mandatory draw / 50-move claim rule where static evaluation cannot account for an impending draw. | **SOUND** |
| **Transposition Table Cache** | `self._store_tt(key, depth, beta, "lower", tt_move, ply)` | Correctly stores $\beta$ as a `"lower"` bound with the probe-inherited move. | **SOUND** |
| **Fail-Hard Value** | `return beta, []` | Conforms to Janus's fail-hard negamax framework. | **SOUND** |

---

## 4. Architectural Interactions & Flaws

Despite the structural guards being mathematically well-formed, this audit identifies four key theoretical vulnerabilities in the interaction between RFP and Janus's overall search and evaluation pipeline:

### 4.1 Lack of Zugzwang / Piece-Count Guard
- Unlike Null Move Pruning (`self._has_nmp_material(board)` at line 840), RFP contains **no piece-count or endgame material guard**.
- In king-and-pawn endgames or zugzwang positions, having a large static evaluation does not guarantee that the side to move can maintain that evaluation when forced to move. If every legal move loses a pawn or yields key squares, assuming a beta cutoff based purely on static evaluation creates false fail-highs.

### 4.2 Tactical Blindspots & Hanging Pieces
- `evaluate_side_to_move` computes static material and piece-square values without tactical search.
- If the side to move has an undefended major piece or is subjected to an unpreventable tactical motif (fork, skewer, trapped piece, discovered check on the next ply), `static_eval` overestimates the true score by up to the full piece value ($300\text{--}900\text{ cp}$).
- At depth 1, the margin is only $120\text{ cp}$. If side to move is statically $+200\text{ cp}$ (e.g. up two pawns), but has a knight or bishop hanging to a tactical capture, $S(s) - 120 = +80 \ge \beta$ (if $\beta \le +80$). RFP prunes without searching the recapture or defense.

### 4.3 Quiescence Search Discrepancy
- At depth 0, Janus invokes `_quiescence(board, alpha, beta, ply)`, where stand-pat pruning occurs if $S(s) \ge \beta$. However, quiescence search then verifies captures: if the opponent has captures, they are explored.
- In contrast, RFP at depth 1 prunes the node entirely without ever entering quiescence search if $S(s) - 120 \ge \beta$. If the opponent's threat exceeds $120\text{ cp}$, the tactical threat is completely missed.

### 4.4 Black Defense Asymmetry (Empirical Link)
- In the v0.43 replication, RFP White performance matched K0 exactly ($64.5\%$). However, Black performance dropped from $58.5\%$ to $55.0\%$ ($-3.5\%$, 7 fewer game points).
- When playing Black against Stockfish, Black is frequently under aggressive tactical pressure. If RFP prunes defensive variations on frontier nodes because Black appears statically fine, Black fails to find the critical defensive resources.

---

## 5. Gate B Conclusion & Sign-Off

The implementation of RFP in `src/janus/search.py` is verified to be syntactically, mechanically, and procedurally correct according to standard static null move pruning specifications. The failure of RFP to improve playing strength is **not** caused by a coding bug or broken guard, but by **structural search vulnerabilities** (tactical blindspots at small margins and lack of zugzwang/tactical threat verification).

**Gate B Status:** **PASS** — Proceeding to Phase C (Position-Level Diagnostic Instrumentation).

