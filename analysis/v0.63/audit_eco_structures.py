import json
import chess
from pathlib import Path
from characterize_structures import compute_structural_descriptors

ROOT = Path(__file__).resolve().parents[2]
d61 = json.load(open(ROOT / 'analysis/v0.56/corpus/independent_openings_v056.json'))
d62 = json.load(open(ROOT / 'analysis/v0.62/corpus/independent_openings_v062.json'))

def get_boards_by_cat(corpus, cat_prefix, eco_key):
    boards = []
    for op in corpus:
        val = op.get(eco_key, '')
        if cat_prefix in val:
            b = chess.Board()
            for m in op.get('uci_sequence', []):
                b.push(chess.Move.from_uci(m))
            boards.append(b)
    return boards

print("=" * 80)
print("STRUCTURAL COMPARISON BY CATEGORY (v0.61 vs v0.62)")
print("=" * 80)

metrics_list = ['blocked_pawns', 'locked_headon_pairs', 'open_files', 'semi_open_files', 'central_tension', 'pawn_breaks', 'legal_mobility']

for cat in ['A', 'B', 'C', 'D', 'E']:
    b61 = get_boards_by_cat(d61, cat, 'eco')
    b62 = get_boards_by_cat(d62, f'ECO_{cat}', 'category')
    m61 = [compute_structural_descriptors(b) for b in b61]
    m62 = [compute_structural_descriptors(b) for b in b62]

    print(f"\n--- ECO {cat} (v0.61: {len(b61)} openings, v0.62: {len(b62)} openings) ---")
    for k in metrics_list:
        v61 = sum(m[k] for m in m61) / len(m61) if m61 else 0.0
        v62 = sum(m[k] for m in m62) / len(m62) if m62 else 0.0
        print(f"  {k:22s} | v0.61: {v61:6.3f} | v0.62: {v62:6.3f} | Delta: {v62 - v61:+6.3f}")
