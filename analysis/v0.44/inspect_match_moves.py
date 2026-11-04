import csv

with open("analysis/v0.43/match_replication/match_moves.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row["pair"] in ["1", "2", "3", "54"] and row["is_janus"] == "True" and int(row["ply"]) <= 8:
            print(f"Pair {row['pair']:2s} ({row['candidate']:3s}, {row['color']:5s}) ply {row['ply']:2s}: mv={row['move']:5s} depth={row['depth']:2s} nodes={row['nodes']:6s} time={row['actual_time_ms']:6s} alloc={row['target_alloc_ms']:6s}")

