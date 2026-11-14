# Milestone P1.19 Phase 2: Classical Backward-Pawn Definition & Correctness Audit

**Date:** November 14, 2026  
**Status:** Certified & Verified (12/12 Scenarios Passed)  
**Branch:** `phase1/classical-janus`  
**Target:** Candidate X24 Evaluation Subsystem (`engine/classical_x/janus_classical_x.cpp`)  
**Raw Test Artifact:** `analysis/phase1/p1.19/raw/backward_pawn_audit_results.json`

---

## 1. Executive Summary

Milestone P1.19 Phase 2 conducted an exhaustive mathematical, algorithmic, and bitboard-level audit of the handcrafted classical backward-pawn evaluation term implemented for Candidate X24. Backward pawns represent an essential classical computer chess evaluation concept, identifying rearmost pawns whose forward advance is physically controlled by enemy pawns and which cannot be defended by friendly pawns from behind or alongside.

The implementation was audited across **12 distinct, adversarial pawn-structure scenarios**, testing edge files, doubled files, pawn chains, dynamic push transitions, exchanges, multiple compounding weaknesses, and color anti-symmetry. 

**Result: 12 out of 12 scenarios (100.0%) passed all theoretical expectations without exception.**

---

## 2. Formal Mathematical Formulation

In the Janus classical architecture, a friendly pawn of color $c \in \{\text{WHITE}, \text{BLACK}\}$ on file $f \in [0, 7]$ is evaluated for backwardness during pawn structure evaluation:

### Definition Invariants
1. **Rearmost File Position:**
   The pawn must be the base (rearmost) pawn on file $f$:
   $$s = \text{base\_sq}(f) = \begin{cases} \text{bitscan\_forward}(P_c \cap \text{FILE\_MASKS}[f]) & \text{if } c = \text{WHITE} \\ \text{bitscan\_reverse}(P_c \cap \text{FILE\_MASKS}[f]) & \text{if } c = \text{BLACK} \end{cases}$$
   $$\text{base\_r} = \lfloor s / 8 \rfloor$$

2. **Controlled Stop Square:**
   The forward stop square $s_{\text{stop}} = s + 8$ (White) or $s - 8$ (Black) must be attacked by at least one enemy pawn:
   $$(\text{pawn\_attacks}[c][s_{\text{stop}}] \cap P_{1-c}) \neq \emptyset$$
   *(Note: By attack reciprocity, $\text{pawn\_attacks}[c][s_{\text{stop}}]$ contains the exact squares from which an enemy pawn of color $1-c$ attacks $s_{\text{stop}}$.)*

3. **Absence of Friendly Rear/Lateral Support:**
   No friendly pawn exists on adjacent files $f \pm 1$ at or behind $\text{base\_r}$:
   $$\forall p \in (P_c \cap (\text{FILE\_MASKS}[f-1] \cup \text{FILE\_MASKS}[f+1])), \quad \text{rank}(p) > \text{base\_r} \quad (\text{White})$$
   $$\forall p \in (P_c \cap (\text{FILE\_MASKS}[f-1] \cup \text{FILE\_MASKS}[f+1])), \quad \text{rank}(p) < \text{base\_r} \quad (\text{Black})$$

### Handcrafted Evaluation Penalty
When all three conditions hold simultaneously:
$$\Delta \text{mg}[c] = -10 \, \text{cp}, \quad \Delta \text{eg}[c] = -15 \, \text{cp}$$

---

## 3. 12-Scenario Correctness Matrix

