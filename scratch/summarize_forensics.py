import json
from collections import Counter

with open("analysis/v0.8_loss_analysis.json") as f:
    loss_data = json.load(f)

with open("analysis/v0.8_draw_analysis.json") as f:
    draw_data = json.load(f)

with open("analysis/v0.8_win_analysis.json") as f:
    win_data = json.load(f)

crit = loss_data["critical_moments"]
cats = Counter(m["category"] for m in crit)
print(f"Loss Failure Categories (Total: {len(crit)}):")
for k, v in cats.most_common():
    pct = v / len(crit) * 100
    print(f"  {k}: {v} ({pct:.1f}%)")

sorted_moments = sorted(crit, key=lambda x: x.get("deep_drop_cp", 0), reverse=True)
print("\nTop 10 Critical Deterioration Moments:")
for m in sorted_moments[:10]:
    g = m["game_number"]
    p = m["ply"]
    c = m["janus_color"]
    op = m["opening_id"]
    jm = m["janus_move"]
    sfb = m["sf_best_move"]
    d = m["deep_drop_cp"]
    cat = m["category"]
    print(f"  Game {g} (ply {p}, {c}, {op}): played {jm}, SF best {sfb}, drop: {d} cp | {cat}")

draw_cats = Counter(d["classification"] for d in draw_data["draws"])
print(f"\nDraw Classifications (Total: {len(draw_data['draws'])}):")
for k, v in draw_cats.most_common():
    print(f"  {k}: {v}")

print("\nGame 32 Analysis:")
for p in win_data["plies"]:
    sc = p["score_after"]
    ply = p["ply"]
    side = p["side"]
    mv = p["move"]
    bm = p["best_move"]
    cp_val = sc["cp"]
    if sc["type"] == "cp" and abs(cp_val) >= 200:
        print(f"  Ply {ply} ({side}): {mv}, score after: {cp_val} cp (SF best before: {bm})")
    elif sc["type"] == "mate":
        print(f"  Ply {ply} ({side}): {mv}, score after: mate in {sc['mate_in']}")
