# Mitigating Negative Transfer in Local Developer Agents via Outcome-Calibrated Experiential Memory

**Subtitle:** Asymmetric Trust Decay and Deterministic Failure Quarantine for Autonomous Software Engineering on Consumer Hardware

**Authors:** Sumit Das, Sakshi Dattaprasad Kasat
**Track:** Google - The Gemma 4 Developer Agent Paper Track
**Resources & Code Links:**
* **Kaggle Public Benchmark Notebook:** [Agent Memory Confirmatory Benchmark Analysis](https://www.kaggle.com/code/sumitdevai/agent-memory-confirmatory-benchmark-analysis)
* **Kaggle Model Registry:** [Adaptive Agent Memory (PyTorch TorchScript & Scikit-Learn)](https://www.kaggle.com/models/sumitdevai/adaptive-agent-memory)
* **Kaggle Empirical Dataset (10.0 Usability):** [Agent Memory Resilience & Poisoning Benchmark](https://www.kaggle.com/datasets/sumitdevai/agent-memory-resilience-benchmark)
* **Kaggle Confirmatory Multi-Seed Dataset:** [Agent Memory Confirmatory Multi-Seed Benchmark](https://www.kaggle.com/datasets/sumitdevai/agent-memory-confirmatory-multi-seed-benchmark)

---

## Abstract

Autonomous software engineering agents powered by open foundation models offer the promise of private, offline development on consumer hardware without prohibitive cloud API latency or cost. However, compact models deployable locally exhibit heightened susceptibility to multi-turn error compounding when resolving real-world software issues. While external episodic memory and self-reflection mechanisms allow agents to store past problem-solving attempts, existing Retrieval-Augmented Generation (RAG) paradigms naively equate semantic vector proximity with operational correctness. In multi-step code synthesis and debugging, this architectural blind spot triggers **catastrophic negative transfer**: an unverified workaround or deprecated tool syntax matching prompt embeddings is retrieved with high cosine similarity, causing the agent to duplicate past failures repeatedly.

In this work, we present **Outcome-Calibrated Experiential Memory (OCEM)**, a zero-GPU, sub-0.15ms cognitive memory middleware for resource-constrained developer agents. OCEM structures past executions into atomic `{Trigger, Strategy, Pitfall}` procedural tuples and replaces static vector rankings with an Asymmetric Exponential Moving Average (A-EMA) trust engine. Failing strategies are deterministically quarantined once trust falls below a preregistered threshold. In a confirmatory evaluation of 738 trials across 30 multi-domain cases (24 harmful + 6 positive controls), our system reduces the Harmful Influence Rate under naive memory (M0) from 100% to 0% at trial 4, as confirmed by an exact McNemar test ($p = 1.19 \times 10^{-7}$), while preserving beneficial memory with 0.0% false quarantine rate.

---

## 1. Introduction: The Local Developer Agent Dilemma

State-of-the-art software engineering agents rely on large cloud-hosted models consuming significant VRAM and incurring substantial API costs per resolved issue. Transitioning this capability to developer workstations powered by open weights is essential for developer privacy, air-gapped enterprise compliance, and zero-latency local development.

However, smaller models deployable on consumer hardware suffer from two severe structural bottlenecks in long-horizon software engineering:
1. **Limited Working Context:** When attempting multi-file repository navigation, error tracing, and test suite execution, small context windows quickly saturate, necessitating external memory.
2. **The "Relevance != Reliability" Fallacy:** Existing agent architectures (LangGraph, AutoGen, Reflexion) store past execution traces in dense vector indices. In software development, agents frequently explore flawed refactorings, invalid API flags, or deprecated dependencies during initial exploration. Because dense embeddings only score semantic topicality, subsequent similar queries retrieve these flawed experiences with near-perfect cosine similarity.

```
+------------------------------------------------------------------------+
|                      The Negative Transfer Trap                        |
|                                                                        |
|  Query: "Fix connection pool exhaustion in async client"               |
|                                                                        |
|  [Vector Store Search]                                                 |
|  Retrieved Experience: "Set max_connections=1 to serialize queries"   |
|  Cosine Similarity: 0.94 (High topical match)                          |
|  Empirical Outcome: Deadlock / Performance collapse                   |
|                                                                        |
|  Result: Local agent blindly executes retrieved flawed code,           |
|          locking the developer into an infinite debugging loop.       |
+------------------------------------------------------------------------+
```

Without outcome-aware calibration, giving an agent memory makes it **less reliable than having no memory at all** in adversarial retrieval conditions. To solve this, we introduce an ultra-lightweight, mathematical trust layer that operates entirely offline on CPU.

---

## 2. Methodology & Mathematical Formulation

### 2.1 The Experiential Memory Schema
Rather than dumping unformatted conversation transcripts into vector databases, executions are distilled into structured tuples:
$$\mathcal{M}_i = \langle \text{Domain}, \text{Trigger}, \text{Strategy}, \text{Pitfall}, \mathbf{e}_i, S_i \rangle$$
where:
* $\text{Trigger}$: The syntactic/semantic condition activating the memory.
* $\text{Strategy}$: The actionable refactoring or command directive.
* $\text{Pitfall}$: Explicit operational constraints and anti-patterns to avoid.
* $\mathbf{e}_i \in \mathbb{R}^d$: Dense semantic embedding vector.
* $S_i \in [0, 1]$: Asymmetric EMA trust score governing retrieval eligibility.

### 2.2 Asymmetric Exponential Moving Average (A-EMA) Trust Updating
We model trust as a scalar score $S$ initialized at $S_0 = 0.75$. Upon observing a binary execution outcome $r \in \{0, 1\}$:
$$S_{t+1} = \begin{cases} \alpha \cdot S_t + (1 - \alpha) & \text{if } r = 1 \text{ (success)} \\ \beta \cdot S_t & \text{if } r = 0 \text{ (failure)} \end{cases}$$
with $\alpha = 0.85$ (success smoothing) and $\beta = 0.70$ (failure decay). The asymmetry ($\beta < \alpha$) ensures failures are penalized faster than successes rebuild trust, providing a conservative safety margin.

**Concrete Trust Decay Trajectory under Consecutive Failures ($r=0, r=0, r=0$):**
$$S_0 = 0.750 \xrightarrow{\times 0.70} S_1 = 0.525 \xrightarrow{\times 0.70} S_2 = 0.3675 \xrightarrow{\times 0.70} S_3 = 0.2572$$

### 2.3 Deterministic Quarantine Threshold
A memory record is deterministically excluded from retrieval when its trust score falls below a preregistered quarantine threshold $\theta = 0.35$:
$$\text{quarantine}(\mathcal{M}_i) = \mathbb{I}[S_i < 0.35]$$

**Corollary:** Under the initialized trust $S_0 = 0.75$ and $\beta = 0.70$, any memory that fails on 2 consecutive trials has its trust reduced to $0.75 \times 0.70^2 = 0.3675$, approaching the threshold. After 3 consecutive failures, trust is $0.75 \times 0.70^3 = 0.2572 < 0.35$, triggering guaranteed quarantine. This property is fixed by the A-EMA parameters, not by stochastic sampling.

### 2.4 Composite Retrieval Scoring
Candidates are ranked using a composite function blending semantic relevance and trust:
$$\text{Score}(\mathcal{M}_i, q) = \lambda \cdot \cos(\mathbf{e}_i, \mathbf{e}_q) + (1 - \lambda) \cdot S_i$$
with composite weight $\lambda = 0.70$. Quarantined records ($S_i < 0.35$) are excluded from candidate sets entirely prior to scoring.

---

## 3. System Architecture for Consumer Hardware

The system is deployed as an asynchronous middleware wrapper around local model runtimes (via Ollama or Hugging Face Transformers).

```
   +--------------------------------------------------------------+
   |                  Local Developer Workstation                 |
   |                                                              |
   |  [Developer Task / CLI Command]                              |
   |                 |                                            |
   |                 v                                            |
   |  +------------------------------+                            |
   |  |   Memory Retrieval Layer     |                            |
   |  | - Local Vector Embedding     |                            |
   |  | - A-EMA Trust Re-Scoring     |                            |
   |  | - Deterministic Quarantine   |  < 0.15ms latency (CPU)   |
   |  +------------------------------+  < 15KB memory footprint  |
   |                 |                                            |
   |                 v                                            |
   |  +------------------------------+                            |
   |  |   Local Agent Engine         |                            |
   |  |   (Gemma / qwen2.5 / etc.)   |  Consumer GPU / CPU       |
   |  +------------------------------+                            |
   |                 |                                            |
   |                 v                                            |
   |  +------------------------------+                            |
   |  | Outcome Validation / Sandbox |                            |
   |  | (pytest, linter, exit code)  |                            |
   |  +------------------------------+                            |
   |                 |                                            |
   |                 v                                            |
   |  +------------------------------+                            |
   |  | A-EMA Posterior Update       |                            |
   |  | (Trust Score Update)         |                            |
   |  +------------------------------+                            |
   +--------------------------------------------------------------+
```

* **Zero GPU Footprint:** The trust calculation is pure arithmetic, executing in < 0.15 ms per candidate on a single CPU core.
* **Compatibility:** Native integration with LangGraph, AutoGen, and ReAct agent loops.

---

## 4. Empirical Evaluation & Benchmarks

### 4.1 Benchmark Setup
All experimental protocols were preregistered and manifest hashes frozen before execution.

**Model:** `qwen2.5:1.5b` via Ollama, temperature 0.0 (deterministic decoding).
**Evaluator:** `StrictKeyAnswerEvaluator` v1.0-strict (SHA-256: `686bd43c...`).

We evaluated our system on 30 tasks spanning 8 domains:
* **Primary Harmful Cases ($N=24$):** Tasks where naive memory retrieves a stored incorrect answer (factual QA, geography, science, procedural systems, arithmetic, programming API, tool parameters). Under E0 (no memory), the model answers all 24 correctly.
* **Positive Controls ($N=6$):** Tasks with verified correct memory entries to confirm that adaptive filtering preserves legitimate positive transfer.
* **Replication Protocol:** Multi-seed evaluation across seeds 42, 43, and 44. Seeds 43 and 44 serve as deterministic reproducibility audits. Total: **738 execution trials**.

### 4.2 Experimental Conditions
1. **E0 (Stateless Baseline):** Agent operates without memory. 1 trial per case. Total: 90 trials.
2. **M0 (Naive Static Memory):** Harmful memory injected; trust fixed at $S=0.75$ regardless of outcome. 4 trials per harmful case. Total: 288 trials.
3. **A0 (Adaptive A-EMA Memory - Ours):** A-EMA trust updating with quarantine at $S < 0.35$. 4 trials per harmful case. Total: 288 trials.
4. **P0 (Beneficial Memory Control):** Verified correct memory; A-EMA policy active. 4 trials per positive case. Total: 72 trials.

### 4.3 Results

| Experimental Condition | Total Trials | Successful Trials | Trial-4 Accuracy | Mean Reward | Quarantine Rate |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **E0 (Stateless Baseline)** | 90 | 90 | 100.0% (24/24) | 1.000 | N/A |
| **M0 (Naive Static Memory)** | 288 | 0 | 0.0% (0/24) | 0.100 | 0.0% |
| **A0 (Adaptive A-EMA - Ours)** | 288 | 72 | **100.0% (24/24)** | 0.325 | **100.0% (24/24)** |
| **P0 (Beneficial Memory Control)** | 72 | 72 | 100.0% (6/6) | 1.000 | 0.0% |

**Wilson 95% Score Confidence Intervals (Seed 42, N=24 harmful cases):**
* Harmful Influence Rate (M0 Trial 1): 100.0% [95% CI: 86.2%, 100.0%]
* A0 Quarantine Rate: 100.0% [95% CI: 86.2%, 100.0%]
* A0 Trial-4 Recovery Rate: 100.0% [95% CI: 86.2%, 100.0%]

### 4.4 Statistical Significance

**McNemar Exact Test (M0 vs A0 at Trial 4, Seed 42, paired discordant cases):**
* Cell $b$ (M0 pass, A0 fail): 0 cases
* Cell $c$ (M0 fail, A0 pass): 24 cases
* Exact two-tailed $p = 1.19 \times 10^{-7}$ ($p \ll 0.001$)

The sign and magnitude of the discordant cell ($c=24, b=0$) shows that every case where M0 failed at Trial 4, A0 recovered -- and not one case reversed direction.

**Cross-Seed Concordance:** Seeds 43 and 44 produced 100.0% binary agreement with Seed 42 across all conditions, confirming the results are governed by deterministic mechanism convergence rather than sampling variance.

#### Key Empirical Findings:
1. **Persistent Degradation under Naive Memory (M0):** Unmanaged static memory collapsed task success from 100% (E0 baseline) to 0.0% at Trial 4. The harmful memory record remained at $S=0.75$ throughout all 4 trials because the trust was never updated.
2. **A-EMA Recovery by Trial 4:** Under A0, trust decayed as $0.75 \to 0.525 \to 0.3675 \to$ quarantine active (trust = 0.2572 < 0.35 by Trial 3). At Trial 4, the quarantined memory was suppressed from context, allowing the model to recover its intrinsic baseline accuracy: 100.0% recovery across all 24 harmful cases.
3. **Positive Control Retention:** Across all 6 positive control cases, zero false quarantines occurred. Final trust after 4 success trials: $S_4 = 0.8695$ (monotonically increasing from $S_0 = 0.75$).

---

## 5. Limitations

The following limitations apply to these findings and must be stated explicitly:

1. **Deterministic Decoding Only:** All evaluations used `temperature = 0.0`. Behavior under stochastic sampling is uncharacterized.
2. **Synthetic Distractors:** Harmful memories represent explicit factual counter-factuals. Naturalistic, subtle, or multi-hop conversational drift was not evaluated.
3. **Task Complexity:** Tasks are bounded structured queries with deterministic ground truths. Open-ended long-horizon coding workflows require further investigation.
4. **Sample Size:** $N=24$ harmful cases, $N=6$ positive controls. Category-level power is limited ($N=1$ to $N=5$ per category).
5. **Single Model Family:** Experiments used `qwen2.5:1.5b`. Generalization to other model architectures (including Gemma) requires direct empirical validation.

---

## 6. Kaggle Resources & Open Artifacts

All artifacts are published openly on Kaggle for community reproducibility:

1. **Kaggle Datasets:**
   * [`sumitdevai/agent-memory-resilience-benchmark`](https://www.kaggle.com/datasets/sumitdevai/agent-memory-resilience-benchmark): 1,200 chronological steps under 50% adversarial noise injection.
   * [`sumitdevai/agent-memory-confirmatory-multi-seed-benchmark`](https://www.kaggle.com/datasets/sumitdevai/agent-memory-confirmatory-multi-seed-benchmark): 738 multi-seed confirmatory evaluation trials.
2. **Kaggle Models Hub:**
   * [`sumitdevai/adaptive-agent-memory`](https://www.kaggle.com/models/sumitdevai/adaptive-agent-memory): PyTorch TorchScript and Scikit-Learn calibrator variations.
3. **Kaggle Code Notebooks:**
   * [Confirmatory Benchmark Analysis](https://www.kaggle.com/code/sumitdevai/agent-memory-confirmatory-benchmark-analysis)
   * [R Statistical Hypothesis Testing](https://www.kaggle.com/code/sumitdevai/adaptive-memory-r-statistical-analysis)

---

## 7. Citations & References

```bibtex
@article{das2026adaptiveagentmemory,
  title   = {Mitigating Negative Transfer in Autonomous Language Agents via Reliability-Aware Experiential Memory},
  author  = {Sumit Das and Sakshi Dattaprasad Kasat},
  journal = {Google Gemma 4 Developer Agent Paper Track},
  year    = {2026}
}
@article{shinn2023reflexion,
  title   = {Reflexion: Language agents with verbal reinforcement learning},
  author  = {Shinn, Noah and Cassano, Federico and Berman, Edward and Ashwin, G and Narasimhan, Karthik and Yao, Shunyu},
  journal = {NeurIPS},
  year    = {2023}
}
@article{yao2023react,
  title   = {ReAct: Synergizing Reasoning and Acting in Language Models},
  author  = {Yao, Shunyu and Zhao, Jeffrey and Yu, Dian and Du, Nan and Shafran, Izhak and Narasimhan, Karthik and Cao, Yuan},
  journal = {ICLR},
  year    = {2023}
}
@article{packer2023memgpt,
  title   = {MemGPT: Towards LLMs as Operating Systems},
  author  = {Packer, Charles and Fang, Vivian and Patil, Shishir G and Lin, Kevin and Wooders, Sarah and Gonzalez, Joseph E},
  journal = {arXiv preprint arXiv:2310.08560},
  year    = {2023}
}
```
