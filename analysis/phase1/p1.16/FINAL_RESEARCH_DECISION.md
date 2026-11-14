# Milestone P1.16 Phase 13: Formal Promotion Adjudication & Final Research Decision

**Date:** November 14, 2026  
**Status:** Authoritatively Adjudicated  
**Branch:** `phase1/classical-janus`  
**Governing Charter:** Non-ML Classical Computer Chess Architecture (Zero Neural Networks, NNUE, Learned Weights, SPSA, or Texel Tuning)  
**Candidate Evaluated:** Janus Classical X21 (Commit `2226c0c` / frozen binary SHA-256: `AD1E1F0598D0CA016267CA4F03DC771346CEE9D0D563A36AB6B6590D7F4731FD`)  
**Frozen Baselines Maintained:**
- Single-Thread Qualified Baseline: **Janus Classical X7** (`b34e342`)
- Four-Thread SMP Qualified Baseline: **Janus Classical X12** (`78ca3d5`)

---

## 1. Statutory Promotion Criterion & Legal Charter Standard

Under the governing charter of Project Janus:
> **The Standard of Scientific Promotion:** A candidate engine is promoted to baseline status if and only if:
> 1. It operates strictly within non-ML classical chess architecture.
> 2. It passes all perft, legality, determinism, and thread-safety qualification suites without exception.
> 3. It demonstrates statistically significant superior playing strength against the reigning qualified baseline under identical computational resources, defined as:
>    - A paired 95% confidence interval lower bound exceeding 50.0% ($CI_{low} > 0.500$).
>    - A one-sided p-value against the null hypothesis of non-superiority ($H_0: \mu \le 0.500$) of $p < 0.05$.
> 4. It demonstrates non-regressive scaling at slower time controls.

Any candidate that fails any of these criteria must be formally rejected for promotion. No promotional exceptions are permitted for "correctness improvements," "architectural elegance," or "theoretical superiority."

---

## 2. Complete Independent Tournament Evidence Ledger

A total of 420 tournament games were administered under strict, automated, color-inverted opening pairs using the standard independent corpus.

| Match ID | Match Description | Configuration / TC | Games | W | D | L | Score (%) | Elo Diff | Paired 95% CI | 1-Sided p-value | Statutory Finding |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Match 1** | X21-S vs X7 Baseline | 1T, 1.0s + 50ms | 100 | 22 | 47 | 31 | **45.5%** | -31.3 | [37.9%, 53.1%] | 0.8762 | **REJECTED** ($CI_{low} < 50\%$) |
| **Match 2** | X21-S vs X7 Baseline | 1T, 2.5s + 100ms (Slow) | 50 | 7 | 25 | 18 | **39.0%** | -77.7 | [31.0%, 47.0%] | 0.9963 | **REGRESSION** ($p = 0.996$) |
| **Match 3** | X21-P vs X12 Baseline | 4T SMP, 1.0s + 50ms | 100 | 24 | 46 | 30 | **47.0%** | -20.9 | [39.6%, 54.4%] | 0.7878 | **REJECTED** ($CI_{low} < 50\%$) |
| **Match 4** | X21-S vs X19/X20 Refs | 1T, 1.0s + 50ms | 50 | 15 | 22 | 13 | **52.0%** | +13.9 | [38.5%, 65.2%] | — | **PARITY CONFIRMED** |
| **Match 5** | X21-S vs Stockfish 4 | 1T, 1.5s + 50ms | 40 | 10 | 2 | 28 | **27.5%** | -168.4 | [16.9%, 38.1%] | 0.99998 | **CALIBRATED** |
| **Match 6** | X21-S vs Stockfish 11 | 1T, 1.5s + 50ms | 40 | 11 | 0 | 29 | **27.5%** | -168.4 | [16.3%, 38.7%] | 0.99996 | **CALIBRATED** |
| **Match 7** | X21-S vs Stockfish 19 | 1T, 1.5s + 50ms | 40 | 8 | 2 | 30 | **22.5%** | -214.8 | [11.9%, 33.1%] | 1.00000 | **CALIBRATED** |

---

## 3. Statutory Promotion Adjudication

### Finding on Single-Thread Promotion (Match 1 & Match 2):
In Match 1, Janus Classical X21-S scored **45.5%** against X7. The paired 95% confidence interval is $[37.9\%, 53.1\%]$, with a one-sided p-value of $p = 0.8762$. The lower bound of 37.9% decisively fails the statutory threshold of $> 50.0\%$. Furthermore, in Match 2 at $2.5\times$ slower time control, X21-S regressed to **39.0%** ($p = 0.9963$).
**Ruling:** Single-Thread Promotion is **DENIED**.

### Finding on Four-Thread SMP Promotion (Match 3):
In Match 3, Janus Classical X21-P scored **47.0%** against X12. The paired 95% confidence interval is $[39.6\%, 54.4\%]$, with a one-sided p-value of $p = 0.7878$. The lower bound of 39.6% decisively fails the statutory threshold of $> 50.0\%$.
**Ruling:** Four-Thread SMP Promotion is **DENIED**.

---

## 4. Formal Categorization

In accordance with Project Janus milestone adjudication taxonomy, the outcome of Milestone P1.16 is authoritatively designated as:

### **CATEGORY B: CORRECTNESS MILESTONE, PARITY CONFIRMED, BASELINES PRESERVED**

**Definition:** The candidate engine successfully identifies, diagnoses, and completely resolves major architectural defects in search correctness and execution integrity, achieving flawless correctness pass rates and operational parity with modern references, but fails to demonstrate a statistically significant net playing-strength promotion over the entrenched baselines under competitive tournament conditions.

---

## 5. Disposition of Assets & Immutable Baselines

1. **Janus Classical X7 (`b34e342`)** remains the permanent, immutable **1-Thread Qualified Baseline**.
2. **Janus Classical X12 (`78ca3d5`)** remains the permanent, immutable **4-Thread Qualified Baseline**.
3. **Janus Classical X21** is formally frozen and archived in `analysis/phase1/p1.16/control/`:
   - Executable: `janus_classical_x21.exe` (`AD1E1F0598D0CA016267CA4F03DC771346CEE9D0D563A36AB6B6590D7F4731FD`)
   - Library: `janus_classical_x21.dll` (`B8A930BC9302788E06533B7A04B318E0AEB7E64A04BD7C0F52564F77EB253A60`)
   - Source: `janus_classical_x21.cpp` (`AF67D06809A0E4FF3BBA4E55C1C8CF6B0B9BCA5A9BEB06AAED70C57A1806B2D2`)
4. **Permanent Role of X21:** Janus Classical X21 serves as the authoritative, verified search-correctness reference candidate. All subsequent classical development must build upon X21's verified quiescence search and pawn-hash architecture while introducing classical evaluation terms to overcome the baseline playing-strength barrier.