| ID | Structural Scenario | Test FEN | Expected | Observed | Status |
| :---: | :--- | :--- | :---: | :---: | :---: |
| **1** | **True Backward Pawn** (Black d6 vs White e4/f2) | `8/8/3p4/2p1p3/4P3/8/5P2/4K2k w - - 0 1` | $+15\text{ cp}$ | $+15\text{ cp}$ | **PASS** |
| **2** | **Supported Backward-Looking Pawn** (c7 behind d6) | `8/2p5/3p4/2p1p3/4P3/8/5P2/4K2k w - - 0 1` | $0\text{ cp}$ | $0\text{ cp}$ | **PASS** |
| **3** | **Isolated Pawn Interaction** (Isolated + Backward) | `8/8/3p4/2p5/8/3P4/8/4K2k w - - 0 1` | $-15\text{ cp}$ | $-15\text{ cp}$ | **PASS** |
| **4** | **Doubled Pawns on File** (Rearmost d3 penalized) | `8/8/3p4/2p5/3P4/3P4/5P2/4K2k w - - 0 1` | $-15\text{ cp}$ | $-15\text{ cp}$ | **PASS** |
| **5** | **Blocked Backward Pawn** (Piece on stop square) | `8/8/3p4/2pnp3/4P3/8/5P2/4K2k w - - 0 1` | $+15\text{ cp}$ | $+15\text{ cp}$ | **PASS** |
| **6** | **Candidate Passed Pawn** (Uninhibited stop square) | `8/8/8/4p3/3P4/8/8/4K2k w - - 0 1` | $0\text{ cp}$ | $0\text{ cp}$ | **PASS** |
| **7** | **Advance Removing Backwardness** (d3 $\to$ d4 push) | Transition test | $+35\text{ cp}$ | $+35\text{ cp}$ | **PASS** |
| **8** | **Exchange Creating Backwardness** (Supporter lost) | Transition test | $+135\text{ cp}$ | $+135\text{ cp}$ | **PASS** |
| **9** | **Color Anti-Symmetry** (White d2 vs Black d7) | Mirrored FEN pair | $\Delta_W = \Delta_B$ | $-15 = -15$ | **PASS** |
| **10** | **Multiple Backward Pawns** (b3 & d3 compounding) | `8/8/3p4/2p5/8/1P1P4/8/4K2k w - - 0 1` | $-30\text{ cp}$ | $-30\text{ cp}$ | **PASS** |
| **11** | **Edge-File Backward Pawn** (a-file single flank) | `8/8/2p5/1p6/8/P7/8/4K2k w - - 0 1` | $-15\text{ cp}$ | $-15\text{ cp}$ | **PASS** |
| **12** | **Pawn Chain Base Immunity** (c2 in c2-d3-e4 chain) | `8/8/8/8/4P3/3P4/2P5/4K2k w - - 0 1` | $0\text{ cp}$ | $0\text{ cp}$ | **PASS** |

---

## 4. Key Engineering Discoveries During Audit

1. **Flank File Distance Invariance:**
   A pawn on the b-file (e.g. b7) cannot support a pawn on the d-file (e.g. d6) because the files are non-adjacent ($|\Delta f| = 2$). The friendly adjacent mask properly rejected $b7$ and correctly demanded a supporter on $c7$ or $e7$.
2. **Mutual Backwardness Cancellation:**
   In symmetrical endgames where both sides hold isolated or unsupported pawns facing enemy pawns (e.g. White e4 vs Black d6 with no wing supporters), both White and Black receive $-10\text{ mg} / -15\text{ eg}$ penalties, resulting in an exact zero net evaluation delta ($(-15) - (-15) = 0$). To isolate the true marginal impact of an individual backward pawn, control positions must establish friendly supporter pawns on one side.
3. **Pawn Hash Cache Invalidation:**
   When dynamically switching `UCI_BackwardPawns` during benchmarking or UCI play, the 64K thread-local pawn hash table (`g_pawn_table`) must be immediately invalidated via `clear_pawn_table()` to prevent reading stale pawn evaluations computed under the alternate mode. This hook was verified and permanently integrated into `native_set_backward_pawns_mode()`.

---

## 5. Certification & Sign-off

The handcrafted C++17 backward-pawn detection module demonstrates complete structural correctness, color symmetry, and bitboard efficiency. It is certified for full integration into **Janus Classical Candidate X24**.
