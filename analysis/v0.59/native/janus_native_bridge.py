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
import numpy as np

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

# LMR Functions (Phase 3 v0.52)
_dll.native_set_lmr_options.argtypes = [ctypes.c_bool, ctypes.c_int, ctypes.c_int, ctypes.c_int]
_dll.native_set_lmr_options.restype = None

_dll.native_reset_lmr_telemetry.argtypes = []
_dll.native_reset_lmr_telemetry.restype = None

_dll.native_clear_tt.argtypes = []
_dll.native_clear_tt.restype = None

_dll.native_get_lmr_telemetry.argtypes = [ctypes.POINTER(ctypes.c_uint64)]
_dll.native_get_lmr_telemetry.restype = None

# PVS Functions (Phase 3 v0.53)
_dll.native_set_pvs_options.argtypes = [ctypes.c_bool]
_dll.native_set_pvs_options.restype = None

_dll.native_reset_pvs_telemetry.argtypes = []
_dll.native_reset_pvs_telemetry.restype = None

_dll.native_get_pvs_telemetry.argtypes = [ctypes.POINTER(ctypes.c_uint64)]
_dll.native_get_pvs_telemetry.restype = None

# Move Ordering Functions (Phase 2 & 3 v0.54)
_dll.native_set_ordering_options.argtypes = [ctypes.c_bool, ctypes.c_bool]
_dll.native_set_ordering_options.restype = None

_dll.native_clear_killers.argtypes = []
_dll.native_clear_killers.restype = None

_dll.native_clear_history_heuristic.argtypes = []
_dll.native_clear_history_heuristic.restype = None

_dll.native_reset_ordering_telemetry.argtypes = []
_dll.native_reset_ordering_telemetry.restype = None

_dll.native_get_ordering_telemetry.argtypes = [ctypes.POINTER(ctypes.c_uint64)]
_dll.native_get_ordering_telemetry.restype = None

_dll.native_get_killer.argtypes = [ctypes.c_int, ctypes.c_int]
_dll.native_get_killer.restype = ctypes.c_uint16

_dll.native_get_history_score.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
_dll.native_get_history_score.restype = ctypes.c_int

# SEE Functions (Phase 4 v0.56)
_dll.native_see.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_uint16]
_dll.native_see.restype = ctypes.c_int

_dll.native_set_see_ordering.argtypes = [ctypes.c_int]
_dll.native_set_see_ordering.restype = None

_dll.native_set_see_in_quiescence.argtypes = [ctypes.c_int]
_dll.native_set_see_in_quiescence.restype = None

_dll.native_reset_see_telemetry.argtypes = []
_dll.native_reset_see_telemetry.restype = None

_dll.native_get_see_telemetry.argtypes = [ctypes.POINTER(ctypes.c_uint64)]
_dll.native_get_see_telemetry.restype = None

# Neural Policy Functions (Phase 3 v0.58)
_dll.native_load_policy_model.argtypes = [ctypes.c_char_p]
_dll.native_load_policy_model.restype = ctypes.c_int

_dll.native_set_neural_policy_options.argtypes = [ctypes.c_bool, ctypes.c_int, ctypes.c_int, ctypes.c_int]
_dll.native_set_neural_policy_options.restype = None

_dll.native_encode_board_tensor.argtypes = [ctypes.POINTER(NativeBoard), ctypes.POINTER(ctypes.c_float)]
_dll.native_encode_board_tensor.restype = ctypes.c_int

_dll.native_encode_action.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_uint16]
_dll.native_encode_action.restype = ctypes.c_int

_dll.native_forward_policy.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float)]
_dll.native_forward_policy.restype = ctypes.c_int

_dll.native_get_neural_telemetry.argtypes = [
    ctypes.POINTER(ctypes.c_uint64),
    ctypes.POINTER(ctypes.c_uint64),
    ctypes.POINTER(ctypes.c_uint64),
]
_dll.native_get_neural_telemetry.restype = None

_dll.native_reset_neural_telemetry.argtypes = []
_dll.native_reset_neural_telemetry.restype = None

# Causal Policy & Search Gating Functions (Phase 1-3 v0.59)
_dll.native_set_causal_policy_mode.argtypes = [ctypes.c_int]
_dll.native_set_causal_policy_mode.restype = None

_dll.native_set_search_gating_mode.argtypes = [ctypes.c_int]
_dll.native_set_search_gating_mode.restype = None

