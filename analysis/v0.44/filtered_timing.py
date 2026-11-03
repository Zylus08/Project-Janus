import csv
import statistics

k0_filtered = []
rfp_filtered = []

with open("analysis/v0.43/match_replication/match_moves.csv", "r", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        if row["is_janus"] == "True":
            t = float(row["actual_time_ms"])
            if t < 2000:  # exclude host pause anomalies
                if row["candidate"] == "k0":
                    k0_filtered.append(t)
                elif row["candidate"] == "rfp":
                    rfp_filtered.append(t)

print(f"Filtered K0 moves: {len(k0_filtered)}, Mean: {statistics.mean(k0_filtered):.2f} ms, Median: {statistics.median(k0_filtered):.2f} ms")
print(f"Filtered RFP moves: {len(rfp_filtered)}, Mean: {statistics.mean(rfp_filtered):.2f} ms, Median: {statistics.median(rfp_filtered):.2f} ms")

