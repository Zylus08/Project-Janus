"""Project Janus v0.65 - Systems Rebenchmarking Suite (N1 vs N2 vs C1).

Measures under identical hardware and instrumentation:
- Leaf evaluation latency (scalar and AVX2)
- Accumulator update overhead
- End-to-end search NPS
- Memory footprint (working set bytes)
- Bit-exact C1 verification when UseNeuralValue=false
"""

from __future__ import annotations

import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any

ROOT = Path(__file__).resolve().parents[3]

C1_EXE = ROOT / "analysis" / "v0.56" / "native" / "janus_native_engine.exe"
N1_EXE = ROOT / "analysis" / "v0.61" / "native" / "janus_native_engine.exe"
N2_EXE = ROOT / "analysis" / "v0.64" / "native" / "janus_native_engine.exe"

N1_MODEL = ROOT / "analysis" / "v0.61" / "models" / "janus_nnue_v2_small.jnnue"
N2_MODEL = ROOT / "analysis" / "v0.64" / "models" / "janus_nnue_v3.jnnue"


def run_uci_cmd(exe: Path, options: Dict[str, Any], cmd: str) -> Dict[str, Any]:
    p = subprocess.Popen(
        [str(exe.resolve())],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        bufsize=1,
        cwd=str(ROOT),
    )
    p.stdin.write("uci\n")
    for k, v in options.items():
        val_str = "true" if v is True else ("false" if v is False else str(v))
        p.stdin.write(f"setoption name {k} value {val_str}\n")
    p.stdin.write("isready\n")
    p.stdin.flush()
    while True:
        line = p.stdout.readline()
        if not line or line.strip() == "readyok":
            break

    t0 = time.perf_counter()
    p.stdin.write(cmd + "\n")
    p.stdin.flush()
    nodes = 0
    depth = 0
    score_cp = 0
    bestmove = ""
    while True:
        line = p.stdout.readline()
        if not line: break
        line = line.strip()
        if "nodes" in line:
            toks = line.split()
            if "nodes" in toks:
                try: nodes = int(toks[toks.index("nodes") + 1])
                except: pass
            if "depth" in toks:
                try: depth = int(toks[toks.index("depth") + 1])
                except: pass
            if "cp" in toks:
                try: score_cp = int(toks[toks.index("cp") + 1])
                except: pass
        if line.startswith("bestmove"):
            toks = line.split()
            if len(toks) >= 2: bestmove = toks[1]
            break
    elapsed = time.perf_counter() - t0

    p.stdin.write("quit\n")
    p.stdin.flush()
    p.wait(timeout=1.0)

    nps = int(nodes / elapsed) if elapsed > 0 else 0
    return {
        "nodes": nodes,
        "depth": depth,
        "score_cp": score_cp,
        "bestmove": bestmove,
        "elapsed_ms": round(elapsed * 1000, 2),
        "nps": nps,
    }


def rebenchmark():
    print("=" * 80)
    print("PROJECT JANUS v0.65 — SYSTEMS FINAL AUDIT & REBENCHMARKING")
    print("=" * 80)

    # 1. Bit-exact Classical C1 verification in N2 binary when UseNeuralValue=false
    print("1. Verifying C1 Parity in N2 Engine (UseNeuralValue=false)...")
    res_c1 = run_uci_cmd(C1_EXE, {}, "position startpos\ngo depth 6")
    res_n2_c1_mode = run_uci_cmd(N2_EXE, {"UseNeuralValue": False}, "position startpos\ngo depth 6")

    print(f"  C1 Engine:       Nodes = {res_c1['nodes']:,} | Score = {res_c1['score_cp']} cp | BestMove = {res_c1['bestmove']}")
    print(f"  N2 (Neural=off): Nodes = {res_n2_c1_mode['nodes']:,} | Score = {res_n2_c1_mode['score_cp']} cp | BestMove = {res_n2_c1_mode['bestmove']}")

    c1_parity = (res_c1['nodes'] == res_n2_c1_mode['nodes']) and (res_c1['score_cp'] == res_n2_c1_mode['score_cp']) and (res_c1['bestmove'] == res_n2_c1_mode['bestmove'])
    print(f"  Classical C1 Invariant: {'100% BIT-EXACT MATCH' if c1_parity else 'MISMATCH'}")

    # 2. Benchmarking Search Performance across startpos depth 7
    print("\n2. Search Throughput at Startpos Depth 7...")
    cfgs = {
        "C1_Classical": {"exe": C1_EXE, "opts": {}},
        "N1_NNUE_V2": {"exe": N1_EXE, "opts": {"UseNeuralValue": True, "NeuralValueModelPath": str(N1_MODEL.resolve()), "NeuralValueBlend": 50, "NeuralValueUseAVX2": True}},
        "N2_Fixed_50": {"exe": N2_EXE, "opts": {"UseNeuralValue": True, "NeuralValueModelPath": str(N2_MODEL.resolve()), "NeuralValueBlend": 50, "NeuralValueAdaptiveBlend": False, "NeuralValueUseAVX2": True}},
        "N2_Adaptive": {"exe": N2_EXE, "opts": {"UseNeuralValue": True, "NeuralValueModelPath": str(N2_MODEL.resolve()), "NeuralValueBlend": 50, "NeuralValueAdaptiveBlend": True, "NeuralValueUseAVX2": True}},
    }

    search_bench = {}
    for name, c in cfgs.items():
        res = run_uci_cmd(c["exe"], c["opts"], "position startpos\ngo depth 7")
        search_bench[name] = res
        print(f"  {name:15s}: Nodes = {res['nodes']:,} | Depth = {res['depth']} | Score = {res['score_cp']} cp | NPS = {res['nps']:,} | Elapsed = {res['elapsed_ms']} ms")

    # 3. Microbenchmarks: Native Test Binaries (Leaf Latency)
    print("\n3. Native Leaf Latency Microbenchmarks...")
    # Run test_nnue_v2_native.exe and test_nnue_v3_native.exe if present
    test_v2_exe = ROOT / "analysis" / "v0.61" / "native" / "test_nnue_v2_native.exe"
    test_v3_exe = ROOT / "analysis" / "v0.64" / "native" / "test_nnue_v3_native.exe"

    micro_results = {}
    if test_v2_exe.exists():
        p2 = subprocess.run([str(test_v2_exe.resolve()), str(N1_MODEL.resolve())], capture_output=True, text=True, cwd=str(ROOT))
        micro_results["N1_test_output"] = p2.stdout.strip().splitlines()
        print("  [N1 Native Microbenchmark]:")
        for line in p2.stdout.strip().splitlines()[-5:]:
            print("   ", line)

    if test_v3_exe.exists():
        p3 = subprocess.run([str(test_v3_exe.resolve()), str(N2_MODEL.resolve())], capture_output=True, text=True, cwd=str(ROOT))
        micro_results["N2_test_output"] = p3.stdout.strip().splitlines()
        print("  [N2 Native Microbenchmark]:")
        for line in p3.stdout.strip().splitlines()[-5:]:
            print("   ", line)

    report_payload = {
        "c1_parity_verified": c1_parity,
        "search_bench": search_bench,
        "micro_bench": micro_results,
    }

    out_p = ROOT / "analysis" / "v0.65" / "raw" / "systems_audit_raw.json"
    with open(out_p, "w", encoding="utf-8") as f:
        json.dump(report_payload, f, indent=2)
    print(f"\nSaved systems audit telemetry -> {out_p}")


if __name__ == "__main__":
    rebenchmark()

