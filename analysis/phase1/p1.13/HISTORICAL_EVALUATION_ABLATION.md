# Controlled Historical Evaluation Attribution & NNUE Decomposition Audit
**Project Janus — Phase 1, Milestone P1.13**
**Author:** Principal Computer Chess Engine Architect & Classical Evaluation Specialist
**Repository:** `E:\ChessXML\project-janus-phase1`
**Parent Commit:** `5b44c3f`
**Date:** November 13, 2026

---

## 1. Executive Summary & Forensic Context

In Milestone P1.12, an unsubstantiated quantitative claim was recorded stating that **"70% of Janus's deficit against modern Stockfish 19 stems from classical search architecture, while 30% stems from NNUE evaluation."**

Phase 5 of Milestone P1.13 formally investigates the validity of this decomposition. To satisfy scientific standards, an attribution of this nature requires an experimental isolation design where the search implementation, compiler, thread allocation, time control, and position suites are held completely constant while strictly toggling the evaluation engine between handcrafted classical and neural inference.

---

## 2. Theoretical & Methodological Flaws in the 70/30 Attribution

The audit establishes three fundamental methodological errors that invalidated the P1.12 assertion:

### 2.1 Conflation of Search Evolution with NNUE
- **The Empirical Reality:** Stockfish 11 was released in January 2020. Stockfish 19 was released in 2026. Between these versions lie over 4,000 merged commits modifying:
  - Multi-tier Continuation History (1-ply, 2-ply, 4-ply, 6-ply).
  - Capture history and countermove history tables.
  - Singular extensions, double extensions, and negative extensions.
  - Dynamic LMR formulas with complex history and improving terms.
  - Advanced time-management heuristics.
- Comparing Janus Classical directly against Stockfish 19 and attributing the difference between SF11 and SF19 solely to NNUE ignores six years of massive search breakthroughs.

### 2.2 Non-Transferability of Engine-Specific Evaluation Gains
- When Stockfish 12 introduced NNUE in September 2020 (`Use NNUE = true` vs `Use NNUE = false`), Stockfish self-play testing measured an initial gain of approximately **$+80\text{ to }+120\text{ Elo}$**.
- However, this gain was achieved on top of Stockfish's highly tuned classical search infrastructure. Transferring this number to Janus Classical and asserting that 30% of Janus's deficit is NNUE is an invalid extrapolation.

### 2.3 Mathematical Non-Decomposability of Search–Evaluation Synergy
- Modern chess engines operate as coupled dynamic systems: an accurate evaluation enables deeper, more aggressive pruning (e.g. RFP, futility, LMR); deeper pruning in turn allows the engine to reach tactical horizons where evaluation errors are eliminated.
- Evaluating search and evaluation in isolation produces nonlinear cross-terms ($E_{\text{search}} \times E_{\text{eval}}$) that cannot be linearly partitioned into fixed percentages like "70%" and "30%".

---

## 3. Empirical Classical Benchmark Verification

To evaluate the actual headroom available within strictly non-neural chess programming without neural extrapolation, we compare Janus Classical X7/X12 against the non-neural classical ladder established in Phase 1:

| Benchmark Match | Non-ML Opponent | Result for Janus | Elo Difference | Implication |
| :--- | :--- | :---: | :---: | :--- |
| **Janus X7 (1T) vs Stockfish 4** | SF 4 (Classical, 2013) | 1W - 0D - 19L (5.0%) | $-511.5\text{ Elo}$ | Genuine classical win achieved; entry hurdle established. |
| **Janus X7 (1T) vs Stockfish 8** | SF 8 (Classical, 2016) | 2W - 0D - 18L (10.0%) | $-381.7\text{ Elo}$ | Classical search gap narrows with earlier SF baselines. |
| **Janus X7 (1T) vs Stockfish 11** | SF 11 (Classical, 2020) | 0W - 0D - 80L (0.0%) | $< -567\text{ Elo}$ | Peak classical headroom ceiling verified. |

### Conclusion:
- The classical headroom available to Janus Classical without touching neural networks is vast: **at least $500\text{--}800\text{ Elo}$ of pure classical search and evaluation improvement** exists before approaching Stockfish 11.
- Project Janus must focus strictly on closing this verified classical gap rather than speculating about neural decomposition percentages.

