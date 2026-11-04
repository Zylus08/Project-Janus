# Project Janus v0.50 — Native Board-State Prototype

**Milestone:** Project Janus v0.50  
**Parent Baseline Commit:** `d037f77` (v0.49 Final)  
**Evaluated Architecture:** Candidate N2 (Native Search Core Prototype)  
**Binary:** `analysis/v0.50/native/janus_native.dll`  
**Test Suite:** `analysis/v0.50/tests/test_native_qualification.py`

---

## 1. Executive Disposition: PHASE D QUALIFIED

The native board-state prototype has been fully verified against `python-chess`:
1. **FEN Parsing and Serialization (D1):**
   - 100.0% round-trip agreement across all 37 positions of the diagnostic corpus.
   - Exact preservation of piece placement, side to move, castling rights, and en-passant squares.
2. **Attack Detection (D2):**
   - Precomputed ray and attack tables (`KNIGHT_ATTACKS`, `KING_ATTACKS`, `PAWN_ATTACKS`, `RAYS`) accurately compute sliding attacks (rooks, bishops, queens) and non-sliding attacks.
3. **Check Detection (D3):**
   - Evaluated against `python-chess` across all 37 diagnostic positions and 1,475 randomized game positions: **100.0% exact check status agreement**.
4. **State Integrity (D4):**
   - Zero piece duplication, zero occupancy corruption, zero bitboard drift.

---

## 2. Test Verification Matrix

| Test Category | Target Positions | Expected Outcome | Measured Result |
|---|---:|---|---|
| **FEN Round-Trip** | 37 diagnostic positions | 100% string/board match | **37 / 37 (100.0%)** |
| **Check Detection** | 37 diagnostic positions | 100% boolean check match | **37 / 37 (100.0%)** |
| **Randomized Board States** | 1,475 game positions | 100% check/occupancy match | **1,475 / 1,475 (100.0%)** |
| **Square Indexing Parity** | 64 squares | Bit 0 = A1, Bit 63 = H8 | **Verified Bit-Identical** |

