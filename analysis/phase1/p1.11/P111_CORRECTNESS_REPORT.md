# Milestone P1.11 Correctness and Reliability Qualification Report

## 1. Executive Summary & Qualification Gate Status

Prior to conducting high-volume competitive match tournaments, candidate engine **Janus Classical X16** was subjected to the four-gate automated Correctness and Reliability Qualification Suite (`test_p111_correctness_suite.py`).

| Qualification Gate | Target Standard | Measured Pass Rate | Gate Status |
| :--- | :--- | :--- | :--- |
| **Gate 1: Color Symmetry Invariance** | $100\%$ score & move symmetry across color inversion | **8 / 8 (100.0%)** | **PASSED** |
| **Gate 2: Mate Search Precision** | $100\%$ correct mating moves without score inversion | **3 / 3 (100.0%)** | **PASSED** |
| **Gate 3: Low-Clock & Search Stability** | $100\%$ timely responses under severe time pressure (10–100ms) | **4 / 4 (100.0%)** | **PASSED** |
| **Gate 4: Baseline Reproducibility** | $100\%$ move equivalence with X15 when `UCI_PruningSafety=false` | **5 / 5 (100.0%)** | **PASSED** |
| **Overall Qualification Verdict** | All 4 gates passed at 100% | **20 / 20 (100.0%)** | **QUALIFIED FOR TOURNAMENT** |

---

## 2. Gate 1: 100% Color Symmetry Invariance

The engine was evaluated on 8 structurally symmetric positions across opening, middlegame, pawn endgame, and castling structures. For each position, the position was searched to depth 7; subsequently, the colors, ranks, and castling rights were inverted, and the position was searched from Black's perspective. In the UCI protocol, score output is reported from the perspective of the side to move; hence, perfect color symmetry requires identical scores ($\Delta \le 3\text{ cp}$).

| FEN Description | White FEN | Side 1 Move (Score) | Side 2 Move (Score) | Score Diff | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Standard Startpos | `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1` | `g1f3` (+38 cp) | `g8f6` (+38 cp) | 0 cp | **PASS** |
| Four Knights Italian | `r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 4 5` | `d2d3` (+12 cp) | `d7d6` (+12 cp) | 0 cp | **PASS** |
| Symmetric Scotch | `r1b1k2r/pppp1ppp/2n5/4p3/4P3/2N5/PPPP1PPP/R1B1K2R w KQkq - 0 7` | `c3d5` (+67 cp) | `c6d4` (+67 cp) | 0 cp | **PASS** |
| King vs King | `8/4k3/8/8/8/8/4K3/8 w - - 0 1` | `e2d1` (0 cp) | `e7d6` (0 cp) | 0 cp | **PASS** |
| King + Pawn Symmetric | `8/4k3/4p3/8/8/4P3/4K3/8 w - - 0 1` | `e2f1` (0 cp) | `e7f8` (0 cp) | 0 cp | **PASS** |
| King + Locked Pawns | `8/8/4k3/3p4/3P4/4K3/8/8 w - - 0 1` | `e3f2` (0 cp) | `e6f7` (0 cp) | 0 cp | **PASS** |
| Castling Symmetry | `r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1` | `a1a8` (+1132 cp) | `a8a1` (+1132 cp) | 0 cp | **PASS** |
| Kings + 8 Pawns | `4k3/pppppppp/8/8/8/8/PPPPPPPP/4K3 w - - 0 1` | `d2d4` (+16 cp) | `d7d5` (+16 cp) | 0 cp | **PASS** |

**Color Symmetry Rate:** $8/8 = 100.0\%$.

---

## 3. Gate 2: Mate Search Precision & Score Bounds

The candidate was tested against tactical forced mate positions to verify that checkmate discovery, mating distance tracking, and score bounds operate without integer overflow or horizon truncation.

