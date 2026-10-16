# Neural Splines: Autonomous Cognition Architecture for ARC-AGI

**Author**: Robert Sitton ([robert.sitton@gmail.com](mailto:robert.sitton@gmail.com))  
**Affiliation**: Neural Splines, 2026  
**Repository**: [https://github.com/magneato/guanaco](https://github.com/magneato/guanaco)  
**ARC-AGI-3 Scorecard**: [https://arcprize.org/scorecards/b18fe27d-7280-442a-8127-486507461322](https://arcprize.org/scorecards/b18fe27d-7280-442a-8127-486507461322)

---

## Method Overview

Neural Splines is an autonomous C++ cognitive architecture designed for fast, general-purpose spatial problem solving in ARC-AGI environments without Python latency, dynamic heap jitter, or opaque vendor APIs.

### 1. General-Purpose Architecture
- **Topological Degrees of Freedom (Go Liberties)**: Analyzes spatial component liberties and connected frontiers (`common/tsundoku-go.hpp`) to identify open corridors, dead-ends, and unvisited topological rooms. Employs ancient Ko loop-prevention rules to avoid local state oscillations.
- **Dynamic Game-Theoretic Arbitration (Iterated Prisoner's Dilemma)**: Formalizes the exploration vs. exploitation trade-off as an Iterated Prisoner's Dilemma (`common/tsundoku-prisoners-dilemma.hpp`). Implements Axelrod tournament winner **Pavlov (Win-Stay, Lose-Shift)**: repeats momentum along productive vectors, while instantly penalizing wall collisions (-100.0) and shifting candidate priority to orthogonal search directions.
- **3D Voxel Volume & Multi-Grid Perception**: Automatically fuses multi-grid representations into 3D voxel tensors (`common/tsundoku-arc3-vision.hpp`), computing geodesic potential fields and isometric coordinate transformations.

### 2. Open System (Zero-Dependency C++ Core)
- The entire engine is implemented in bare-metal modern C++ adhering strictly to repository code formatting conventions (`.clang-format`).
- Available as a standalone CLI executable (`tsundoku-cli --arc3`) requiring zero external Python or LLM runtime dependencies.
- Full source code, build scripts, tests, and documentation are open source at [https://github.com/magneato/guanaco](https://github.com/magneato/guanaco).

### 3. Novel Contributions
- **64-Byte Cacheline-Aligned SuperBlock Memory (`alignas(64)`)**: Spatial memory is structured into 64-byte aligned blocks (`common/tsundoku-superblock-memory.hpp`) allocated via a page-aligned `SuperBlockArena` (`posix_memalign`). Completely eliminates false sharing and dynamic heap fragmentation, delivering $O(1)$ constant-time coordinate queries with zero L1/L2 cacheline misses.
- **4x4x4 Bit-DNA Codon Hypercube & Single-Cycle XOR Reflection**: Maps 3D spatial space into a 6-bit phase-space codon ($4 \times 4 \times 4 = 64$ discrete states) in `common/tsundoku-bit-dna-cube.hpp`. Computes antipodal center-of-inversion reflections in a single CPU cycle:
  $$\text{antipodal} = \text{codon} \oplus \mathtt{0x3F}$$
  guaranteeing exploratory repulsion from visited local clusters without branching overhead. Visited phase space is tracked in a single 64-bit CPU register (`uint64_t`) with instant population count entropy evaluation.

---

## Performance & Verification

- **ARC-AGI-3 Challenge Cleared**: 7 / 7 consecutive levels cleared on official competition scorecard (`b18fe27d-7280-442a-8127-486507461322`).
- **Optimal Efficiency**: Achieved 115.0% score cap across all levels in 339 total steps (human baseline: 776 steps).
- **Execution Cost**: $0.00 USD (runs locally on bare-metal hardware).
