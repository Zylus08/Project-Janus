import chess

# HalfKP-40960 Feature Schema
# 64 King Squares * 10 Piece Categories * 64 Piece Squares = 40,960 features.
# Piece categories:
# Friendly: 0: Pawn, 1: Knight, 2: Bishop, 3: Rook, 4: Queen
# Enemy:    5: Pawn, 6: Knight, 7: Bishop, 8: Rook, 9: Queen

PIECE_TO_TYPE_INDEX = {
    chess.PAWN: 0,
    chess.KNIGHT: 1,
    chess.BISHOP: 2,
    chess.ROOK: 3,
    chess.QUEEN: 4,
}

def flip_square(sq: int) -> int:
    """Flip rank (rank r -> 7 - r) for Black perspective."""
    return sq ^ 56

def get_halfkp_features(board: chess.Board):
    """
    Returns (white_features, black_features) as lists of integer feature indices [0, 40959].
    """
    white_king_sq = board.king(chess.WHITE)
    black_king_sq = board.king(chess.BLACK)
    
    if white_king_sq is None or black_king_sq is None:
        raise ValueError("Board must have both kings.")
        
    white_k = white_king_sq
    black_k = flip_square(black_king_sq)
    
    white_features = []
    black_features = []
    
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece is None or piece.piece_type == chess.KING:
            continue
            
        t_idx = PIECE_TO_TYPE_INDEX[piece.piece_type]
        
        # White perspective:
        cat_w = t_idx if piece.color == chess.WHITE else 5 + t_idx
        idx_w = white_k * 640 + cat_w * 64 + sq
        white_features.append(idx_w)
        
        # Black perspective:
        cat_b = t_idx if piece.color == chess.BLACK else 5 + t_idx
        sq_b = flip_square(sq)
        idx_b = black_k * 640 + cat_b * 64 + sq_b
        black_features.append(idx_b)
        
    return white_features, black_features

