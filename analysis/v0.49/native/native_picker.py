"""Project Janus v0.49 - Native Move Picker Bridge & Fallback (Candidate N1).

Provides ctypes-based bindings to analysis/v0.49/native/move_picker.dll
with automatic detection, version checking, and pure-Python fallback.
"""

import ctypes
import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

DLL_PATH = Path(__file__).parent / "move_picker.dll"

_dll = None
native_available = False
native_version = 0

try:
    if DLL_PATH.exists():
        _dll = ctypes.CDLL(str(DLL_PATH))
        _dll.native_move_picker_version.restype = ctypes.c_int
        native_version = _dll.native_move_picker_version()

        # Define function signatures
        _dll.native_select_next_best.argtypes = [
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_int,
        ]
        _dll.native_select_next_best.restype = ctypes.c_int

        _dll.native_stable_partial_sort.argtypes = [
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_int),
        ]
        _dll.native_stable_partial_sort.restype = ctypes.c_int

        native_available = True
except Exception as e:
    native_available = False
    _dll = None


def is_native_available() -> bool:
    """Return whether the compiled native move picker DLL is active."""
    return native_available


def py_stable_partial_sort(scores: List[int], k: int) -> List[int]:
    """Pure-Python reference fallback for stable partial sort."""
    n = len(scores)
    indices = list(range(n))
    # Python list.sort with reverse=True is stable
    indices.sort(key=lambda idx: scores[idx], reverse=True)
    return indices[:k]


def native_stable_partial_sort(scores: List[int], k: int) -> List[int]:
    """Stably sorts and returns top-k indices using native C DLL or Python fallback.

    Guarantees exact stability: if scores[i] == scores[j] with i < j,
    i strictly precedes j in the returned ordering.
    """
    n = len(scores)
    if n <= 1:
        return list(range(n))
    if k <= 0:
        return []
    if k > n:
        k = n

    if not native_available or _dll is None:
        return py_stable_partial_sort(scores, k)

    # Marshall arrays
    c_scores = (ctypes.c_int * n)(*scores)
    c_out = (ctypes.c_int * n)()

    ret = _dll.native_stable_partial_sort(c_scores, n, k, c_out)
    if ret != 0:
        return py_stable_partial_sort(scores, k)

    return [c_out[i] for i in range(k)]


def native_select_next_best(scores: List[int], selected: List[bool]) -> int:
    """Selects the index of the highest-scoring unselected element."""
    n = len(scores)
    if not native_available or _dll is None:
        best_idx = -1
        best_score = -2147483647
        for i in range(n):
            if not selected[i] and scores[i] > best_score:
                best_score = scores[i]
                best_idx = i
        return best_idx

    c_scores = (ctypes.c_int * n)(*scores)
    c_mask = (ctypes.c_uint8 * n)(*selected)

    return _dll.native_select_next_best(c_scores, c_mask, n)

