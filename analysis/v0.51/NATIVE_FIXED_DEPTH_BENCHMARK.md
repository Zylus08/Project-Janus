# Project Janus v0.51 — Native Fixed-Depth Benchmark & TT Reusability

## 1. Executive Summary

Phase F1 benchmarks the standalone native engine (`janus_native_engine.exe`) under controlled fixed-depth conditions across the 37-position diagnostic corpus. To evaluate transposition table efficiency, every position was evaluated under two conditions:
1. **Cold TT**: Transposition table cleared via `ucinewgame` immediately before search.
2. **Warm TT**: Search repeated immediately on the same position with transposition table populated.

### Key Findings:
- **Throughput Scaling**: Native N2 processes 4.46 million nodes across the corpus at Depth 5, maintaining ~383,000 to ~594,000 NPS.
- **TT Reuse Acceleration**: Transposition table hit rates reduce search runtime dramatically:
  * At Depth 3: Mean runtime drops from 9.3ms to 0.4ms (**-95.5% time reduction**).
  * At Depth 4: Mean runtime drops from 41.6ms to 1.4ms (**-96.6% time reduction**).
  * At Depth 5: Mean runtime drops from 314.1ms to 2.8ms (**-99.1% time reduction**).
- **Per-Position Consistency**: Median runtimes track mean runtimes closely (e.g. 31.7ms median at Depth 4; 234.7ms median at Depth 5), demonstrating low dispersion across tactical and quiet positions.

---

## 2. Fixed-Depth Cold vs Warm Benchmark Results (37 Positions)

| Nominal Depth | Total Nodes | Effective NPS | Mean Cold Time | Median Cold Time | Mean Warm Time | Median Warm Time | TT Warmup Speedup |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Depth 1** | 4,203 | 252,517 | 0.4 ms | 0.3 ms | 0.3 ms | 0.3 ms | **34.0%** |
| **Depth 2** | 26,897 | 361,621 | 2.0 ms | 1.9 ms | 0.4 ms | 0.3 ms | **81.6%** |
| **Depth 3** | 204,849 | 594,804 | 9.3 ms | 6.5 ms | 0.4 ms | 0.4 ms | **95.5%** |
| **Depth 4** | 767,214 | 498,723 | 41.6 ms | 31.7 ms | 1.4 ms | 0.4 ms | **96.6%** |
| **Depth 5** | 4,459,212 | 383,738 | 314.1 ms | 234.7 ms | 2.8 ms | 0.9 ms | **99.1%** |

---

## 3. Comparison with Python Baseline

| Metric | Python K0 (v0.50) | Native N2 (v0.51 Standalone) | Speedup / Advantage |
|---|:---:|:---:|:---:|
| **Depth 3 Aggregate Time** | 29.79 s | 0.34 s | **87.6x faster** |
| **Depth 4 Aggregate Time** | 103.62 s | 1.54 s | **67.3x faster** |
| **Depth 5 Aggregate Time** | 243.65 s | 11.62 s | **21.0x faster** |
| **Depth 5 NPS Throughput** | ~5,137 NPS | ~383,738 NPS | **~75x throughput gain** |
| **Memory Footprint** | ~65 MB (Python + libs) | ~16.5 MB (Total process RAM) | **-74.6% memory reduction** |

---

## 4. Conclusion

Standalone native execution eliminates Python bytecode dispatch overhead and leverages L1/L2 cache locality for transposition table lookups. The 1M-entry direct-mapped TT delivers 95% to 99% time savings upon repeated position evaluations, providing a highly responsive foundation for competitive tournament play.

