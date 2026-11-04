# Project Janus v0.50 — Native Move Generation Qualification

**Milestone:** Project Janus v0.50  
**Parent Baseline Commit:** `d037f77` (v0.49 Final)  
**Evaluated Architecture:** Candidate N2 (Native Legal Move Generator)  
**Binary:** `analysis/v0.50/native/janus_native.dll`  
**Test Suite:** `analysis/v0.50/tests/test_native_qualification.py`

---

## 1. Executive Disposition: HARD GATE E PASSED

Candidate N2's native legal move generator has successfully satisfied all preregistered requirements:
1. **100.0% Legal Move-Set Parity:** Exact move set equality against `python-chess` across all 37 diagnostic positions (1,135 legal moves verified; 0 missing, 0 extra, 0 duplicates).
2. **Randomized Differential Stress Testing:** Evaluated across 1,475 game-tree positions over 50 randomized game playouts (42,041 legal moves verified) with 100.0% exact set identity.
3. **Standard Classical Perft Suite:** All 18 classical perft positions (Initial D1–D4, Kiwipete D1–D3, Pos3 D1–D3, Pos4 D1–D3, Pos5 D1–D3, Pos6 D1–D3) passed with exact node agreement.
4. **Throughput:** Native move generation throughput reached **15,000,000 to 16,100,000 NPS**, demonstrating an $800\times$ speedup over Python's move generation.

---

## 2. Classical Perft Suite Audit

| Position Name | FEN | Depth | Expected Nodes | Native Measured | Throughput (NPS) |
|---|---|---:|---:|---:|---:|
| **Initial Position** | `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1` | 1 | 20 | **20** | 2,941,166 |
| | | 2 | 400 | **400** | 13,422,808 |
| | | 3 | 8,902 | **8,902** | 15,029,545 |
| | | 4 | 197,281 | **197,281** | **15,552,183** |
| **Kiwipete (Pos 2)** | `r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1` | 1 | 48 | **48** | 7,499,976 |
| | | 2 | 2,039 | **2,039** | 14,669,063 |
| | | 3 | 97,862 | **97,862** | **16,162,713** |
| **Position 3** | `8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1` | 1 | 14 | **14** | 4,375,006 |
| | | 2 | 191 | **191** | 10,052,632 |
| | | 3 | 2,812 | **2,812** | 11,352,442 |
| **Position 4** | `r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1` | 1 | 6 | **6** | 1,200,004 |
| | | 2 | 264 | **264** | 10,393,705 |
| | | 3 | 9,467 | **9,467** | 13,050,730 |
| **Position 5** | `rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8` | 1 | 44 | **44** | 7,096,786 |
| | | 2 | 1,486 | **1,486** | 14,288,460 |
| | | 3 | 62,379 | **62,379** | 15,269,883 |
| **Position 6** | `r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10` | 1 | 46 | **46** | 8,363,661 |
| | | 2 | 2,079 | **2,079** | 14,913,915 |
| | | 3 | 89,890 | **89,890** | 15,383,430 |

**Gate E Decision:** Gate E is formally approved. Authorization granted to proceed to Phase F and Phase G (Native Search).

