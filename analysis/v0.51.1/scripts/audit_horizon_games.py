import chess
import chess.pgn
import json
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PGN_PATH = ROOT / "analysis" / "v0.51" / "pgn" / "n2_vs_k0_match.pgn"
OUT_CSV = ROOT / "analysis" / "v0.51.1" / "raw" / "termination_audit.csv"

pgn_file = open(PGN_PATH, "r", encoding="utf-8")

all_audit_records = []
horizon_records = []
game_idx = 0

while True:
    game = chess.pgn.read_game(pgn_file)
    if game is None:
        break
    game_idx += 1
    term = game.headers.get("Termination", "")
    fen = game.headers.get("FEN", chess.STARTING_FEN)
    result = game.headers.get("Result", "*")
    white = game.headers.get("White", "")
    black = game.headers.get("Black", "")
    
    board = chess.Board(fen)
    pawn_or_capture_plies = []
    ply = 0
    
    for m in game.mainline_moves():
        is_pawn = (board.piece_at(m.from_square).piece_type == chess.PAWN)
        is_cap = board.is_capture(m)
        if is_pawn or is_cap:
            pawn_or_capture_plies.append(ply)
        board.push(m)
        ply += 1
        
    last_reset = pawn_or_capture_plies[-1] if pawn_or_capture_plies else 0
    final_clock = board.halfmove_clock
    is_mate = board.is_checkmate()
    is_stale = board.is_stalemate()
    can_50 = board.can_claim_fifty_moves()
    is_75 = board.is_seventyfive_moves()
    can_rep3 = board.can_claim_threefold_repetition()
    is_rep5 = board.is_fivefold_repetition()
    is_ins = board.is_insufficient_material()
    
    # Classification
    # A. Valid automatic FIDE draw
    # B. Valid claimable draw, with evidence of a claim or controller policy
    # C. Explicit artificial horizon adjudication permitted by the frozen match protocol
    # D. Invalid or unsupported adjudication
    if is_mate:
        fide_status = "VALID_CHECKMATE"
    elif is_rep5 or is_75 or is_stale or is_ins:
        fide_status = "A_VALID_AUTOMATIC_FIDE_DRAW"
    elif can_50 or can_rep3:
        fide_status = "B_VALID_CLAIMABLE_DRAW"
    elif "horizon" in term and ply >= 150:
        fide_status = "C_ARTIFICIAL_HORIZON_PROTOCOL_ADJUDICATION"
    else:
        fide_status = "D_INVALID_OR_UNSUPPORTED"
        
    rec = {
        "game_id": game_idx,
        "pair_id": (game_idx - 1) // 2 + 1,
        "white_engine": white,
        "black_engine": black,
        "result": result,
        "plies": ply,
        "reported_termination": term,
        "final_halfmove_clock": final_clock,
        "last_reset_ply": last_reset,
        "plies_since_reset": ply - last_reset,
        "is_checkmate": is_mate,
        "is_stalemate": is_stale,
        "is_fivefold": is_rep5,
        "is_seventyfive": is_75,
        "can_claim_fifty": can_50,
        "can_claim_threefold": can_rep3,
        "is_insufficient_material": is_ins,
        "fide_audit_classification": fide_status,
        "final_fen": board.fen()
    }
    all_audit_records.append(rec)
    if "horizon" in term:
        horizon_records.append(rec)

pgn_file.close()

# Save termination audit CSV
with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(all_audit_records[0].keys()))
    writer.writeheader()
    writer.writerows(all_audit_records)

print(f"Total games audited: {len(all_audit_records)}")
print(f"Total horizon games: {len(horizon_records)}")
for h in horizon_records:
    print(f"Game {h['game_id']} (Pair {h['pair_id']}): Plies={h['plies']}, HalfmoveClock={h['final_halfmove_clock']}, CanClaim50={h['can_claim_fifty']}, Is75={h['is_seventyfive']}, CanClaim3fold={h['can_claim_threefold']}, Class={h['fide_audit_classification']}")

print("\n--- Detailed Material Analysis of the 9 Horizon Games ---")
piece_vals = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330, chess.ROOK: 500, chess.QUEEN: 900}

for h in horizon_records:
    b = chess.Board(h['final_fen'])
    w_mat = sum(piece_vals.get(p.piece_type, 0) for p in b.piece_map().values() if p.color == chess.WHITE)
    b_mat = sum(piece_vals.get(p.piece_type, 0) for p in b.piece_map().values() if p.color == chess.BLACK)
    n2_is_white = "Native" in h['white_engine']
    n2_mat = w_mat if n2_is_white else b_mat
    k0_mat = b_mat if n2_is_white else w_mat
    mat_diff = n2_mat - k0_mat
    print(f"Game {h['game_id']:3d} (Pair {h['pair_id']:2d}): N2={'White' if n2_is_white else 'Black'} | N2 Mat={n2_mat:4d} cp, K0 Mat={k0_mat:4d} cp | Diff={mat_diff:+5d} cp | Turn={'White' if b.turn == chess.WHITE else 'Black'}")
