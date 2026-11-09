# Project Janus Phase 1 — Milestone P1.0
## Classical Lineage Recovery & Native Baseline Verification

**Milestone:** P1.0  
**Program:** Classical Engine Supremacy Program (Phase 1)  
**Role:** Principal Computer Chess Engineer, C++17 Systems Architect, Search Algorithm Researcher, and Testing Auditor  
**Primary Repository:** `E:\ChessXML\project-janus` (`v0.3-benchmark-harness`, HEAD `6500b3f`)  
**Phase 1 Worktree Base:** `2b24d13` (Milestone v0.57 Classical Freeze Anchor)  
**Phase 1 Worktree Path:** `E:\ChessXML\project-janus-phase1`  
**Phase 1 Branch:** `phase1/classical-janus`  
**Frozen Production Baseline:** Janus Classical Baseline C1 (Native N5 Frozen)  
**New Engine Lineage:** Janus Classical X  
**Date:** 2026-11-09  
**Deliverable:** `analysis/phase1/p1.0/CLASSICAL_LINEAGE_RECOVERY.md`  

---

## 1. Executive Summary

In accordance with Phase 1 Governing Rules 1 and 2, Project Janus has formally branched into a dedicated, strictly non-ML classical supremacy engineering effort while preserving the complete, immutable historical neural research record in the primary repository (`v0.3-benchmark-harness` at `6500b3f`).

An isolated Git worktree was established at `E:\ChessXML\project-janus-phase1` anchored to parent commit `2b24d13` (v0.57), the exact milestone where Classical Baseline C1 was calibrated against Stockfish 19 and frozen. The native C++17 production source and binary of Classical C1 were cryptographically audited, and an independent developmental source tree for the **Janus Classical X** lineage was created in `engine/classical_x/`.

---

## 2. Git Worktree & Repository Isolation Audit

### 2.1 Primary Repository Verification
- **Working Directory:** `E:\ChessXML\project-janus`
- **Active Branch:** `v0.3-benchmark-harness`
- **HEAD Commit:** `6500b3f` (`feat(research): final causal attribution, endgame verification, and manuscript readiness (v0.65)`)
- **Working Tree State:** Completely clean.
- **Neural Baselines Preserved:** N8 (Policy), N1 (NNUE-V2 Small Hybrid 50/50), N2 (NNUE-V3 Small + SEF Phase-Tapered Adaptive).

### 2.2 Phase 1 Worktree Creation
- **Worktree Path:** `E:\ChessXML\project-janus-phase1`
- **Branch Created:** `phase1/classical-janus`
- **Base Anchor Commit:** `2b24d13` (`feat(classical): freeze baseline C1, calibrate against Stockfish 19, and qualify neural integration readiness (v0.57)`)
- **Source Anchor Commit:** `e543dab` (`feat(search): implement and validate native Static Exchange Evaluation (SEE) capture ordering (v0.56)`)
- **Git Command Executed:**
  ```powershell
  git worktree add -b phase1/classical-janus E:\ChessXML\project-janus-phase1 2b24d13
  ```

---

## 3. Classical Baseline C1 Cryptographic Audit

The baseline source and compiled executable located at `analysis/v0.56/native/` were inspected and compared against the v0.57 freeze specification recorded in `analysis/v0.57/CLASSICAL_BASELINE_FREEZE.md`:

| Component | Path | Recorded Size | Measured Size | Recorded SHA-256 | Measured SHA-256 | Status |
| :--- | :--- | :---: | :---: | :--- | :--- | :---: |
| **C1 Native Executable** | `analysis/v0.56/native/janus_native_engine.exe` | 341,504 | 341,504 | `a4f9d9d18b549d29b2e6740ac90d90d39167d92d3846b95fc0c4f5b966add83f` | `a4f9d9d18b549d29b2e6740ac90d90d39167d92d3846b95fc0c4f5b966add83f` | **EXACT MATCH** |
| **C1 Native DLL** | `analysis/v0.56/native/janus_native.dll` | 259,072 | 259,072 | `db06d15b0bfa9da16dfa99f196a642eeb9491629858aa58cf27393e1ea66518f` | `db06d15b0bfa9da16dfa99f196a642eeb9491629858aa58cf27393e1ea66518f` | **EXACT MATCH** |
| **C1 Native Source** | `analysis/v0.56/native/janus_native.cpp` | 80,677 (LF) | 80,677 (LF) | `43ad79ade44cc6d6dd97a4cfeb6e9ba2b32c8d080190808d22cac486616397a4` | `43ad79ade44cc6d6dd97a4cfeb6e9ba2b32c8d080190808d22cac486616397a4` | **EXACT MATCH** |

*Integrity Conclusion:* Classical Baseline C1 is cryptographically intact and bit-exact across both source code and binaries.

---

## 4. C1 Production Configuration Recovery

The production configuration of C1 operates under the following frozen parameters:

```text
id name Janus 0.56 Native (N7 Candidate)
id author Project Janus Team
option name UseKillerOrdering type check default true
option name UseHistoryOrdering type check default true
option name UsePVS type check default false
option name UseLMR type check default true
option name LMRMinDepth type spin default 3 min 2 max 8
option name LMRMoveThreshold type spin default 4 min 2 max 16
option name LMRBaseReduction type spin default 1 min 1 max 3
option name UseSEEOrdering type check default false
option name UseSEEInQuiescence type check default false
uciok
```

### Algorithmic Parameters:
- **Transposition Table:** 64 MB (1,048,576 slots, 64 bytes per entry struct, depth-preferred replacement).
- **Move Ordering Pipeline:**
  1. TT Hash Move: $10,000,000$
  2. Queen / Rook Promotions: $800,000 - 900,000$
  3. MVV-LVA Captures: $100,000 + (10 \times \text{Victim}) - \text{Attacker}$
  4. Primary Killer Move: $90,000$
  5. Secondary Killer Move: $80,000$
  6. Butterfly History Table: Normalized up to $16,384$
  7. Quiet moves: $0$
- **Pruning & Reductions:**
  - LMR: Enabled ($R = 1$ when $\text{depth} \ge 3$ and $\text{move\_index} \ge 4$, quiet moves only).
  - PVS: Disabled (pure negamax alpha-beta).
  - Null Move Pruning (NMP): Not implemented in C1 native.
  - Reverse Futility Pruning (RFP): Not implemented in C1 native.
  - SEE Move Ordering: Disabled in C1 default.
  - Quiescence Search: Captures only, MVV-LVA ordered.

---

## 5. Developmental Source Tree: Janus Classical X

To ensure that Classical Baseline C1 remains an **immutable, frozen control**, an independent developmental source tree has been created:

- **Source Directory:** `engine/classical_x/`
- **Source File:** `engine/classical_x/janus_classical_x.cpp`
- **Build Script:** `engine/classical_x/build.py`
- **Compiler:** Microsoft Visual C++ Build Tools 2022 (`v19.43.34809 x64`), `/O2 /Ot /Oi /std:c++17 /EHsc`
- **Output Binaries:**
  - `engine/classical_x/janus_classical_x.exe` (Standalone UCI Engine, 341,504 bytes)
  - `engine/classical_x/janus_classical_x.dll` (Shared Library, 259,072 bytes)

### Engine Identification:
```text
id name Janus Classical X (P1.0 Development)
id author Project Janus Team
```

### Strict Non-ML Verification:
The `engine/classical_x/` codebase contains:
- 0 neural network headers or weight loaders.
- 0 NNUE evaluators or tensor definitions.
- 0 machine learning runtime dependencies.
- 100% pure handcrafted C++17 bitboard search and evaluation logic.