class HalfKPAccumulator:
    """Simulates HalfKP incremental accumulator state for testing and oracle validation."""
    def __init__(self, hidden_dim=128):
        self.hidden_dim = hidden_dim
        self.white_indices = set()
        self.black_indices = set()
        self.white_king_sq = None
        self.black_king_sq = None

    def refresh(self, board: chess.Board):
        wf, bf = get_halfkp_features(board)
        self.white_indices = set(wf)
        self.black_indices = set(bf)
        self.white_king_sq = board.king(chess.WHITE)
        self.black_king_sq = board.king(chess.BLACK)

    def apply_move(self, board_before: chess.Board, move: chess.Move):
        """
        Incrementally updates active features given board_before and move.
        Returns whether full refresh was performed for (white, black).
        """
        piece = board_before.piece_at(move.from_square)
        is_white = piece.color == chess.WHITE if piece else True
        from_sq = move.from_square
        to_sq = move.to_square
        
        # Board after move
        board_after = board_before.copy(stack=False)
        board_after.push(move)
        
        white_refreshed = False
        black_refreshed = False
        
        # Case A: King moves
        if piece and piece.piece_type == chess.KING:
            if is_white:
                # White king moved -> White perspective full refresh
                wf, _ = get_halfkp_features(board_after)
                self.white_indices = set(wf)
                self.white_king_sq = board_after.king(chess.WHITE)
                white_refreshed = True
                
                # In Black perspective, Black king did not move:
                # 1. Did White castle? Then White rook moved!
                if board_before.is_castling(move):
                    if to_sq == chess.G1: r_from, r_to = chess.H1, chess.F1
                    elif to_sq == chess.C1: r_from, r_to = chess.A1, chess.D1
                    r_t = PIECE_TO_TYPE_INDEX[chess.ROOK]
                    r_cat_b = 5 + r_t # Enemy rook
                    self.black_indices.remove(flip_square(self.black_king_sq) * 640 + r_cat_b * 64 + flip_square(r_from))
                    self.black_indices.add(flip_square(self.black_king_sq) * 640 + r_cat_b * 64 + flip_square(r_to))
                # 2. Did White King capture a piece on to_sq? Then remove it from Black perspective!
                elif board_before.piece_at(to_sq):
                    cap_piece = board_before.piece_at(to_sq)
                    if cap_piece.piece_type != chess.KING:
                        cap_t = PIECE_TO_TYPE_INDEX[cap_piece.piece_type]
                        cap_cat_b = cap_t # Friendly piece to Black
                        self.black_indices.remove(flip_square(self.black_king_sq) * 640 + cap_cat_b * 64 + flip_square(to_sq))
            else:
                # Black king moved -> Black perspective full refresh
                _, bf = get_halfkp_features(board_after)
                self.black_indices = set(bf)
                self.black_king_sq = board_after.king(chess.BLACK)
                black_refreshed = True
                
                # In White perspective, White king did not move:
                # 1. Did Black castle?
                if board_before.is_castling(move):
                    if to_sq == chess.G8: r_from, r_to = chess.H8, chess.F8
                    elif to_sq == chess.C8: r_from, r_to = chess.A8, chess.D8
                    r_t = PIECE_TO_TYPE_INDEX[chess.ROOK]
                    r_cat_w = 5 + r_t # Enemy rook
                    self.white_indices.remove(self.white_king_sq * 640 + r_cat_w * 64 + r_from)
                    self.white_indices.add(self.white_king_sq * 640 + r_cat_w * 64 + r_to)
                # 2. Did Black King capture a piece on to_sq?
                elif board_before.piece_at(to_sq):
                    cap_piece = board_before.piece_at(to_sq)
                    if cap_piece.piece_type != chess.KING:
                        cap_t = PIECE_TO_TYPE_INDEX[cap_piece.piece_type]
                        cap_cat_w = cap_t # Friendly piece to White
                        self.white_indices.remove(self.white_king_sq * 640 + cap_cat_w * 64 + to_sq)
                        
            return white_refreshed, black_refreshed
            
        # Case B: Non-king move (Pure delta updates for both perspectives)
        t_idx = PIECE_TO_TYPE_INDEX[piece.piece_type]
        
        # 1. Removed feature at from_square
        cat_w_from = t_idx if is_white else 5 + t_idx
        idx_w_del = self.white_king_sq * 640 + cat_w_from * 64 + from_sq
        self.white_indices.remove(idx_w_del)
        
        cat_b_from = t_idx if not is_white else 5 + t_idx
        idx_b_del = flip_square(self.black_king_sq) * 640 + cat_b_from * 64 + flip_square(from_sq)
        self.black_indices.remove(idx_b_del)
        
        # 2. Captured piece (if any)
        if board_before.is_en_passant(move):
            cap_sq = chess.square(chess.square_file(to_sq), chess.square_rank(from_sq))
            cap_piece = board_before.piece_at(cap_sq)
            cap_t = PIECE_TO_TYPE_INDEX[cap_piece.piece_type]
            cap_cat_w = 5 + cap_t if is_white else cap_t
            cap_cat_b = cap_t if is_white else 5 + cap_t
            self.white_indices.remove(self.white_king_sq * 640 + cap_cat_w * 64 + cap_sq)
            self.black_indices.remove(flip_square(self.black_king_sq) * 640 + cap_cat_b * 64 + flip_square(cap_sq))
        elif board_before.piece_at(to_sq):
            cap_piece = board_before.piece_at(to_sq)
            if cap_piece.piece_type != chess.KING:
                cap_t = PIECE_TO_TYPE_INDEX[cap_piece.piece_type]
                cap_cat_w = 5 + cap_t if is_white else cap_t
                cap_cat_b = cap_t if is_white else 5 + cap_t
                self.white_indices.remove(self.white_king_sq * 640 + cap_cat_w * 64 + to_sq)
                self.black_indices.remove(flip_square(self.black_king_sq) * 640 + cap_cat_b * 64 + flip_square(to_sq))
            
        # 3. Added piece at to_square (with promotion if any)
        added_piece_type = move.promotion if move.promotion else piece.piece_type
        added_t = PIECE_TO_TYPE_INDEX[added_piece_type]
        added_cat_w = added_t if is_white else 5 + added_t
        added_cat_b = 5 + added_t if is_white else added_t
        self.white_indices.add(self.white_king_sq * 640 + added_cat_w * 64 + to_sq)
        self.black_indices.add(flip_square(self.black_king_sq) * 640 + added_cat_b * 64 + flip_square(to_sq))
        
        return white_refreshed, black_refreshed
