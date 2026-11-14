import os
import subprocess
import sys

VCVARS = r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
ENGINE_DIR = r"E:\ChessXML\project-janus-phase1\engine\classical_x"

def build():
    cmd = f'call "{VCVARS}" && cd /d "{ENGINE_DIR}" && cl /O2 /Oi /Ot /std:c++17 /EHsc janus_classical_x.cpp /Fe:janus_classical_x.exe && cl /O2 /Oi /Ot /std:c++17 /EHsc /LD janus_classical_x.cpp /Fe:janus_classical_x.dll'
    print(f"Running build command...")
    res = subprocess.run(f'cmd.exe /c "{cmd}"', shell=True, capture_output=True, text=True)
    print("STDOUT:\n", res.stdout)
    print("STDERR:\n", res.stderr)
    print("Return code:", res.returncode)
    if res.returncode != 0:
        sys.exit(1)
    print("Build successful!")

if __name__ == "__main__":
    build()
