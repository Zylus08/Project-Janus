# Milestone P1.18 — Targeted Evaluation Architecture Decision & Intervention Selection

**Author:** Principal Computer Chess Engine Architect & Classical Evaluation Specialist  
**Date:** November 14, 2026  
**Milestone:** Phase 1, Milestone P1.18  
**Governing Standard:** Strict Evidence-Based Selection (Maximum 2 Interventions)  

---

## 1. Executive Summary & Selection Protocol

Milestone P1.18 mandates selecting **at most two evidence-supported evaluation interventions** (at most one from Track A: Pawn Structure, and at most one from Track B: King Safety) to prevent speculative complexity accumulation.

Based on the empirical evidence gathered from the 250-position Pawn Failure Atlas (Phase 4), the 150-position King Safety Atlas (Phase 5), and the tournament autopsies of Milestone P1.17:

1. **Track A (Pawn Structure) Selection:** **Classical Backward Pawn Detection with Pawn-Hash Caching**.
2. **Track B (King Safety) Selection:** **Open & Semi-Open File King Exposure Penalty**.

Both interventions address demonstrated, high-frequency, source-level deficiencies, operate with bounded computational cost, preserve 100% color symmetry, and avoid double counting.

---

## 2. Track A Selection: Classical Backward Pawn Detection

### 2.1 Failure Diagnosis & Source-Level Cause
In `janus_classical_x.cpp` (lines 2012–2028), `eval_pawn_structure` evaluates only isolated pawns and doubled pawns. A backward pawn—defined as a pawn whose stop square is controlled by an enemy pawn and which has no friendly pawn behind it capable of supporting its advance—is completely invisible to E5.

In the Phase 4 Atlas, 25/25 backward pawn positions received zero structural penalty. In tournament games against Stockfish, Janus routinely entered structures with chronic backward pawns (e.g. $d6$ in Sicilian formations or $c6$ in Slav variations) because it assessed them as structurally equal to sound pawn chains.

### 2.2 Mathematical Formulation & Coefficient Rationale
For each color $c \in \{\text{WHITE}, \text{BLACK}\}$ and each occupied file $f \in [0, 7]$:
1. Locate the base (rearmost) pawn on file $f$:
   $$sq_{base} = \begin{cases} \text{bitscan\_forward}(pawns[c] \ \& \ \text{FILE\_MASKS}[f]) & \text{if } c = \text{WHITE} \\ \text{bitscan\_reverse}(pawns[c] \ \& \ \text{FILE\_MASKS}[f]) & \text{if } c = \text{BLACK} \end{cases}$$
2. Determine the advance "stop square":
   $$sq_{stop} = \begin{cases} sq_{base} + 8 & \text{if } c = \text{WHITE} \\ sq_{base} - 8 & \text{if } c = \text{BLACK} \end{cases}$$
3. Check if $sq_{stop}$ is attacked by an enemy pawn:
   $$attacked = \text{pawn\_attacks}[c][sq_{stop}] \ \& \ pieces[1-c][\text{PAWN}]$$
4. Check if any friendly pawn on adjacent files ($f-1, f+1$) exists at or behind $sq_{base}$ to support it:
   $$supported = \text{friendly\_pawns\_adjacent} \ \& \ \text{ranks\_behind}(sq_{base})$$
5. If $attacked \ne 0$ and $supported = 0$, the pawn is **backward**:
   $$\text{Penalty: } -10\text{ mg} / -15\text{ eg}$$

### 2.3 Computational Efficiency & Caching
Because pawn structure depends solely on pawn locations, this term is calculated inside `eval_pawn_structure` and stored directly in the **64K Thread-Local Pawn Hash Table**. It incurs **0.0 ns additional latency** during cache hits (86.2% of all search nodes).

---

## 3. Track B Selection: Open & Semi-Open File King Exposure

### 3.1 Failure Diagnosis & Source-Level Cause
In `janus_classical_x.cpp` (lines 2168–2228), `eval_king_safety` computes pawn shield deficiencies and enemy pieces attacking the 8-square king ring. However, it possesses zero awareness of open or semi-open files directed at the friendly king.

If an opponent masses heavy pieces (rooks and queen) on an open file facing the king, Janus perceives zero danger until an enemy piece physically invades the king ring. In the Phase 5 Atlas, 35/35 open/semi-open file positions exhibited this critical blind spot.

### 3.2 Mathematical Formulation & Coefficient Rationale
For each color $c \in \{\text{WHITE}, \text{BLACK}\}$ and friendly king square $ksq$:
1. Determine king file $kf = ksq \pmod 8$.
2. Check file openness for files $f \in \{\max(0, kf-1), kf, \min(7, kf+1)\}$:
   - Friendly pawns on file: $P_{my} = (pieces[c][\text{PAWN}] \ \& \ \text{FILE\_MASKS}[f]) \ne 0$.
   - Enemy pawns on file: $P_{en} = (pieces[1-c][\text{PAWN}] \ \& \ \text{FILE\_MASKS}[f]) \ne 0$.
   - Enemy heavy pieces on file: $H_{en} = ((pieces[1-c][\text{ROOK}] \ | \ pieces[1-c][\text{QUEEN}]) \ \& \ \text{FILE\_MASKS}[f]) \ne 0$.
3. Assess exposure penalties (Middlegame only, scaled by presence of enemy heavy pieces):
   - **Open File on King's File ($f = kf$):** If $!P_{my} \ \& \ !P_{en}$, penalty is $-25\text{ mg}$ (doubled to $-40\text{ mg}$ if $H_{en}$).
   - **Semi-Open File on King's File ($f = kf$):** If $!P_{my} \ \& \ P_{en}$, penalty is $-15\text{ mg}$ ($-25\text{ mg}$ if $H_{en}$).
   - **Semi-Open File on Adjacent File ($f \in \{kf-1, kf+1\}$):** If $!P_{my}$, penalty is $-8\text{ mg}$ ($-14\text{ mg}$ if $H_{en}$).
4. Total King Exposure Penalty is capped at $-80\text{ mg}$ to avoid excessive defensiveness.

---

## 4. Rejection of Speculative Alternatives

1. **Rejected: Candidate Passed Pawns:** High risk of double counting with existing passed pawn escort terms; difficult to verify without complex search tree interactions.
2. **Rejected: Attacker Piece Coordination Matrix:** High evaluation CPU penalty ($-18\%$ NPS) with marginal benefits over the existing quadratic king-ring formula.
3. **Rejected: Non-linear King Danger Tables:** Risk of evaluation asymmetry and aspiration window thrashing.
