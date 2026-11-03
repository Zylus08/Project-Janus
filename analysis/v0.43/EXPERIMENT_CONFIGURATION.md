# Project Janus v0.43 — Experimental Configuration & Single-Variable Proof (Phase C)

**Milestone:** v0.43 — Independent Strength Replication & RFP Production Qualification  
**Date:** 2026-11-03  
**Status:** FROZEN & VERIFIED  

---

## 1. Engine Configuration Matrix

| Component / Subsystem | Baseline Arm (K0) | Treatment Arm (RFP) | Match Status |
|:---|:---|:---|:---:|
| **Engine Entry Point** | `src/janus/uci.py` | `src/janus/uci.py` | Identical |
| **Search Class** | `JanusSearch` (`src/janus/search.py`) | `JanusSearch` (`src/janus/search.py`) | Identical |
| **Evaluation Function** | Full tapered evaluation (`--eval-all`) | Full tapered evaluation (`--eval-all`) | Identical |
| Material Weights | Pawn=100, Knight=320, Bishop=330, Rook=500, Queen=900 | Same | Identical |
| Piece-Square Tables | PeSTO midgame / endgame tables | Same | Identical |
| Pawn Structure | Doubled, isolated, passed pawn bonuses | Same | Identical |
| Rook Placement | Open and semi-open files | Same | Identical |
| King Safety | Tapered king attack zones | Same | Identical |
| Uncastled King Safety | Open d/e file penalty with phase scaling | Same | Identical |
| **Search Tree Structure** | Principal Variation Search (PVS) | Principal Variation Search (PVS) | Identical |
| Aspiration Windows | Initial window [-50, +50] cp | Initial window [-50, +50] cp | Identical |
| Transposition Table | `always_replace`, max 200,000 entries | `always_replace`, max 200,000 entries | Identical |
| Late Move Reductions | Depth >= 3, non-tactical moves | Depth >= 3, non-tactical moves | Identical |
| Null Move Pruning | Depth >= 3, R = 2, verification | Depth >= 3, R = 2, verification | Identical |
| Move Ordering | MVV/LVA, TT move, Killers, History | MVV/LVA, TT move, Killers, History | Identical |
| Quiescence Search | Stand-pat, captures only, max 12 plies | Stand-pat, captures only, max 12 plies | Identical |
| Draw Detection | 3-fold at ply > 0, 5-fold, 75-move | 3-fold at ply > 0, 5-fold, 75-move | Identical |
| Time Management | `arm_c` (adaptive Fischer manager) | `arm_c` (adaptive Fischer manager) | Identical |
| **Reverse Futility Pruning**| **DISABLED (`enable_rfp = False`)** | **ENABLED (`enable_rfp = True`)** | **TREATMENT DIFFERENCE** |
| RFP Max Depth | N/A (disabled) | `rfp_max_depth = 2` | Treatment Setting |
| RFP Margin | N/A (disabled) | `rfp_margin_per_depth = 120` | Treatment Setting |
| Opponent Configuration | Stockfish 19 (Elo 1320, 1T, 64MB) | Stockfish 19 (Elo 1320, 1T, 64MB) | Identical |
| Time Control | 3000 ms + 100 ms Fischer increment | 3000 ms + 100 ms Fischer increment | Identical |

---

## 2. Machine-Readable Configuration Diff

```json
{
  "baseline_k0": {
    "uci_args": [
      "-m", "janus.uci",
      "--name", "Janus-K0",
      "--eval-all",
      "--time-policy", "arm_c"
    ],
    "enable_rfp": false,
    "rfp_max_depth": null,
    "rfp_margin_per_depth": null
  },
  "treatment_rfp": {
    "uci_args": [
      "-m", "janus.uci",
      "--name", "Janus-RFP",
      "--eval-all",
      "--time-policy", "arm_c",
      "--enable-rfp"
    ],
    "enable_rfp": true,
    "rfp_max_depth": 2,
    "rfp_margin_per_depth": 120
  },
  "diff": {
    "single_variable_difference": true,
    "isolated_parameters": [
      "enable_rfp"
    ],
    "unintended_differences": []
  }
}
```

---

## 3. Verification of Single-Variable Isolation

1. **Source Code Level:** In `JanusSearch._negamax`, the execution path between K0 and RFP diverges if and only if `self.enable_rfp` evaluates `True`. When `self.enable_rfp` is `False`, lines 812–828 are completely bypassed.
2. **Harness Level:** Both engines are spawned via `SupervisedEngineSession` using the exact same virtual environment Python binary (`.venv/Scripts/python.exe`), working directory (`E:\ChessXML\project-janus`), and standard library packages.
3. **Conclusion:** All non-RFP parameters are strictly held invariant. Any observed playing-strength delta between K0 and RFP is causally attributable to the treatment variable.
