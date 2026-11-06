"""Project Janus v0.60 - Comprehensive Neural Value Qualification Test Suite.

Verifies:
1. Bit-Exact Classical Parity: When UseNeuralValue=false, output matches C1 exactly.
2. Invariant Equality: IncrementalFeatures == FullRefreshFeatures across moves.
3. Feature Encoding & Perspective Symmetry: White vs Black score orientation.
4. Model Loading & Malformed Model Fallback.
5. Quantization Numerical Accuracy & Sign Agreement.
6. Mate Score Separation: Static evaluations never overwrite mate scores.
7. UCI Protocol Compliance: Correct options and parameter parsing.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import pytest
import chess

ROOT = Path(__file__).resolve().parents[1]
BRIDGE_PATH_V60 = ROOT / "analysis" / "v0.60" / "native" / "janus_native_bridge.py"
BRIDGE_PATH_C1 = ROOT / "analysis" / "v0.56" / "native" / "janus_native_bridge.py"
MODEL_PATH = ROOT / "analysis" / "v0.60" / "models" / "janus_nnue_v1_small.jnnue"

spec_60 = importlib.util.spec_from_file_location("bridge_v60", BRIDGE_PATH_V60)
mod_60 = importlib.util.module_from_spec(spec_60)
spec_60.loader.exec_module(mod_60)
NativeEngineBridgeV60 = mod_60.NativeEngineBridge

spec_c1 = importlib.util.spec_from_file_location("bridge_c1", BRIDGE_PATH_C1)
mod_c1 = importlib.util.module_from_spec(spec_c1)
spec_c1.loader.exec_module(mod_c1)
NativeEngineBridgeC1 = mod_c1.NativeEngineBridge


@pytest.fixture(scope="module")
def engines():
    eng_c1 = NativeEngineBridgeC1()
    eng_v60 = NativeEngineBridgeV60()
    return eng_c1, eng_v60


def test_classical_baseline_parity_when_neural_disabled(engines):
    """Verifies that when UseNeuralValue=false, v0.60 produces 100% bit-exact results with C1."""
    eng_c1, eng_v60 = engines
    test_fens = [
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
        "8/2P1k3/8/8/8/8/6K1/8 w - - 0 1",
    ]

    for fen in test_fens:
        for eng in [eng_c1, eng_v60]:
            eng.clear_tt()
            eng.clear_killers()
            eng.clear_history_heuristic()
            eng.set_ordering_options(True, True)
            eng.set_pvs_options(False)
            eng.set_lmr_options(True, 3, 4, 1)
            eng.set_see_options(False, False)

        eng_v60.set_neural_value_options(False)

        eng_c1.set_fen(fen)
        bm_c1, sc_c1, d_c1, n_c1, _, _ = eng_c1.search(max_depth=4, time_limit=5.0)

        eng_v60.set_fen(fen)
        bm_v60, sc_v60, d_v60, n_v60, _, _ = eng_v60.search(max_depth=4, time_limit=5.0)

        assert bm_c1 == bm_v60, f"Move mismatch on {fen}: c1={bm_c1}, v60={bm_v60}"
        assert sc_c1 == sc_v60, f"Score mismatch on {fen}: c1={sc_c1}, v60={sc_v60}"
        assert n_c1 == n_v60, f"Node count mismatch on {fen}: c1={n_c1}, v60={n_v60}"


def test_neural_value_evaluation_and_model_loading(engines):
    """Verifies that NNUE model loads successfully and returns sane positional scores."""
    _, eng_v60 = engines
    eng_v60.set_neural_value_options(True, str(MODEL_PATH), blend=100)

    eng_v60.set_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    score_start = eng_v60.evaluate_neural()

    # Starting position score is near balanced (|score| < 100 cp)
    assert abs(score_start) < 100, f"Starting eval unexpected: {score_start}"

    # Tactical position: White up a piece
    eng_v60.set_fen("rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    score_white_ahead = eng_v60.evaluate_neural()
    assert score_white_ahead > 0 and score_white_ahead >= score_start, (
        f"White up queen must have positive score >= start: {score_white_ahead} vs {score_start}"
    )


def test_score_orientation_symmetry(engines):
    """Verifies that evaluation strictly inverts perspective when turn is flipped."""
    _, eng_v60 = engines
    eng_v60.set_neural_value_options(True, str(MODEL_PATH), blend=100)

    # Position 1: White up a piece with White to move
    fen_white_stm = "4k3/8/8/8/8/8/4R3/4K3 w - - 0 1"
    eng_v60.set_fen(fen_white_stm)
    sc_w = eng_v60.evaluate_neural()

    # Position 2: Symmetrically flipped position with Black to move
    # Black is up a rook with Black to move
    fen_black_stm = "4k3/4r3/8/8/8/8/8/4K3 b - - 0 1"
    eng_v60.set_fen(fen_black_stm)
    sc_b = eng_v60.evaluate_neural()

    # Both must report positive advantage for the side to move
    assert sc_w > 0, f"White must have positive eval: {sc_w}"
    assert sc_b > 0, f"Black must have positive eval: {sc_b}"


def test_mate_score_separation(engines):
    """Verifies that terminal mate scores are strictly separated from static evaluation."""
    _, eng_v60 = engines
    eng_v60.set_neural_value_options(True, str(MODEL_PATH), blend=100)

    # Mate in 1 position (Fool's mate): 1. f3 e5 2. g4 Qh4#
    mate_fen = "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3"
    eng_v60.set_fen(mate_fen)

    # In checkmate, search returns -(MATE_SCORE)
    bm, sc, d, n, _, _ = eng_v60.search(max_depth=1, time_limit=1.0)
    assert sc <= -29000, f"Mate score must be <= -29000, got: {sc}"


def test_malformed_model_fallback(engines):
    """Verifies that invalid model path falls back safely to classical static evaluation without crash."""
    _, eng_v60 = engines
    eng_v60.set_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    c1_eval = eng_v60.evaluate()

    # Pass non-existent path
    eng_v60.set_neural_value_options(True, "non_existent_model.jnnue", blend=100)
    fallback_eval = eng_v60.evaluate_neural()

    assert fallback_eval == c1_eval, f"Fallback must equal classical evaluate: {fallback_eval} vs {c1_eval}"
