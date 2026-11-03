"""Analyze raw benchmark results, call counts, and run post-optimization profiling for v0.29."""
import json
import os
import io
import cProfile
import pstats
import statistics
from typing import Any
import chess
from janus.search import JanusSearch

BENCHMARK_PATH = os.path.join("analysis", "v0.29", "benchmarks", "v029_interleaved_benchmark.json")
OUTPUT_SUMMARY = os.path.join("analysis", "v0.29", "benchmarks", "v029_benchmark_summary.json")
PROFILE_DIR = os.path.join("analysis", "v0.29", "profile")


def calc_med_iqr(vals: list[float]) -> tuple[float, float]:
    sorted_vals = sorted(vals)
    med = float(statistics.median(sorted_vals))
    if len(sorted_vals) >= 4:
        q = statistics.quantiles(sorted_vals, n=4)
        iqr = float(q[2] - q[0])
    else:
        iqr = 0.0
    return med, iqr


def measure_detailed_call_counts():
    """Measure gives_check calls and rejection breakdown across benchmark positions."""
    with open("benchmarks/positions.json", "r", encoding="utf-8") as f:
        positions = json.load(f)

    # 1. Measure Eager baseline call count
    orig_gives_check = chess.Board.gives_check
    eager_calls = 0

    def eager_counter(self, move):
        nonlocal eager_calls
        eager_calls += 1
        return orig_gives_check(self, move)

    # 2. Measure Lazy candidate call count
    lazy_calls = 0

    def lazy_counter(self, move):
        nonlocal lazy_calls
        lazy_calls += 1
        return orig_gives_check(self, move)

    # We also want to instrument the rejection breakdown in negamax
    rejection_reasons = {
        "lmr_disabled": 0,
        "early_move_index (< 3)": 0,
        "shallow_depth (< 3)": 0,
        "root_ply (== 0)": 0,
        "in_check": 0,
        "tactical_capture": 0,
        "promotion": 0,
        "killer_move": 0,
        "passed_to_gives_check": 0,
    }

    # Let's count by depth
    stats_by_depth = {}

    for depth in [4, 5]:
        eager_calls = 0
        lazy_calls = 0

        # Eager count:
        # Patch gives_check for eager
        chess.Board.gives_check = eager_counter
        # We can construct eager search
        with open("src/janus/search.py", "r", encoding="utf-8") as f:
            src = f.read()

        target_lazy = """        for move in moves:
            is_capture = board.is_capture(move)
            is_promotion = move.promotion is not None

            eligible_for_lmr = (
                self.enable_lmr
                and moves_searched >= 3
                and depth >= 3
                and ply > 0
                and not in_check
                and not is_capture
                and not is_promotion
                and (
                    ply >= len(self.killers)
                    or (move != self.killers[ply][0] and move != self.killers[ply][1])
                )
                and not board.gives_check(move)
            )"""

        replacement_eager = """        for move in moves:
            is_capture = board.is_capture(move)
            is_promotion = move.promotion is not None
            gives_check = board.gives_check(move)

            eligible_for_lmr = (
                self.enable_lmr
                and moves_searched >= 3
                and depth >= 3
                and ply > 0
                and not in_check
                and not is_capture
                and not is_promotion
                and not gives_check
                and (
                    ply >= len(self.killers)
                    or (move != self.killers[ply][0] and move != self.killers[ply][1])
                )
            )"""

        eager_ns = {"__name__": "janus.search", "__file__": "src/janus/search.py"}
        exec(src.replace(target_lazy, replacement_eager), eager_ns)
        EagerSearch = eager_ns["JanusSearch"]

        for p in positions:
            b = chess.Board(p["fen"])
            s = EagerSearch()
            s.search(b, max_depth=depth)

        e_count = eager_calls

        # Lazy count:
        chess.Board.gives_check = lazy_counter
        for p in positions:
            b = chess.Board(p["fen"])
            s = JanusSearch()
            s.search(b, max_depth=depth)

        l_count = lazy_calls
        avoided = e_count - l_count
        reduction_pct = (avoided / e_count * 100) if e_count > 0 else 0.0

        stats_by_depth[f"depth_{depth}"] = {
            "eager_calls": e_count,
            "lazy_calls": l_count,
            "calls_avoided": avoided,
            "reduction_pct": reduction_pct,
        }

    chess.Board.gives_check = orig_gives_check
    return stats_by_depth


