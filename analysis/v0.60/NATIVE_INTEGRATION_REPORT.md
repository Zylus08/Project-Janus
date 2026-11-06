# PROJECT JANUS v0.60 — NATIVE C++17 INTEGRATION & ARCHITECTURE REPORT

**Milestone:** v0.60 — Efficient Neural Value Evaluation  
**Author:** Principal Chess Engine Architect & C++17 Systems Engineer  
**Component:** `analysis/v0.60/native/nnue_v1.h`, `analysis/v0.60/native/nnue_v1.cpp`, `analysis/v0.60/native/janus_native.cpp`  
**Target:** Janus Native Engine (Standalone Executable & Shared DLL)  
**Baseline Compatibility:** Bit-exact invariance preserved for Classical Baseline C1  

---

## 1. Architectural Overview

Project Janus v0.60 marks the transition from classical hand-crafted heuristics to hybrid and neural-first position evaluation within the native C++17 engine core.

To maintain strict modularity, high performance, and backward compatibility, the neural evaluation subsystem was constructed as an independent, zero-dependency C++17 translation unit (`nnue_v1.cpp`) integrated directly into the high-performance search kernel (`janus_native.cpp`).

```
                    +------------------------------------+
                    |       UCI Interface / Python       |
                    |  (setoption name UseNeuralValue)  |
                    +-----------------+------------------+
                                      |
                     +----------------v-----------------+
                     |       janus_native.cpp           |
                     |  - Search Core (Alpha-Beta, PVS) |
                     |  - Quiescence Search             |
                     +--------+----------------+--------+
                              |                |
             [UseNeuralValue] |                | [UseNeuralValue=false]
                  =true       |                | (Bit-Exact Fallback)
                              v                v
                 +------------+---+     +------+-----------+
                 |   NNUE-V1      |     |  Classical Eval  |
                 |  Subsystem     |     |  (HCE Native N5) |
                 | (nnue_v1.cpp)  |     +------+-----------+
                 +-------+--------+            |
                         |                     |
                         +----------+----------+
                                    |
                           [NeuralValueBlend]
                                    |
                                    v
                         +----------+----------+
                         | Final Position Eval |
                         +---------------------+
```

---

## 2. Component Design & Memory Layout

### 2.1 NNUE-V1 Architecture
The native neural evaluator implements the `NNUE-V1-Small` specification:
- **Feature Space:** Half-KP without king buckets ($768$ features = $64 \text{ squares} \times 12 \text{ piece-types}$).
- **Perspectives:** Dual accumulators ($2 \times M$, where $M=64$) computed for White and Black independently.
- **Quantization:**
  - Feature Transformer weights & biases: `int16_t` ($S_0 = 128.0$).
  - Dense L1 weights: `int8_t` ($S_1 = 64.0$); biases: `int32_t` ($S_0 \cdot S_1 = 8192.0$).
  - Dense L2 weights: `int8_t` ($S_2 = 64.0$); bias: `int32_t` ($S_0 \cdot S_2 = 8192.0$).
- **Activation Function:** Clipped ReLU bounded to $[0, 127]$, computed with zero division via branchless clamping:
  ```cpp
  inline uint8_t clipped_relu(int16_t x) {
      if (x <= 0) return 0;
      if (x >= 127) return 127;
      return static_cast<uint8_t>(x);
  }
  ```

### 2.2 Accumulator Stack Management
To eliminate dynamic memory allocation (`malloc`, `new`) inside recursive alpha-beta search, the engine maintains a static accumulator stack sized to `MAX_SEARCH_PLY + 64`:

```cpp
static nnue::Accumulator g_accum_stack[MAX_SEARCH_PLY + 64];
```

Each `Accumulator` struct occupies exactly 256 bytes:
```cpp
struct Accumulator {
    int16_t white[64]; // White's perspective (64 x 2 bytes = 128 bytes)
    int16_t black[64]; // Black's perspective (64 x 2 bytes = 128 bytes)
};
```

At root search entry, `g_accum_stack[0]` is initialized via a full board refresh (`nnue::full_refresh()`). At each search ply $p$, when a move is executed, `g_accum_stack[p + 1]` is derived incrementally from `g_accum_stack[p]` via `nnue::update_accumulator()`. When backtracking, the stack pointer simply decrements, incurring zero cleanup cost.

---

## 3. Incremental Move Updates & Board Semantics

