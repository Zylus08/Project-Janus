# PROJECT JANUS — PHASE 1, MILESTONE P1.8
## Phase 5: Independent Syzygy Tablebase Feasibility & Correctness Architecture

**Role:** Principal Computer Chess Engineer, Systems Architect, Endgame Specialist  
**Repository:** `E:\ChessXML\project-janus-phase1`  
**Branch:** `phase1/classical-janus`  
**Date:** 2026-11-11  
**Status:** Feasibility Qualified & Architecture Specified  

---

### 1. Architectural Scope & Provenance

In Phase 1's failure taxonomy, endgame outcome errors (Category F6) accounted for $25.0\%$ of all chess failures in Janus Classical engines. While middle-game and opening play are governed by evaluation and search selectivity, endgames with $\le 5$ pieces (and up to 7 pieces) are mathematically solved by Syzygy endgame tablebases.

To evaluate tablebase assistance without compromising the strictly non-ML integrity of Janus, we conducted an independent feasibility study of embedding **Fathom** (Basil Falcinelli, based on Ronald de Man's canonical `tbprobe` library, MIT License):
* **Tablebase Formats:** `.rtbw` (Win-Draw-Loss) and `.rtbz` (Distance-to-Zero).
* **Piece Counts:** 3-piece, 4-piece, and 5-piece endgames.
* **Licensing & Dependencies:** Strictly non-neural, C/C++ native, zero external ML dependencies.

---

### 2. Probing Protocol & Correctness Requirements

```
+---------------------------------------------------------------------------------------------------------+
|                                    SYZYGY TABLEBASE INTEGRATION MODEL                                   |
|                                                                                                         |
|  [Interior Alpha-Beta Search] ──> Probes WDL when pieces <= SyzygyProbeLimit & ply >= SyzygyProbeDepth: |
|                                   - TB_WIN  : returns MATE_SCORE - ply (immediate cutoff)               |
|                                   - TB_LOSS : returns -MATE_SCORE + ply (immediate cutoff)              |
|                                   - TB_DRAW : returns 0 (immediate cutoff)                              |
|                                                                                                         |
|  [Root Move Decision]         ──> Probes DTZ when pieces <= SyzygyProbeLimit:                           |
|                                   - Selects the fastest winning move (minimal DTZ) or                   |
|                                   - Selects the most resilient drawing move.                            |
|                                                                                                         |
|  [Safety Guardrails]          ──> Castling rights present -> BYPASS (tablebases assume no castling)     |
|                               ──> 50-move counter near 100 -> Respect blessed loss / cursed win          |
|                               ──> Missing files / path empty -> GRACEFUL FALLBACK to standard search    |
+---------------------------------------------------------------------------------------------------------+
```

#### Correctness Invariants:
1. **Castling Rights Exclusion:** Tablebase generation assumes no castling rights remain. Any position where `castling_rights != 0` must strictly bypass tablebase probing.
2. **En Passant Semantics:** En passant capture squares must be verified against pawn positions prior to index lookup.
3. **Rule-50 Adjudication (Blessed Loss / Cursed Win):** Under the 50-move rule, certain theoretical wins exceed the 50-move threshold before a capture or pawn push. In DTZ probing, cursed wins are evaluated as draws when `Syzygy50MoveRule` is enabled.
4. **Missing File Resilience:** If `SyzygyPath` is unconfigured (empty string) or if requested `.rtbw` files are absent from disk, the probing core must immediately return `TB_RESULT_FAILED` and seamlessly continue alpha-beta search without crashing, throwing exceptions, or allocating memory.

---

### 3. UCI Option Interface Specification

Janus Classical engines support standard UCI options for Syzygy probing:
```
option name SyzygyPath type string default <empty>
option name SyzygyProbeDepth type spin default 1 min 1 max 100
option name SyzygyProbeLimit type spin default 5 min 0 max 7
option name Syzygy50MoveRule type check default true
```

* When `SyzygyPath` is set by the GUI/user, tablebase indices are initialized.
* When `SyzygyPath` is empty (default), tablebase probing is 100% bypassed.

---

### 4. Mandatory Experimental Separation Charter

Under the governing project rules:
> **The primary classical engine candidate (Janus Classical X13) MUST remain tablebase-disabled (`SyzygyPath <empty>`) for all primary strength qualification tournaments (Matches A, B, and C).**

* Handcrafted classical evaluation progress must be demonstrated and qualified strictly through chess knowledge and search algorithms alone.
* Any tablebase-assisted match must be reported as a separate, clearly identified intervention.
* In our audit of the Stockfish 19 benchmark (Match SF in P1.7), Stockfish was run with `SyzygyPath` empty, confirming that Stockfish's victory was achieved without tablebases.

