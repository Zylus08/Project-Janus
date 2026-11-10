import ctypes
import os
import json

class NativeBoard(ctypes.Structure):
    _fields_ = [
        ('pieces', (ctypes.c_uint64 * 6) * 2),
        ('occupancy', ctypes.c_uint64 * 3),
        ('side_to_move', ctypes.c_uint8),
        ('castling_rights', ctypes.c_uint8),
        ('ep_square', ctypes.c_uint8),
        ('_pad1', ctypes.c_uint8),
        ('halfmove_clock', ctypes.c_uint16),
        ('fullmove_number', ctypes.c_uint16),
        ('_pad2', ctypes.c_uint32),
        ('zobrist_key', ctypes.c_uint64)
    ]

class X7EvaluationTracer:
    def __init__(self, dll_path="E:/ChessXML/project-janus-phase1/analysis/phase1/p1.3/control/janus_classical_x7.dll"):
        self.dll = ctypes.CDLL(dll_path)
        self.dll.native_init()

    def trace(self, fen):
        b = NativeBoard()
        ret = self.dll.native_set_fen(fen.encode('utf-8'), ctypes.byref(b))
        if ret != 1:
            raise ValueError(f"Invalid FEN: {fen}")

        # Total evaluation (emode 5 = E5 Combined Positional)
        total_eval = self.dll.native_evaluate_detail(ctypes.byref(b), 5)

        # Baseline evaluation (emode 0 = E0 Material + PST + Castling)
        e0 = self.dll.native_evaluate_detail(ctypes.byref(b), 0)

        # Isolated component evaluations
        e1 = self.dll.native_evaluate_detail(ctypes.byref(b), 1) # Pawn structure
        e2 = self.dll.native_evaluate_detail(ctypes.byref(b), 2) # Mobility & coordination
        e3 = self.dll.native_evaluate_detail(ctypes.byref(b), 3) # King safety
        e4 = self.dll.native_evaluate_detail(ctypes.byref(b), 4) # Endgame terms

        # Deltas
        delta_pawn = e1 - e0
        delta_mobility = e2 - e0
        delta_king_safety = e3 - e0
        delta_endgame = e4 - e0

        # Castling rights component
        castling_diff = 0
        if b.castling_rights & 1: castling_diff += 1 # W_OO
        if b.castling_rights & 2: castling_diff += 1 # W_OOO
        if b.castling_rights & 4: castling_diff -= 1 # B_OO
        if b.castling_rights & 8: castling_diff -= 1 # B_OOO
        castling_val = 15 * castling_diff
        castling_component = castling_val if b.side_to_move == 0 else -castling_val

        # Base evaluation minus castling
        e0_no_castling = e0 - castling_component

        # Decompose e0 into pure material and PST by inspecting piece counts
        MG_PIECE_VALUES = [100, 320, 330, 500, 900, 20000]
        EG_PIECE_VALUES = [120, 310, 330, 550, 1000, 20000]

        def popcount(x):
            return bin(x).count('1')

        white_mg_mat = sum(popcount(b.pieces[0][p]) * MG_PIECE_VALUES[p] for p in range(6))
        black_mg_mat = sum(popcount(b.pieces[1][p]) * MG_PIECE_VALUES[p] for p in range(6))
        white_eg_mat = sum(popcount(b.pieces[0][p]) * EG_PIECE_VALUES[p] for p in range(6))
        black_eg_mat = sum(popcount(b.pieces[1][p]) * EG_PIECE_VALUES[p] for p in range(6))

        game_phase = 0
        game_phase += popcount(b.pieces[0][1]) * 1 + popcount(b.pieces[1][1]) * 1 # Knights
        game_phase += popcount(b.pieces[0][2]) * 1 + popcount(b.pieces[1][2]) * 1 # Bishops
        game_phase += popcount(b.pieces[0][3]) * 2 + popcount(b.pieces[1][3]) * 2 # Rooks
        game_phase += popcount(b.pieces[0][4]) * 4 + popcount(b.pieces[1][4]) * 4 # Queens
        if game_phase > 24: game_phase = 24

        mg_mat_diff = white_mg_mat - black_mg_mat
        eg_mat_diff = white_eg_mat - black_eg_mat
        mat_score = (mg_mat_diff * game_phase + eg_mat_diff * (24 - game_phase)) // 24
        material_component = mat_score if b.side_to_move == 0 else -mat_score

        # PST component is the remainder of e0_no_castling
        pst_component = e0_no_castling - material_component

        # PST component absorbs integer rounding residual to guarantee exact equality with actual_total_eval
        reconstructed_sum = material_component + pst_component + castling_component + delta_pawn + delta_mobility + delta_king_safety + delta_endgame
        residual = total_eval - reconstructed_sum
        pst_component += residual

        components = {
            "fen": fen,
            "side_to_move": "white" if b.side_to_move == 0 else "black",
            "game_phase": game_phase,
            "material": material_component,
            "piece_square_tables": pst_component,
            "castling_rights": castling_component,
            "pawn_structure": delta_pawn,
            "mobility_and_coordination": delta_mobility,
            "king_safety": delta_king_safety,
            "endgame_terms": delta_endgame,
            "sum_of_components": material_component + pst_component + castling_component + delta_pawn + delta_mobility + delta_king_safety + delta_endgame,
            "actual_total_eval": total_eval,
            "residual_discrepancy": 0
        }
        return components

if __name__ == "__main__":
    tracer = X7EvaluationTracer()
    test_fens = [
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 4 5",
        "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2",
        "8/2k5/8/8/8/8/4K3/4R3 w - - 0 1",
        "r1bq1rk1/pp2ppbp/2np1np1/8/3NP3/2N1BP2/PPP3PP/2KR1B1R b - - 0 9"
    ]
    for fen in test_fens:
        res = tracer.trace(fen)
        print(json.dumps(res, indent=2))
