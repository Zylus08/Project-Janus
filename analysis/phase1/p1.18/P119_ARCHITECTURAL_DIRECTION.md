# Architectural Direction for Milestone P1.19 (Phase 16 Report)
**Project Janus — Phase 1, Milestone P1.18**
**Next Candidate Target:** Janus Classical Candidate X24 (Conditional)
**Qualified Single-Thread Baseline:** Janus Classical X7 (`b34e342`)
**Qualified Four-Thread Baseline:** Janus Classical X12 (`78ca3d5`)
**Date:** 2026-11-14 | **Branch:** `phase1/classical-janus`

---

## 1. Context & Retrospective

Milestone P1.18 achieved two foundational breakthroughs while identifying one critical negative interaction:
1. **Pawn Hash Synergy:** Proved that embedding classical structural terms into `eval_pawn_structure` achieves 100% caching in the 64K thread-local pawn table, delivering $+13.5\%$ raw evaluation speedup and zero search tree overhead.
2. **Backward Pawn Elo Gain:** Proved that **Track A Classical Backward Pawn Detection** alone delivers **$+17.4$ Elo ($52.5\%$)** in controlled head-to-head matches against Reference X22-S.
3. **King File Exposure Failure:** Proved that **Track B Open/Semi-Open King File Exposure** induces severe positional timidity ($-88.7$ Elo), causing premature defensive pawn pushes and suppressing dynamic counterplay.

Because Candidate X23 combined both tracks, Track B dragged the overall engine down to $44.0\text{--}49.0\%$ against Qualified Baselines X7 and X12, preventing baseline promotion.

---

## 2. Strategic Objectives for Milestone P1.19

### 2.1 Primary Architecture Track: Candidate X24 (Track A Isolation)
The most direct and immediate opportunity for Category A baseline promotion is to **isolate Track A (Backward Pawns)** into Candidate X24 while disabling Track B completely:
- Candidate X24 will preserve:
  - Corrected Quiescence Search (Q1).
  - True Outpost Bitboard Ray Verification (permanent vs kickable outposts).
  - 64K Thread-Local Pawn Hash Table on both 1T and 4T configurations.
  - Track A Backward Pawn Detection ($-10$ mg / $-15$ eg).
- Candidate X24 will remove:
  - Track B King File Exposure Penalties (restoring natural pawn mobility around the castled king).

### 2.2 Secondary Research Track: Dynamic King Infiltration Rays
Rather than applying static penalties to open/semi-open files, king safety should evaluate **dynamic infiltration potential**:
- A file facing the king should only be penalized if:
  1. An enemy heavy piece (rook or queen) occupies the file.
  2. The enemy heavy piece has an unobstructed ray of attack to an entry square on rank 6, 7, or 8 in the friendly camp.
  3. No friendly piece controls or can interpose on the entry square.
- This prevents the engine from panicking over files that are completely defended by friendly knights, bishops, or rooks.

### 2.3 Tertiary Evaluation Enhancement: Connected Passed Pawns on the 5th/6th Rank
Phase 4 (Pawn Structure Failure Atlas) revealed that while Janus rewards passed pawns, it under-values connected passed pawns on ranks 5 and 6 (phalanx pawns). Adding a modest $+12$ mg / $+20$ eg bonus for connected passed pawns on the 5th and 6th ranks will incentivize powerful central and kingside pawn roller attacks.

---

## 3. Experimental Protocol for P1.19

1. **Pre-Flight Verification:** Confirm that Candidate X24 passes all 7 correctness gates (Perft D1–D4, KiwiPete D1–D3, single-thread bitwise determinism, 4T SMP concurrency, 225-position color symmetry, and adversarial harness gate).
2. **P1.19 Tournament Battery:**
   - Match 1: Candidate X24-S vs Qualified Baseline X7 (100 games @ 1.0s + 50ms).
   - Match 2: Candidate X24-P vs Qualified Baseline X12 (100 games @ 1.0s + 50ms, 4T SMP).
   - Match 3: Candidate X24-S vs Reference X22-S (50 games @ 1.0s + 50ms).
   - Match 4: Candidate X24-S vs Reference X23-S (50 games @ 1.0s + 50ms) to directly measure the Elo gain from removing Track B.
   - Matches 5–7: External matched calibration vs Stockfish 4, 11, and 19.

Milestone P1.19 has a clear, evidence-backed roadmap toward achieving Category A baseline promotion.
