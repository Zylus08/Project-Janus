import csv

with open("analysis/v0.43/match_replication/match_moves.csv", "r", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        t = float(row["actual_time_ms"])
        if t > 5000:
            print(f"Cand={row['candidate']:3s} Game={row['game']:3s} Pair={row['pair']:3s} Ply={row['ply']:3s} Time={t:10.1f}ms Janus={row['is_janus']} Move={row['move']}")