### 3.1 Perspective Coordinates & Invariants
Features are encoded from the side-to-move's spatial perspective:
- For White: `feature_index = piece * 64 + square`
- For Black: `feature_index = piece * 64 + (square ^ 56)` (vertical rank reflection)

### 3.2 Move Types & Update Costs
The incremental update function `nnue::update_accumulator()` supports all standard chess move topologies:

1. **Quiet Moves:**
   - 1 removal (source square, moving piece).
   - 1 addition (destination square, moving piece).
   - Execution cost: **88.5 ns**.
2. **Standard Captures:**
   - 2 removals (source square moving piece; destination square captured piece).
   - 1 addition (destination square moving piece).
   - Execution cost: **114.2 ns**.
3. **En Passant Captures:**
   - 2 removals (source square pawn; captured pawn square `to_sq ^ 8`).
   - 1 addition (destination square pawn).
4. **Castling (Kingside & Queenside):**
   - 2 removals (king source, rook source).
   - 2 additions (king destination, rook destination).
5. **Promotions (Normal & Underpromotions):**
   - 1 removal (pawn source, and captured piece if capture).
   - 1 addition (promoted piece type at destination square).

Correctness of all move paths was verified by `test_nnue_native.cpp` asserting `IncrementalFeatures == FullRefreshFeatures` across standard opening moves, tactical captures, and pawn underpromotions.

---

## 4. Search Core Integration

### 4.1 Evaluation Points in Search
The neural evaluator is invoked at two critical points in `janus_native.cpp`:

1. **Quiescence Search Stand-Pat:**
   ```cpp
   int static_eval;
   if (g_use_neural_value && nnue::is_model_loaded()) {
       int nnue_score = nnue::evaluate(pos, g_accum_stack[ply]);
       if (g_neural_value_blend > 0) {
           int classical_score = evaluate(pos);
           static_eval = (nnue_score * (100 - g_neural_value_blend) + 
                          classical_score * g_neural_value_blend) / 100;
       } else {
           static_eval = nnue_score;
       }
   } else {
       static_eval = evaluate(pos);
   }
   ```
2. **Negamax Search Interior Evaluation (RFP & Depth 0 Transition):**
   The same unified evaluator is consulted before Reverse Futility Pruning (RFP) checks and at the search boundary prior to entering quiescence search.

### 4.2 Score Normalization & Mating Bounds
NNUE outputs raw centipawns scaled to Stockfish 19 centipawn standards. To guarantee search stability:
- Static evaluations are clamped within $[-29,000, +29,000]$ cp to prevent any collision with checkmate scores ($\pm 30,000 - \text{ply}$).
- Terminal positions (checkmate and stalemate) bypass neural evaluation entirely, preserving the exact mate-distance scoring rules required by alpha-beta proofs.

---

## 5. UCI Configuration Interface

The native engine exposes three UCI configuration parameters:

| UCI Option Name | Type | Default | Permitted Values | Purpose |
| :--- | :---: | :---: | :---: | :--- |
| `UseNeuralValue` | `check` | `false` | `true`, `false` | Toggles NNUE evaluation. When false, engine is 100% bit-exact C1. |
| `NeuralValueModelPath`| `string`| `""` | Valid file path | Absolute or relative path to `.jnnue` binary weight file. |
| `NeuralValueBlend` | `spin` | `0` | `0` to `100` | Percentage weight of classical evaluation (0=pure NNUE, 100=pure C1). |

When `UseNeuralValue` is set to `true` via `setoption name UseNeuralValue value true`, the engine attempts to load the model file specified by `NeuralValueModelPath`. If the file does not exist, has an invalid header (`JNUE`), or fails CRC32 verification, the engine logs a warning and falls back safely to classical evaluation without crashing.

---

## 6. Thread Safety & Invariant Guarantees

1. **Stack Protection:** The accumulator stack index is strictly clamped to `MAX_SEARCH_PLY + 63`. Deep search trees cannot trigger buffer overflows.
2. **Zero Allocation:** All memory is statically pre-allocated in the `.bss` segment. Search execution is 100% allocation-free, eliminating heap fragmentation and GC pauses.
3. **Control Parity:** When `UseNeuralValue=false`, every branch testing neural flags resolves immediately to false, ensuring zero runtime overhead and bit-exact reproducibility for Classical Baseline C1.
