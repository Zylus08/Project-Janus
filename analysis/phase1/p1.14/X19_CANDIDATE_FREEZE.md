# Milestone P1.14: Candidate X19 Freeze Protocol & Verification
**Candidate Identifier:** Janus Classical X19  
**Architectural Foundation:** Option C — Staged MovePicker Reform with SEE Capture Partitioning  
**Frozen Binary Location:** `analysis/phase1/p1.14/control/janus_classical_x19.exe`  
**Date of Freeze:** 2026-11-13  
**Auditor:** Principal Computer Chess Engine Architect & Independent Statistical Auditor  
**Status:** FROZEN & SEALED FOR QUALIFICATION

---

## 1. Candidate Specification

Candidate X19 implements a targeted interior move-ordering reform designed to eliminate search tree bloat caused by searching losing tactical captures ahead of high-probability quiet refutations (Killers and Countermoves).

### Two Dedicated Tracks:
1. **Janus Classical X19-S (Single-Thread 1T Track):**
   - **Baseline Foundation:** Janus Classical X7 (`b34e342`)
   - **Evaluation Engine:** Combined Classical Eval `E5` (Preserves pure classical material, mobility, king safety, and endgame scaling)
   - **Move Ordering Pipeline:**
     - Stage 0: Transposition Table Best Move
     - Stage 1: Good Captures ($\text{SEE} \ge 0$, MVV-LVA scored)
     - Stage 2: Killer Moves (Primary & Secondary killers)
     - Stage 3: Countermove Heuristic (Butterfly countermove table `M2`)
     - Stage 4: Quiet Moves (Butterfly History + 2-ply Continuation History `H3`)
     - Stage 5: Bad Captures ($\text{SEE} < 0$, MVV-LVA scored)
   - **Selectivity:** Conservative PVS + Logarithmic LMR `L3` (History-LMR disabled to eliminate toxic reduction volatility)
   - **Late Move Pruning:** Disabled (`L0`) to maintain search depth reliability on 1T.

2. **Janus Classical X19-P (Four-Thread 4T Track):**
   - **Baseline Foundation:** Janus Classical X12 (`78ca3d5`)
   - **Evaluation Engine:** Enhanced Classical Evaluation `E10` + 64K entry Pawn Hash Table
   - **Move Ordering Pipeline:** Staged MovePicker Reform identical to X19-S
   - **Multithreading:** Shared lock-free Transposition Table + Dynamic Time Management
   - **Selectivity:** Safe Late Move Pruning (`L1`, max depth 4) + RFP Margin 90 cp.

---

## 2. Compilation and Environment Manifest

The candidate was compiled using the official release toolchain:
- **Compiler:** Microsoft (R) C/C++ Optimizing Compiler Version 19.43.34809 for x64
- **Flags:** `/O2 /Oi /Ot /GL /std:c++17 /EHsc /DNDEBUG`
- **Linker Flags:** `/LTCG /OPT:REF /OPT:ICF`
- **Target OS:** Windows 10/11 x86_64

---

## 3. Cryptographic Hashes (SHA-256)

| Component | Path | SHA-256 Checksum |
|---|---|---|
| **C++ Source** | `engine/classical_x/janus_classical_x.cpp` | `67356E7D1E78ADC131913D2483AD084394C758A82DBEBC79EDA451211FF12085` |
| **X19 Frozen Binary** | `analysis/phase1/p1.14/control/janus_classical_x19.exe` | `CBB7785A47E5F9EC64C51C20B8387DE3EFE782F42BDFCEA38008F6450E534629` |
| **X7 1T Baseline** | `analysis/phase1/p1.3/control/janus_classical_x7.exe` | `86392A2F4BD4182A4D7DC21E32940BD7939F6816794D5E1AB02F4082431CA28B` |
| **X12 4T Baseline** | `analysis/phase1/p1.7/control/janus_classical_x12.exe` | `00B4F5FEDEA02A392A1AF9713A96512E5199A0E3AE55C295AD1C7CFFF1B47059` |
| **Stockfish 4** | `E:\ChessXML\tools\stockfish_4\stockfish_4.exe` | `1128CAB83386063359947F04155A2210C966080E71176DD385D8BDC3B6C32674` |
| **Stockfish 11** | `E:\ChessXML\tools\stockfish_11\stockfish_11.exe` | `B004C03BD71BB84E8BC1832C580E72A7E883F121E1834EA6DA2802D1575E8048` |
| **Stockfish 19** | `E:\ChessXML\tools\stockfish\stockfish.exe` | `45BC8E4969147DB9C2EB533810637994619BFF0EACC81CCFD9854394901BCBD0` |

---

## 4. Verification Protocol

The frozen binary was subjected to functional qualification prior to freeze:
- `test_p114_correctness_suite.py`: Passed 10/10 MovePicker property positions, 4/4 startpos perft depths, and UCI protocol negotiation.
- Resulting status: **CERTIFIED FROZEN FOR COMPETITIVE TOURNAMENT EXECUTION**.

