# Project Janus v0.49 — Compiled Move-Picker Feasibility Study

**Milestone:** Project Janus v0.49  
**Parent Baseline Commit:** `6b46eb4` (v0.48 Final)  
**Evaluated Technologies:**
- **Option A:** Cython typed extension
- **Option B:** Native C DLL via CPython C-extension / `ctypes`
- **Option C:** Python built-in C primitives (`list.sort`, `_heapq`, `math`, generator slicing)

---

## 1. Defining the Native Boundary (B1)

In Project Janus, the move-ordering pipeline occurs at every interior node of the alpha-beta search.

### Operations Suitable for Native Compilation:
1. **Move Selection & Partial Sorting:** Finding the maximum-scoring move from an array of candidates, swapping it into the next position (selection sort), and yielding it without sorting the remaining tail.
2. **History Table Representation & Lookup:** Indexing a $64 \times 64$ flat integer array (`history[from_sq * 64 + to_sq]`) and applying depth-based increment or saturation.
3. **Move Comparison & Tie-Breaking:** Comparing 32-bit integer scores and preserving original move generation order on score ties.

### Operations That Must Remain in Python:
1. **Legal Move Generation:** `chess.Board.legal_moves` is implemented by `python-chess`. Extracting move generation into C would require rewriting the entire board representation, bitboards, attack masks, and castling rules in C, violating the milestone constraints.
2. **Search Recursion & Board State:** `board.push(move)` and `board.pop()` maintain transposition keys, repetition lists, and move undo state.
3. **Evaluation & Static Exchange Evaluation (SEE):** Interacts directly with `chess.Piece` and bitboard structures.
4. **Time Management & UCI Protocol:** Threading events, deadlines, and standard I/O must remain in Python.

### Conclusion on Boundary:
The narrowest, most viable native boundary is a **Move Selection Kernel**: Python generates legal moves; integer move descriptors and their integer scores are passed to the native kernel; the native kernel returns the selected move indices or partially sorted order.

---

## 2. Evaluation of Native Implementation Alternatives (B2)

| Criteria | Option A: Cython | Option B: Native C DLL (`ctypes`) | Option C: Python Built-in C Primitives |
|---|---|---|---|
| **Build Dependency** | Requires `cython`, `setuptools`, `wheel` (not installed in project venv). | Requires only MSVC `cl.exe` (installed at `C:\Program Files (x86)\...`). | **Zero build dependencies** (built into CPython runtime). |
| **Python 3.13 Support** | Experimental in Cython 3.0; free-threading / ABI issues on Windows. | **Full support** (standard C ABI via `ctypes` / C-API). | **100% native CPython 3.13 support**. |
| **Call Boundary Overhead** | Low (if C-types used directly), but still requires Python bridge. | Moderate: ctypes argument marshalling (~200–500 ns per call). | **Zero boundary overhead** (already inside CPython runtime). |
| **Maintenance & Portability** | High: generates multi-megabyte C files, sensitive to compiler versions. | Low: clean, single-file ANSI C (`move_picker.c`), easily compiled with gcc/clang/cl. | **Zero maintenance cost**. |
| **Fallback Complexity** | Requires compiling dual codebases or complex import fallbacks. | Simple: `try: ctypes.CDLL(...) except OSError: fallback()`. | Not applicable (always available). |

---

## 3. The Boundary Overhead Tradeoff: The "Micro-Kernel Paradox"

In interpreted Python, calling a C function via `ctypes` or C-API incurs a fixed overhead of approximately $200$ to $500$ nanoseconds per call.
- In Project Janus, an average node examines $\sim 30$ moves.
- Sorting 30 Python integers with built-in `list.sort()` (implemented in C Timsort) takes approximately **$1.5$ to $2.5$ microseconds**.
- If a native function is invoked repeatedly to pick moves one-by-one (incremental selection), 30 calls $\times 300\text{ ns} = \mathbf{9.0\ \mu s}$, which is **$4\times$ slower than Python's built-in `list.sort()`**!
- Therefore, **repeated per-move native calls are mathematically guaranteed to regress performance**.
- The ONLY viable native architecture is **Batch Execution**: passing the move array once and receiving either a partially sorted array or an index mapping in a single C call.

---

## 4. Feasibility Decision (B3)

### **Selected Implementation Path: Option B (Self-Contained Native C DLL via MSVC `cl.exe` and `ctypes`)**

1. **Architecture:** We will implement `analysis/v0.49/native/move_picker.c`, containing:
   - `stable_incremental_select(int* move_ids, int* scores, int n, int k, int* out_indices)`
   - `batch_partial_sort(int* move_ids, int* scores, int n, int cutoff_limit, int* out_indices)`
2. **Build Toolchain:** Compiled directly using MSVC BuildTools 2022 (`cl.exe /LD /O2 /Fe:move_picker.dll move_picker.c`) with zero third-party pip dependencies.
3. **Fallback Guarantee:** An explicit, transparent Python fallback will be maintained. If the DLL is missing or fails to load, the system falls back to Python selection and logs an explicit diagnostic flag (`native_available=False`).
4. **Feasibility Validation:** Proceed to Phase C to prototype Candidate N1.

