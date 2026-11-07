"""Project Janus v0.63 - Phase 1 Structural Chess Position Characterization.

Implements reproducible position-level structural descriptors and audits distributions across:
1. v0.61 opening positions (terminal EPDs)
2. v0.62 opening positions (terminal EPDs)
3. NNUE-V2 training corpus (80,000 positions sample: 5,000 positions)
4. NNUE-V2 test corpus (10,000 positions sample: 5,000 positions)
5. v0.61 game middlegames (plies 16, 24, 32 from 200 games)
6. v0.62 game middlegames (plies 16, 24, 32 from 200 games)
"""

import json
import math
import random
from pathlib import Path
from typing import Dict, List, Any
import chess
import chess.pgn

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "analysis" / "v0.63"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def compute_structural_descriptors(board: chess.Board) -> Dict[str, float]:
    white_pawns = board.pieces(chess.PAWN, chess.WHITE)
    black_pawns = board.pieces(chess.PAWN, chess.BLACK)
    occupied = board.occupied

    # 1. Blocked pawns
    blocked_count = 0
    for sq in white_pawns:
        if sq + 8 < 64 and (occupied & (1 << (sq + 8))):
            blocked_count += 1
    for sq in black_pawns:
        if sq - 8 >= 0 and (occupied & (1 << (sq - 8))):
            blocked_count += 1

    # 2. Locked opposing pawn chains (head-on pawn collision: white pawn on sq, black pawn on sq+8)
    locked_headon_pairs = 0
    for sq in white_pawns:
        if sq + 8 < 64 and (black_pawns & (1 << (sq + 8))):
            locked_headon_pairs += 1

    # 3. Open and semi-open files
    file_pawn_counts_w = [0] * 8
    file_pawn_counts_b = [0] * 8
    for sq in white_pawns:
        file_pawn_counts_w[chess.square_file(sq)] += 1
    for sq in black_pawns:
        file_pawn_counts_b[chess.square_file(sq)] += 1

    open_files = 0
    semi_open_files = 0
    for f in range(8):
        cw = file_pawn_counts_w[f]
        cb = file_pawn_counts_b[f]
        if cw == 0 and cb == 0:
            open_files += 1
        elif (cw == 0 and cb > 0) or (cw > 0 and cb == 0):
            semi_open_files += 1

    # 4. Isolated pawns
    isolated_pawns = 0
    for sq in white_pawns:
        f = chess.square_file(sq)
        left = file_pawn_counts_w[f - 1] if f > 0 else 0
        right = file_pawn_counts_w[f + 1] if f < 7 else 0
        if left == 0 and right == 0:
            isolated_pawns += 1
    for sq in black_pawns:
        f = chess.square_file(sq)
        left = file_pawn_counts_b[f - 1] if f > 0 else 0
        right = file_pawn_counts_b[f + 1] if f < 7 else 0
        if left == 0 and right == 0:
            isolated_pawns += 1

    # 5. Doubled pawns
    doubled_pawns = 0
    for f in range(8):
        if file_pawn_counts_w[f] > 1:
            doubled_pawns += (file_pawn_counts_w[f] - 1)
        if file_pawn_counts_b[f] > 1:
            doubled_pawns += (file_pawn_counts_b[f] - 1)

    # 6. Passed pawns
    passed_pawns = 0
    for sq in white_pawns:
        f = chess.square_file(sq)
        r = chess.square_rank(sq)
        # Check enemy pawns on f-1, f, f+1 on ranks r+1..7
        is_passed = True
        for adj_f in (f - 1, f, f + 1):
            if 0 <= adj_f <= 7:
                for adj_r in range(r + 1, 8):
                    if black_pawns & (1 << (adj_r * 8 + adj_f)):
                        is_passed = False
                        break
        if is_passed:
            passed_pawns += 1

    for sq in black_pawns:
        f = chess.square_file(sq)
        r = chess.square_rank(sq)
        is_passed = True
        for adj_f in (f - 1, f, f + 1):
            if 0 <= adj_f <= 7:
                for adj_r in range(0, r):
                    if white_pawns & (1 << (adj_r * 8 + adj_f)):
                        is_passed = False
                        break
        if is_passed:
            passed_pawns += 1

    # 7. Central tension: pawns on c, d, e, f attacking enemy pawns
    central_tension = 0
    central_files = (2, 3, 4, 5) # c, d, e, f
    for sq in white_pawns:
        if chess.square_file(sq) in central_files:
            # White pawn attacks sq+7 (if file > 0) and sq+9 (if file < 7)
            f = chess.square_file(sq)
            if f > 0 and sq + 7 < 64 and (black_pawns & (1 << (sq + 7))):
                central_tension += 1
            if f < 7 and sq + 9 < 64 and (black_pawns & (1 << (sq + 9))):
                central_tension += 1

    # 8. Pawn mobility and pawn breaks
    # Count legal pawn moves for current side to move
    curr_turn = board.turn
    legal_pawn_moves = 0
    pawn_breaks = 0
    for m in board.legal_moves:
        p = board.piece_at(m.from_square)
        if p and p.piece_type == chess.PAWN:
            legal_pawn_moves += 1
            # Check if this pawn move lands on a capture or attacks an enemy pawn
            to_sq = m.to_square
            if m.to_square in black_pawns if curr_turn == chess.WHITE else m.to_square in white_pawns:
                pawn_breaks += 1
            else:
                # Does the new square attack an opposing pawn?
                enemy_pawns = black_pawns if curr_turn == chess.WHITE else white_pawns
                tf = chess.square_file(to_sq)
                tr = chess.square_rank(to_sq)
                if curr_turn == chess.WHITE:
                    if tf > 0 and tr + 1 < 8 and (enemy_pawns & (1 << ((tr + 1) * 8 + (tf - 1)))):
                        pawn_breaks += 1
                    elif tf < 7 and tr + 1 < 8 and (enemy_pawns & (1 << ((tr + 1) * 8 + (tf + 1)))):
                        pawn_breaks += 1
                else:
                    if tf > 0 and tr - 1 >= 0 and (enemy_pawns & (1 << ((tr - 1) * 8 + (tf - 1)))):
                        pawn_breaks += 1
                    elif tf < 7 and tr - 1 >= 0 and (enemy_pawns & (1 << ((tr - 1) * 8 + (tf + 1)))):
                        pawn_breaks += 1

    # Legal mobility
    legal_mobility = board.legal_moves.count()

    # 9. Material phase
    # Knight=1, Bishop=1, Rook=2, Queen=4. Max = 24
    phase = (
        len(board.pieces(chess.KNIGHT, chess.WHITE)) * 1 +
        len(board.pieces(chess.KNIGHT, chess.BLACK)) * 1 +
        len(board.pieces(chess.BISHOP, chess.WHITE)) * 1 +
        len(board.pieces(chess.BISHOP, chess.BLACK)) * 1 +
        len(board.pieces(chess.ROOK, chess.WHITE)) * 2 +
        len(board.pieces(chess.ROOK, chess.BLACK)) * 2 +
        len(board.pieces(chess.QUEEN, chess.WHITE)) * 4 +
        len(board.pieces(chess.QUEEN, chess.BLACK)) * 4
    )

    # 10. King safety: pawn shelter in front of king
    def get_shelter(color, ksq):
        kf = chess.square_file(ksq)
        kr = chess.square_rank(ksq)
        pawns = white_pawns if color == chess.WHITE else black_pawns
        shelter = 0
        for df in (-1, 0, 1):
            f = kf + df
            if 0 <= f <= 7:
                for dr in (1, 2) if color == chess.WHITE else (-1, -2):
                    r = kr + dr
                    if 0 <= r <= 7 and (pawns & (1 << (r * 8 + f))):
                        shelter += 1
        return shelter

    w_ksq = board.king(chess.WHITE)
    b_ksq = board.king(chess.BLACK)
    w_shelter = get_shelter(chess.WHITE, w_ksq) if w_ksq is not None else 0
    b_shelter = get_shelter(chess.BLACK, b_ksq) if b_ksq is not None else 0

    return {
        "blocked_pawns": blocked_count,
        "locked_headon_pairs": locked_headon_pairs,
        "open_files": open_files,
        "semi_open_files": semi_open_files,
        "isolated_pawns": isolated_pawns,
        "doubled_pawns": doubled_pawns,
        "passed_pawns": passed_pawns,
        "central_tension": central_tension,
        "legal_pawn_moves": legal_pawn_moves,
        "pawn_breaks": pawn_breaks,
        "legal_mobility": legal_mobility,
        "material_phase": phase,
        "avg_king_shelter": 0.5 * (w_shelter + b_shelter),
    }


