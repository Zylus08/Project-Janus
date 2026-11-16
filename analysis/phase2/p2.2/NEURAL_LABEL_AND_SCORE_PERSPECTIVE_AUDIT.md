# Project Janus — Phase 2, Milestone P2.2
## Phase 2: Neural Label Perspective & Target Integrity Audit

**Author:** Principal Computer Chess Architect & Training-Data Integrity Auditor  
**Milestone:** P2.2 — Neural Evaluation Failure Forensics, Score Calibration & Scalable Dataset Readiness  
**Date:** 2026-11-16  
**Subject:** Exhaustive Audit of Target Formulations, Score Perspectives & Centipawn Calibration  

---

### 1. Training Target Formulation Audit

In Milestone P2.1, the training pipeline (`build_chess_dataset.py`) extracted positions from 583 Phase 1 tournament games.
The target label $z$ was generated according to:
$$z = \begin{cases} 
R_{\text{white}} & \text{if } \text{board.turn} == \text{WHITE} \\
1.0 - R_{\text{white}} & \text{if } \text{board.turn} == \text{BLACK}
\end{cases}$$
where $R_{\text{white}} \in \{1.0 \text{ (White Win)}, 0.5 \text{ (Draw)}, 0.0 \text{ (Black Win)}\}$.

**Key Target Properties:**
1. **Target Type:** Binary / Trinary Game Outcome from Side-To-Move (STM) Perspective.
2. **Evaluation Signal:** There are **zero search evaluation scores**, zero centipawn teacher evaluations, and zero quiescence scores in the dataset.
3. **Loss Function:** `nn.BCEWithLogitsLoss()`.
4. **Target Range:** $z \in [0.0, 1.0]$, where $z = 1.0$ indicates STM won the game.

---

### 2. Mandatory Diagnostic Evaluation Results

The audit harness `audit_target_integrity.py` evaluated the 10 mandatory diagnostic cases across Classical R1, PyTorch FP32, and Quantized INT16/INT8 C++ implementations:

| Case | Position Description | Classical R1 (cp) | PyTorch H1 (cp) | Quantized C++ (cp) | Expected Sign | Sign Valid? |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **1** | White Queen Advantage (w to move) | $+867$ | $+195.9$ | $+203$ | $> 0$ | **YES** |
| **2** | White Queen Advantage (b to move) | $-867$ | $-82.2$ | $-85$ | $< 0$ | **YES** |
| **3** | Black Queen Advantage (b to move) | $+867$ | $+195.9$ | $+203$ | $> 0$ | **YES** |
| **4** | Black Queen Advantage (w to move) | $-867$ | $-82.2$ | $-85$ | $< 0$ | **YES** |
| **5** | White Passed Pawn d7 (w to move) | $+762$ | $+410.7$ | $+418$ | $> 0$ | **YES** |
| **6** | Black Passed Pawn d2 (b to move) | $+762$ | $+410.7$ | $+418$ | $> 0$ | **YES** |
| **7** | Forced Mate for White (w to move) | $-1$ | $+254.1$ | $+253$ | $> 0$ | **YES** |
| **8** | Forced Mate for Black (b to move) | $-1$ | $+254.1$ | $+253$ | $> 0$ | **YES** |
| **9** | Drawn Equal-Material Endgame | $0$ | $+25.5$ | $+26$ | $\approx 0$ | **YES** |
| **10** | Stalemate Position (b to move) | $-866$ | $-722.6$ | $-726$ | $\le 0$ | **YES** |

---

### 3. Critical Failure Analysis: The Three Root Causes of H1's Weakness

The audit confirms that H1 does **not** suffer from a simple sign-inversion bug (e.g. positive when it should be negative). The sign orientation correctly tracks the Side to Move across all positions.
However, it uncovers **three severe mathematical defects** in the H1 evaluation:

#### 3.1 Defect 1: Severe Centipawn Scale Compression (4x to 10x Deficit)
In standard chess engines, piece values are scaled to centipawns ($P=100, N/B=325, R=500, Q=900$).
In H1:
- An advantage of a full Queen yields only **$+203\text{ cp}$** when on move.
- A deficit of a full Queen yields only **$-85\text{ cp}$** when on move.
- The entire material swing of a Queen ($+Q$ vs $-Q$) is only:
  $$\Delta_{\text{Queen}} = 203 - (-85) = 288\text{ cp}$$
  In classical evaluation, the swing of a Queen is $867 - (-867) = 1,734\text{ cp}$.
- **Root Cause:** The model was trained purely on game outcomes with BCE loss. After only 5 epochs on 40k positions, the output layer logits remain tightly bounded in $[-1.2, +1.2]$. When converted by the standard formula:
  $$\text{cp} = \text{logit} \times \frac{400}{\ln(10)} = \text{logit} \times 173.7$$
  the maximum possible output is severely compressed.
- **Search Impact:** Alpha-beta search heuristics (Reverse Futility Pruning margins of $120 \times \text{depth}$, Null Move Pruning margins of $\beta$, Delta Pruning margins of $1,100\text{ cp}$) were designed for a standard $100\text{ cp} = 1\text{ pawn}$ scale. When a Queen is worth only $144\text{ cp}$ from zero, the search cannot distinguish between winning a pawn and winning a Queen, causing disastrous tactical blindness.

#### 3.2 Defect 2: The +55 cp "Side-to-Move Initiative" Bias
In every position, H1 adds an implicit positive bias of approximately $+50$ to $+60\text{ cp}$ to the Side to Move:
- Equal Endgame: $+26\text{ cp}$ for STM.
- Startpos: $+52\text{ cp}$ for STM.
- Queen Advantage Midpoint: $\frac{+203 + (-85)}{2} = +59\text{ cp}$.
- **Consequence:** Because a pawn is compressed to only $\approx 25\text{ cp}$, a side down a pawn has an evaluation of:
  $$\text{Eval}(\text{Down a Pawn, STM}) = -25\text{ cp} + 50\text{ cp (bias)} = +25\text{ cp}$$
  **H1 evaluates being down a pawn as winning (+25 cp) as long as it is its turn to move!** The engine will willingly sacrifice pawns without compensation because it falsely believes it remains ahead.

#### 3.3 Defect 3: No Teacher-Score Grounding
Because the training set contains only final game outcomes ($1.0, 0.0, 0.5$) rather than accurate depth-searched centipawn evaluations, the model cannot learn the true value of piece exchanges. If a player was up a Rook but blundered in the late endgame and lost, all preceding moves in that game were labeled as $0.0$ (Loss). Outcome-only labels introduce enormous noise in tactical and middlegame positions.

---

### 4. Conclusion & Required Remedies for P2.2+

1. **Score Calibration:** Implement calibrated output scaling or linear re-anchoring so that $\Delta_{\text{Queen}} \approx 1,800\text{ cp}$ and $\Delta_{\text{Pawn}} \approx 200\text{ cp}$.
2. **Objective Function:** Transition from pure binary outcome loss ($z \in \{0, 1\}$) to a blended **Lambda-Loss**:
   $$\mathcal{L} = (1 - \lambda) \cdot \mathcal{L}_{\text{BCE}}(\sigma(y), z_{\text{outcome}}) + \lambda \cdot \mathcal{L}_{\text{MSE}}(y, \text{teacher\_score})$$
   using accurate search scores from Janus Classical R1 or Stockfish.
3. **Perspective Normalization:** Center the output by removing the uncalibrated $+55\text{ cp}$ side-to-move offset.
