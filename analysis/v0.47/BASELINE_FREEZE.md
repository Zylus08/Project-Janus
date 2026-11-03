# Baseline Freeze & Reference Provenance (v0.47 Gate A)

## 1. Repository Provenance & Environment

- **Repository Path:** `E:\ChessXML\project-janus`
- **Branch:** `v0.3-benchmark-harness`
- **Baseline Parent Commit:** `9858aacad01692c0119c58ec8c740f66cb75527c` (verified exact match to v0.46 final commit)
- **Working Tree State:** Clean (0 uncommitted or untracked changes at start of v0.47)
- **Python Version:** 3.13.2 AMD64 (`MSC v.1942 64 bit`)
- **Host OS & CPU:** Windows 11 (Build 26200), Intel64 Family 6 Model 154 Stepping 3 (GenuineIntel)
- **Core Dependencies:** `chess == 1.11.2`

## 2. Stockfish Reference Engine Verification & Reconciliation

### Investigation of Prior Milestones:
- In v0.39, v0.40, v0.41, v0.42, and v0.43, match experiments utilized Stockfish 19 configured at Elo 1320.
- In v0.45 and v0.46, position-level fixed-depth reference evaluations were labeled "Stockfish 14" in several prose headers because evaluation was performed to depth 14 (`depth=14`), but the underlying binary executed by the python harness has always been **Stockfish 19**.
- **Executable Path:** `E:\ChessXML\tools\stockfish\stockfish.exe`
- **Engine Banner:** `Stockfish 19 by the Stockfish developers`
- **Verified SHA-256 Digest:**
  `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0` (matches expected baseline digest exactly).

## 3. Baseline Test Suite Qualification

- **Command:** `$env:PYTHONPATH='E:\ChessXML\project-janus;E:\ChessXML\project-janus\src'; & 'E:\ChessXML\project-janus\.venv\Scripts\python.exe' -m unittest discover -s 'tests' -p "test_*.py"`
- **Total Tests Discovered:** 466
- **Result:** **466 passed, 0 failed, 0 errors, 0 skipped** (313.575s runtime)
- **Status:** PASS (Gate A complete)

## 4. Frozen Baseline Configuration (K0 Reference)

- **Move Ordering Pipeline:** Eager full legal move generation (`list(board.legal_moves)`), full list scoring and sorting (`moves.sort(key=...)`).
- **Move Scoring Tiers:**
  1. TT Move: $10,000,000$
  2. Captures: $1,000,000 + \text{MVV\_LVA}$
  3. Promotions: $800,000 + \text{promo}$
  4. Killer Moves: $700,000$ (primary), $600,000$ (secondary)
  5. Countermoves: $550,000$
  6. Quiet History: $0\text{--}500,000$ (butterfly table)
  7. Unranked Quiets: $0$
- **RFP Pruning:** `enable_rfp = False` (production default)
- **Diagnostic Corpus:** 37 positions (`analysis/v0.47/corpus/diagnostic_corpus.json`)
  - **Corpus SHA-256:** `9f72ea66729cb190163eb6cd4b9dc4309dd25ca384d56533911449f6985ccb36`

