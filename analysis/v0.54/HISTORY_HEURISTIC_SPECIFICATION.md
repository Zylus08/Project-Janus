# PROJECT JANUS v0.54 — HISTORY HEURISTIC SPECIFICATION

**Phase:** Phase 3 — Formal History Heuristic Specification  
**Date:** 2026-11-05  
**Candidate Engine:** Janus Native N5  

---

## 1. Algorithmic Purpose

While the killer heuristic records move success localized to a specific tree ply, the **history heuristic** tracks the global success of quiet moves across the entire search tree. Moves from square $s_{from}$ to $s_{to}$ that repeatedly cause beta cutoffs across diverse positions and depths accumulate a high history score, allowing the engine to prioritize them whenever they are legal in any sub-branch.

---

## 2. Data Representation & Memory Layout

```cpp
// Static 3D Array: [side: 2][from_square: 64][to_square: 64]
constexpr int SIDES = 2;
constexpr int SQUARES = 64;
constexpr int MAX_HISTORY_SCORE = 70000;

static int g_history_table[SIDES][SQUARES][SQUARES];
```

- **Footprint:** $2 \times 64 \times 64 \times 4 \text{ bytes} = 32,768 \text{ bytes (32 KB)}$.
- Statically allocated in BSS segment; zero dynamic memory allocations during search.

---

## 3. Update Policy & Bounded Reinforcement

### 3.1 Positive Reinforcement on Beta Cutoff
When a quiet move $m$ (from square `from`, to square `to`) executed by side `b->side_to_move` causes a beta cutoff ($alpha \ge beta$) at depth $d$:

```cpp
if (g_use_history_ordering) {
    bool is_quiet = (undo.captured_piece == NO_PIECE) && (move_flag(m) != 3);
    if (is_quiet) {
        int bonus = depth * depth;
        int side = b->side_to_move;
        int from = move_from(m);
        int to = move_to(m);

        g_history_table[side][from][to] += bonus;

        // Saturation guard to prevent integer overflow and preserve score boundaries
        if (g_history_table[side][from][to] > MAX_HISTORY_SCORE) {
            g_history_table[side][from][to] = MAX_HISTORY_SCORE;
        }
    }
}
```

### 3.2 Saturation & Bounds
- Depth bonus: $bonus = depth^2$. At depth 5, $bonus = 25$; at depth 10, $bonus = 100$.
- Saturation ceiling: Capped strictly at `MAX_HISTORY_SCORE = 70,000`.
- Ensures that history-scored moves never overtake Secondary Killers ($80,000$), Primary Killers ($90,000$), or Captures ($99,996$).

---

## 4. Aging & Reset Semantics

1. **New Game (`ucinewgame`):**
   Entire table is cleared via `std::memset(g_history_table, 0, sizeof(g_history_table))`.
2. **Generational Decay / Aging:**
   At the start of each top-level iterative deepening search, or when `g_tt_age` increments, history scores can be decayed:
   $$g\_history\_table[s][f][t] = g\_history\_table[s][f][t] / 2$$
   This prevents historical moves from dominating modern moves after major board-state transitions.
3. **Isolation from Evaluation:**
   History scores are used strictly within `score_move_for_ordering()`. They are never passed to static evaluation, terminal checks, or leaf node scores.

---

## 5. Move Ordering Priority Integration

In `score_move_for_ordering()`:

```cpp
// 6. History-Scored Quiet Moves (if enabled)
if (g_use_history_ordering) {
    int side = b->side_to_move;
    int h_score = g_history_table[side][from][to];
    if (h_score > 0) {
        return std::min(MAX_HISTORY_SCORE, h_score);
    }
}

// 7. Remaining Quiet Moves
return 0;
```

This completes the seamless 7-tier ordering hierarchy:
$$\text{TT Move} (10M) > \text{Promotions} (800k-900k) > \text{Captures} (100k) > \text{Killer 1} (90k) > \text{Killer 2} (80k) > \text{History} (1-70k) > \text{Unscored Quiets} (0)$$