def analyze_benchmarks():
    with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    runs = data["runs"]

    # Check invariants
    all_pv_legal = all(r["pv_legal"] for r in runs)
    print(f"All PVs legal: {all_pv_legal}")

    # Check move and score consistency between baseline and candidate
    paired_checks = {}
    for r in runs:
        key = (r["rep"], r["depth"], r["position_id"])
        if key not in paired_checks:
            paired_checks[key] = {}
        paired_checks[key][r["arm"]] = r

    mismatches = 0
    for key, arm_dict in paired_checks.items():
        base = arm_dict.get("baseline")
        cand = arm_dict.get("candidate")
        if base and cand:
            if (
                base["best_move"] != cand["best_move"]
                or base["score"] != cand["score"]
                or base["nodes"] != cand["nodes"]
            ):
                print(f"Mismatch at {key}: base={base['best_move']}/{base['score']}/{base['nodes']} vs cand={cand['best_move']}/{cand['score']}/{cand['nodes']}")
                mismatches += 1
    print(f"Paired move/score/node mismatches: {mismatches} (Expected: 0)")

    depths = sorted(list(set(r["depth"] for r in runs)))
    positions = sorted(list(set(r["position_id"] for r in runs)))

    summary_tables = {}

    for d in depths:
        print(f"\n=================== DEPTH {d} SUMMARY ===================")
        reps = sorted(list(set(r["rep"] for r in runs)))
        base_rep_times = []
        cand_rep_times = []
        base_rep_nodes = []
        cand_rep_nodes = []

        for rep in reps:
            b_runs = [r for r in runs if r["rep"] == rep and r["depth"] == d and r["arm"] == "baseline"]
            c_runs = [r for r in runs if r["rep"] == rep and r["depth"] == d and r["arm"] == "candidate"]
            base_rep_times.append(sum(r["elapsed_s"] for r in b_runs))
            cand_rep_times.append(sum(r["elapsed_s"] for r in c_runs))
            base_rep_nodes.append(sum(r["nodes"] for r in b_runs))
            cand_rep_nodes.append(sum(r["nodes"] for r in c_runs))

        base_time_med, base_time_iqr = calc_med_iqr(base_rep_times)
        cand_time_med, cand_time_iqr = calc_med_iqr(cand_rep_times)

        time_speedup_med = (base_time_med - cand_time_med) / base_time_med * 100

        total_nodes = int(base_rep_nodes[0])
        base_nps_med = total_nodes / base_time_med if base_time_med > 0 else 0
        cand_nps_med = total_nodes / cand_time_med if cand_time_med > 0 else 0
        nps_gain = (cand_nps_med - base_nps_med) / base_nps_med * 100

        print(f"Total Suite Time (Median): Baseline = {base_time_med:.3f}s (IQR: {base_time_iqr:.3f}s) | Candidate = {cand_time_med:.3f}s (IQR: {cand_time_iqr:.3f}s) | Speedup = {time_speedup_med:+.2f}%")
        print(f"Total Suite Nodes: {total_nodes}")
        print(f"Throughput (NPS): Baseline = {base_nps_med:.0f} | Candidate = {cand_nps_med:.0f} | Gain = {nps_gain:+.2f}%")

        pos_stats = []
        print("\nPer-Position Breakdown:")
        print(f"{'Position':<18} | {'Nodes':>6} | {'Base Med (s)':>12} | {'Cand Med (s)':>12} | {'Speedup (%)':>11} | {'Move':>6} | {'Score':>6}")
        print("-" * 85)
        for pid in positions:
            b_p = [r["elapsed_s"] for r in runs if r["depth"] == d and r["arm"] == "baseline" and r["position_id"] == pid]
            c_p = [r["elapsed_s"] for r in runs if r["depth"] == d and r["arm"] == "candidate" and r["position_id"] == pid]
            b_med, b_iqr = calc_med_iqr(b_p)
            c_med, c_iqr = calc_med_iqr(c_p)
            sp = (b_med - c_med) / b_med * 100 if b_med > 0 else 0.0
            r_sample = [r for r in runs if r["depth"] == d and r["position_id"] == pid][0]
            pos_stats.append({
                "position_id": pid,
                "nodes": r_sample["nodes"],
                "base_median": b_med,
                "base_iqr": b_iqr,
                "cand_median": c_med,
                "cand_iqr": c_iqr,
                "speedup_pct": sp,
                "best_move": r_sample["best_move"],
                "score": r_sample["score"],
            })
            print(f"{pid:<18} | {r_sample['nodes']:>6} | {b_med:>7.3f} (±{b_iqr:.3f}) | {c_med:>7.3f} (±{c_iqr:.3f}) | {sp:>+10.2f}% | {r_sample['best_move']:>6} | {r_sample['score']:>6}")

        summary_tables[f"depth_{d}"] = {
            "depth": d,
            "total_nodes": total_nodes,
            "baseline_median_s": base_time_med,
            "baseline_iqr_s": base_time_iqr,
            "candidate_median_s": cand_time_med,
            "candidate_iqr_s": cand_time_iqr,
            "suite_speedup_pct": time_speedup_med,
            "baseline_nps": base_nps_med,
            "candidate_nps": cand_nps_med,
            "nps_gain_pct": nps_gain,
            "positions": pos_stats,
        }

    # Add call count stats
    print("\nMeasuring call counts...")
    call_stats = measure_detailed_call_counts()
    summary_tables["call_counts"] = call_stats
    for depth_key, s in call_stats.items():
        print(f"{depth_key}: Eager = {s['eager_calls']}, Lazy = {s['lazy_calls']}, Avoided = {s['calls_avoided']} ({s['reduction_pct']:.1f}%)")

    os.makedirs(os.path.dirname(OUTPUT_SUMMARY), exist_ok=True)
    with open(OUTPUT_SUMMARY, "w", encoding="utf-8") as f:
        json.dump(summary_tables, f, indent=2)
    print(f"\nSaved statistical summary to {OUTPUT_SUMMARY}")