_dll.native_set_neural_budget_us.argtypes = [ctypes.c_uint64]
_dll.native_set_neural_budget_us.restype = None

_dll.native_set_deterministic_seed.argtypes = [ctypes.c_uint64]
_dll.native_set_deterministic_seed.restype = None

_dll.native_reset_root_telemetry.argtypes = []
_dll.native_reset_root_telemetry.restype = None

_dll.native_get_root_telemetry_json.argtypes = [ctypes.c_int]
_dll.native_get_root_telemetry_json.restype = ctypes.c_char_p

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

    def get_legal_moves(self) -> List[int]:
        moves_buf = (ctypes.c_uint16 * 256)()
        count = _dll.native_generate_legal_moves(ctypes.byref(self.board), moves_buf)
        return [int(moves_buf[i]) for i in range(count)]

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

    def set_lmr_options(self, use_lmr: bool, min_depth: int = 3, move_threshold: int = 4, base_reduction: int = 1):
        _dll.native_set_lmr_options(ctypes.c_bool(use_lmr), ctypes.c_int(min_depth), ctypes.c_int(move_threshold), ctypes.c_int(base_reduction))

    def reset_lmr_telemetry(self):
        _dll.native_reset_lmr_telemetry()

    def clear_tt(self):
        _dll.native_clear_tt()

    def get_lmr_telemetry(self) -> dict:
        arr = (ctypes.c_uint64 * 4)()
        _dll.native_get_lmr_telemetry(arr)
        return {
            "eligible_moves": int(arr[0]),
            "reduced_moves": int(arr[1]),
            "researches": int(arr[2]),
            "cutoffs": int(arr[3]),
        }

    def set_pvs_options(self, use_pvs: bool):
        _dll.native_set_pvs_options(ctypes.c_bool(use_pvs))

    def reset_pvs_telemetry(self):
        _dll.native_reset_pvs_telemetry()

    def get_pvs_telemetry(self) -> dict:
        arr = (ctypes.c_uint64 * 4)()
        _dll.native_get_pvs_telemetry(arr)
        return {
            "full_window_searches": int(arr[0]),
            "null_window_searches": int(arr[1]),
            "researches": int(arr[2]),
            "cutoffs": int(arr[3]),
        }

    def set_ordering_options(self, use_killer: bool, use_history: bool):
        _dll.native_set_ordering_options(ctypes.c_bool(use_killer), ctypes.c_bool(use_history))

    def clear_killers(self):
        _dll.native_clear_killers()

    def clear_history_heuristic(self):
        _dll.native_clear_history_heuristic()

    def reset_ordering_telemetry(self):
        _dll.native_reset_ordering_telemetry()

    def get_ordering_telemetry(self) -> dict:
        arr = (ctypes.c_uint64 * 12)()
        _dll.native_get_ordering_telemetry(arr)
        total_cutoffs = int(arr[0])
        sum_idx = int(arr[1])
        mean_idx = (sum_idx / total_cutoffs) if total_cutoffs > 0 else 0.0
        return {
            "total_cutoffs": total_cutoffs,
            "mean_cutoff_index": mean_idx,
            "cutoff_move_1": int(arr[2]),
            "cutoff_move_2": int(arr[3]),
            "cutoff_move_3": int(arr[4]),
            "cutoff_move_4plus": int(arr[5]),
            "cutoff_tt": int(arr[6]),
            "cutoff_killer1": int(arr[7]),
            "cutoff_killer2": int(arr[8]),
            "cutoff_history": int(arr[9]),
            "cutoff_captures": int(arr[10]),
            "cutoff_quiet": int(arr[11]),
            "first_move_cutoff_rate": (int(arr[2]) / total_cutoffs * 100.0) if total_cutoffs > 0 else 0.0,
        }

    def get_killer(self, ply: int, slot: int) -> int:
        return int(_dll.native_get_killer(ctypes.c_int(ply), ctypes.c_int(slot)))

    def get_history_score(self, side: int, from_sq: int, to_sq: int) -> int:
        return int(_dll.native_get_history_score(ctypes.c_int(side), ctypes.c_int(from_sq), ctypes.c_int(to_sq)))

    def see(self, move_val: int) -> int:
        return int(_dll.native_see(ctypes.byref(self.board), ctypes.c_uint16(move_val)))

    def set_see_options(self, use_see_ordering: bool, use_see_in_quiescence: bool):
        _dll.native_set_see_ordering(1 if use_see_ordering else 0)
        _dll.native_set_see_in_quiescence(1 if use_see_in_quiescence else 0)

    def reset_see_telemetry(self):
        _dll.native_reset_see_telemetry()

    def get_see_telemetry(self) -> dict:
        arr = (ctypes.c_uint64 * 5)()
        _dll.native_get_see_telemetry(arr)
        return {
            "total_evaluations": int(arr[0]),
            "positive_captures": int(arr[1]),
            "neutral_captures": int(arr[2]),
            "negative_captures": int(arr[3]),
            "ordering_inversions": int(arr[4]),
        }

    def load_policy_model(self, path: str) -> bool:
        return bool(_dll.native_load_policy_model(path.encode('utf-8')))

    def set_neural_policy_options(self, use_policy: bool, max_ply: int = 0, min_depth: int = 4, score_weight: int = 50000):
        _dll.native_set_neural_policy_options(ctypes.c_bool(use_policy), ctypes.c_int(max_ply), ctypes.c_int(min_depth), ctypes.c_int(score_weight))

    def encode_board_tensor(self) -> np.ndarray:
        tensor = np.zeros(896, dtype=np.float32)
        c_arr = tensor.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
        ok = _dll.native_encode_board_tensor(ctypes.byref(self.board), c_arr)
        if not ok:
            raise RuntimeError("native_encode_board_tensor failed")
        return tensor

    def encode_action(self, move_val: int) -> int:
        return int(_dll.native_encode_action(ctypes.byref(self.board), ctypes.c_uint16(move_val)))

    def forward_policy(self, tensor: np.ndarray) -> np.ndarray:
        logits = np.zeros(4168, dtype=np.float32)
        c_tensor = tensor.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
        c_logits = logits.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
        ok = _dll.native_forward_policy(c_tensor, c_logits)
        if not ok:
            raise RuntimeError("native_forward_policy failed (model not loaded?)")
        return logits

    def get_neural_telemetry(self) -> dict:
        evals = ctypes.c_uint64(0)
        moves_scored = ctypes.c_uint64(0)
        time_us = ctypes.c_uint64(0)
        _dll.native_get_neural_telemetry(ctypes.byref(evals), ctypes.byref(moves_scored), ctypes.byref(time_us))
        return {
            "evaluations": int(evals.value),
            "moves_scored": int(moves_scored.value),
            "inference_time_us": int(time_us.value),
        }

    def reset_neural_telemetry(self):
        _dll.native_reset_neural_telemetry()

    def set_causal_policy_mode(self, mode: int) -> None:
        _dll.native_set_causal_policy_mode(ctypes.c_int(mode))

    def set_search_gating_mode(self, mode: int) -> None:
        _dll.native_set_search_gating_mode(ctypes.c_int(mode))

    def set_neural_budget_us(self, budget_us: int) -> None:
        _dll.native_set_neural_budget_us(ctypes.c_uint64(budget_us))

    def set_deterministic_seed(self, seed: int) -> None:
        _dll.native_set_deterministic_seed(ctypes.c_uint64(seed))

    def reset_root_telemetry(self) -> None:
        _dll.native_reset_root_telemetry()

    def get_root_telemetry(self, depth: int) -> dict:
        import json
        ptr = _dll.native_get_root_telemetry_json(ctypes.c_int(depth))
        if not ptr:
            return {}
        try:
            return json.loads(ptr.decode("utf-8"))
        except Exception:
            return {}

    def get_ordering_telemetry(self) -> dict:
        arr = (ctypes.c_uint64 * 12)()
        _dll.native_get_ordering_telemetry(arr)
        total_cutoffs = int(arr[0])
        move1_cutoffs = int(arr[2])
        return {
            "total_cutoffs": total_cutoffs,
            "sum_cutoff_index": int(arr[1]),
            "cutoff_move_1": move1_cutoffs,
            "cutoff_move_2": int(arr[3]),
            "cutoff_move_3": int(arr[4]),
            "cutoff_move_4plus": int(arr[5]),
            "cutoff_tt": int(arr[6]),
            "cutoff_killer1": int(arr[7]),
            "cutoff_killer2": int(arr[8]),
            "cutoff_history": int(arr[9]),
            "cutoff_captures": int(arr[10]),
            "cutoff_quiet": int(arr[11]),
            "first_move_cutoff_rate": (move1_cutoffs / total_cutoffs) if total_cutoffs > 0 else 0.0,
        }

    def reset_ordering_telemetry(self) -> None:
        _dll.native_reset_ordering_telemetry()




