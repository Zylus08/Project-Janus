# Project Janus — Phase 2 Charter & Formal Transition Record

**Milestone:** Phase 2, Milestone P2.1  
**Transition Parent Commit:** `6346caf` (Phase 1 Closure Commit on branch `phase1/classical-janus`)  
**New Development Branch:** `phase2/nnue-r1`  
**Date:** November 16, 2026  
**Role:** Principal Computer Chess Architect, Neural-Network Researcher, C++17 Performance Engineer, and Independent Experimental Auditor  

---

## 1. Executive Charter Transition

### Phase 1 Charter (Concluded & Sealed)
- **Scope:** Strictly non-ML Classical Computer Chess Architecture.
- **Rules:** Zero neural networks, NNUE, learned evaluation parameters, offline model fitting, SPSA, or Texel tuning.
- **Outcome:** Successfully sealed at commit `6346caf` with 22 milestones (P1.1–P1.22), establishing frozen strength controls Janus Classical X7 (1T), Janus Classical X12 (4T), correctness reference Janus Classical X22-S, and clean-sheet search core Janus Classical R1.0.

### Phase 2 Charter (Active)
- **Scope:** Hybrid Classical Search with Original Neural Evaluation (Project Janus NNUE).
- **Core Mission:** Develop an independent, original neural network evaluation architecture (NNUE) integrated with the clean C++17 Janus R1 search core.
- **Rules of Engagement:**
  1. **Strictly Original Neural Architecture:** No importing, copying, or distilling of pre-trained Stockfish NNUE networks (such as `nn-*.nnue`) as the principal Janus model. All model weights must be trained from documented random initialization on reproducible, licensed datasets.
  2. **Matched Classical-versus-Neural Comparisons:** Every evaluation change must be isolated and evaluated against the identical Janus R1 search implementation to attribute playing strength differences causally to evaluation rather than unverified search pruning adjustments.
  3. **Strict Software Verification:** Incremental accumulator updates must be mathematically verified against full recomputations (zero mismatch allowed). Quantized INT8/INT16 inference must be tested for overflow and numerical stability.
  4. **Preservation of Phase 1 Controls:** Frozen baselines X7, X12, X22, and R1.0 remain immutable. Phase 1 historical records and closure documents will not be modified or retroactively rebranded.

---

## 2. Frozen Historical Controls & Anchors Verification

The frozen baseline binaries from Phase 1 have been audited and verified:

| Engine Designation | Milestone | Path | SHA-256 Checksum | Role |
| :--- | :---: | :--- | :--- | :--- |
| **Janus Classical X7** | P1.3 | `analysis/phase1/p1.3/control/janus_classical_x7.exe` | `86392A2F4BD4182A4D7DC21E32940BD7939F6816794D5E1AB02F4082431CA28B` | Qualified 1T Strength Control |
| **Janus Classical X12** | P1.7 | `analysis/phase1/p1.7/control/janus_classical_x12.exe` | `00B4F5FEDEA02A392A1AF9713A96512E5199A0E3AE55C295AD1C7CFFF1B47059` | Qualified 4T SMP Strength Control |
| **Janus Classical X22-S** | P1.17 | `analysis/phase1/p1.17/control/janus_classical_x22.exe` | `35D095CFFE8A2EDA412171803C09BE52A74DFB3F9744C04F573D2A7FFB1C2F1C` | Correctness-Preserving Reference |
| **Janus Classical R1.0** | P1.22 | `analysis/phase1/p1.22/control/janus_classical_r1.exe` | `7312B2B73CD9D40F108EE1B5F3903632A2A7805B19BC73082A796922DE66029B` | Qualified Public Research Core |

---

## 3. Branching & Git Topology

- **Closed Historical Branch:** `phase1/classical-janus` (frozen at commit `6346caf`).
- **Active Development Branch:** `phase2/nnue-r1` (branched cleanly from `6346caf`).
- **Policy:** Strictly local Git commits at milestone conclusion; zero remote Git pushes without authorization.
