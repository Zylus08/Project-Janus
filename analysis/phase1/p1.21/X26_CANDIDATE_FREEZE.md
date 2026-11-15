# Milestone P1.21: Candidate Freeze — Janus Classical X26

**Milestone:** Phase 1, Milestone P1.21 (Search–Evaluation Decoupling, Pruning Reliability & Classical Architecture Decision Gate)  
**Deliverable:** `analysis/phase1/p1.21/X26_CANDIDATE_FREEZE.md`  
**Phase:** Phase 12 — Candidate Freeze  
**Candidate Name:** Janus Classical X26  
**Candidate Tracks:**
- **Janus Classical X26-S:** Single-Thread Strength Candidate (1T)
- **Janus Classical X26-P:** Multi-Thread Parallel Strength Candidate (4T SMP)
**Parent Commit:** `c232730`  
**Freeze Timestamp:** 2026-11-15T19:10:00Z  
**Governing Intervention:** Option A (Verified Reverse Futility Pruning Correctness Repair)  

---

## 1. Frozen Artifacts & Cryptographic Verification

All binaries and associated source files have been sealed under cryptographic SHA-256 hashes in `analysis/phase1/p1.21/control/`:

| Artifact Description | Local File Path | Size (Bytes) | Cryptographic SHA-256 Checksum |
| :--- | :--- | :---: | :--- |
| **Frozen Executable** | `analysis/phase1/p1.21/control/janus_classical_x26.exe` | $1,616,384$ | `0C2338DB3643F06C1E61AEADFD7B01A0E87BE5C4975E595123163F712F00C380` |
| **Frozen Dynamic Library** | `analysis/phase1/p1.21/control/janus_classical_x26.dll` | $1,517,568$ | `4E4DC1F81AEBEC6B20E04D7605B5B765E3875269F28D11250EA9F3623A4236BC` |
| **Frozen C++17 Source** | `analysis/phase1/p1.21/control/janus_classical_x26.cpp` | $266,545$ | `C6EE178EEE406965A5DFF9C8103DF0BCBA8AFD326BA19186B4CD4A945C2C1412` |

---

## 2. Frozen Architectural Configuration

### 2.1 Evaluator Specifications
- **Evaluator Mode:** `g_eval_mode = 5` (E5 Classical Combined on 1T); `g_eval_mode = 10` (E10 Enhanced Classical on 4T).
- **Pawn Structure:** Classical pawn structure with Option B connected & supported passed pawn bonuses (`g_use_connected_pawns = 1`).
- **Ablated Terms:** Unstable backward pawn penalties (`g_use_backward_pawns = 0`) and king file exposure penalties (`g_use_king_file_exposure = 0`) are permanently disabled.
- **Pawn Hash Table:** 64K-entry thread-local pawn hash table active (`g_use_pawn_hash = true`).

### 2.2 Search & Pruning Specifications
- **Reverse Futility Pruning Contract (Option A Full Repair, Level B3):**
  - `g_use_reverse_futility = true`
  - Margin per depth: $120\text{ cp/ply}$ (1T); $90\text{ cp/ply}$ (4T).
  - **Repair 1 (Non-PV Guard):** RFP strictly forbidden at PV nodes ($\beta - \alpha > 1$).
  - **Repair 2 (TT Lower Storage):** On cutoff, records `TT_LOWER` bound with `depth` and `static_eval` to `g_tt` / `g_parallel_tt`.
  - **Repair 3 (TT Conflict Check):** RFP suppressed if existing TT entry proves position fails low (`flag == TT_UPPER` and `score < beta`).
  - **Repair 4 (Zugzwang Guard):** RFP suppressed when moving side possesses zero non-pawn material.
- **Null-Move Pruning:** $R = 3$, non-pawn material check active.
- **Move Ordering:** Staged move generator with killer moves, countermoves, and history heuristics ($82.5\%\text{–}97.2\%$ first-move cutoff rate).
- **Quiescence Search:** Mode Q1 (Corrected in-check evasions and checkmate detection).

---

## 3. Pre-Tournament Verification Sign-Off

Candidate X26 has successfully fulfilled all technical prerequisites:
1. Exact shallow minimax invariance: **VERIFIED (30/30 at D1..D3)**.
2. Perft correctness: **100% PASSED (12,477,883 nodes across 5 suites)**.
3. 15-case referee integrity suite: **15/15 PASSED**.
4. Controlled ablations: **Tactical discovery latency eliminated; root moves refined**.

Candidate X26 is officially sealed and cleared for **Phase 13: Independent Competitive Qualification**.
