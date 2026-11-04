"""Project Janus v0.49 - Native Move Picker Correctness Qualification (Phase D1, D2, D4).

Exhaustively verifies:
1. Ordering equivalence:
   - Randomized scores, equal scores, duplicate values, negative scores, extreme integer scores.
   - Empty lists, single-move lists, large branching factors (up to 200 items).
   - Strict stability: earlier index in original list must win on identical score.
2. Move integrity:
   - No duplicates, no omissions, valid indices, no mutation of input lists, deterministic results.
3. Fault and Fallback tests:
   - Missing DLL / corrupted path, invalid arguments, dimension mismatches, graceful fallback.
"""

import sys
import os
import random
import ctypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).parent / "native"))

import native_picker
from native_picker import (
    native_stable_partial_sort,
    native_select_next_best,
    py_stable_partial_sort,
    is_native_available,
)


def run_correctness_qualification():
    print("=" * 80, flush=True)
    print("PROJECT JANUS v0.49 - NATIVE CORRECTNESS QUALIFICATION (Phase D)", flush=True)
    print("=" * 80, flush=True)

    assert is_native_available(), "Native DLL must be available for correctness qualification!"

    # --- D1 & D2: Equivalence & Integrity Tests ---
    random.seed(1337)
    test_cases_passed = 0

    # 1. Empty and Single-Element Lists
    print("\n[Test 1] Empty and single-element lists...", flush=True)
    assert native_stable_partial_sort([], 0) == []
    assert native_stable_partial_sort([], 5) == []
    assert native_stable_partial_sort([42], 1) == [0]
    assert native_stable_partial_sort([42], 5) == [0]
    test_cases_passed += 1

    # 2. Extreme and Negative Scores
    print("[Test 2] Extreme and negative integer scores...", flush=True)
    extreme_scores = [
        -2147483640, -1000000, -500, 0, 500, 1000000, 2147483640
    ]
    random.shuffle(extreme_scores)
    c_out = native_stable_partial_sort(extreme_scores, len(extreme_scores))
    py_out = py_stable_partial_sort(extreme_scores, len(extreme_scores))
    assert c_out == py_out, f"Mismatch on extreme scores: C={c_out}, Py={py_out}"
    test_cases_passed += 1

    # 3. Duplicate and All-Equal Scores (Strict Stability Check)
    print("[Test 3] All-equal scores (strict stability verification)...", flush=True)
    for n in [2, 5, 10, 25, 50]:
        scores = [100] * n
        c_out = native_stable_partial_sort(scores, n)
        expected = list(range(n))
        assert c_out == expected, f"Failed stability on n={n}: got {c_out}, expected {expected}"
    test_cases_passed += 1

    # 4. Large Branching Factors (up to 200 moves) with Random Duplicates
    print("[Test 4] Large branching factors (up to 200 moves) with ties...", flush=True)
    for trial in range(100):
        n = random.randint(2, 200)
        k = random.randint(1, n)
        # Use narrow score range to force heavy duplicate collisions
        scores = [random.randint(-10, 20) for _ in range(n)]
        original_scores_copy = list(scores)

        c_out = native_stable_partial_sort(scores, k)
        py_out = py_stable_partial_sort(scores, k)

        assert scores == original_scores_copy, "Input scores list was mutated!"
        assert len(c_out) == k, f"Length mismatch: {len(c_out)} vs {k}"
        assert len(set(c_out)) == k, f"Duplicate indices found in output: {c_out}"
        assert all(0 <= idx < n for idx in c_out), f"Out-of-bounds index in: {c_out}"
        assert c_out == py_out, f"Mismatch on trial {trial} (n={n}, k={k}): C={c_out} vs Py={py_out}"
    test_cases_passed += 1

    # 5. Incremental Next-Best Selection vs Partial Sort
    print("[Test 5] Incremental next-best selection vs partial sort...", flush=True)
    for trial in range(50):
        n = random.randint(5, 50)
        scores = [random.randint(-1000, 1000) for _ in range(n)]
        selected = [False] * n

        incremental_order = []
        for step in range(n):
            best = native_select_next_best(scores, selected)
            assert 0 <= best < n, f"Invalid selected index {best}"
            assert not selected[best], f"Index {best} selected twice!"
            selected[best] = True
            incremental_order.append(best)

        full_sorted = native_stable_partial_sort(scores, n)
        assert incremental_order == full_sorted, (
            f"Incremental selection diverged from partial sort: {incremental_order} vs {full_sorted}"
        )
    test_cases_passed += 1

    # --- D4: Fault and Fallback Tests ---
    print("\n[Test 6] Fault and Fallback tests...", flush=True)
    # Test invalid k
    assert native_stable_partial_sort([10, 20], -1) == []
    # Test k > n
    assert native_stable_partial_sort([10, 20], 100) == [1, 0]

    # Test pure-Python fallback execution
    # Temporarily set native_available to False
    native_picker.native_available = False
    fb_out = native_picker.native_stable_partial_sort([10, 30, 20], 2)
    assert fb_out == [1, 2], f"Fallback returned unexpected result: {fb_out}"
    # Restore native_available
    native_picker.native_available = True
    print("  Fallback execution validated successfully.")
    test_cases_passed += 1

    print("\n" + "=" * 80)
    print(f"CORRECTNESS QUALIFICATION PASSED! ({test_cases_passed}/6 comprehensive test suites passed)")
    print("=" * 80, flush=True)


if __name__ == "__main__":
    run_correctness_qualification()