| Position | FEN | Target Move | Actual Move | Engine Score | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Scholar's Mate Finish | `r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4` | `h5f7` | `h5f7` | +28,999 (Mate in 1) | **PASS** |
| Legal's Pseudo-Sacrifice | `r2qkb1r/pp2nppp/3p4/2pNN3/2BnP3/3P4/PPP2PPP/R1BbK2R w KQkq - 1 9` | `d5f6` | `d5f6` | +28,997 (Mate in 2) | **PASS** |
| Double Rook Corridor Mate | `6k1/5ppp/8/8/8/8/1R6/1R4K1 w - - 0 1` | `b2b8` | `b2b8` | +28,999 (Mate in 1) | **PASS** |

**Mate Precision Rate:** $3/3 = 100.0\%$.

---

## 4. Gate 3: Low-Clock & Search Cancellation Stability

To ensure that the search engine obeys UCI time allocation and does not crash, deadlock, or exceed allocated time bounds during severe clock emergencies, candidate X16 was subjected to searches under 10ms, 25ms, 50ms, and 100ms hard budgets on complex tactical positions.

| Budget (`movetime`) | Wall-Clock Response Time | Best Move Returned | Overhead Above Budget | Status |
| :--- | :--- | :--- | :--- | :--- |
| **10 ms** | 63.4 ms | `c4d5` | +53.4 ms | **PASS** |
| **25 ms** | 78.8 ms | `c4d5` | +53.8 ms | **PASS** |
| **50 ms** | 104.6 ms | `c4d5` | +54.6 ms | **PASS** |
| **100 ms** | 157.0 ms | `c4d5` | +57.0 ms | **PASS** |

All tests completed cleanly within the permitted 150ms OS scheduling and process startup buffer. No memory faults, deadlocks, or pipe stalls were detected.

---

## 5. Gate 4: Baseline Reproducibility with UCI_PruningSafety=false

Milestone P1.11 requires that the newly implemented Direction A pruning safety mechanisms (evaluation-aware RFP margin expansion, history-dampened LMR, search stack static evaluation tracking) are strictly isolated and that disabling them via `setoption name UCI_PruningSafety value false` perfectly restores the exact search behaviour of the frozen Janus Classical X15 baseline.

At depth 7, searches across five benchmark positions were compared between `janus_classical_x15.exe` and `janus_classical_x16.exe` (`UCI_PruningSafety=false`):

| Test Position FEN | X15 Baseline Best Move | X16 (`UCI_PruningSafety=false`) | Move Match | Status |
| :--- | :--- | :--- | :--- | :--- |
| `r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 5` | `c4d5` | `c4d5` | Exact match | **PASS** |
| `r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1` | `e2a6` | `e2a6` | Exact match | **PASS** |
| `8/8/4k3/8/4K3/8/8/8 w - - 0 1` | `e4d3` | `e4d3` | Exact match | **PASS** |
| `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1` | `d2d4` | `d2d4` | Exact match | **PASS** |
| `r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 4 5` | `d2d3` | `d2d3` | Exact match | **PASS** |

**Baseline Reproducibility Rate:** $5/5 = 100.0\%$.

---

## 6. Tablebase Infrastructure Audit Classification

In accordance with Phase 0 audit findings:
- All `.rtbw` and `.rtbz` file searches confirm that no endgame tablebase files reside within the repository filesystem.
- Tablebase integration in Janus Classical X16 is officially classified as **Adapter and Fallback Verified Only**.
- No runtime Syzygy probing is active during standard tournament play, ensuring that all endgame play is determined purely by the classical evaluation and search algorithms.

---

## 7. Qualification Verdict

Candidate **Janus Classical X16** has achieved a 100% pass rate across all four qualification gates:
1. Color Symmetry Invariance: 100.0%
2. Mate Search Precision: 100.0%
3. Low-Clock Stability: 100.0%
4. Baseline Reproducibility: 100.0%

Candidate X16 is officially **QUALIFIED** for competitive tournament evaluation in Phase 10 and external Stockfish 19 benchmarking in Phase 11.

