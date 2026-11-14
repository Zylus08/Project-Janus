import subprocess

vcvars = r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
engine_dir = r"E:\ChessXML\project-janus-phase1\engine\classical_x"

cmd = f'call "{vcvars}" && cd /d "{engine_dir}" && cl /O2 /Oi /Ot /std:c++17 /EHsc /LD janus_classical_x.cpp /Fe:janus_classical_x.dll && cd /d "E:\\ChessXML\\project-janus-phase1" && cl /std:c++17 /EHsc analysis\\phase1\\p1.19\\tests\\test_cpp_bp.cpp /Fe:analysis\\phase1\\p1.19\\tests\\test_cpp_bp.exe engine\\classical_x\\janus_classical_x.lib && copy /y engine\\classical_x\\janus_classical_x.dll analysis\\phase1\\p1.19\\tests\\ && analysis\\phase1\\p1.19\\tests\\test_cpp_bp.exe'

res = subprocess.run(f'cmd.exe /c "{cmd}"', shell=True, capture_output=True, text=True)
print(res.stdout)
if res.stderr:
    print("STDERR:", res.stderr)
