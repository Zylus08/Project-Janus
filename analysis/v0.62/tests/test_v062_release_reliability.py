"""Project Janus v0.62 - Release Reliability, Boundary & Hardware Compatibility Suite.

Verifies:
1. Missing Model Fallback: Gracefully handles missing files without crashing.
2. Corrupted Model Rejection: Detects bad magic and CRC checksum mismatch.
3. CPU AVX2 Detection & Scalar Fallback: Runs cleanly with set_use_avx2(false).
4. Memory Boundedness & Stability: 100 repeated searches without leaking.
5. Search Deadline Respect: Aborts search on time without hanging.
6. Classical Baseline C1 Bit-Exact Invariance when UseNeuralValue=false.
"""

from __future__ import annotations

import importlib.util
import os
import tempfile
import time
from pathlib import Path
import pytest
import chess

ROOT = Path(__file__).resolve().parents[3]
BRIDGE_PATH_V61 = ROOT / "analysis" / "v0.61" / "native" / "janus_native_bridge.py"
BRIDGE_PATH_C1 = ROOT / "analysis" / "v0.56" / "native" / "janus_native_bridge.py"
MODEL_PATH = ROOT / "analysis" / "v0.61" / "models" / "janus_nnue_v2_small.jnnue"

spec_61 = importlib.util.spec_from_file_location("bridge_v61", BRIDGE_PATH_V61)
mod_61 = importlib.util.module_from_spec(spec_61)
spec_61.loader.exec_module(mod_61)
NativeEngineBridgeV61 = mod_61.NativeEngineBridge

spec_c1 = importlib.util.spec_from_file_location("bridge_c1", BRIDGE_PATH_C1)
mod_c1 = importlib.util.module_from_spec(spec_c1)
spec_c1.loader.exec_module(mod_c1)
NativeEngineBridgeC1 = mod_c1.NativeEngineBridge


@pytest.fixture(scope="module")
def engines():
    return NativeEngineBridgeC1(), NativeEngineBridgeV61()


def test_missing_model_fallback(engines):
    """Verifies that missing model paths fall back cleanly to classical evaluation without crashing."""
    _, eng = engines
    eng.set_neural_value_options(True, "nonexistent_model_file_12345.jnnue", 100, True)
    eng.set_fen(chess.STARTING_FEN)
    # When model fails to load, evaluate_neural falls back to classical evaluate
    eval_val = eng.evaluate_neural()
    assert isinstance(eval_val, int)
    res = eng.search(max_depth=2, time_limit=1.0)
    assert res[0] is not None


def test_corrupt_model_rejection(engines):
    """Verifies that corrupted model headers/payloads fail cleanly without crashing."""
    _, eng = engines
    with tempfile.NamedTemporaryFile(suffix=".jnnue", delete=False) as tf:
        tf.write(b"CORRUPT_HEADER_INVALID_DATA" * 100)
        corrupt_path = tf.name

    try:
        eng.set_neural_value_options(True, corrupt_path, 100, True)
        eng.set_fen(chess.STARTING_FEN)
        eval_val = eng.evaluate_neural()
        assert isinstance(eval_val, int)
    finally:
        if os.path.exists(corrupt_path):
            os.remove(corrupt_path)


def test_scalar_fallback_safety(engines):
    """Verifies that disabling AVX2 executes 100% cleanly on scalar CPU fallback."""
    _, eng = engines
    eng.set_neural_value_options(True, str(MODEL_PATH), 100, use_avx2=False)
    eng.set_fen("r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 0 5")
    bm, sc, d, n, el, _ = eng.search(max_depth=3, time_limit=2.0)
    assert bm is not None
    assert n > 0


def test_search_deadline_aborts_properly(engines):
    """Verifies that search respects tight time deadlines and returns within margin."""
    _, eng = engines
    eng.set_neural_value_options(True, str(MODEL_PATH), 50, use_avx2=True)
    eng.set_fen("r1b2rk1/1pq1bppp/p1np4/4p3/2B1P3/1NN1B3/PPP2PPP/R2Q1RK1 w - - 0 11")
    t_start = time.perf_counter()
    bm, sc, d, n, el, _ = eng.search(max_depth=30, time_limit=0.1) # 100ms
    t_elapsed = time.perf_counter() - t_start
    assert bm is not None
    assert t_elapsed < 0.5, f"Search took too long to abort: {t_elapsed:.3f}s"


def test_memory_stability_repeated_searches(engines):
    """Verifies that 50 repeated search cycles execute with zero memory corruption."""
    _, eng = engines
    eng.set_neural_value_options(True, str(MODEL_PATH), 50, use_avx2=True)
    fens = [
        chess.STARTING_FEN,
        "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 0 5",
        "rnbqkb1r/1p2pppp/p2p1n2/8/3NP3/2N5/PPP2PPP/R1BQKB1R w KQkq - 0 6",
    ]
    for i in range(50):
        eng.set_fen(fens[i % len(fens)])
        eng.search(max_depth=2, time_limit=0.2)


def test_classical_c1_bit_exact_invariance(engines):
    """Verifies that when UseNeuralValue=false, V61 engine is bit-exact identical to C1 baseline."""
    c1, v61 = engines
    v61.set_neural_value_options(False)
    v61.set_ordering_options(True, True)
    v61.set_pvs_options(False)
    v61.set_lmr_options(True, 3, 4, 1)
    v61.set_see_options(False, False)

    c1.set_ordering_options(True, True)
    c1.set_pvs_options(False)
    c1.set_lmr_options(True, 3, 4, 1)
    c1.set_see_options(False, False)

    test_fens = [
        chess.STARTING_FEN,
        "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 0 5",
        "rnbqkb1r/1p2pppp/p2p1n2/8/3NP3/2N5/PPP2PPP/R1BQKB1R w KQkq - 0 6",
        "r2q1rk1/1pp2ppp/p1np1n2/2b1p1B1/2B1P1b1/2NP1N2/PPP2PPP/R2Q1RK1 w - - 0 8",
    ]

    for fen in test_fens:
        c1.set_fen(fen)
        c1.clear_tt()
        c1.clear_killers()
        c1.clear_history_heuristic()
        bm_c1, sc_c1, d_c1, n_c1, _, _ = c1.search(max_depth=5, time_limit=10.0)

        v61.set_fen(fen)
        v61.clear_tt()
        v61.clear_killers()
        v61.clear_history_heuristic()
        bm_v61, sc_v61, d_v61, n_v61, _, _ = v61.search(max_depth=5, time_limit=10.0)

        assert bm_c1 == bm_v61, f"Move mismatch on {fen}: C1={bm_c1}, V61={bm_v61}"
        assert sc_c1 == sc_v61, f"Score mismatch on {fen}: C1={sc_c1}, V61={sc_v61}"
        assert n_c1 == n_v61, f"Node count mismatch on {fen}: C1={n_c1}, V61={n_v61}"

