# Project Janus v0.51 — Standalone Native UCI Engine Qualification

## 1. Executive Summary

Phase E establishes the first standalone native executable chess engine in Project Janus: `janus_native_engine.exe`.

In previous milestones (v0.40–v0.50), Janus required Python bytecode execution and `python-chess` for game orchestration, UCI protocol management, and board representation. In v0.51, Candidate **N2** operates as a fully autonomous, standalone 64-bit native executable that speaks standard Universal Chess Interface (UCI) protocol directly via standard I/O streams.

### Key Milestones Achieved:
1. **Zero-Python Execution**: The engine operates independently without requiring Python, virtual environments, or external dependencies beyond standard Windows C/C++ runtimes.
2. **Deterministic Unbuffered I/O**: `stdin` and `stdout` use non-buffered I/O (`setvbuf(..., _IONBF, 0)` and `std::unitbuf`), eliminating pipe buffering stalls under GUI controllers and tournament harnesses.
3. **Fischer Time Management**: Allocates search time dynamically based on remaining clock and increment:
   $$T_{\text{alloc}} = \frac{T_{\text{remaining}} + 40 \times \text{inc}}{40}$$
   with a mandatory safety buffer ($T_{\text{remaining}} - 50$ ms).
4. **Complete Protocol Qualification**: Passed 10 automated integration tests covering handshakes, synchronization, position parsing, move sequences, Fischer clocks, and multi-game self-play (`tests/test_native_uci_protocol.py`).

---

## 2. Implemented UCI Command & Response Matrix

| Inbound Command | Parameters / Formats Supported | Native Engine Behaviour | Outbound Response |
|---|---|---|---|
| `uci` | None | Initializes attack tables, TT, and history; identifies engine | `id name Janus 0.51 Native`<br>`id author Project Janus Team`<br>`uciok` |
| `isready` | None | Flushes pending operations; verifies ready state | `readyok` |
| `ucinewgame` | None | Resets game history stack to 0; clears 1M-entry transposition table | Silent (ready for `position`) |
| `position` | `startpos [moves m1 m2 ...]` | Resets to standard opening position; pushes moves to history | Silent |
| `position` | `fen <FEN> [moves m1 m2 ...]` | Validates and parses FEN string; pushes subsequent moves | Silent |
| `go` | `depth <d>` | Binds search to exact nominal depth; iterative deepening | `info depth ... score ... pv ...`<br>`bestmove <m>` |
| `go` | `movetime <ms>` | Binds search to wall-clock limit in milliseconds | `info ...`<br>`bestmove <m>` |
| `go` | `wtime <ms> btime <ms> [winc <ms>] [binc <ms>]` | Calculates dynamic Fischer time allocation | `info ...`<br>`bestmove <m>` |
| `stop` | None | Sets abort flag; immediately terminates and outputs best move | `bestmove <m>` |
| `quit` | None | Closes handles and terminates process with exit code 0 | Process exit |

---

## 3. Info Output & PV Formatting

During search, `janus_native_engine.exe` formats standard diagnostic lines conformant with international tournament GUIs (e.g. Cutechess, Arena, Banksia):

```
info depth 4 score cp 50 nodes 6249 nps 1665644 time 3 pv b1c3 b8c6 g1f3 g8f6
bestmove b1c3
```

- `depth <d>`: Current completed nominal iteration depth.
- `score cp <s>`: Root position evaluation in centipawns from mover's perspective.
- `nodes <n>`: Cumulative total nodes evaluated (alpha-beta negamax + quiescence).
- `nps <rate>`: Effective search speed in nodes per second.
- `time <ms>`: Wall-clock execution time elapsed in milliseconds.
- `pv <moves>`: Full principal variation extracted from the internal triangular PV table.
- `bestmove <m>`: Coordinate notation best move (e.g. `e2e4`, `g1f3`, `e7e8q`).

---

## 4. Time Management Policy

In standard tournament play (e.g. 3s + 100ms increment), engines must avoid losing on time due to operating-system thread scheduling jitter.

### Native Policy Specification:
```cpp
if (movetime < 0) {
    int my_time = (board.side_to_move == WHITE) ? wtime : btime;
    int my_inc = (board.side_to_move == WHITE) ? winc : binc;

    if (my_time > 0) {
        // Fischer allocation assuming 40-move horizon
        double alloc_ms = (my_time + 40.0 * my_inc) / 40.0;
        // Safety reserve: never consume within 50ms of flag-fall
        if (alloc_ms > my_time - 50.0) alloc_ms = std::max(10.0, my_time - 50.0);
        time_limit = alloc_ms / 1000.0;
    }
}
```

---

## 5. Automated Protocol Test Results (`tests/test_native_uci_protocol.py`)

```
Ran 10 tests in 1.055s. OK.
```

| Test Case | Target Subsystem | Verification Goal | Status |
|---|---|---|:---:|
| `test_01` | Handshake | Responds with identity tokens and `uciok` | **PASS** |
| `test_02` | Synchronization | Responds to `isready` with `readyok` | **PASS** |
| `test_03` | Startpos Setup | Generates and selects legal best move from initial position | **PASS** |
| `test_04` | FEN Setup | Sets Legall's mate position; finds `d5f6#` | **PASS** |
| `test_05` | Move History | Parses 4-move opening line; produces legal response | **PASS** |
| `test_06` | Info Tokens | Validates presence of `depth`, `score cp`, `nodes`, `nps`, `time`, `pv` | **PASS** |
| `test_07` | Fischer Clock | Executes search under `wtime 3000 btime 3000 winc 100 binc 100` | **PASS** |
| `test_08` | State Reset | Validates `ucinewgame` resets game history between matches | **PASS** |
| `test_09` | Multi-Game Session | Plays 10 plies of self-play on single persistent process | **PASS** |
| `test_10` | Termination | Terminates cleanly on `quit` with exit code 0 | **PASS** |

---

## 6. Reproducible Launch & Build Instructions

### Compilation:
```powershell
cmd /c 'call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" && cl /O2 /std:c++17 /EHsc /Fe:analysis\v0.51\native\janus_native_engine.exe analysis\v0.51\native\janus_native.cpp'
```

### Execution:
```powershell
.\analysis\v0.51\native\janus_native_engine.exe
```
Or configure in any UCI-compliant GUI pointing directly to the executable path.

