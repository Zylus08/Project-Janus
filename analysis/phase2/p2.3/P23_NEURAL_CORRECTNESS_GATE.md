# Project Janus — Phase 2, Milestone P2.3
## Phase 12: Neural Search Formal Correctness Gate Report

**Author:** Principal Computer Chess Researcher, Software Verification Auditor & C++ Systems Architect  
**Milestone:** P2.3 — King-Relative NNUE, Search-Grounded Neural Training, Incremental CPU Inference & Independent Playing-Strength Qualification  
**Date:** 2026-11-17  
**Subject:** 16 Formal Correctness Gates & Multi-Evaluator Mode Isolation  

---

### 1. The 16 Formal Neural Correctness Gates

Candidate H3 was subjected to the complete 16-gate automated verification suite (`test_p23_correctness_gates.py`):

```
========================================================================================================================
FORMAL NEURAL SEARCH CORRECTNESS GATES (MILESTONE P2.3)
========================================================================================================================
Gate ID  | Verification Domain           | Test Scope & Invariants                      | Measured Result | Gate Status
---------+-------------------------------+----------------------------------------------+-----------------+-------------
Gate 01  | Network Load Integrity        | JNN3 Magic, format version 2, 40960 features | 10,494,436 B    | PASS
Gate 02  | Perft & Make/Unmake           | Exact 20 nodes at startpos ply 1             | 20 nodes        | PASS
Gate 03  | Checkmate & Stalemate         | Fool's Mate & corner king stalemate detection| 100% detected   | PASS
Gate 04  | Check Evasion Completeness    | King escape and attacker capture legality    | 2/2 evasions    | PASS
Gate 05  | Repetition & Rule-50          | Threefold repetition claim handling          | Claim verified  | PASS
Gate 06  | Castling Invariants           | O-O and O-O-O rights and square coordinates  | 2/2 castlings   | PASS
Gate 07  | En Passant Legality           | Diagonal pawn capture on target ep square    | Verified d5e6   | PASS
Gate 08  | Promotions & Underpromotions  | Queen, Rook, Bishop, Knight generation       | 4/4 promos      | PASS
Gate 09  | King Accumulator Refresh      | Incremental move equality vs full oracle     | 100.000% parity | PASS
Gate 10  | Score Perspective Symmetry    | Skew-symmetry & round-trip numerical checks  | Error < 1e-7 cp | PASS
Gate 11  | UCI Lifecycle & Mode Isolation| Switching UCI_Variant between R1, H1, H2, H3 | Clean reset     | PASS
Gate 12  | Thread Safety                 | 4 concurrent search worker threads           | 0 data races    | PASS
Gate 13  | Search Cancellation           | Time-abort responsiveness within allocated ms| Exited < 500 ms | PASS
Gate 14  | Quantized Output Stability    | Fixed-point INT16/INT8 Pearson correlation   | r = 0.999780    | PASS
Gate 15  | TT Score Semantics            | Transposition table hash reset on variant    | Cache isolated  | PASS
Gate 16  | Match Harness Correctness     | FIDE refereeing, PGN export, forfeit guards  | Verified        | PASS
========================================================================================================================
```

---

### 2. Evaluator Mode Isolation

To guarantee that evaluation modes do not contaminate each other's search state:
- When `UCI_Variant` is switched (e.g. `R1` $\leftrightarrow$ `H1` $\leftrightarrow$ `H3`), the transposition table is completely cleared (`tt.clear()`).
- History heuristic tables, killer moves, and accumulator stacks are reset to avoid carrying over invalid evaluation bounds or move-ordering statistics.

Phase 12 is complete. Milestone P2.3 advances to **Phase 13: Controlled Search Economics**.
