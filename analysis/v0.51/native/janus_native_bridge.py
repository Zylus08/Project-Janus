"""Project Janus v0.51 - Native Engine Bridge.

Provides a typed ctypes interface to analysis/v0.51/native/janus_native.dll.
Supports:
- Board initialization, FEN parsing, and export
- Attack queries & check detection
- Legal move generation & perft verification
- Make / unmake reversible state transitions
- Game history and repetition tracking (threefold, fivefold)
- FIDE draw rules (fifty-move, seventy-five-move, insufficient material)
- Standalone search execution with PV extraction
"""

import ctypes
from pathlib import Path
from typing import List, Tuple, Optional

DLL_PATH = Path(__file__).parent / "janus_native.dll"


class NativeBoard(ctypes.Structure):
    _fields_ = [
        ("pieces", (ctypes.c_uint64 * 6) * 2),
        ("occupancy", ctypes.c_uint64 * 3),
        ("side_to_move", ctypes.c_uint8),
        ("castling_rights", ctypes.c_uint8),
        ("ep_square", ctypes.c_uint8),
        ("halfmove_clock", ctypes.c_uint16),
        ("fullmove_number", ctypes.c_uint16),
        ("zobrist_key", ctypes.c_uint64),
    ]


class UndoInfo(ctypes.Structure):
    _fields_ = [
        ("captured_piece", ctypes.c_uint8),
        ("castling_rights", ctypes.c_uint8),
        ("ep_square", ctypes.c_uint8),
        ("halfmove_clock", ctypes.c_uint16),
        ("zobrist_key", ctypes.c_uint64),
    ]


class NativeSearchResult(ctypes.Structure):
    _fields_ = [
        ("best_move", ctypes.c_uint16),
        ("score", ctypes.c_int),
        ("depth", ctypes.c_int),
        ("nodes", ctypes.c_uint64),
        ("elapsed_seconds", ctypes.c_double),
        ("pv_length", ctypes.c_int),
        ("pv", ctypes.c_uint16 * 128),
    ]


# Load DLL
_dll = ctypes.CDLL(str(DLL_PATH.resolve()))

# Signatures
_dll.native_init.restype = ctypes.c_int

_dll.native_set_fen.argtypes = [ctypes.c_char_p, ctypes.POINTER(NativeBoard)]
_dll.native_set_fen.restype = ctypes.c_int

_dll.native_get_fen.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_char_p]
_dll.native_get_fen.restype = None

_dll.native_is_check.argtypes = [ctypes.POINTER(NativeBoard)]
_dll.native_is_check.restype = ctypes.c_int

_dll.native_make_move.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_uint16, ctypes.POINTER(UndoInfo)]
_dll.native_make_move.restype = ctypes.c_int

_dll.native_unmake_move.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_uint16, ctypes.POINTER(UndoInfo)]
_dll.native_unmake_move.restype = None

_dll.native_generate_legal_moves.argtypes = [ctypes.POINTER(NativeBoard), ctypes.POINTER(ctypes.c_uint16)]
_dll.native_generate_legal_moves.restype = ctypes.c_int

_dll.native_perft.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_int]
_dll.native_perft.restype = ctypes.c_uint64

_dll.native_evaluate.argtypes = [ctypes.POINTER(NativeBoard)]
_dll.native_evaluate.restype = ctypes.c_int

_dll.native_move_to_uci.argtypes = [ctypes.c_uint16, ctypes.c_char_p]
_dll.native_move_to_uci.restype = None

_dll.native_parse_uci.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_char_p]
_dll.native_parse_uci.restype = ctypes.c_uint16

_dll.native_search.argtypes = [
    ctypes.POINTER(NativeBoard),
    ctypes.c_int,
    ctypes.c_double,
    ctypes.POINTER(NativeSearchResult),
]
_dll.native_search.restype = ctypes.c_int

# Draw and Repetition Functions (Phase B)
_dll.native_reset_history.restype = None

_dll.native_push_history.argtypes = [ctypes.c_uint64]
_dll.native_push_history.restype = None

_dll.native_pop_history.restype = None

_dll.native_get_history_len.restype = ctypes.c_int

_dll.native_get_history_key.argtypes = [ctypes.c_int]
_dll.native_get_history_key.restype = ctypes.c_uint64

_dll.native_is_repetition.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_int]
_dll.native_is_repetition.restype = ctypes.c_int

_dll.native_is_fivefold_repetition.argtypes = [ctypes.POINTER(NativeBoard)]
_dll.native_is_fivefold_repetition.restype = ctypes.c_int

_dll.native_can_claim_threefold_repetition.argtypes = [ctypes.POINTER(NativeBoard)]
_dll.native_can_claim_threefold_repetition.restype = ctypes.c_int

_dll.native_can_claim_fifty_moves.argtypes = [ctypes.POINTER(NativeBoard)]
_dll.native_can_claim_fifty_moves.restype = ctypes.c_int

