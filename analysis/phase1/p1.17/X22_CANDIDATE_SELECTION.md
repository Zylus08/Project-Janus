# Milestone P1.17 Phase 11: Candidate Selection & Architecture Freeze

**Date:** November 14, 2026  
**Status:** Frozen & Certified  
**Branch:** `phase1/classical-janus`  
**Candidate Name:** Janus Classical X22  
**Roles:** X22-S (Single-Thread Classical Candidate), X22-P (Four-Thread SMP Classical Candidate)  

---

## 1. Candidate Architectural Blueprint

Candidate Janus Classical X22 is the direct scientific successor to Janus Classical X21, designed to preserve complete tactical and quiescence correctness while recovering practical playing strength through targeted non-ML positional evaluation and 1-thread pawn hash acceleration:

```
+---------------------------------------------------------------------------------------------------+
| JANUS CLASSICAL X22 ARCHITECTURAL SPECIFICATION                                                   |
+---------------------------------------------------------------------------------------------------+
| 1. Quiescence Search:    Policy Q1 (100% Correct)                                                 |
|                          - Mandatory legal check evasion generation                               |
|                          - Stand-pat suppression under check                                      |
|                          - Terminal checkmate -(MATE_SCORE - ply) and stalemate 0 cp              |
|                          - Exemption of all in-check evasions from negative-SEE pruning           |
|                          - Recursion depth limit MAX_QSEARCH_PLY = 24                             |
| 2. Positional Evaluation: E5 Classical Core + True Outposts with Enemy Pawn Immunity               |
|                          - True Knight Outpost (Defended + Immunity): +28 mg / +18 eg             |
|                          - True Central Bishop Outpost (files c-f, Defended + Immunity): +22 / +14|
|                          - Transient Outpost (Defended, kickable): +8 mg / +4 eg                  |
| 3. Pawn Hash Acceleration: 16K direct-mapped thread-local cache enabled on 1T and 4T SMP          |
|                          - +52.1% isolated eval speedup; +10.6% full search NPS                   |
| 4. Move Ordering:        P1.15 MovePicker with C1 near-even capture staging                       |
| 5. Pruning Calibration:  Calibrated LMR (dynamic history mode 3) + R=3 NMP + 120 cp RFP           |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Frozen Artifact Checksums & Build Environment

All candidate binaries and source files are permanently frozen in `analysis/phase1/p1.17/control/`:

| Artifact Name | Role / File Type | Size (Bytes) | SHA-256 Cryptographic Hash |
| :--- | :--- | :---: | :--- |
| **`janus_classical_x22.exe`** | Production Executable | 1,610,752 | `35D095CFFE8A2EDA412171803C09BE52A74DFB3F9744C04F573D2A7FFB1C2F1C` |
| **`janus_classical_x22.dll`** | Dynamic Link Library | 1,514,496 | `004ACE07C31F9D8124B8C0EA9D402C497D906CC3042A4A3C171A7D5A5D710DA4` |
| **`janus_classical_x22.cpp`** | C++17 Source Snapshot | 245,537 | `FD67D0B2B7659E8EA013BF7E38252B9ABDD6627B4EAD991C46E340BF27CD02A8` |

### Compiler & Optimization Parameters:
- **Compiler:** Microsoft (R) C/C++ Optimizing Compiler Version 19.42.34436 for x64
- **Flags:** `/O2 /Oi /Ot /std:c++17 /EHsc`
- **Target CPU Architecture:** x86-64 with AVX2 instruction set support
- **UCI Variant Handshake:** `setoption name UCI_Variant value X22`
