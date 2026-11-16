#!/usr/bin/env python3
"""
audit_dataset_provenance.py
Phase 3: Dataset Provenance, Split Leakage & Distribution Audit.
Audits the P2.1 training/val/test datasets in analysis/phase2/p2.1/data/
"""

import sys
import json
import hashlib
from pathlib import Path
from collections import Counter
import chess

ROOT = Path("E:/ChessXML/project-janus-phase1")
DATA_DIR = ROOT / "analysis" / "phase2" / "p2.1" / "data"
OPENINGS_FILE = ROOT / "analysis" / "v0.56" / "corpus" / "independent_openings_v056.json"

def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def audit_dataset():
    print("=" * 80)
    print("PHASE 3: DATASET PROVENANCE, LEAKAGE & DISTRIBUTION AUDIT")
    print("=" * 80)

    split_files = {
        "train": DATA_DIR / "janus_nnue_train.jsonl",
        "val": DATA_DIR / "janus_nnue_val.jsonl",
        "test": DATA_DIR / "janus_nnue_test.jsonl"
    }

    records_by_split = {}
    fens_by_split = {}
    games_by_split = {}
    
    for split_name, path in split_files.items():
        if not path.exists():
            print(f"ERROR: Missing file {path}")
            return
        
        recs = []
        fens = set()
        game_ids = set()
        
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    recs.append(r)
                    fens.add(r["fen"])
                    game_ids.add(r["game_id"])
                    
        records_by_split[split_name] = recs
        fens_by_split[split_name] = fens
        games_by_split[split_name] = game_ids
        print(f"Loaded {split_name:5s}: {len(recs)} records | {len(fens)} unique FENs | {len(game_ids)} games | SHA256: {sha256_file(path)[:16]}...")

    # 1. Split sizes & total sum
    total_recs = sum(len(r) for r in records_by_split.values())
    expected_train = 40736
    expected_val = 5127
    expected_test = 5115
    total_expected = 50978
    
    # 2. Leakage across splits (FEN overlap)
    train_val_overlap = len(fens_by_split["train"] & fens_by_split["val"])
    train_test_overlap = len(fens_by_split["train"] & fens_by_split["test"])
    val_test_overlap = len(fens_by_split["val"] & fens_by_split["test"])
    
    # 3. Game ID overlap
    train_val_game_overlap = len(games_by_split["train"] & games_by_split["val"])
    train_test_game_overlap = len(games_by_split["train"] & games_by_split["test"])
    val_test_game_overlap = len(games_by_split["val"] & games_by_split["test"])

    # 4. Tournament Openings Contamination
    # Check if any training position matches any opening position from independent_openings_v056.json
    opening_fens = set()
    if OPENINGS_FILE.exists():
        with open(OPENINGS_FILE, "r", encoding="utf-8") as f:
            openings_data = json.load(f)
        for item in openings_data:
            opening_fens.add(item.get("fen", ""))

    opening_train_overlap = len(opening_fens & fens_by_split["train"])
    opening_test_overlap = len(opening_fens & fens_by_split["test"])

    # 5. Dataset Statistical Distribution across Train
    train_recs = records_by_split["train"]
    stm_counter = Counter(r["stm"] for r in train_recs)
    target_counter = Counter(r["target_res"] for r in train_recs)
    source_counter = Counter(r["source"] for r in train_recs)
    ply_values = [r["ply"] for r in train_recs]
    mean_ply = sum(ply_values) / len(ply_values)

    # Check for in-check states in training positions
    check_count = 0
    piece_count_dist = Counter()
    for r in train_recs[:5000]: # Sample 5k positions for detailed speed
        b = chess.Board(r["fen"])
        if b.is_check():
            check_count += 1
        num_pieces = len(b.piece_map())
        piece_count_dist[num_pieces] += 1
    sample_check_pct = (check_count / 5000) * 100.0

    provenance_report = {
        "record_counts": {
            "train": len(records_by_split["train"]),
            "val": len(records_by_split["val"]),
            "test": len(records_by_split["test"]),
            "total": total_recs,
            "matches_expected": (total_recs == total_expected and len(records_by_split["train"]) == expected_train)
        },
        "leakage": {
            "fen_overlap_train_val": train_val_overlap,
            "fen_overlap_train_test": train_test_overlap,
            "fen_overlap_val_test": val_test_overlap,
            "game_overlap_train_val": train_val_game_overlap,
            "game_overlap_train_test": train_test_game_overlap,
            "game_overlap_val_test": val_test_game_overlap,
            "is_completely_leakage_free": (train_val_overlap == 0 and train_test_overlap == 0 and val_test_overlap == 0 and
                                          train_val_game_overlap == 0 and train_test_game_overlap == 0 and val_test_game_overlap == 0)
        },
        "tournament_contamination": {
            "opening_corpus_size": len(opening_fens),
            "openings_in_training_set": opening_train_overlap,
            "openings_in_test_set": opening_test_overlap,
            "contamination_detected": (opening_train_overlap > 0)
        },
        "training_distribution": {
            "side_to_move": dict(stm_counter),
            "target_scores": dict(target_counter),
            "source_files": dict(source_counter),
            "mean_ply": round(mean_ply, 1),
            "sample_check_pct": round(sample_check_pct, 2),
            "sample_piece_count_distribution": dict(sorted(piece_count_dist.items()))
        }
    }

    out_file = ROOT / "analysis" / "phase2" / "p2.2" / "raw" / "dataset_provenance_audit.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(provenance_report, f, indent=2)

    print("\n--- Provenance Summary ---")
    print(f"Total Unique Positions: {total_recs} (Train: {len(records_by_split['train'])}, Val: {len(records_by_split['val'])}, Test: {len(records_by_split['test'])})")
    print(f"FEN Overlap Across Splits: {train_val_overlap + train_test_overlap + val_test_overlap} (Clean: {provenance_report['leakage']['is_completely_leakage_free']})")
    print(f"Game Overlap Across Splits: {train_val_game_overlap + train_test_game_overlap + val_test_game_overlap}")
    print(f"Tournament Openings in Train Set: {opening_train_overlap}")
    print(f"Side to move distribution in Train: White={stm_counter['w']} ({stm_counter['w']/len(train_recs)*100:.1f}%), Black={stm_counter['b']} ({stm_counter['b']/len(train_recs)*100:.1f}%)")
    print(f"Target distribution in Train: {dict(target_counter)}")
    print(f"Sample In-Check Percentage: {sample_check_pct:.1f}%")
    print(f"Report written to: {out_file}")

if __name__ == "__main__":
    audit_dataset()