def run_post_profile():
    with open("benchmarks/positions.json", "r") as f:
        positions = json.load(f)

    pr = cProfile.Profile()
    pr.enable()

    for depth in [4, 5]:
        for p in positions:
            b = chess.Board(p["fen"])
            s = JanusSearch()
            s.search(b, max_depth=depth)

    pr.disable()

    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats("tottime")
    ps.print_stats(40)
    tottime_str = s.getvalue()

    s2 = io.StringIO()
    ps2 = pstats.Stats(pr, stream=s2).sort_stats("cumtime")
    ps2.print_stats(40)
    cumtime_str = s2.getvalue()

    os.makedirs(PROFILE_DIR, exist_ok=True)
    out_txt = os.path.join(PROFILE_DIR, "v029_candidate_profile.txt")
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write("================================================================================\n")
        f.write("PROJECT JANUS v0.29 — POST-OPTIMISATION CANDIDATE PROFILE\n")
        f.write("================================================================================\n\n")
        f.write("TOP 40 FUNCTIONS BY EXCLUSIVE TIME (tottime):\n")
        f.write("--------------------------------------------------------------------------------\n")
        f.write(tottime_str)
        f.write("\n\n")
        f.write("================================================================================\n")
        f.write("TOP 40 FUNCTIONS BY CUMULATIVE TIME (cumtime):\n")
        f.write("--------------------------------------------------------------------------------\n")
        f.write(cumtime_str)

    print(f"\nSaved v0.29 candidate profile to {out_txt}")


if __name__ == "__main__":
    analyze_benchmarks()
    run_post_profile()
