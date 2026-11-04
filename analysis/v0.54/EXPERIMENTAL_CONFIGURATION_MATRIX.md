# PROJECT JANUS v0.54 — EXPERIMENTAL CONFIGURATION MATRIX

**Milestone:** Project Janus v0.54  
**Date:** 2026-11-05  
**Candidate Engine:** Janus Native N5  

---

## 1. Experimental Factorial Design

To isolate the individual and interactive effects of move ordering heuristics, Project Janus v0.54 establishes a $2 \times 2$ factorial experimental matrix:

```
                          UseHistoryOrdering
                     False                   True
               +----------------------+----------------------+
         False |     C0 (Control)     |  C2 (History Only)   |
UseKiller      +----------------------+----------------------+
Ordering  True |   C1 (Killer Only)   |     C3 (Combined)    |
               +----------------------+----------------------+
```

---

## 2. Configuration Definitions

| Configuration ID | Role in Milestone | Killer Moves (`UseKillerOrdering`) | History Heuristic (`UseHistoryOrdering`) | Equivalence Target |
| :---: | :--- | :---: | :---: | :--- |
| **C0** | Frozen Production Control | **`false`** | **`false`** | Strictly identical to Janus Native N3 |
| **C1** | Killer Ablation Variant | **`true`** | **`false`** | Isolates ply-specific quiet cutoffs |
| **C2** | History Ablation Variant | **`false`** | **`true`** | Isolates global quiet cutoffs |
| **C3** | Primary Experimental Candidate (N5) | **`true`** | **`true`** | Combined tiered ordering intelligence |

---

## 3. Invariant Environmental Constants

All four configurations share bit-identical underlying search engine parameters:
- **Search Core:** C++17 native compiled core (`janus_native.cpp`).
- **Late Move Reductions (LMR):** `UseLMR = true` (`LMRMinDepth = 3`, `LMRMoveThreshold = 4`, `LMRBaseReduction = 1`).
- **Principal Variation Search (PVS):** `UsePVS = false` (Category B baseline standard).
- **Transposition Table:** 1,048,576 entries (24 MB), depth-preferred replacement with generational aging.
- **Static Evaluation:** Unified midgame and endgame piece-square tables.
- **Capture Ordering:** Standard MVV-LVA.
- **Quiescence Search:** Delta pruning with 1,100 cp margin.
- **Time Controls:** Fischer 3.0s base + 100ms increment.

---

## 4. UCI Interface Specification

```
option name UseKillerOrdering type check default false
option name UseHistoryOrdering type check default false
option name UseLMR type check default true
option name UsePVS type check default false
```

Both options can be dynamically negotiated at runtime via standard UCI commands:
```
setoption name UseKillerOrdering value true
setoption name UseHistoryOrdering value true
```

