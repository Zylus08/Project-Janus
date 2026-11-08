import json

d61 = json.load(open('analysis/v0.61/raw/v061_v2_vs_c1_match_raw.json'))
ops61 = {op['pair_id']: 'ECO_' + op['eco'][0] for op in json.load(open('analysis/v0.56/corpus/independent_openings_v056.json'))}

cat_stats61 = {}
for g in d61.get('games', []):
    pid = g['pair_id']
    cat = ops61.get(pid, 'UNKNOWN')
    if cat not in cat_stats61:
        cat_stats61[cat] = {'games': 0, 'wins': 0, 'draws': 0, 'losses': 0, 'points': 0.0}
    cat_stats61[cat]['games'] += 1
    cand_white = 'Neural' in g.get('white', '')
    res = g.get('result', '')
    if res == '1-0':
        pts = 1.0 if cand_white else 0.0
    elif res == '0-1':
        pts = 0.0 if cand_white else 1.0
    else:
        pts = 0.5
    cat_stats61[cat]['points'] += pts
    if pts == 1.0: cat_stats61[cat]['wins'] += 1
    elif pts == 0.5: cat_stats61[cat]['draws'] += 1
    else: cat_stats61[cat]['losses'] += 1

d62 = json.load(open('analysis/v0.62/raw/v062_confirmatory_match_raw.json'))
cat_stats62 = d62['category_performance']

print("=== Category Comparison ===")
print("Category | v0.61 (Score, %) | v0.62 (Score, %) | Diff (Points, %)")
for cat in sorted(cat_stats61.keys()):
    s61 = cat_stats61[cat]
    s62 = cat_stats62.get(cat, {})
    p61 = s61['points']
    g61 = s61['games']
    pct61 = (p61 / g61) * 100.0
    p62 = s62.get('points', 0.0)
    g62 = s62.get('games', 0)
    pct62 = (p62 / g62) * 100.0 if g62 else 0.0
    print(f"{cat:8s} | {p61:4.1f}/{g61:2d} ({pct61:5.1f}%) | {p62:4.1f}/{g62:2d} ({pct62:5.1f}%) | {p62 - p61:+5.1f} pts ({pct62 - pct61:+5.1f}%)")
