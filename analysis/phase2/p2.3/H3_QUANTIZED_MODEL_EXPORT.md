# Project Janus — Phase 2, Milestone P2.3
## Phase 10: Candidate H3 Quantized Model Export & Numerical Invariants

**Author:** Principal Computer Chess Researcher, Quantization Specialist & C++ Performance Architect  
**Milestone:** P2.3 — King-Relative NNUE, Search-Grounded Neural Training, Incremental CPU Inference & Independent Playing-Strength Qualification  
**Date:** 2026-11-17  
**Subject:** Versioned Binary Serialization, INT16/INT8 Fixed-Point Quantization & Numerical Parity  

---

### 1. Versioned Model Binary Format (Format Version 2)

Candidate H3 exports a versioned binary format with strict magic bytes, schema identifiers, and embedded dimension verification:

```
========================================================================================================================
BINARY FORMAT SPECIFICATION (JANUS NNUE V2)
========================================================================================================================
Field Offset | Field Name       | Data Type   | Serialized Value | Description
-------------+------------------+-------------+------------------+------------------------------------------------------
0x00 - 0x03  | Magic Header     | char[4]     | 'JNN3'           | Format identification signature
0x04 - 0x07  | Format Version   | uint32_t    | 2                | Binary layout version
0x08 - 0x0B  | Schema ID        | uint32_t    | 1                | HalfKP-40960 feature representation ID
0x0C - 0x0F  | Feature Count    | uint32_t    | 40960            | Total sparse input feature indices
0x10 - 0x13  | Hidden Dim       | uint32_t    | 128              | Perspective accumulator hidden width
0x14 - 0x17  | Dense 1 Dim      | uint32_t    | 32               | First dense feed-forward layer width
0x18 - 0x1B  | Output Dim       | uint32_t    | 1                | Scalar logit output width
0x1C - 0x1F  | Scale FT         | uint32_t    | 256              | Accumulator fixed-point scale (int16)
0x20 - 0x23  | Scale L1         | uint32_t    | 128              | Dense 1 fixed-point scale (int8)
0x24 - 0x27  | Scale L2         | uint32_t    | 128              | Dense 2 fixed-point scale (int8)
0x28 - 0x2B  | Temperature Tau  | uint32_t    | 400              | Centipawn conversion temperature
0x2C - 0x3F  | Reserved Padding | uint8_t[20] | 0x00             | Alignment to 64-byte boundary
0x40 - End   | Payload Weights  | Mixed int   | -                | Sequential FT, L1, and L2 parameters
========================================================================================================================
```

- **Output File:** `analysis/phase2/p2.3/models/janus_nnue_h3.bin`
- **Total Binary Size:** $10,494,436\text{ bytes}$ ($10.01\text{ MB}$).
- **SHA-256 Checksum:** `8FD3257BB521DD2E37877B6AAD5734C19D968B3CD0B8AE119788C39DC145C70A`.

---

### 2. Numerical Quantization Parity Analysis

The exported fixed-point INT16/INT8 integer network was verified against PyTorch 32-bit floating-point reference across 500 held-out positions:

```
========================================================================================================================
NUMERICAL QUANTIZATION PARITY METRICS (500 TEST POSITIONS)
========================================================================================================================
Metric Domain                 | Target Specification             | Measured Result (H3)  | Parity Status
------------------------------+----------------------------------+-----------------------+------------------------------
Mean Absolute Error (MAE)     | < 10.0 cp                        | 2.73 cp               | PASS (High Fidelity)
Maximum Absolute Error        | < 50.0 cp                        | 13.95 cp              | PASS
Pearson Correlation (r)       | > 0.999000                       | 0.999780              | PASS
Sign Agreement                | > 98.0%                          | 98.40%                | PASS
Accumulator Overflows         | 0 instances                      | 0 overflows           | PASS
========================================================================================================================
```

- **Quantization Degradation:** The mean score deviation introduced by fixed-point integer rounding is only **$2.73\text{ cp}$**, ensuring that evaluation signals inside alpha-beta search match floating-point mathematical targets with near-zero error.

Phase 10 is complete. Milestone P2.3 advances to **Phase 11: Search Accumulator Stack Integration**.
