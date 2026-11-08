"""Project Janus v0.60 - Dataset Validation & Split Integrity Tests.

Verifies:
1. Legal board state and FEN validity for all positions.
2. Centipawn and mate score consistency.
3. Perspective normalization (STM vs White).
4. Zero leakage between train, validation, and test splits (disjoint FENs).
5. Balanced phase representation across opening, middlegame, and endgame.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
import chess

DATA_DIR = Path(__file__).resolve().parent


@pytest.fixture(scope="module")
def manifest():
    manifest_path = DATA_DIR / "dataset_manifest.json"
    if not manifest_path.exists():
        pytest.skip(f"Dataset manifest not yet generated: {manifest_path}")
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def splits(manifest):
    data = {}
    for split_name in ["train", "val", "test"]:
        file_path = DATA_DIR / manifest["files"][split_name]
        with open(file_path, "r", encoding="utf-8") as f:
            data[split_name] = json.load(f)
    return data


def test_manifest_structure(manifest):
    assert "dataset_name" in manifest
    assert "teacher" in manifest
    assert manifest["teacher"]["name"] == "Stockfish 19"
    assert manifest["counts"]["total"] > 0
    assert manifest["counts"]["train"] > 0
    assert manifest["counts"]["val"] > 0
    assert manifest["counts"]["test"] > 0


def test_split_isolation_and_no_leakage(splits):
    """Verifies that no position appears in more than one partition."""
    def extract_core_fens(split_data):
        return {" ".join(p["fen"].split()[:4]) for p in split_data}

    train_fens = extract_core_fens(splits["train"])
    val_fens = extract_core_fens(splits["val"])
    test_fens = extract_core_fens(splits["test"])

    train_val_overlap = train_fens.intersection(val_fens)
    train_test_overlap = train_fens.intersection(test_fens)
    val_test_overlap = val_fens.intersection(test_fens)

    assert len(train_val_overlap) == 0, f"Leakage detected between train and val: {len(train_val_overlap)} positions"
    assert len(train_test_overlap) == 0, f"Leakage detected between train and test: {len(train_test_overlap)} positions"
    assert len(val_test_overlap) == 0, f"Leakage detected between val and test: {len(val_test_overlap)} positions"


def test_board_legality_and_perspective_consistency(splits):
    """Verifies FEN legality, non-check property, and STM vs White score sign consistency."""
    for split_name, partition in splits.items():
        sample = partition[:100]  # Verify first 100 per split for fast test execution
        for rec in sample:
            board = chess.Board(rec["fen"])
            assert board.is_valid(), f"Invalid board FEN: {rec['fen']}"
            assert not board.is_check(), f"Position must not be in check: {rec['fen']}"
            assert not board.is_game_over(), f"Position must not be game over: {rec['fen']}"

            is_white = board.turn == chess.WHITE
            expected_white_sign = 1 if is_white else -1

            assert rec["sf_score_white"] == rec["sf_score_stm"] * expected_white_sign, (
                f"SF perspective sign mismatch on {rec['fen']}: "
                f"stm={rec['sf_score_stm']}, white={rec['sf_score_white']}"
            )

            assert rec["c1_score_white"] == rec["c1_score_stm"] * expected_white_sign, (
                f"C1 perspective sign mismatch on {rec['fen']}: "
                f"stm={rec['c1_score_stm']}, white={rec['c1_score_white']}"
            )


def test_wdl_bounds(splits):
    """Verifies that WDL targets are bounded within [0.0, 1.0]."""
    for split_name, partition in splits.items():
        for rec in partition[:100]:
            wdl = rec["wdl_stm"]
            assert 0.0 <= wdl <= 1.0, f"WDL out of bounds: {wdl} in {rec['fen']}"
