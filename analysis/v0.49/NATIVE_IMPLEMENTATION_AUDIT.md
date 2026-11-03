# Project Janus v0.49 — Native Implementation Audit

**Milestone:** Project Janus v0.49  
**Parent Baseline Commit:** `6b46eb4` (v0.48 Final)  
**Evaluated Architecture:** Candidate N1 (Native Move Picker Kernel via MSVC C DLL and `ctypes`)  
**Source Code:** [`analysis/v0.49/native/move_picker.c`](file:///E:/ChessXML/project-janus/analysis/v0.49/native/move_picker.c)  
**Compiled Binary:** [`analysis/v0.49/native/move_picker.dll`](file:///E:/ChessXML/project-janus/analysis/v0.49/native/move_picker.dll)  
**Runtime Bridge:** [`analysis/v0.49/native/native_picker.py`](file:///E:/ChessXML/project-janus/analysis/v0.49/native/native_picker.py)  
**Build Manifest:** [`analysis/v0.49/native_build_manifest.json`](file:///E:/ChessXML/project-janus/analysis/v0.49/native_build_manifest.json)

---

## 1. Candidate Architecture (Phase C1 & C2)

Candidate N1 implements a high-performance C kernel that offloads move-order sorting and incremental selection from Python to native machine code.

### Exported C ABI Functions:
1. `native_select_next_best(const int* scores, const unsigned char* selected_mask, int n)`
   - Computes the highest-scoring candidate move in $O(N)$ with strict stability: if two moves share an identical score, the move with the lowest original index is returned.
2. `native_stable_partial_sort(const int* scores, int n, int k, int* out_indices)`
   - Executes an in-place stable partial selection sort on move indices.
   - For small move arrays ($N \approx 20\text{--}60$), it avoids dynamic heap allocations, avoids recursion, and guarantees that ties preserve generation order.
3. `native_move_picker_version()`
   - Returns ABI version `4901` for runtime verification.

---

## 2. Toolchain and Build Provenance (Phase C4)

- **Compiler:** Microsoft (R) C/C++ Optimizing Compiler Version 19.43.34809 for x64
- **Toolset:** MSVC BuildTools 2022 (v17.13.5)
- **Compilation Command:**
  ```cmd
  call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" && cl /O2 /LD /Fe:analysis\v0.49\native\move_picker.dll analysis\v0.49\native\move_picker.c
  ```
- **Optimization Flags:** `/O2` (maximize speed), `/LD` (create DLL), 64-bit target architecture.
- **Dependencies:** Strictly ANSI C standard library (`stdlib.h`, `string.h`), zero external DLL dependencies.

---

## 3. Native Boundary Overhead Analysis (Phase C3)

Across 5,000 randomized microbenchmark iterations across move list sizes:

| Move List Size ($N$) | Python `list.sort` | Python Incremental Top 1 | Native Partial Sort Top 1 | Native Full Sort ($N$) | Native Per-Move Call |
|---|---:|---:|---:|---:|---:|
| **$N = 10$** | **1.30 µs** | **0.50 µs** | 3.40 µs | 4.60 µs | 4.30 µs |
| **$N = 25$** | **3.40 µs** | **1.10 µs** | 5.40 µs | 9.10 µs | 8.10 µs |
| **$N = 35$** | **5.20 µs** | **1.40 µs** | 7.00 µs | 16.60 µs | 10.30 µs |
| **$N = 50$** | 9.50 µs | **1.80 µs** | **8.60 µs** | 19.30 µs | 13.80 µs |
| **$N = 75$** | 10.60 µs | **2.60 µs** | 11.60 µs | 24.90 µs | 20.70 µs |

### Architectural Findings:
1. **The Ctypes Marshaling Penalty:** Allocating `(ctypes.c_int * n)` in Python and passing pointers across the C boundary requires $\sim 2.5\text{--}3.0\ \mu\text{s}$ per call.
2. **Break-Even Threshold:** Native execution only begins to break even with Python's C-implemented `list.sort()` when $N \ge 50$ candidate moves.
3. **Repeated Calls Are Unviable:** Invoking `native_select_next_best` per move costs 8.1 µs to 13.8 µs per call, confirming the theoretical prediction from Phase B that per-move native calls cannot compete with batch sorting.

---

## 4. Fallback and Graceful Degradation (Phase C4)

The runtime bridge in [`analysis/v0.49/native/native_picker.py`](file:///E:/ChessXML/project-janus/analysis/v0.49/native/native_picker.py) provides automatic detection:
- If `move_picker.dll` is missing, corrupted, or incompatible, `native_available` is set to `False`.
- Any call to `native_stable_partial_sort` transparently routes to `py_stable_partial_sort`, logging no unhandled exceptions and maintaining 100% search correctness.

