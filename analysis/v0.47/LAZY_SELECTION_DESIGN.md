# Lazy Move Selection Design (v0.47 Phase C)

## 1. Objectives & Invariance Requirements

1. **Exact Semantic Equivalence:** The sequence of moves yielded by the lazy selector must match the sequence produced by K0's eager `moves.sort()` for any search node.
2. **On-Demand Selection:** Rather than sorting all moves upfront, moves are selected incrementally. If move 0 causes a beta cutoff, remaining moves are never evaluated or sorted.
3. **Preservation of Ties & Edge Cases:** If two moves have equal scores, the tie-breaking behavior must preserve the original order in `board.legal_moves`.
4. **Zero State Side Effects:** Selection must not alter board state, search depth, or evaluation weights.

## 2. Evaluation of Strategies

### Strategy A: Incremental Selection (Selection Sort / In-Place Swapping)
- Generate `moves = list(board.legal_moves)`.
- At step $i$ from $0$ to $N-1$:
  - Compute scores for moves $j \in [i, N-1]$ (or use cached scores).
  - Find the index with the maximum score (maintaining stability on ties).
  - Swap the maximum move to position $i$ and yield it.
- **Cost:** If cutoff occurs at move $0$, only 1 pass of scoring is performed. If cutoff occurs at move $k \ll N$, only $k$ selections are made.
- **Pros:** 100% equivalent to K0, simple, zero risk of missing/duplicating moves, no generator state corruption.

### Strategy B: Staged Move Generator (`MovePicker`)
- Separate moves into discrete stages:
  - Stage 0: TT move.
  - Stage 1: Captures & promotions (scored & sorted).
  - Stage 2: Killers & countermove.
  - Stage 3: Remaining quiets (scored by history).
- **Pros:** Avoids scoring quiet moves when a capture causes a cutoff.
- **Cons in Python:** Generating pseudo-legal moves or partitioning Python lists introduces substantial object overhead in Python that can exceed the simple C-level Timsort time if not carefully tuned.

### Selected Candidate Design: Strategy A with Score Caching (Incremental In-Place Selection)
An incremental selection approach (`_select_ordered_moves` or an iterator `_iter_ordered_moves`):
When `enable_lazy_move_selection` is True:
1. `moves = list(board.legal_moves)`
2. Maintain a list of precomputed scores or compute on the fly:
   - For $i=0$: evaluate `_move_order_score` for all moves (or lazy evaluate), pick max, swap to $0$, yield move.
   - If move 0 causes cutoff, loop breaks immediately! $O(N)$ instead of $O(N \log N)$ + Python lambda sort overhead.
   - For $i=1$: pick next max from $1 \dots N-1$, swap to $1$, yield move.
Even simpler and faster in Python:
Pre-score all moves into a list of tuples `[(score, original_idx, move), ...]`:
Wait, does pre-scoring all moves still cost time? Yes, scoring takes time, but in Python `list.sort()` is in C while lambda calls in Python are slow.
Let's see: can we do a generator that yields:
- Step 1: If `tt_move` is in legal moves, yield `tt_move` immediately without scoring any other moves!
  - Remember from v0.46 telemetry: **TT cutoffs occur in $21.15\%$ of cutoffs**!
  - If TT move is legal, yielding it first costs $O(1)$ and **zero** other moves are scored or sorted if it cuts off!
- Step 2: If TT move fails to cut off or is None, then generate/score remaining moves.

Let's design `_ordered_moves_iter(board, tt_move, ply, prev_move)`:
```python
def _ordered_moves_iter(
    self,
    board: chess.Board,
    tt_move: Optional[chess.Move] = None,
    ply: int = 0,
    prev_move: Optional[chess.Move] = None,
) -> Iterator[chess.Move]:
```
1. `legal_moves = list(board.legal_moves)`
2. If `len(legal_moves) <= 1`:
   yield from legal_moves; return
3. If `tt_move` in legal_moves:
   yield tt_move
   # Remove tt_move from remaining
   remaining = [m for m in legal_moves if m != tt_move]
4. For remaining moves:
   - Use selection / partial sort or score.
   - In fact, if we score remaining moves with decorated tuples `(score, -idx, move)` and sort them or incrementally pick them:
   Notice that sorting `remaining` *only when needed* (after TT move fails high) completely saves $100\%$ of sorting work at all TT cutoff nodes ($21.15\%$ of nodes)!
   Furthermore, we can test incremental max selection vs cached sort.

Let's test both variants in a quick benchmark script to verify exact equivalence and speed!

