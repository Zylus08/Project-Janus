"""Project Janus v0.61 - Native C++17 Engine Python Bridge with NNUE-V2 & AVX2 Support."""

from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import chess

_THIS_DIR = Path(__file__).resolve().parent
_DLL_PATH = _THIS_DIR / "janus_native.dll"

if not _DLL_PATH.exists():
    raise FileNotFoundError(f"janus_native.dll not found at {_DLL_PATH}. Compile it first.")

_dll = ctypes.CDLL(str(_DLL_PATH))


# Structures matching C++ definitions
class NativeBoard(ctypes.Structure):
    _fields_ = [
        ("pieces", (ctypes.c_uint64 * 6) * 2),
        ("occupancy", ctypes.c_uint64 * 3),
        ("side_to_move", ctypes.c_int),
        ("castling_rights", ctypes.c_uint8),
        ("ep_square", ctypes.c_uint8),
        ("halfmove_clock", ctypes.c_uint8),
        ("fullmove_number", ctypes.c_uint16),
        ("zobrist_key", ctypes.c_uint64),
    ]


class UndoInfo(ctypes.Structure):
    _fields_ = [
        ("captured_piece", ctypes.c_int),
        ("castling_rights", ctypes.c_uint8),
        ("ep_square", ctypes.c_uint8),
        ("halfmove_clock", ctypes.c_uint8),
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


# Function Signatures
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

_dll.native_reset_history.restype = None
_dll.native_clear_tt.argtypes = []
_dll.native_clear_tt.restype = None

_dll.native_set_lmr_options.argtypes = [ctypes.c_bool, ctypes.c_int, ctypes.c_int, ctypes.c_int]
_dll.native_set_lmr_options.restype = None

_dll.native_set_pvs_options.argtypes = [ctypes.c_bool]
_dll.native_set_pvs_options.restype = None

_dll.native_set_ordering_options.argtypes = [ctypes.c_bool, ctypes.c_bool]
_dll.native_set_ordering_options.restype = None

_dll.native_clear_killers.argtypes = []
_dll.native_clear_killers.restype = None

_dll.native_clear_history_heuristic.argtypes = []
_dll.native_clear_history_heuristic.restype = None

_dll.native_set_see_ordering.argtypes = [ctypes.c_int]
_dll.native_set_see_ordering.restype = None

_dll.native_set_see_in_quiescence.argtypes = [ctypes.c_int]
_dll.native_set_see_in_quiescence.restype = None

# NNUE-V2 specific functions
_dll.native_set_neural_value_options.argtypes = [ctypes.c_bool, ctypes.c_char_p, ctypes.c_int, ctypes.c_bool]
_dll.native_set_neural_value_options.restype = None

_dll.native_evaluate_neural.argtypes = [ctypes.POINTER(NativeBoard)]
_dll.native_evaluate_neural.restype = ctypes.c_int


class NativeEngineBridge:
    def __init__(self):
        self.board = NativeBoard()
        _dll.native_init()
        self.set_fen(chess.STARTING_FEN)

    def set_fen(self, fen: str):
        res = _dll.native_set_fen(fen.encode("utf-8"), ctypes.byref(self.board))
        if res == 0:
            raise ValueError(f"Invalid FEN: {fen}")

    def get_fen(self) -> str:
        buf = ctypes.create_string_buffer(128)
        _dll.native_get_fen(ctypes.byref(self.board), buf)
        return buf.value.decode("utf-8")

    def is_check(self) -> bool:
        return _dll.native_is_check(ctypes.byref(self.board)) != 0

    def evaluate(self) -> int:
        return _dll.native_evaluate(ctypes.byref(self.board))

    def evaluate_neural(self) -> int:
        return _dll.native_evaluate_neural(ctypes.byref(self.board))

    def set_neural_value_options(
        self,
        enabled: bool,
        model_path: str = "analysis/v0.61/models/janus_nnue_v2_small.jnnue",
        blend: int = 100,
        use_avx2: bool = True,
    ):
        if model_path:
            p = Path(model_path)
            if not p.is_absolute():
                proj_root = _THIS_DIR.parents[2]
                candidate = proj_root / model_path
                if candidate.exists():
                    p = candidate
            c_path = str(p).encode("utf-8")
        else:
            c_path = None
        _dll.native_set_neural_value_options(enabled, c_path, blend, use_avx2)

    def set_ordering_options(self, use_killer: bool, use_history: bool):
        _dll.native_set_ordering_options(use_killer, use_history)

    def set_pvs_options(self, use_pvs: bool):
        _dll.native_set_pvs_options(use_pvs)

    def set_lmr_options(self, use_lmr: bool, min_depth: int = 3, move_threshold: int = 4, base_reduction: int = 1):
        _dll.native_set_lmr_options(use_lmr, min_depth, move_threshold, base_reduction)

    def set_see_options(self, use_see_ordering: bool, use_see_in_quiescence: bool):
        _dll.native_set_see_ordering(1 if use_see_ordering else 0)
        _dll.native_set_see_in_quiescence(1 if use_see_in_quiescence else 0)

    def clear_tt(self):
        _dll.native_clear_tt()

    def clear_killers(self):
        _dll.native_clear_killers()

    def clear_history_heuristic(self):
        _dll.native_clear_history_heuristic()

    def reset_history(self):
        _dll.native_reset_history()

    def search(self, max_depth: int = 4, time_limit: float = 5.0) -> Tuple[str, int, int, int, float, List[str]]:
        res = NativeSearchResult()
        _dll.native_search(ctypes.byref(self.board), max_depth, time_limit, ctypes.byref(res))

        buf = ctypes.create_string_buffer(16)
        _dll.native_move_to_uci(res.best_move, buf)
        best_move_str = buf.value.decode("utf-8")

        pv_moves = []
        for i in range(res.pv_length):
            pv_buf = ctypes.create_string_buffer(16)
            _dll.native_move_to_uci(res.pv[i], pv_buf)
            pv_moves.append(pv_buf.value.decode("utf-8"))

        return best_move_str, res.score, res.depth, res.nodes, res.elapsed_seconds, pv_moves
