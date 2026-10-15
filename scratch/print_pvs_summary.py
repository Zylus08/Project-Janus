import json

data = json.load(open('analysis/v0.15/pvs_benchmarks.json'))
for depth in [3, 4, 5]:
    print(f"\n=== DEPTH {depth} PER-POSITION NODES & TELEMETRY ===")
    dis = data['raw_runs'][str(depth)]['pvs_disabled'][0]['results']
    ena = data['raw_runs'][str(depth)]['pvs_enabled'][0]['results']
    for d, e in zip(dis, ena):
        diff = e['nodes'] - d['nodes']
        pct = (diff / d['nodes'] * 100) if d['nodes'] > 0 else 0
        scout = e.get('scout_searches', 0)
        fh = e.get('scout_fail_highs', 0)
        res = e.get('researches', 0)
        print(f"{d['id']:<18} | Dis: {d['nodes']:<7} | Ena: {e['nodes']:<7} | Delta: {diff:<7} ({pct:+.2f}%) | Scout: {scout:<5} FH: {fh:<3} Re: {res:<3} | Best: {e['best_move_uci']} Score: {e['score_from_side_to_move']}")
