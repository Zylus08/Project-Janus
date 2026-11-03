import json

with open("analysis/v0.44/diagnostic_positions.json", "r", encoding="utf-8") as f:
    corpus = json.load(f)

print(f"Total positions: {len(corpus)}")
for x in corpus:
    if x["pair"] in [3, 54, 76, 99, 100]:
        print(f"Pair {x['pair']:3d} ({x['color']:5s}) ply {x['ply']:2d}: {x['opening']:30s} | K0={x['k0_move']} ({x['k0_result']}) vs RFP={x['rfp_move']} ({x['rfp_result']})")

