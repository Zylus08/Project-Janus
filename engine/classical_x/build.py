#!/usr/bin/env python3
"""
Project Janus — Phase 1 Classical X Engine Build Pipeline
Compiles the developmental Janus Classical X source from C1 baseline anchor.
Produces:
  - janus_classical_x.exe (Standalone UCI engine)
  - janus_classical_x.dll (Shared library for Python ctypes / profiling)
"""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
C1_SRC = ROOT / "analysis" / "v0.56" / "native" / "janus_native.cpp"
TARGET_DIR = ROOT / "engine" / "classical_x"
TARGET_CPP = TARGET_DIR / "janus_classical_x.cpp"
TARGET_EXE = TARGET_DIR / "janus_classical_x.exe"
TARGET_DLL = TARGET_DIR / "janus_classical_x.dll"

VCVARS = r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"

def setup_source():
    # Only setup source from C1 baseline if developmental source does not already exist
    if TARGET_CPP.exists():
        print(f"Preserving existing developmental source: {TARGET_CPP} ({TARGET_CPP.stat().st_size:,} bytes).")
        return
    print(f"Initializing Janus Classical X developmental source in {TARGET_DIR}...")
    with open(C1_SRC, "r", encoding="utf-8") as f:
        code = f.read()
    
    code = code.replace(
        'std::cout << "id name Janus 0.56 Native (N7 Candidate)" << std::endl;',
        'std::cout << "id name Janus Classical X (P1.0 Development)" << std::endl;'
    )
    
    with open(TARGET_CPP, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"Wrote {TARGET_CPP} ({len(code):,} bytes).")

def run_msvc(cmd: str):
    full_cmd = f'cmd.exe /c ""{VCVARS}" && {cmd}""'
    print(f"\n[BUILD] Running: {cmd}")
    res = subprocess.run(
        full_cmd,
        cwd=str(TARGET_DIR),
        capture_output=True,
        text=True
    )
    if res.returncode != 0:
        print("[BUILD] STDOUT:\n", res.stdout)
        print("[BUILD] STDERR:\n", res.stderr)
        raise RuntimeError(f"Build failed with exit code {res.returncode}")
    print(f"[BUILD] Success! Output line: {res.stdout.strip().splitlines()[-1] if res.stdout.strip() else 'OK'}")

def main():
    setup_source()
    # 1. Compile Standalone UCI Engine
    run_msvc("cl /O2 /Ot /Oi /std:c++17 /EHsc janus_classical_x.cpp /Fe:janus_classical_x.exe")
    # 2. Compile Shared DLL
    run_msvc("cl /O2 /Ot /Oi /std:c++17 /EHsc /LD janus_classical_x.cpp /Fe:janus_classical_x.dll")
    print(f"\nJanus Classical X built successfully!")
    print(f"  EXE: {TARGET_EXE} (size: {TARGET_EXE.stat().st_size:,} bytes)")
    print(f"  DLL: {TARGET_DLL} (size: {TARGET_DLL.stat().st_size:,} bytes)")

if __name__ == "__main__":
    main()
