# Project Janus — Phase 2, Milestone P2.3
## Phase 4: Search-Grounded Dataset Pilot Specification & Audit

**Author:** Principal Computer Chess Researcher, Dataset Integrity Auditor & Deep Learning Engineer  
**Milestone:** P2.3 — King-Relative NNUE, Search-Grounded Neural Training, Incremental CPU Inference & Independent Playing-Strength Qualification  
**Date:** 2026-11-17  
**Subject:** 5,052-Position Pilot Dataset Extraction, Teacher Evaluation Signals & Clean Split Verification  

---

### 1. Dataset Generation Methodology

Using the clean-room self-play generation engine (`generate_search_grounded_pilot.py`), a 5,052-position pilot dataset was generated using `Janus Classical R1.0` as both self-play engine and teacher evaluator:
- **Teacher Configuration:** Depth 5 full alpha-beta search with classical evaluation.
- **Teacher Executable:** `janus_classical_r1.exe` (SHA-256: `7312B2B73CD9D40F108EE1B5F3903632A2A7805B19BC73082A796922DE66029B`).
- **Openings Source:** `independent_openings_v056.json` (open games, closed games, flank openings, gambits).
- **Total Games Played:** 72 complete self-play games.
- **Total Positions Extracted:** 5,052 quality-controlled positions spanning opening, tactical middlegames, and endgames.

---

### 2. Schema Specification & Record Metadata

Each record in the dataset is structured as a self-contained JSON line with the following fields:

```json
{
  "fen": "r1bqk2r/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3",
  "game_id": "PILOT_G_0001",
  "opening_id": "OP_001",
  "ply": 6,
  "stm": "b",
  "teacher_engine": "Janus_Classical_R1",
  "teacher_exe_sha256": "7312B2B73CD9D40F108EE1B5F3903632A2A7805B19BC73082A796922DE66029B",
  "teacher_depth": 5,
  "teacher_score_perspective": "STM",
  "teacher_score_cp": -5,
  "teacher_mate": null,
  "position_checksum": "a8f3b2c1d0e4f5a6",
  "game_result": "1/2-1/2",
  "target_outcome": 0.5,
  "target_score_prob": 0.493751,
  "lambda_target": 0.495001,
  "partition": "train"
}
```

---

### 3. Clean Partitioning & Leakage Verification

To strictly prevent data leakage between training, validation, and test sets, partitioning was performed **exclusively by unique Game ID**:

```
========================================================================================================================
DATASET PARTITION AUDIT & LEAKAGE VERIFICATION
========================================================================================================================
Partition Split | Games Count | Position Records | Unique FENs Count | Cross-Partition Leakage
----------------+-------------+------------------+-------------------+--------------------------------------------------
Train (80%)     | 57 games    | 4,002 positions  | 4,002 unique FENs | 0 FENs (100.0% clean isolation)
Validation (10%)| 7 games     | 533 positions    | 533 unique FENs   | 0 FENs (100.0% clean isolation)
Test (10%)      | 8 games     | 517 positions    | 517 unique FENs   | 0 FENs (100.0% clean isolation)
----------------+-------------+------------------+-------------------+--------------------------------------------------
TOTAL PILOT     | 72 games    | 5,052 positions  | 5,052 unique FENs | 0 FEN LEAKAGE VERIFIED
========================================================================================================================
```

- **Cryptographic Hashes:**
  - `pilot_train.jsonl`: Verified and logged in `raw/pilot_data_manifest.json`.
  - `pilot_val.jsonl`: Verified and logged.
  - `pilot_test.jsonl`: Verified and logged.

Phase 4 is complete. Milestone P2.3 now advances to **Phase 6 & Phase 7: Calibrated Lambda-Loss Ablation Study & Pilot Training**.
