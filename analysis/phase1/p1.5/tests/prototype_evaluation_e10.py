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

class E10Prototype:
    def __init__(self, dll_path="E:/ChessXML/project-janus-phase1/analysis/phase1/p1.3/control/janus_classical_x7.dll"):
        self.dll = ctypes.CDLL(dll_path)
        self.dll.native_init()

    def evaluate_e10(self, fen):
        b = NativeBoard()
        ret = self.dll.native_set_fen(fen.encode('utf-8'), ctypes.byref(b))
        if ret != 1:
            raise ValueError(f"Invalid FEN: {fen}")

        # Get base X7 evaluation (emode 5)
        base_x7_eval = self.dll.native_evaluate_detail(ctypes.byref(b), 5)
        e0 = self.dll.native_evaluate_detail(ctypes.byref(b), 0)

        # Decompose board
        WHITE, BLACK = 0, 1
        PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING = 0, 1, 2, 3, 4, 5
        
        def popcount(x):
            return bin(x).count('1')

        # Check queens
        white_queens = popcount(b.pieces[WHITE][QUEEN])
        black_queens = popcount(b.pieces[BLACK][QUEEN])

        e10_mg_adj = 0
        e10_eg_adj = 0

        # 1. E2' Fix: Queenless King Safety Adjustment
        # In X7, king safety was computed with quadratic danger regardless of queens
        # If White has no queen, Black's king cannot be in heavy danger; if Black has no queen, White's king cannot be in heavy danger
        if black_queens == 0:
            # White's king has no danger from Black queen; refund phantom king safety penalties
            e3_w = self.dll.native_evaluate_detail(ctypes.byref(b), 3) - e0
            if e3_w < 0:
                e10_mg_adj += abs(e3_w) // 2 # Soften exaggerated penalty
        if white_queens == 0:
            e3_b = self.dll.native_evaluate_detail(ctypes.byref(b), 3) - e0
            if e3_b > 0:
                e10_mg_adj -= e3_b // 2

        # 2. E3' Fix: Outpost Sanity Check
        # Check knights on ranks 4-6
        # In X7, knights on d5/e5 got +15 mg, +10 eg even if kickable
        # If kickable, reduce bonus
        for c in [WHITE, BLACK]:
            knights = b.pieces[c][KNIGHT]
            enemy_pawns = b.pieces[1 - c][PAWN]
            while knights:
                lsb = (knights & -knights).bit_length() - 1
                knights &= knights - 1
                r = (lsb // 8) if c == WHITE else (7 - (lsb // 8))
                f = lsb % 8
                if 3 <= r <= 5:
                    # Check if enemy pawns can attack this square
                    # Forward adjacent span
                    kickable = False
                    for adj_f in [f - 1, f + 1]:
                        if 0 <= adj_f <= 7:
                            for enemy_r in range(r if c == WHITE else 0, 8 if c == WHITE else r + 1):
                                if enemy_pawns & (1 << (enemy_r * 8 + adj_f)):
                                    kickable = True
                                    break
                    if kickable:
                        adj = -10 if c == WHITE else 10
                        e10_mg_adj += adj
                        e10_eg_adj += adj // 2

        # 3. E5' Fix: Pure Pawn Endgame Rule of the Square
        total_pieces = sum(popcount(b.pieces[c][p]) for c in [0, 1] for p in range(1, 6))
        if total_pieces == 0:
            # King + Pawns endgame
            # Check for unstoppable passed pawns
            pass

        # Interpolate adjustment with game phase
        game_phase = 0
        game_phase += (popcount(b.pieces[WHITE][KNIGHT]) + popcount(b.pieces[BLACK][KNIGHT])) * 1
        game_phase += (popcount(b.pieces[WHITE][BISHOP]) + popcount(b.pieces[BLACK][BISHOP])) * 1
        game_phase += (popcount(b.pieces[WHITE][ROOK]) + popcount(b.pieces[BLACK][ROOK])) * 2
        game_phase += (popcount(b.pieces[WHITE][QUEEN]) + popcount(b.pieces[BLACK][QUEEN])) * 4
        if game_phase > 24: game_phase = 24

        total_adj = (e10_mg_adj * game_phase + e10_eg_adj * (24 - game_phase)) // 24
        final_score = base_x7_eval + (total_adj if b.side_to_move == WHITE else -total_adj)

        return {
            "fen": fen,
            "base_x7_eval": base_x7_eval,
            "e10_mg_adj": e10_mg_adj,
            "e10_eg_adj": e10_eg_adj,
            "total_adj": total_adj,
            "final_e10_eval": final_score
        }

if __name__ == "__main__":
    proto = E10Prototype()
    # Test on POS_27 and POS_28 (queenless middlegames)
    for pos_id, fen in [
        ("POS_17_KNIGHT_OUT_DEV", "r1b2rk1/pp1n1ppp/2p1pn2/q2p2B1/2PP4/2N1PN2/PPQ2PPP/R3KB1R w KQ - 1 9"),
        ("POS_27_QUEENLESS_DEV", "r1b2rk1/pp1n1ppp/2p1pn2/8/2PP4/1PN1PN2/P2B1PPP/R3KB1R b KQ - 0 10"),
        ("POS_28_QUEENLESS_HELD", "r1b1r1k1/pp1n1ppp/2p2n2/3p4/2PP4/1PN1PN2/P2B1PPP/R3KB1R w KQ - 1 11")
    ]:
        res = proto.evaluate_e10(fen)
        print(f"[{pos_id}] Base X7: {res['base_x7_eval']} cp -> E10: {res['final_e10_eval']} cp (adj: {res['total_adj']} cp)")

