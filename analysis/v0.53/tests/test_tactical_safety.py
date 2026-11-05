"""Project Janus v0.53 - Tactical Safety & Differential Benchmark.

Evaluates N3 (Baseline, UsePVS=false, UseLMR=true) vs N4 (Candidate, UsePVS=true, UseLMR=true) across:
1. 12-position inherited tactical regression corpus
2. 16-position inherited validation corpus
3. 20-position independent tactical corpus (v0.53)
Total: 48 diverse tactical and strategic positions.

Records:
- Best moves, scores, nodes, search durations
- Move agreement rates and solve rates
- Independent Stockfish 19 reference moves
- PVS telemetry (full-window, null-window, re-searches, cutoffs)
"""

import json
import time
import subprocess
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
bridge_path = ROOT / "analysis" / "v0.53" / "native" / "janus_native_bridge.py"
spec = importlib.util.spec_from_file_location("janus_native_bridge_v53", bridge_path)
v53_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v53_mod)

NativeEngineBridge = v53_mod.NativeEngineBridge

CORPUS_DIR = ROOT / "analysis" / "v0.53" / "corpus"
RAW_DIR = ROOT / "analysis" / "v0.53" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)
STOCKFISH_PATH = Path("E:/ChessXML/tools/stockfish/stockfish.exe")


def get_stockfish_move(fen: str, movetime_ms: int = 200) -> str:
    try:
        p = subprocess.Popen(
            [str(STOCKFISH_PATH)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        cmds = ["uci", "isready", f"position fen {fen}", f"go movetime {movetime_ms}", "quit"]
        out, _ = p.communicate("\n".join(cmds) + "\n", timeout=5)
        for line in out.splitlines():
            if line.startswith("bestmove"):
                parts = line.split()
                if len(parts) >= 2:
                    return parts[1]
    except Exception:
        pass
    return ""


def evaluate_corpus(corpus_path: Path, depth: int = 5):
    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    bridge = NativeEngineBridge()
    results = []

    for entry in corpus:
        pos_id = entry["id"]
        fen = entry["fen"]
        expected = entry.get("solution") or entry.get("expected_move")
        theme = entry.get("theme", "Tactical")
        sf_mv = get_stockfish_move(fen, movetime_ms=300)

        # 1. Search N3 Baseline (UsePVS=false, UseLMR=true)
        bridge.clear_tt()
        bridge.reset_history()
        bridge.reset_pvs_telemetry()
        bridge.reset_lmr_telemetry()
        bridge.set_lmr_options(True)
        bridge.set_pvs_options(False)
        bridge.set_fen(fen)

        t0 = time.perf_counter()
        mv_n3, sc_n3, dp_n3, nd_n3, el_n3, pv_n3 = bridge.search(max_depth=depth, time_limit=5.0)
        t_n3 = time.perf_counter() - t0

        # 2. Search N4 Candidate (UsePVS=true, UseLMR=true)
        bridge.clear_tt()
        bridge.reset_history()
        bridge.reset_pvs_telemetry()
        bridge.reset_lmr_telemetry()
        bridge.set_lmr_options(True)
        bridge.set_pvs_options(True)
        bridge.set_fen(fen)

        t0 = time.perf_counter()
        mv_n4, sc_n4, dp_n4, nd_n4, el_n4, pv_n4 = bridge.search(max_depth=depth, time_limit=5.0)
        t_n4 = time.perf_counter() - t0
        telem_n4_pvs = bridge.get_pvs_telemetry()
        telem_n4_lmr = bridge.get_lmr_telemetry()

        n3_solved = (mv_n3 == expected) if expected else None
        n4_solved = (mv_n4 == expected) if expected else None
        agreed = (mv_n3 == mv_n4)
        node_diff_pct = ((nd_n3 - nd_n4) / nd_n3 * 100.0) if nd_n3 > 0 else 0.0

        results.append({
            "id": pos_id,
            "theme": theme,
            "fen": fen,
            "expected": expected,
            "stockfish_move": sf_mv,
            "n3_move": mv_n3,
            "n3_score": sc_n3,
            "n3_nodes": nd_n3,
            "n3_time": t_n3,
            "n3_solved": n3_solved,
            "n4_move": mv_n4,
            "n4_score": sc_n4,
            "n4_nodes": nd_n4,
            "n4_time": t_n4,
            "n4_solved": n4_solved,
            "agreed": agreed,
            "node_reduction_pct": node_diff_pct,
            "pvs_telemetry": telem_n4_pvs,
            "lmr_telemetry": telem_n4_lmr,
        })

    return results


def main():
    print("=" * 70)
    print("Project Janus v0.53 - Tactical Safety & Differential Benchmark")
    print("=" * 70)

    corpora = [
        ("Tactical Regression Suite (12)", CORPUS_DIR / "tactical_regression_corpus.json"),
        ("Validation Suite (16)", CORPUS_DIR / "validation_corpus.json"),
        ("Independent Tactical Suite v0.53 (20)", CORPUS_DIR / "independent_tactical_v053.json"),
    ]

    combined_output = {}

    for name, path in corpora:
        print(f"\nEvaluating {name} at Depth 5...")
        res = evaluate_corpus(path, depth=5)
        n_pos = len(res)
        n3_solv = sum(1 for r in res if r["n3_solved"])
        n4_solv = sum(1 for r in res if r["n4_solved"])
        agr = sum(1 for r in res if r["agreed"])
        tot_nd_n3 = sum(r["n3_nodes"] for r in res)
        tot_nd_n4 = sum(r["n4_nodes"] for r in res)
        pct_red = ((tot_nd_n3 - tot_nd_n4) / tot_nd_n3 * 100.0) if tot_nd_n3 > 0 else 0.0

        key = path.stem
        combined_output[key] = {
            "summary": {
                "name": name,
                "total": n_pos,
                "n3_solved": n3_solv,
                "n4_solved": n4_solv,
                "agreed": agr,
                "agreement_pct": agr / n_pos * 100.0,
                "total_nodes_n3": tot_nd_n3,
                "total_nodes_n4": tot_nd_n4,
                "node_reduction_pct": pct_red,
            },
            "positions": res,
        }

        print(f"Results for {name}:")
        print(f"  N3 Solved: {n3_solv}/{n_pos} ({n3_solv/n_pos*100:.1f}%)")
        print(f"  N4 Solved: {n4_solv}/{n_pos} ({n4_solv/n_pos*100:.1f}%)")
        print(f"  Move Agreement: {agr}/{n_pos} ({agr/n_pos*100:.1f}%)")
        print(f"  Total Nodes: N3={tot_nd_n3:,} vs N4={tot_nd_n4:,} ({pct_red:+.1f}%)")

        for r in res:
            status = "SOLVED" if r["n4_solved"] else ("AGREED" if r["agreed"] else "DIFF")
            print(f"  {r['id']:<30} Exp: {str(r['expected']):<5} N3: {str(r['n3_move']):<5} N4: {str(r['n4_move']):<5} SF: {str(r['stockfish_move']):<5} [{status}] Nodes: {r['n3_nodes']} -> {r['n4_nodes']}")

    out_file = RAW_DIR / "tactical_safety_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(combined_output, f, indent=2)

    print(f"\nRaw results written to {out_file}")


if __name__ == "__main__":
    main()

