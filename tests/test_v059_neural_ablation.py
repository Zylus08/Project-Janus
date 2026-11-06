"""Project Janus v0.59 - Regression and Invariant Test Suite.

Verifies:
1. Bit-Exact Classical Parity:
   - When causal_policy_mode=0, output matches Classical Baseline C1 exactly.
2. Invariance Theorem:
   - C1 (Trained), C2 (Random), and C3 (Shuffled) explore identical nodes at the root.
3. Telemetry JSON Protocol:
   - Root telemetry exports valid JSON with complete MoveOrderTelemetry records.
4. Latency Budget Throttling:
   - Budget constraints stop neural inference when the cap is reached.
"""

import json
import importlib.util
from pathlib import Path
import pytest
import chess

ROOT = Path(__file__).resolve().parents[1]
BRIDGE_PATH_V59 = ROOT / "analysis" / "v0.59" / "native" / "janus_native_bridge.py"
BRIDGE_PATH_V56 = ROOT / "analysis" / "v0.56" / "native" / "janus_native_bridge.py"

spec_59 = importlib.util.spec_from_file_location("bridge_v59_test", BRIDGE_PATH_V59)
mod_59 = importlib.util.module_from_spec(spec_59)
spec_59.loader.exec_module(mod_59)
NativeEngineBridgeV59 = mod_59.NativeEngineBridge

spec_56 = importlib.util.spec_from_file_location("bridge_v56_test", BRIDGE_PATH_V56)
mod_56 = importlib.util.module_from_spec(spec_56)
spec_56.loader.exec_module(mod_56)
NativeEngineBridgeV56 = mod_56.NativeEngineBridge


@pytest.fixture(scope="module")
def engines():
    return NativeEngineBridgeV56(), NativeEngineBridgeV59()


def test_classical_baseline_parity(engines):
    eng_c1, eng_v59 = engines
    test_fens = [
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
        "8/2P1k3/8/8/8/8/6K1/8 w - - 0 1",
    ]

    for fen in test_fens:
        for eng in [eng_c1, eng_v59]:
            eng.clear_tt()
            eng.clear_killers()
            eng.clear_history_heuristic()
            eng.set_ordering_options(True, True)
            eng.set_pvs_options(False)
            eng.set_lmr_options(True, 3, 4, 1)
            eng.set_see_options(False, False)

        eng_c1.set_fen(fen)
        bm_c1, sc_c1, d_c1, n_c1, _, _ = eng_c1.search(max_depth=4, time_limit=5.0)

        eng_v59.set_causal_policy_mode(0)
        eng_v59.set_fen(fen)
        bm_v59, sc_v59, d_v59, n_v59, _, _ = eng_v59.search(max_depth=4, time_limit=5.0)

        assert bm_c1 == bm_v59, f"Move mismatch on {fen}: c1={bm_c1}, v59={bm_v59}"
        assert sc_c1 == sc_v59, f"Score mismatch on {fen}: c1={sc_c1}, v59={sc_v59}"
        assert n_c1 == n_v59, f"Node count mismatch on {fen}: c1={n_c1}, v59={n_v59}"


def test_causal_invariance_theorem(engines):
    _, eng_v59 = engines
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    nodes_by_mode = {}
    for mode in [1, 2, 3]: # Trained, Random, Shuffled
        eng_v59.clear_tt()
        eng_v59.clear_killers()
        eng_v59.clear_history_heuristic()
        eng_v59.set_causal_policy_mode(mode)
        eng_v59.set_search_gating_mode(0) # Root gating
        eng_v59.set_deterministic_seed(42)
        eng_v59.set_neural_policy_options(True, max_ply=0, min_depth=4, score_weight=50000)
        eng_v59.set_fen(fen)
        bm, sc, d, n, _, _ = eng_v59.search(max_depth=4, time_limit=5.0)
        nodes_by_mode[mode] = n

    assert nodes_by_mode[1] == nodes_by_mode[2] == nodes_by_mode[3], (
        f"Invariance failed: Trained={nodes_by_mode[1]}, Random={nodes_by_mode[2]}, Shuffled={nodes_by_mode[3]}"
    )


def test_root_telemetry_json_export(engines):
    _, eng_v59 = engines
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    eng_v59.clear_tt()
    eng_v59.clear_killers()
    eng_v59.clear_history_heuristic()
    eng_v59.set_causal_policy_mode(1)
    eng_v59.set_search_gating_mode(0)
    eng_v59.set_neural_policy_options(True, max_ply=0, min_depth=4, score_weight=50000)
    eng_v59.set_fen(fen)
    eng_v59.search(max_depth=4, time_limit=5.0)

    telem = eng_v59.get_root_telemetry(4)
    assert isinstance(telem, dict)
    assert telem["depth"] == 4
    assert telem["root_move_count"] == 20
    assert "tt_move" in telem
    assert "eventual_pv_move" in telem
    assert "spearman_correlation" in telem
    assert len(telem["moves"]) == 20
    assert "uci" in telem["moves"][0]
    assert "classical_score" in telem["moves"][0]
    assert "neural_prob" in telem["moves"][0]


def test_budget_throttling(engines):
    _, eng_v59 = engines
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    eng_v59.clear_tt()
    eng_v59.clear_killers()
    eng_v59.clear_history_heuristic()
    eng_v59.reset_neural_telemetry()
    eng_v59.set_neural_policy_options(True, max_ply=2, min_depth=1, score_weight=50000)
    eng_v59.set_causal_policy_mode(1)
    eng_v59.set_search_gating_mode(1) # Internal nodes
    eng_v59.set_neural_budget_us(1) # Tiny 1 microsecond budget
    eng_v59.set_fen(fen)
    eng_v59.search(max_depth=4, time_limit=5.0)

    telem = eng_v59.get_neural_telemetry()
    # At most 1 evaluation permitted before budget cap terminates inference
    assert telem["evaluations"] <= 1
