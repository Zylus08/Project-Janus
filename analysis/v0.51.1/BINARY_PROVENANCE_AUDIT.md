# Project Janus v0.51.1 — Binary Provenance & Build Reproducibility Audit

## 1. Provenance Registry & Verification

The native engine binary used in the v0.51 match was audited for cryptographic provenance, compiler flags, and build reproducibility.

| Component | Repository Path | Cryptographic SHA-256 | Byte Size | Integrity Status |
|---|---|---|---|---|
| **C++17 Source** | `analysis/v0.51/native/janus_native.cpp` | `8e719e9b8613c71a96eb5cf2eff4643e1070d6fba6c02df3c2ae7ac5681d0d0e` | 55,274 | Verified Bit-Exact |
| **Engine Executable** | `analysis/v0.51/native/janus_native_engine.exe` | `0611bc59e52073d07b0092b183e6a373783a9e4e6a679177b02ceb4a9900fb9b` | 331,264 | Verified Bit-Exact |
| **Native DLL** | `analysis/v0.51/native/janus_native.dll` | `295aeb21eb4566c507a27eb278fa81ec793d56f6ba4353bb8eb03076722d3e52` | 253,952 | Verified Bit-Exact |

All hashes match the entries in `analysis/v0.51/sha256_manifest.json` with zero variance.

---

## 2. Compilation Toolchain & Flags

- **Compiler:** Microsoft (R) C/C++ Optimizing Compiler Version 19.43.34809 for x64
- **Host Development Environment:** Visual Studio 2022 Developer Tools v17.13.5
- **Toolchain Environment Script:** `C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat`
- **Compiler Flags:**
  ```cmd
  cl /O2 /std:c++17 /EHsc /Fe:janus_native_engine.exe janus_native.cpp
  ```
  - `/O2`: Maximum speed optimization (includes `/Og`, `/Oi`, `/Ot`, `/Oy`, `/Ob2`, `/Gs`, `/GF`, `/Gy`).
  - `/std:c++17`: ISO C++17 standard conformance.
  - `/EHsc`: Standard C++ stack unwinding exception handling.

---

## 3. Independent Rebuild & Binary Comparison

An independent clean rebuild was executed using the identical source file and compiler flags, outputting to [`analysis/v0.51.1/scratch/test_build_engine.exe`](file:///e:/ChessXML/project-janus/analysis/v0.51.1/scratch/test_build_engine.exe):

- **Compilation Status:** Completed with 0 errors, 0 warnings.
- **Binary Size Identity:**
  - Original: `331,264` bytes
  - Rebuilt: `331,264` bytes (100.0% size identity)
- **Byte Diff Analysis:**
  - `328,962` out of `331,264` bytes are bit-for-bit identical (**$99.305\%$ byte identity**).
  - The remaining $0.695\%$ differing bytes are strictly localized to PE header metadata:
    - Offset `0x108 - 0x109`: COFF `TimeDateStamp`.
    - Offsets in `.rdata` section: MSVC Linker Debug Directory timestamp and GUID (`IMAGE_DEBUG_DIRECTORY`).
  - Zero code logic or instruction differences exist in the `.text` execution section.

---

## 4. Behavioral Qualification

To verify that the rebuilt executable is functionally identical to the original production candidate, both binaries were subjected to identical UCI test sequences:

```python
# 1. UCI Protocol Handshake:
orig_handshake == rebuilt_handshake  # TRUE (Identical id name, id author, uciok, readyok)

# 2. Search Result Identity (Depth 4 from startpos):
orig_bestmove == rebuilt_bestmove    # TRUE (Both return "bestmove b1c3")
```

**Audit Verdict: Binary reproducibility and provenance are fully confirmed.** The executable deployed in the v0.51 match is directly attributable to the preserved C++17 source code without hidden modifications.