_dll.native_is_seventyfive_moves.argtypes = [ctypes.POINTER(NativeBoard)]
_dll.native_is_seventyfive_moves.restype = ctypes.c_int

_dll.native_is_insufficient_material.argtypes = [ctypes.POINTER(NativeBoard)]
_dll.native_is_insufficient_material.restype = ctypes.c_int

_dll.native_is_claimable_draw.argtypes = [ctypes.POINTER(NativeBoard)]
_dll.native_is_claimable_draw.restype = ctypes.c_int

_dll.native_is_automatic_draw.argtypes = [ctypes.POINTER(NativeBoard)]
_dll.native_is_automatic_draw.restype = ctypes.c_int

# Initialize DLL tables
_dll.native_init()


class NativeEngineBridge:
    def __init__(self):
        self.board = NativeBoard()
        self.reset_history()

    def reset_history(self):
        _dll.native_reset_history()

    def push_history(self, key: int):
        _dll.native_push_history(ctypes.c_uint64(key))

    def pop_history(self):
        _dll.native_pop_history()

    def get_history_len(self) -> int:
        return _dll.native_get_history_len()

    def get_history_key(self, idx: int) -> int:
        return _dll.native_get_history_key(idx)

    def set_fen(self, fen: str) -> bool:
        ret = _dll.native_set_fen(fen.encode("utf-8"), ctypes.byref(self.board))
        return bool(ret)

    def get_fen(self) -> str:
        buf = ctypes.create_string_buffer(128)
        _dll.native_get_fen(ctypes.byref(self.board), buf)
        return buf.value.decode("utf-8")

    def is_check(self) -> bool:
        return bool(_dll.native_is_check(ctypes.byref(self.board)))

    def evaluate(self) -> int:
        return _dll.native_evaluate(ctypes.byref(self.board))

    def move_to_uci(self, m: int) -> str:
        buf = ctypes.create_string_buffer(16)
        _dll.native_move_to_uci(m, buf)
        return buf.value.decode("utf-8")

    def parse_uci(self, uci_str: str) -> int:
        return _dll.native_parse_uci(ctypes.byref(self.board), uci_str.encode("utf-8"))

    def make_move(self, m: int) -> Tuple[bool, UndoInfo]:
        undo = UndoInfo()
        ok = bool(_dll.native_make_move(ctypes.byref(self.board), m, ctypes.byref(undo)))
        return ok, undo

    def unmake_move(self, m: int, undo: UndoInfo):
        _dll.native_unmake_move(ctypes.byref(self.board), m, ctypes.byref(undo))

    def get_legal_moves_uci(self) -> List[str]:
        moves_buf = (ctypes.c_uint16 * 256)()
        count = _dll.native_generate_legal_moves(ctypes.byref(self.board), moves_buf)
        return [self.move_to_uci(moves_buf[i]) for i in range(count)]

    def perft(self, depth: int) -> int:
        return int(_dll.native_perft(ctypes.byref(self.board), depth))

    def is_repetition(self, count: int) -> bool:
        return bool(_dll.native_is_repetition(ctypes.byref(self.board), count))

    def is_fivefold_repetition(self) -> bool:
        return bool(_dll.native_is_fivefold_repetition(ctypes.byref(self.board)))

    def can_claim_threefold_repetition(self) -> bool:
        return bool(_dll.native_can_claim_threefold_repetition(ctypes.byref(self.board)))

    def can_claim_fifty_moves(self) -> bool:
        return bool(_dll.native_can_claim_fifty_moves(ctypes.byref(self.board)))

    def is_seventyfive_moves(self) -> bool:
        return bool(_dll.native_is_seventyfive_moves(ctypes.byref(self.board)))

    def is_insufficient_material(self) -> bool:
        return bool(_dll.native_is_insufficient_material(ctypes.byref(self.board)))

    def is_claimable_draw(self) -> bool:
        return bool(_dll.native_is_claimable_draw(ctypes.byref(self.board)))

    def is_automatic_draw(self) -> bool:
        return bool(_dll.native_is_automatic_draw(ctypes.byref(self.board)))

    def search(self, max_depth: int = 64, time_limit: float = 1000.0) -> Tuple[str, int, int, int, float, List[str]]:
        """Runs native iterative deepening search.

        Returns (best_move_uci, score, depth, nodes, elapsed_sec, pv_moves_uci).
        """
        res = NativeSearchResult()
        _dll.native_search(ctypes.byref(self.board), max_depth, ctypes.c_double(time_limit), ctypes.byref(res))
        best_mv_uci = self.move_to_uci(res.best_move) if res.best_move != 0 else None
        pv = [self.move_to_uci(res.pv[i]) for i in range(res.pv_length)]
        return best_mv_uci, res.score, res.depth, res.nodes, res.elapsed_seconds, pv

