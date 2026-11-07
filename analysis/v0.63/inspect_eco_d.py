import json
import chess

d61 = json.load(open('analysis/v0.56/corpus/independent_openings_v056.json'))
d62 = json.load(open('analysis/v0.62/corpus/independent_openings_v062.json'))

print("=== v0.61 ECO_D Openings (14 pairs) ===")
for op in d61:
    eco = op.get('eco', '')
    if eco.startswith('D'):
        print(f"[{eco}] {op['name']} (depth {op.get('ply_depth', 0)}): {op.get('san_sequence', '')}")

print("\n=== v0.62 ECO_D Openings (15 pairs) ===")
for op in d62:
    eco = op.get('category', op.get('eco_category', ''))
    name = op.get('name', '')
    if 'ECO_D' in eco or 'Closed' in name or 'Gambit' in name or 'Slav' in name:
        moves = op.get('uci_sequence', [])
        b = chess.Board()
        san_moves = []
        for m in moves:
            san_moves.append(b.san(chess.Move.from_uci(m)))
            b.push(chess.Move.from_uci(m))
        print(f"[{eco}] {name} (depth {len(moves)}): {' '.join(san_moves)}")