def summarize_dataset(name: str, boards: List[chess.Board]) -> Dict[str, Any]:
    if not boards:
        return {}
    metrics = [compute_structural_descriptors(b) for b in boards]
    keys = metrics[0].keys()
    summary = {}
    for k in keys:
        vals = [m[k] for m in metrics]
        mean_v = sum(vals) / len(vals)
        std_v = math.sqrt(sum((v - mean_v) ** 2 for v in vals) / (len(vals) - 1)) if len(vals) > 1 else 0.0
        summary[k] = {
            "mean": round(mean_v, 3),
            "std": round(std_v, 3),
            "min": round(min(vals), 3),
            "max": round(max(vals), 3),
        }
    return {"name": name, "count": len(boards), "metrics": summary}


def extract_game_positions(pgn_path: Path, sample_plies=(16, 24, 32), max_games=200) -> List[chess.Board]:
    boards = []
    if not pgn_path.exists():
        return boards
    with open(pgn_path, "r", encoding="utf-8") as f:
        game_idx = 0
        while game_idx < max_games:
            game = chess.pgn.read_game(f)
            if game is None:
                break
            game_idx += 1
            board = game.board()
            ply = 0
            for move in game.mainline_moves():
                board.push(move)
                ply += 1
                if ply in sample_plies:
                    boards.append(board.copy())
    return boards


