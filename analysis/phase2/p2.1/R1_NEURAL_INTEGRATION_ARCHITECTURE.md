# Janus R1 — Neural Integration Architecture (Phase 1)

**Milestone:** Phase 2, Milestone P2.1  
**Architecture:** Janus Classical R1.0 Search Core + Neural Evaluation Extension  
**Date:** November 16, 2026  
**Auditor:** Principal Computer Chess Architect & Neural-Network Systems Engineer  

---

## 1. Modular Search Architecture Audit

The clean-sheet C++17 **Janus Classical R1.0** search engine established in Milestone P1.22 consists of 8 encapsulated, decoupled subsystems:

```
  ┌─────────────────────────────────────────────────────────────┐
  │                      SearchController                       │
  │                  (UCI, Time Management, Logs)               │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
  ┌──────────────────────────────▼──────────────────────────────┐
  │                         RootSearch                          │
  │              (Iterative Deepening, Aspiration)              │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
  ┌──────────────────────────────▼──────────────────────────────┐
  │                       AlphaBetaCore                         │
  │             (PVS, NMP, RFP, LMR, Cutoff Policies)           │
  └──────────┬───────────────────┬───────────────────┬──────────┘
             │                   │                   │
  ┌──────────▼──────────┐ ┌──────▼──────────┐ ┌──────▼──────────┐
  │   MoveOrdering      │ │ QuiescenceCore  │ │TranspositionStore│
  │(6-Stage MovePicker) │ │(Stand-Pat, SEE) │ │(Aligned Cluster)│
  └─────────────────────┘ └──────┬──────────┘ └─────────────────┘
                                 │
  ┌──────────────────────────────▼──────────────────────────────┐
  │                    EVALUATION INTERFACE                     │
  │           ┌──────────────┬──────────────┬──────────────┐    │
  │           │  CLASSICAL   │     NNUE     │    HYBRID    │    │
  │           └──────────────┴──────────────┴──────────────┘    │
  └─────────────────────────────────────────────────────────────┘
```

### Stable Interfaces Audited:
1. **Position Representation (`NativeBoard`):**
   - 12 bitboards: White/Black $\times$ {Pawns, Knights, Bishops, Rooks, Queens, Kings}.
   - State fields: `side_to_move` (0=White, 1=Black), `castling_rights` (4 bits), `ep_square` (-1 or 0..63), `halfmove_clock`, `fullmove_number`.
2. **Move Representation:**
   - 16-bit packed integer: From (6 bits), To (6 bits), Promotion piece type (2 bits), Move flags (2 bits).
3. **Make / Unmake (`native_make_move`, `native_unmake_move`):**
   - Full reversible state stack storing captured piece, previous castling rights, previous ep square, and halfmove clock.
4. **Static Evaluation Call Sites:**
   - `r1_quiescence.hpp`: Lines 23, 31 (Stand-pat evaluation and in-check fallback).
   - `r1_search.hpp`: Lines 43, 100, 108, 144 (Pure minimax leaf, leaf evaluation, RFP forward cutoff, static eval probe).

---

## 2. Universal Evaluation Subsystem Interface

To allow rigorous scientific isolation of neural evaluation without altering search pruning contracts, the evaluation interface is unified under `r1::EvalMode`:

```cpp
namespace r1 {

enum EvalMode : uint8_t {
    EVAL_CLASSICAL = 0, // Frozen Phase 1 classical non-ML evaluation
    EVAL_NNUE      = 1, // Standalone quantized CPU neural network evaluation
    EVAL_HYBRID    = 2  // Linear blend of Classical and NNUE
};

struct EvalConfig {
    EvalMode mode = EVAL_CLASSICAL;
    int hybrid_nnue_weight = 50; // Weight in [0, 100] for NNUE in hybrid mode
    int nnue_scale = 100;        // Centipawn scaling divisor for NNUE output
};

// Unified Evaluation Dispatcher
int evaluate(const NativeBoard* b, const EvalConfig& cfg, void* accumulator_ctx = nullptr);

} // namespace r1
```

### Blending Semantics for Hybrid Evaluation:
$$\text{Score}_{\text{hybrid}} = \frac{W_{\text{nnue}} \cdot \text{Score}_{\text{nnue}} + (100 - W_{\text{nnue}}) \cdot \text{Score}_{\text{classical}}}{100}$$

### Controlling Invariants:
1. **Search Parity:** All three evaluation modes (`CLASSICAL`, `NNUE`, `HYBRID`) use the exact same alpha-beta search implementation, move picker, quiescence search, and aspiration window loops.
2. **Score Perspective:** All evaluation functions return centipawn scores from the perspective of the **side to move** ($+100\text{ cp} =$ side to move is ahead by 1 pawn).
3. **Mate Score Insulation:** Neural evaluation is strictly clamped to $[-27000, +27000]$, ensuring it never collides with `MATE_SCORE` ($29000$) or forced mate distance bounds ($> 28000$).
4. **Preservation of Legal Check-Evasion:** In check, quiescence search forces all legal evasions regardless of static evaluation or evaluation mode.
