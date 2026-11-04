# Project Janus v0.51.1 — Independent PGN Reconstruction Report

## 1. Audit Methodology & Program Design

The PGN reconstruction was executed independently using `python-chess` without importing any code, helper functions, or score calculation routines from the v0.51 match runner (`run_preregistered_match.py`).

**Primary Input:** `analysis/v0.51/pgn/n2_vs_k0_match.pgn`  
**Reference Openings:** `analysis/v0.51/corpus/openings_v051_100.json` (SHA-256: `2f929719ab8377e1682b3c37c6b93c762a8898bca9284aa3797db936391aca3b`)  
**Generated Artifacts:**
- [`analysis/v0.51.1/raw/independent_game_ledger.csv`](file:///e:/ChessXML/project-janus/analysis/v0.51.1/raw/independent_game_ledger.csv) (200 game records)
- [`analysis/v0.51.1/raw/independent_pair_ledger.csv`](file:///e:/ChessXML/project-janus/analysis/v0.51.1/raw/independent_pair_ledger.csv) (100 pair records)
- [`analysis/v0.51.1/raw/pgn_validation.json`](file:///e:/ChessXML/project-janus/analysis/v0.51.1/raw/pgn_validation.json)

---

## 2. Structural & Rule Verification

Every move of every game was replayed sequentially from its declared FEN starting position:

1. **Game Count Verification:** Exactly 200 games were parsed; zero missing or truncated records.
2. **Opening Suite Alignment:** Exactly 100 opening pairs. Each game's declared starting FEN matched the corresponding record in `openings_v051_100.json` with 100.0% set identity.
3. **Engine Identity & Color Reversal Symmetry:**
   - In odd-numbered games ($2i - 1$, Game A): White was `Janus 0.51 Native (N2)`, Black was `Janus Production (K0)`.
   - In even-numbered games ($2i$, Game B): White was `Janus Production (K0)`, Black was `Janus 0.51 Native (N2)`.
   - Strict color reversal was preserved across all 100 pairs with zero inversions.
4. **Move Legality:** **Zero illegal moves detected across all 200 games.** Every played move existed in `board.legal_moves`.
5. **Terminal State Identity:** All terminal board states matched the result declared in the PGN headers.

---

## 3. Independent Score & Result Ledger

```
+----------------------------------------------------------------------------------------------------------+
|                                    INDEPENDENT RECONSTRUCTION SCOREBOARD                                 |
+---------------------+-------------+-------------+-------------+--------------+------------+--------------+
| Perspective         | Games       | Wins        | Draws       | Losses       | Points     | Win % / Score|
+---------------------+-------------+-------------+-------------+--------------+------------+--------------+
| Native N2 (Overall) | 200         | 179         | 18          | 3            | 188.0      | 94.00%       |
| Python K0 (Overall) | 200         | 3           | 18          | 179          | 12.0       | 6.00%        |
| N2 as White         | 100         | 93          | 7           | 0            | 96.5       | 96.50%       |
| N2 as Black         | 100         | 86          | 11          | 3            | 91.5       | 91.50%       |
| K0 as White         | 100         | 3           | 11          | 86           | 8.5        | 8.50%        |
| K0 as Black         | 100         | 0           | 7           | 93           | 3.5        | 3.50%        |
+---------------------+-------------+-------------+-------------+--------------+------------+--------------+
```

---

## 4. Pairwise Score Audit & Critical Consistency Check

For each pair $i \in \{1, \dots, 100\}$:
$$\Delta_i = S_{N2}(A_i) + S_{N2}(B_i) - [S_{K0}(A_i) + S_{K0}(B_i)] = 2 \times S_{N2}(i) - 2$$

Allowing the full half-point grid $\{-2.0, -1.5, -1.0, -0.5, 0.0, +0.5, +1.0, +1.5, +2.0\}$, the audited empirical frequencies are:

| Delta ($\Delta$) | Meaning | Audited Count | Implied N2 Pair Score | Implied K0 Pair Score | Contribution to $\sum \Delta$ |
|:---:|---|:---:|:---:|:---:|:---:|
| **$+2.0$** | N2 won both games (2-0) | **81** | 162.0 | 0.0 | $+162.0$ |
| **$+1.0$** | N2 won 1, drew 1 (1.5-0.5) | **14** | 21.0 | 7.0 | $+14.0$ |
| **$0.0$** | Even split (1-1) | **5** | 5.0 | 5.0 | $0.0$ |
| **$-1.0$** | K0 won 1, drew 1 | **0** | 0.0 | 0.0 | $0.0$ |
| **$-2.0$** | K0 won both games | **0** | 0.0 | 0.0 | $0.0$ |
| **Total** | — | **100** | **188.0** | **12.0** | **$+176.0$** |

### Mathematical Reconciliation of the 5 Delta-0 Pairs:
The audit mandate raised a critical verification check: do the reported 81 pairs of $+2$, 14 pairs of $+1$, and 5 pairs of $0$ reconcile mathematically with the reported $179\text{W} / 18\text{D} / 3\text{L}$?

Inspection of the independent pair ledger reveals the exact composition of the 5 delta-0 pairs:
- **Pair 44 (Gruenfeld):** Game A = $0.5$ (draw), Game B = $0.5$ (draw) $\implies 2$ draws.
- **Pair 62 (Sicilian Accelerated Dragon):** Game A = $0.5$ (draw), Game B = $0.5$ (draw) $\implies 2$ draws.
- **Pair 21 (Ruy Lopez Morphy):** Game A = $1.0$ (N2 win), Game B = $0.0$ (K0 win) $\implies 1$ N2 win, $1$ K0 win.
- **Pair 68 (Caro-Kann Korchnoi):** Game A = $1.0$ (N2 win), Game B = $0.0$ (K0 win) $\implies 1$ N2 win, $1$ K0 win.
- **Pair 81 (Slav Czech):** Game A = $1.0$ (N2 win), Game B = $0.0$ (K0 win) $\implies 1$ N2 win, $1$ K0 win.

**Reconciliation Arithmetic:**
- N2 Wins: $(81 \times 2) + (14 \times 1) + (3 \times 1) = 162 + 14 + 3 = \mathbf{179\text{ Wins}}$.
- N2 Draws: $(14 \times 1) + (2 \times 2) = 14 + 4 = \mathbf{18\text{ Draws}}$.
- N2 Losses (K0 Wins): $3 \times 1 = \mathbf{3\text{ Losses}}$.
- Mean Paired Delta: $\frac{176.0}{100} = \mathbf{+1.760\text{ points per pair}}$.

The reported pairwise summary and individual game summaries are **100% mutually consistent, mathematically exact, and independently verified**.

---

## 5. Gate 1 Finding

**Gate 1 Status: PASSED WITHOUT RESERVATION.**  
Every single one of the 200 games is accounted for with complete legality, symmetry, and mathematical identity.
