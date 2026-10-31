# Project Janus v0.40 — Search Invariants and Correctness Audit

## 1. Executive Summary

This audit establishes, verifies, and codifies the core search invariants of Project Janus v0.40 across iterative deepening, alpha-beta negamax, quiescence search, check-evasion handling, move ordering, and search interruption contracts.

All 14 mandatory correctness invariants have been formalized and verified by the automated test suite [`tests/test_v040_search_invariants.py`](file:///E:/ChessXML/project-janus/tests/test_v040_search_invariants.py).

---

## 2. Invariant Specifications and Verification Matrix

| ID | Search Invariant | Requirement | Verification Method | Status |
| :---: | :--- | :--- | :--- | :---: |
| **INV-01** | **Root Checkmate** | When board is checkmated at root, search immediately returns score `-MATE_SCORE` (`-30,000`), depth 0, and `best_move = None`. | Tested on Fool's Mate position (`rnb1kbnr/pppp1ppp/4p3/8/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3`). | **VERIFIED** |
| **INV-02** | **Root Stalemate** | When board is stalemated at root, search immediately returns score `0`, depth 0, and `best_move = None`. | Tested on K+Q vs K stalemate (`7k/5Q2/6K1/8/8/8/8/8 b - - 0 1`). | **VERIFIED** |
| **INV-03** | **Check Evasions** | When side to move is in check, returned move must be legal and strictly relieve check. | Tested with Scholar's check position; `board.is_check()` verified false after move push. | **VERIFIED** |
| **INV-04** | **No Legal Evasions** | Terminal score in check with zero legal evasions returns `-MATE_SCORE + ply`. | Tested with `8/8/8/8/8/5K2/6Q1/7k b - - 0 1` at ply 2. | **VERIFIED** |
| **INV-05** | **Losing Check Evasions** | Losing check evasions must never be masked by a neutral score or cutoff. | Tested on bare king in check vs Queen (`7k/8/8/8/8/8/8/4q1K1 w - - 0 1`); score confirmed $< -500$ cp. | **VERIFIED** |
| **INV-06** | **Quiescence Ply Cap** | Quiescence reaches hard ply ceiling (`qsearch_hard_limit = qsearch_max_ply + 8`) without unbounded recursion. | Tested with restricted `qsearch_max_ply = 2`. | **VERIFIED** |
| **INV-07** | **Early Interruption** | Interruption before depth 1 finishes returns completed depth 0 and legal ordered fallback move. | Tested with immediate `stop_event.set()`. | **VERIFIED** |
| **INV-08** | **Deep Interruption** | Interruption during depth $d > 1$ cleanly terminates and preserves completed depth $\ge 1$. | Tested with 30ms tight time budget on standard startpos. | **VERIFIED** |
| **INV-09** | **Iteration Preservation** | Interrupted deeper iteration never overwrites `best_move`, `best_score`, or `best_pv` of last completed iteration. | Verified via mock negamax hook simulating mid-iteration abort at depth 3. | **VERIFIED** |
| **INV-10** | **Defensive Fallback** | Fallback move at depth 0 is selected via move ordering rather than arbitrary index. | Tested with depth 0 abort; move confirmed legal and matching `ordered_root[0]`. | **VERIFIED** |
| **INV-11** | **Mate Score Distance** | Mate scores correctly reflect ply distance: mate in 1 ply returns `MATE_SCORE - 1`. | Tested on queen mate in 1 (`8/7k/5K2/6Q1/8/8/8/8 w - - 0 1`); score verified `29,999`. | **VERIFIED** |
| **INV-12** | **Board Restoration** | Board move stack and FEN are perfectly restored after complete search or timeout. | Verified initial vs post-search FEN and move stack equality. | **VERIFIED** |
| **INV-13** | **Repetition Paths** | Entering or leaving repetition-prone paths does not crash or corrupt internal search state. | Tested on cyclic knight moves (`Nf3-Nf6-Ng1-Ng8`). | **VERIFIED** |
| **INV-14** | **Determinism** | Two independent searches on identical positions with identical configurations yield identical moves and scores. | Verified exact equality of `best_move`, `score`, and `nodes`. | **VERIFIED** |

---

## 3. UCI Search Interruption Contract

A critical engineering guarantee in Project Janus v0.40:
1. **Never Publish Partial Scores:**
   In [search.py](file:///E:/ChessXML/project-janus/src/janus/search.py#L1120-L1135), the update of `best_pv`, `best_move`, `best_score`, and `completed_depth` is strictly conditional on the iteration completing without `SearchTimeout`:
   ```python
   except SearchTimeout:
       break

   # Only publish results from fully completed iterations.
   if pv:
       best_pv = pv
       best_move = pv[0]
   best_score = score
   completed_depth = depth
   ```
2. **Defensive Fallback Ordering:**
   Before depth 1 begins, `ordered_root = self._ordered_moves(board, None, 0)` initializes `best_move = ordered_root[0]`. This guarantees that if the search is aborted before depth 1 finishes (e.g. within 1 millisecond), the engine emits the most promising legal move (e.g. captures or center control) rather than an arbitrary move.

