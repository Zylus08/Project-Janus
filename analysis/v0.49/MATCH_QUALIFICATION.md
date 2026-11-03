# Project Janus v0.49 — Controlled Match Qualification Disposition

**Milestone:** Project Janus v0.49  
**Parent Baseline Commit:** `6b46eb4` (v0.48 Final)  
**Evaluated Candidates:**
- **Candidate N1:** Native C DLL stable partial sort via `ctypes`
- **Candidate H1:** Flattened 1D 4096-element integer history array
- **Candidate H2:** Stage-separated lazy quiet history scoring
- **Candidate K1:** Multi-stage lazy move selector with killer priority
- **Candidate L1:** Inherited lazy move selection reference (`enable_lazy_move_selection=True`)

---

## 1. Executive Disposition: NO CANDIDATE QUALIFIES FOR A MATCH

Following the rigorous empirical evaluations across Phases C through H of Project Janus v0.49, **no candidate meets the preregistered criteria for a controlled playing-strength match**.

### Candidate Status Summary:
1. **Candidate N1 (Native C Move Picker Kernel):**
   - **Correctness:** 100.0% exact node-for-node and score-for-score equivalence to K0 (405,197 nodes at Depth 4).
   - **Performance:** Ordering time was reduced by **$-52.2\%$** (from 1.562s to 0.746s), but end-to-end wall-clock search runtime regressed by **$+6.66\%$** due to Python list pre-evaluation and ctypes argument marshaling overhead.
   - **Match Qualification:** **DISQUALIFIED**. Fails the mandatory requirement of net end-to-end search efficiency. Entering a match with a $-6.2\%$ NPS penalty would handicap the engine under clock constraints.
2. **Candidate H1 (Flat History Array):**
   - **Performance:** Search runtime regressed by $+27.4\%$.
   - **Match Qualification:** **DISQUALIFIED**.
3. **Candidate H2 (Stage-Separated Lazy History):**
   - **Performance:** Successfully reduced history table lookups by **$-69.6\%$** (saving 670,392 lookups at Depth 4), but wall-clock search time was near-neutral ($+1.94\%$) because Python list partitioning offset lookup savings.
   - **Match Qualification:** **DISQUALIFIED**. While architecturally promising, it does not provide an end-to-end speedup in pure Python.
4. **Candidate K1 (Multi-Stage Lazy Killer):**
   - **Performance:** Prioritized 37,985 killer moves, but list partitioning overhead slowed search by $+4.31\%$.
   - **Match Qualification:** **DISQUALIFIED**.
5. **Candidate L1 (Inherited Lazy Move Selection):**
   - **Prior Record:** Already evaluated in a 50-game controlled paired match in v0.47 (mean paired delta $-0.1600$, $p = 0.2562$, 95% bootstrap CI $[-0.4400, +0.0800]$).
   - **Match Qualification:** **DISQUALIFIED FROM REDUNDANT RE-MATCH**. Running another match under identical conditions without algorithmic modifications would be an uninformative expenditure of compute.

---

## 2. Preregistered Qualification Audit

| Preregistered Criterion | Candidate N1 | Candidate H2 | Candidate K1 | Candidate L1 |
|---|---|---|---|---|
| **Exact intended selection behaviour** | **PASS** (100% node-identical to K0) | **PASS** (97.3% move agreement) | **PASS** (97.3% move agreement) | **PASS** (97.3% move agreement) |
| **Reproducible build / toolchain** | **PASS** (MSVC `cl.exe`) | **PASS** (Pure Python) | **PASS** (Pure Python) | **PASS** (Pure Python) |
| **No severe tactical regression** | **PASS** (0 blunders, 0 drops) | **PASS** (0 blunders, 0 drops) | **PASS** (0 blunders, 0 drops) | **PASS** (0 blunders, 0 drops) |
| **End-to-end runtime improvement** | **FAIL** ($+6.66\%$ slower) | **FAIL** ($+1.94\%$ slower) | **FAIL** ($+4.31\%$ slower) | **PASS** ($-17.7\%$ at D5) |
| **Unresolved match hypothesis** | **FAIL** (NPS regression) | **FAIL** (No speedup) | **FAIL** (No speedup) | **FAIL** (Matched in v0.47) |
| **Final Match Status** | **DISQUALIFIED** | **DISQUALIFIED** | **DISQUALIFIED** | **NO RE-MATCH** |

---

## 3. Scientific Rationale

A competitive playing-strength match is an expensive statistical instrument designed to measure whether an efficiency improvement translates into an Elo gain.

In v0.49:
- The investigations into N1, H1, H2, and K1 have yielded a decisive diagnostic finding: **In an interpreted Python chess search, adding complex multi-stage partitioning or ctypes native boundaries adds more interpreter overhead than the move-selection algorithms save.**
- Conducting a 50- or 200-game match on any of these candidates would test an engine that is either computationally slower than K0 (N1, H1, K1) or already known to be strength-neutral (L1).
- Therefore, the scientifically sound and resource-responsible disposition is to disqualify all candidates from match testing and document the structural architectural lessons.