def main():
    print("=" * 80)
    print("PROJECT JANUS v0.63 — PHASE 1 STRUCTURAL DISTRIBUTION AUDIT")
    print("=" * 80)

    # 1. v0.61 Openings
    v61_ops_path = ROOT / "analysis" / "v0.56" / "corpus" / "independent_openings_v056.json"
    with open(v61_ops_path, "r", encoding="utf-8") as f:
        v61_ops = json.load(f)
    boards_v61_openings = []
    for op in v61_ops:
        b = chess.Board()
        for m in op.get("uci_sequence", []):
            b.push(chess.Move.from_uci(m))
        boards_v61_openings.append(b)

    # 2. v0.62 Openings
    v62_ops_path = ROOT / "analysis" / "v0.62" / "corpus" / "independent_openings_v062.json"
    with open(v62_ops_path, "r", encoding="utf-8") as f:
        v62_ops = json.load(f)
    boards_v62_openings = []
    for op in v62_ops:
        b = chess.Board()
        for m in op.get("uci_sequence", []):
            b.push(chess.Move.from_uci(m))
        boards_v62_openings.append(b)

    # 3. NNUE-V2 Training Sample (sample 5,000 from 80,000)
    train_path = ROOT / "analysis" / "v0.61" / "dataset" / "value_v2_train.json"
    boards_train = []
    if train_path.exists():
        with open(train_path, "r", encoding="utf-8") as f:
            train_data = json.load(f)
        random.seed(42)
        sample_train = random.sample(train_data, min(5000, len(train_data)))
        for item in sample_train:
            fen = item.get("fen", "")
            if fen:
                try:
                    boards_train.append(chess.Board(fen))
                except Exception:
                    pass

    # 4. NNUE-V2 Test Sample (sample 5,000 from 10,000)
    test_path = ROOT / "analysis" / "v0.61" / "dataset" / "value_v2_test.json"
    boards_test = []
    if test_path.exists():
        with open(test_path, "r", encoding="utf-8") as f:
            test_data = json.load(f)
        random.seed(42)
        sample_test = random.sample(test_data, min(5000, len(test_data)))
        for item in sample_test:
            fen = item.get("fen", "")
            if fen:
                try:
                    boards_test.append(chess.Board(fen))
                except Exception:
                    pass

    # 5. v0.61 Game Middlegames
    pgn_v61 = ROOT / "analysis" / "v0.61" / "pgn" / "v061_v2_vs_c1_match.pgn"
    boards_v61_games = extract_game_positions(pgn_v61, sample_plies=(16, 24, 32))

    # 6. v0.62 Game Middlegames
    pgn_v62 = ROOT / "analysis" / "v0.62" / "pgn" / "v062_confirmatory_match.pgn"
    boards_v62_games = extract_game_positions(pgn_v62, sample_plies=(16, 24, 32))

    print(f"Loaded {len(boards_v61_openings)} v0.61 opening root positions.")
    print(f"Loaded {len(boards_v62_openings)} v0.62 opening root positions.")
    print(f"Loaded {len(boards_train)} NNUE-V2 training positions sample.")
    print(f"Loaded {len(boards_test)} NNUE-V2 test positions sample.")
    print(f"Loaded {len(boards_v61_games)} v0.61 game middlegame positions.")
    print(f"Loaded {len(boards_v62_games)} v0.62 game middlegame positions.")

    summary_v61_openings = summarize_dataset("v0.61 Openings", boards_v61_openings)
    summary_v62_openings = summarize_dataset("v0.62 Openings", boards_v62_openings)
    summary_train = summarize_dataset("NNUE-V2 Train (Sample)", boards_train)
    summary_test = summarize_dataset("NNUE-V2 Test (Sample)", boards_test)
    summary_v61_games = summarize_dataset("v0.61 Games (Plies 16, 24, 32)", boards_v61_games)
    summary_v62_games = summarize_dataset("v0.62 Games (Plies 16, 24, 32)", boards_v62_games)

    all_summaries = {
        "v61_openings": summary_v61_openings,
        "v62_openings": summary_v62_openings,
        "nnue_train": summary_train,
        "nnue_test": summary_test,
        "v61_games": summary_v61_games,
        "v62_games": summary_v62_games,
    }

    out_file = OUT_DIR / "structural_distributions.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_summaries, f, indent=2)

    print("\n--- Key Structural Metrics Comparison (Openings) ---")
    keys_to_print = ["blocked_pawns", "locked_headon_pairs", "open_files", "semi_open_files", "central_tension", "pawn_breaks", "legal_mobility"]
    print(f"{'Metric':22s} | {'v0.61 Openings':18s} | {'v0.62 Openings':18s} | {'NNUE Train':18s}")
    for k in keys_to_print:
        m61 = summary_v61_openings["metrics"][k]["mean"]
        m62 = summary_v62_openings["metrics"][k]["mean"]
        mtr = summary_train["metrics"][k]["mean"]
        print(f"{k:22s} | {m61:18.3f} | {m62:18.3f} | {mtr:18.3f}")

    print("\n--- Key Structural Metrics Comparison (Played Games Plies 16, 24, 32) ---")
    print(f"{'Metric':22s} | {'v0.61 Games':18s} | {'v0.62 Games':18s} | {'NNUE Train':18s}")
    for k in keys_to_print:
        m61 = summary_v61_games["metrics"][k]["mean"]
        m62 = summary_v62_games["metrics"][k]["mean"]
        mtr = summary_train["metrics"][k]["mean"]
        print(f"{k:22s} | {m61:18.3f} | {m62:18.3f} | {mtr:18.3f}")

    print(f"\nSaved structural distributions to {out_file}")


if __name__ == "__main__":
    main()
