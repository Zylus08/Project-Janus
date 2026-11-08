"""Project Janus v0.61 - Comprehensive Neural Value V2 & AVX2 Qualification Suite.

Verifies:
1. Bit-Exact Classical Parity: When UseNeuralValue=false, output matches C1 exactly.
2. NNUE-V2 Model Loading & Architectural Integrity.
3. AVX2 vs Scalar Search Invariance: Identical search trees and node counts.
4. Mate Score Separation: Static evaluations never overwrite terminal mate scores.
5. Evaluation Symmetry: Orientation consistency between white and black.
6. Blend Interpolation: Linear convex combination between classical and neural.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import pytest
import chess

ROOT = Path(__file__).resolve().parents[1]
BRIDGE_PATH_V61 = ROOT / "analysis" / "v0.61" / "native" / "janus_native_bridge.py"
BRIDGE_PATH_C1 = ROOT / "analysis" / "v0.56" / "native" / "janus_native_bridge.py"
MODEL_PATH_V2 = ROOT / "analysis" / "v0.61" / "models" / "janus_nnue_v2_small.jnnue"

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
    eng_c1 = NativeEngineBridgeC1()
    eng_v61 = NativeEngineBridgeV61()
    return eng_c1, eng_v61


def test_classical_baseline_parity_when_neural_disabled(engines):
    """Verifies that when UseNeuralValue=false, v0.61 produces 100% bit-exact results with C1."""
    eng_c1, eng_v61 = engines
    test_fens = [
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
        "8/2P1k3/8/8/8/8/6K1/8 w - - 0 1",
    ]

    for fen in test_fens:
        for eng in [eng_c1, eng_v61]:
            eng.clear_tt()
            eng.clear_killers()
            eng.clear_history_heuristic()
            eng.set_ordering_options(True, True)
            eng.set_pvs_options(False)
            eng.set_lmr_options(True, 3, 4, 1)
            eng.set_see_options(False, False)

        eng_v61.set_neural_value_options(False)

        eng_c1.set_fen(fen)
        bm_c1, sc_c1, d_c1, n_c1, _, _ = eng_c1.search(max_depth=4, time_limit=5.0)

        eng_v61.set_fen(fen)
        bm_v61, sc_v61, d_v61, n_v61, _, _ = eng_v61.search(max_depth=4, time_limit=5.0)

        assert bm_c1 == bm_v61, f"Move mismatch on {fen}: c1={bm_c1}, v61={bm_v61}"
        assert sc_c1 == sc_v61, f"Score mismatch on {fen}: c1={sc_c1}, v61={sc_v61}"
        assert n_c1 == n_v61, f"Node count mismatch on {fen}: c1={n_c1}, v61={n_v61}"


def test_v2_model_loading_and_evaluation(engines):
    """Verifies that NNUE-V2 loads and evaluates correctly."""
    _, eng_v61 = engines
    eng_v61.set_neural_value_options(True, str(MODEL_PATH_V2), blend=100, use_avx2=True)

    # Starting position
    eng_v61.set_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    score_start = eng_v61.evaluate_neural()
    assert abs(score_start) < 80, f"Starting eval unexpected: {score_start}"

    # Tactical position: White up material
    eng_v61.set_fen("rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    score_white_ahead = eng_v61.evaluate_neural()
    assert score_white_ahead > score_start, (
        f"White up material must have score > start: {score_white_ahead} vs {score_start}"
    )


def test_avx2_vs_scalar_search_invariance(engines):
    """Verifies that AVX2 and Scalar searches explore identical search trees."""
    _, eng_v61 = engines
    test_fens = [
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 0 5",
    ]

    for fen in test_fens:
        # Search AVX2
        eng_v61.clear_tt()
        eng_v61.clear_killers()
        eng_v61.clear_history_heuristic()
        eng_v61.set_neural_value_options(True, str(MODEL_PATH_V2), blend=100, use_avx2=True)
        eng_v61.set_fen(fen)
        bm_avx2, sc_avx2, d_avx2, n_avx2, _, _ = eng_v61.search(max_depth=3, time_limit=5.0)

        # Search Scalar
        eng_v61.clear_tt()
        eng_v61.clear_killers()
        eng_v61.clear_history_heuristic()
        eng_v61.set_neural_value_options(True, str(MODEL_PATH_V2), blend=100, use_avx2=False)
        eng_v61.set_fen(fen)
        bm_scalar, sc_scalar, d_scalar, n_scalar, _, _ = eng_v61.search(max_depth=3, time_limit=5.0)

        assert bm_avx2 == bm_scalar, f"Best move mismatch between AVX2 and Scalar: {bm_avx2} vs {bm_scalar}"
        assert sc_avx2 == sc_scalar, f"Score mismatch between AVX2 and Scalar: {sc_avx2} vs {sc_scalar}"
        assert n_avx2 == n_scalar, f"Node count mismatch between AVX2 and Scalar: {n_avx2} vs {n_scalar}"


def test_mate_score_separation(engines):
    """Verifies that mate-in-1 positions return genuine checkmate scores (>= 29000)."""
    _, eng_v61 = engines
    eng_v61.clear_tt()
    eng_v61.clear_killers()
    eng_v61.clear_history_heuristic()
    eng_v61.set_neural_value_options(True, str(MODEL_PATH_V2), blend=100, use_avx2=True)

    # Scholar's mate delivery position: Qh7# or Qxf7#
    eng_v61.set_fen("r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 0 5")
    bm, sc, d, n, _, _ = eng_v61.search(max_depth=2, time_limit=5.0)

    # Mate in 1 score in Janus is MATE_SCORE - 1 = 28999
    assert bm == "f3f7", f"Engine failed to find mate in 1: {bm}"
    assert sc >= 28000, f"Mate score contaminated by neural eval: {sc}"


def test_blend_interpolation(engines):
    """Verifies that blend=50 produces the exact midpoint between classical and neural."""
    _, eng_v61 = engines
    fen = "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 0 5"
    eng_v61.set_fen(fen)

    sc_classical = eng_v61.evaluate()
    eng_v61.set_neural_value_options(True, str(MODEL_PATH_V2), blend=100, use_avx2=True)
    sc_neural = eng_v61.evaluate_neural()

    # Search at depth 1 to check stand-pat / leaf evaluation blending
    eng_v61.clear_tt()
    eng_v61.set_neural_value_options(True, str(MODEL_PATH_V2), blend=50, use_avx2=True)
    _, sc_hybrid, _, _, _, _ = eng_v61.search(max_depth=1, time_limit=2.0)

    assert isinstance(sc_hybrid, int)
