# Project Janus v0.50 — Portability, Maintainability & Architectural Assessment

## 1. Executive Summary

Milestone v0.50 demonstrated that moving Janus's search pipeline to a native C++17 core yields an order-of-magnitude acceleration (**19.4x to 51.3x speedup**, achieving ~350,000 to ~650,000 NPS compared to ~6,000 to ~21,000 NPS in Python).

However, introducing native compilation fundamentally changes Janus's development workflow, distribution model, and maintainability profile. This document provides a comprehensive engineering assessment of the tradeoffs, build matrix, toolchains, memory safety, and boundary contracts.

---

## 2. Compilation and Build Matrix Across Target Platforms

The native search core (`janus_native.cpp`) is written in strict standard C++17 without proprietary platform dependencies. It requires only standard headers (`<cstdint>`, `<cstring>`, `<iostream>`, `<vector>`, `<chrono>`, `<string>`, `<sstream>`).

| Platform | Supported Compilers | Build Command | Output Artifact | ABI / Calling Convention |
|---|---|---|---|---|
| **Windows x86_64** | MSVC 2019/2022 (BuildTools / cl.exe) | `cl /O2 /LD /std:c++17 /EHsc /Fe:janus_native.dll janus_native.cpp` | `janus_native.dll` | Microsoft x64 (`__cdecl` / `extern "C"`) |
| **Windows x86_64 (GCC)**| MinGW-w64 (g++) | `g++ -O3 -shared -std=c++17 -o janus_native.dll janus_native.cpp` | `janus_native.dll` | x86_64 SysV / MS ABI |
| **Linux x86_64 / aarch64** | GCC 9+, Clang 10+ | `g++ -O3 -fPIC -shared -std=c++17 -o libjanus_native.so janus_native.cpp` | `libjanus_native.so` | System V AMD64 / ARM64 ABI |
| **macOS (Intel / Apple Silicon)** | Apple Clang / LLVM | `clang++ -O3 -dynamiclib -std=c++17 -o libjanus_native.dylib janus_native.cpp` | `libjanus_native.dylib` | Mach-O 64-bit dyld |

### 2.1 Intrinsics and Portability
- Bit scanning uses standard conditional macros:
  - MSVC: `_BitScanForward64` and `_BitScanReverse64` via `<intrin.h>`.
  - GCC / Clang: `__builtin_ctzll` and `__builtin_clzll`.
- Popcount uses:
  - MSVC: `__popcnt64`.
  - GCC / Clang: `__builtin_popcountll`.

---

## 3. Toolchain Dependencies & Deployment Considerations

### 3.1 Developer Environment vs End-User Deployment
1. **Developer Environment**:
   - Python developers modifying search algorithms will require a C++17 compiler toolchain (Visual Studio Build Tools on Windows, `build-essential` on Debian/Ubuntu, Xcode CLI on macOS).
   - A single-command build script or Python `setuptools` / `scikit-build-core` integration must automate compilation upon checkout.
2. **End-User Distribution**:
   - Pre-compiled binary wheels (`wheel`) containing the compiled DLL/so/dylib can be published, requiring zero C++ compiler on the user machine.
   - Zero external dynamic runtime dependencies beyond the standard C runtime (`ucrtbase.dll` / `glibc` / `libSystem.B.dylib`).

---

## 4. Maintainability Comparison: Python Search vs Native Search

| Dimension | Pure Python (v0.40–v0.49) | Native C++17 Core (v0.50+) | Assessment |
|---|---|---|---|
| **Lines of Code (Search + Board)**| ~1,200 LOC (across `search.py`, `evaluation.py`, `see.py`)| ~1,280 LOC (`janus_native.cpp`) | Comparable LOC; C++ is slightly more explicit |
| **Throughput (Depth 5)** | ~6,400 NPS | ~353,000 NPS | **>50x throughput advantage for C++** |
| **Rapid Prototyping** | High (instant edit-and-run) | Moderate (requires 1.5s recompile) | Python facilitates quick algorithmic sketches |
| **Type Safety & Refactoring** | Dynamic duck typing (mypy hints) | Compile-time static type enforcement | C++ catches bitboard type mismatches at build time |
| **Debugging Complexity** | Python pdb / traceback | Visual Studio Debugger / lldb / gdb | C++ requires native debug symbols (`/Zi`) |
| **Testability** | Direct unit testing via `pytest` | Direct testing via `ctypes` bridge + C++ unit tests | Full Python test harness intact via bridge |

---

## 5. Risk Analysis & Mitigation Strategies

| Risk | Impact | Likelihood | Mitigation Strategy |
|---|---|---|---|
| **Memory Safety / Buffer Overflow** | High | Low | Zero dynamic heap allocation during search (`new`/`malloc` avoided). All move lists, PV arrays, and search stacks are statically sized or pre-allocated. |
| **Cross-Platform ABI Drift** | Medium | Low | C-linkage export boundary (`extern "C"`). Plain POD structs (`NativeBoard`, `NativeSearchResult`) with explicit fixed-width integer types (`uint64_t`, `uint16_t`, `uint8_t`). |
| **Heuristic Semantic Drift** | Medium | Medium | Automated differential regression test suite running in CI comparing Python K0 and Native N2 across the 37-position diagnostic corpus. |
| **Build Friction for Contributors** | Medium | Low | Provide fallback to Python K0 when native DLL is absent (`JANUS_USE_NATIVE=0` environment toggle). |

---

## 6. Boundary Contract Specification (Python-Native Interface)

The interface is defined strictly via standard C ABI types in `janus_native_bridge.py`:

```c
extern "C" {
    // Initialization & Lifecycle
    int native_init();

    // Board Configuration & Queries
    int native_set_fen(const char* fen, NativeBoard* board);
    void native_get_fen(const NativeBoard* board, char* out_fen);
    int native_is_check(const NativeBoard* board);
    int native_evaluate(const NativeBoard* board);

    // State Transitions & Move Generation
    int native_make_move(NativeBoard* board, uint16_t move, UndoInfo* undo);
    void native_unmake_move(NativeBoard* board, uint16_t move, const UndoInfo* undo);
    int native_generate_legal_moves(NativeBoard* board, uint16_t* out_moves);
    uint64_t native_perft(NativeBoard* board, int depth);

    // High-Level Search
    int native_search(
        NativeBoard* board,
        int max_depth,
        double time_limit_sec,
        NativeSearchResult* result
    );

    // Formatting Helpers
    void native_move_to_uci(uint16_t move, char* out_uci);
    uint16_t native_uci_to_move(const NativeBoard* board, const char* uci);
}
```

### Boundary Design Principles:
1. **Coarse-Grained FFI**: Calls across the boundary occur only at engine boundaries (e.g. `native_search` or `native_perft`), entirely avoiding per-node or per-move FFI transitions.
2. **Deterministic Ownership**: All memory is allocated and owned by the caller (Python side allocates the ctypes struct, passing pointers into C++).
3. **No C++ Exception Leakage**: C++ functions return integer status codes (0 = failure, 1 = success) and never throw across the `extern "C"` boundary.

