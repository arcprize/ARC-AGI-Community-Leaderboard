# LMM Agent: Training-Free Equation-Based ARC-AGI-3 Solver

> [!NOTE]
> **Work In Progress**: Development was paused on **May 8, 2026**. This project is currently being advanced as a weekend hobby project. The ultimate goal is a **100% score on all ARC-AGI games at $0 cost**.

[![Work In Progress](https://img.shields.io/badge/Work%20In%20Progress-orange)](https://github.com/wiseaidotdev/lmm)
[![ARC-AGI-3 Score](https://img.shields.io/badge/ARC--AGI--3-14.55%25-blue)](https://arcprize.org/replay/69c86b04-c9ff-4ae2-98e8-eade2e4c2214)
[![Made with Rust](https://img.shields.io/badge/Made%20with-Rust-1f425f.svg?logo=rust&logoColor=white)](https://www.rust-lang.org/)
[![License](https://img.shields.io/badge/License-MIT-brightgreen.svg)](https://github.com/wiseaidotdev/lmm/blob/main/LICENSE)

## What Is This?

**`arc-lmm-agent`** is a pure-Rust autonomous agent that plays ARC-AGI-3 games using **zero training data, zero neural networks, zero GPU, and zero API cost**. It is a concrete implementation of a research thesis that has been evolving across a series of blog posts: _intelligence and knowledge are mutually exclusive_, and genuine fluid intelligence must be architecturally separated from memorised pattern retrieval.

The agent uses the [`arc-agi-rs`](https://github.com/wiseaidotdev/arc-agi-rs) crate as its API client for the ARC-AGI-3 REST API: a pure-Rust, multi-language toolkit (available also for Python and Node.js) that provides environment discovery, scorecard management, and game interaction.

## Research Philosophy

This project is the practical embodiment of a novel research direction first articulated in:

> **[Knowledge and Intelligence Are Mutually Exclusive](https://wiseai.dev/blogs/knowledge-and-intelligence-are-mutually-exclusive)**

The core thesis: systems trained to maximise knowledge retrieval (LLMs) are simultaneously optimised _away_ from genuine intelligence. The training paradigm that produces the most capable knowledge stores is the paradigm least likely to produce generalisation. Scaling such systems cannot cross this boundary: it can only produce more of the same.

This is why the LMM Agent uses **none** of those systems.

### Related Blog Posts (Research Context)

| Post                                                                                                                                                | Thesis                                                                                                          |
| --------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| [LLMs are Useful. LMMs will Bretecak Reality](https://wiseai.dev/blogs/llms-are-usefull-lmms-will-break-reality)                                    | Equations, not tokens, are the medium of genuine understanding. The original post that started this project.    |
| [Training Is an Evil Concept. LMMs Eliminate It Altogether](https://wiseai.dev/blogs/training-is-an-evil-concept-lmms-eliminates-it-altogether)     | Why gradient descent on human text is ethically, architecturally, and epistemically bankrupt.                   |
| [Mathematical Equations Are Multimodal by Default](https://wiseai.dev/blogs/mathematical-equations-are-multimodal-by-default)                       | Mathematical structure encodes mechanism in ways text never can; it is inherently cross-modal.                  |
| [Genuine Intelligence Will Never Emerge from Neural Networks](https://wiseai.dev/blogs/genuine-intelligence-will-never-emerge-from-neural-networks) | The architectural gaps in neural networks are not fixable bugs: they are defining properties.                   |
| [Language Is Limited. ASI Is Impossible](https://wiseai.dev/blogs/language-is-limited-asi-is-impossible)                                            | Text is not the medium of reality; systems living inside text are separated from the world by compression loss. |
| [Rethinking ARC-AGI](https://wiseai.dev/blogs/rethinking-arc-agi)                                                                                   | Re-examines ARC-AGI as a genuine test of fluid intelligence and what it takes to pass it honestly.              |
| [Knowledge and Intelligence Are Mutually Exclusive](https://wiseai.dev/blogs/knowledge-and-intelligence-are-mutually-exclusive)                     | The capstone post tying all of the above into a unified argument with mathematical grounding.                   |

## Novel Approaches

### 1. Intelligence Primitives (No Neural Networks)

The agent is built on five _structural_ intelligence primitives that replace statistical interpolation:

| Primitive                   | Mechanism                                                                                              |
| --------------------------- | ------------------------------------------------------------------------------------------------------ |
| **Calibrated Uncertainty**  | Gaussian belief propagation: the agent knows when it does not know                                     |
| **Axiomatic Reasoning**     | Compositional forward-chaining proofs: every conclusion is auditable                                   |
| **Causal Attribution**      | Pearl do-calculus interventions: distinguishes cause from correlation                                  |
| **Hypothesis Formation**    | Ranks candidate new causal edges by explanatory power                                                  |
| **Internalized Motivation** | Drives: `Curiosity`, `CoherenceSeeking`, `ContradictionResolution`: exploration without reward shaping |

None of these can be "trained in": each requires structural presence at the architectural level.

### 2. HELM: Hybrid Equation-based Lifelong Memory

HELM is a CPU-resident lifelong learning engine with no neural network components:

- Tabular Bellman **Q-learning** (reinforcement, not gradient descent)
- Prototype **meta-adaptation** via Jaccard similarity
- **Knowledge distillation** between Q-table snapshots
- **Self-federated** Q-table aggregation (no central server)
- **Elastic memory guarding** via activation-count pinning
- **PMI co-occurrence mining** from high-reward observations

### 3. ThinkLoop: PI Controller for Iterative Reasoning

A closed-loop **proportional-integral controller** drives reasoning toward a goal by computing Jaccard-error feedback at each cycle. It converges on solutions by iterative refinement: generation, not lookup.

### 4. KnowledgeIndex: Cross-Level IDF Strategy Transfer

After completing a level, the agent ingests a narrative description into an IDF-weighted index. In subsequent levels it queries this index to transfer applicable strategies: transfer learning implemented as information retrieval, not fine-tuning.

### 5. WorldMapGraph: Internal World Modeling

The agent builds a topological graph of the environment as it explores, enabling spatial reasoning about unseen areas under fog-of-war.

### 6. CausalAttributor: do-Calculus Interventions

Uses Pearl's causal hierarchy to attribute outcomes to root causes rather than surface correlations, placing the agent at causal hierarchy level 2-3 rather than level 1 (observation only).

### 7. HypothesisGenerator

Takes unexplained residual variance in the agent's causal graph and ranks candidate new causal edges by explanatory power: proposing hypotheses rather than retrieving patterns.

### 8. Pure Rust + `arc-agi-rs` API Client

The entire stack: agent framework, memory engine, causal reasoner, ARC-AGI-3 API client, is **pure Rust**. The [`arc-agi-rs`](https://github.com/wiseaidotdev/arc-agi-rs) crate provides the full ARC-AGI-3 client API (environment discovery, scorecard management, `reset`/`step` game interaction, anonymous access) as an async-first, high-performance Rust library also available for Python and Node.js.

## Score

| Benchmark | Set    | Score                                                                        | Cost      |
| --------- | ------ | ---------------------------------------------------------------------------- | --------- |
| ARC-AGI-3 | public | [14.5505%](https://arcprize.org/replay/69c86b04-c9ff-4ae2-98e8-eade2e4c2214) | **$0.00** |

The `ls20` game was used: a partially observable grid puzzle with fog-of-war, sequential configuration objectives, and strict step budgets. The agent had **no prior knowledge of the game**: no training data, no human demonstrations, no examples of successful trajectories.

14.5505% from a system with no task-specific training and $0 cost is a structural result, not a statistical one. Every point is earned by genuine out-of-distribution reasoning, not interpolation over a training set.

> [!IMPORTANT]
> **Achieving 100% on ARC-AGI with an LLM is expected and frankly boring.** Throw enough tokens, enough compute, and a frontier model at a visual puzzle benchmark, and you will eventually brute-force it. That is expensive pattern retrieval at scale. What this project is doing is something categorically different and, frankly, kind of ridiculous in its ambition: a zero-cost, training-free, pure-Rust agent built entirely on symbolic mathematics and causal reasoning: no GPUs, no gradient descent, no LLM API, reaching 14.55% and climbing. The novelty is _what is producing the score_, not the score itself.

## Current Status & Roadmap

Development was paused on **May 8, 2026** and is currently progressing as a **weekend hobby project**.

| Milestone                          | Status             |
| ---------------------------------- | ------------------ |
| Core intelligence primitives       | ✅ Done            |
| HELM Q-learning engine             | ✅ Done            |
| ThinkLoop PI controller            | ✅ Done            |
| KnowledgeIndex IDF transfer        | ✅ Done            |
| WorldMapGraph topology             | ✅ Done            |
| ARC-AGI-3 scorecard replay         | ✅ Done (14.5505%) |
| Improved causal graph construction | 🔄 In Progress     |
| Symbolic regression integration    | 🔄 In Progress     |
| Multi-game generalisation          | 🔄 In Progress     |
| **100% ARC-AGI at $0 cost**        | 🎯 Ultimate Goal   |

## Repository

- **Main project**: [github.com/wiseaidotdev/lmm](https://github.com/wiseaidotdev/lmm)
- **ARC agent example**: [`examples/arc-lmm-agent`](https://github.com/wiseaidotdev/lmm/tree/main/examples/arc-lmm-agent)
- **ARC-AGI-3 API client**: [github.com/wiseaidotdev/arc-agi-rs](https://github.com/wiseaidotdev/arc-agi-rs)
- **Whitepaper**: [`papers/lmm.pdf`](https://github.com/wiseaidotdev/lmm/blob/main/papers/lmm.pdf)
- **Blog**: [wiseai.dev](https://wiseai.dev)
