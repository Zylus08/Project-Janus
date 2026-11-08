#!/usr/bin/env python3
"""Project Janus v0.61 - Compile Native C++17 & AVX2 Binaries with MSVC."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
NATIVE_DIR = ROOT / "analysis" / "v0.61" / "native"
VCVARS = r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"

def run_cmd(cmd: str):
    full_cmd = f'cmd.exe /c ""{VCVARS}" && {cmd}""'
    print(f"\n[BUILD] Running: {cmd}")
    res = subprocess.run(
        full_cmd,
        cwd=str(NATIVE_DIR),
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        print("[BUILD] STDOUT:\n", res.stdout)
        print("[BUILD] STDERR:\n", res.stderr)
        raise RuntimeError(f"Build command failed with code {res.returncode}")
    else:
        print(f"[BUILD] Success! Output: {res.stdout.strip().splitlines()[-1] if res.stdout.strip() else 'OK'}")

def main():
    print("=" * 60)
    print("COMPILING PROJECT JANUS v0.61 NATIVE C++17 / AVX2 BINARIES")
    print("=" * 60)

    # 1. Compile test_nnue_v2_native.exe
    run_cmd("cl /O2 /W4 /std:c++17 /EHsc /arch:AVX2 test_nnue_v2_native.cpp nnue_v2.cpp /Fe:test_nnue_v2_native.exe")

    # 2. Compile janus_native.dll (Shared DLL for Python Bridge and Harness)
    run_cmd("cl /O2 /W4 /std:c++17 /EHsc /arch:AVX2 /LD janus_native.cpp nnue_v2.cpp /Fe:janus_native.dll")

    # 3. Compile janus_native_engine.exe (Standalone UCI Engine)
    run_cmd("cl /O2 /W4 /std:c++17 /EHsc /arch:AVX2 janus_native.cpp nnue_v2.cpp /Fe:janus_native_engine.exe")

    print("\nAll v0.61 native binaries compiled successfully.")

if __name__ == "__main__":
    main()
