import json
from pathlib import Path

raw_file = Path("E:/ChessXML/project-janus-phase1/analysis/phase1/p1.7/raw/thread_forensics_raw.json")
with open(raw_file, "r") as f:
    d = json.load(f)

for tb in ["time_100ms", "time_250ms", "time_500ms", "time_1000ms"]:
    print(f"\n==================== {tb.upper()} ====================")
    t4 = d[tb]["threads_4"]
    print(f"Overall Aggregates: Probes={t4['aggregate_probes']:,}, Stores={t4['aggregate_stores']:,}, "
          f"Shallower Overwrites={t4['aggregate_shallower_overwrites']:,}, Lock Spins={t4['aggregate_lock_spins']:,}")
    print(f"{'Position':<20} | {'Final Move':<10} | {'Depth':<6} | {'Worker Depths [0..3]':<24} | {'Worker Moves [0..3]'}")
    print("-" * 90)
    for p in t4["positions"]:
        w_depths = [w["depth"] for w in p["workers"]]
        w_moves = [w["bestmove"] for w in p["workers"]]
        print(f"{p['position_name']:<20} | {str(p['final_bestmove']):<10} | {p['final_depth']:<6} | {str(w_depths):<24} | {w_moves}")

