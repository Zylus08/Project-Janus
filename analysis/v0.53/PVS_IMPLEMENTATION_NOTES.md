# Project Janus v0.53 — PVS Implementation Notes & Source Invariants

**Milestone:** v0.53  
**Implementation Source:** `analysis/v0.53/native/janus_native.cpp`  
**Bridge Source:** `analysis/v0.53/native/janus_native_bridge.py`  
**Date:** 2026-11-05  

---

## 1. Architectural Summary

Principal Variation Search (PVS) was implemented directly within `negamax()` in `janus_native.cpp`. 

### Key Design Elements:
1. **Zero Heap Allocations:** Traversal uses stack variables and static arrays.
2. **Explicit Window Partitioning:**
   - First searched legal move (`moves_searched == 1`): searched with full window `[-beta, -alpha]`.
   - Subsequent legal moves (`moves_searched > 1`): probed with null window `[-alpha - 1, -alpha]`.
3. **Three-Tier Interaction with LMR:**
   - **Tier 1 (Reduced Null-Window Probe):** If move $m$ meets all 10 LMR criteria, search at reduced depth $d_{\text{reduced}}$ with window `[-alpha - 1, -alpha]`.
   - **Tier 2 (Full-Depth Null-Window Verification):** If Tier 1 returns $score > \alpha$, re-search at full nominal depth $d - 1$ with window `[-alpha - 1, -alpha]`.
   - **Tier 3 (Full-Window PVS Re-Search):** If a full-depth null-window search yields $score > \alpha$ and $score < \beta$, re-search at full nominal depth $d - 1$ with true window `[-beta, -alpha]`.
4. **Zero-Leak Toggling (`UsePVS`):**
   - When `UsePVS=false` (default during qualification), `moves_searched == 1 || !g_use_pvs` is strictly true for all moves, executing the exact bit-identical N3 baseline algorithm.

---

## 2. Telemetry Instrumentation

Four dedicated telemetry counters track PVS operational metrics:
- `g_pvs_full_window_searches`: Total full-window child searches executed (`[-beta, -alpha]`).
- `g_pvs_null_window_searches`: Total null-window child searches executed (`[-alpha - 1, -alpha]`).
- `g_pvs_researches`: Total full-window re-searches necessitated by interior $\alpha$ improvements.
- `g_pvs_cutoffs`: Beta cutoffs achieved during PVS execution.

These counters are exported to Python via `native_get_pvs_telemetry()` and reset between positions via `native_reset_pvs_telemetry()`.

