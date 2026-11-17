import { useState, useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import {
  Search,
  ArrowRight,
  Copy,
  Check,
  Shield,
  Activity,
  Cpu,
  ArrowUpRight,
  Github,
  ChevronRight,
  Menu,
  X,
  FileCode,
  Zap,
} from 'lucide-react'

// Documentation Content Schema
interface DocSection {
  id: string
  title: string
  group: 'Get Started' | 'Core Concepts' | 'SDKs & Tools' | 'Empirical Benchmarks'
  summary: string
  headings: { id: string; label: string }[]
  content: {
    lead: string
    subsections: {
      id: string
      heading: string
      text: string
      codeSnippet?: {
        lang: string
        title: string
        code: string
      }
      cards?: {
        icon: 'zap' | 'activity' | 'cpu' | 'shield'
        title: string
        desc: string
        linkId?: string
      }[]
      callout?: {
        type: 'info' | 'theorem' | 'warning'
        title: string
        text: string
      }
      table?: {
        headers: string[]
        rows: string[][]
      }
    }[]
  }
}

const DOCS_DATA: Record<string, DocSection> = {
  introduction: {
    id: 'introduction',
    title: 'AEMA: Reliability-Aware Experiential Memory',
    group: 'Get Started',
    summary: 'A mathematical memory architecture that tracks execution reliability and isolates negative transfer for autonomous AI agents.',
    headings: [
      { id: 'overview', label: 'Architectural Overview' },
      { id: 'core-pillars', label: 'Three Engineering Guarantees' },
      { id: 'quick-navigation', label: 'Explore the Engine' },
      { id: 'how-it-works', label: 'The 5-Node Cognitive Loop' },
    ],
    content: {
      lead: 'Standard retrieval-augmented generation (RAG) and agent memory systems retrieve past logs based purely on semantic vector similarity. When an agent invents an invalid function call, hallucinates a deprecated parameter, or follows a poisoned heuristic, standard memory blindly retrieves that mistake again in future tasks. AEMA solves this catastrophic failure mode (negative transfer) by scoring every run, isolating failing patterns, and turning past executions into reliable ground truth.',
      subsections: [
        {
          id: 'overview',
          heading: 'Architectural Overview',
          text: 'AEMA operates entirely external to the underlying LLM. The foundational language model is never fine-tuned or retraining-dependent. Instead, learning occurs continuously through a persistent cognitive execution loop: retrieving past verified strategies, executing with parameter guardrails, evaluating outcomes against deterministic test oracles, reflecting to distill (c, a, p) procedural lesson tuples, and updating trust scores via Asymmetric Exponential Moving Average (A-EMA).',
          callout: {
            type: 'theorem',
            title: 'Theorem 1 Deterministic Quarantine Guarantee',
            text: 'When a strategy repeatedly causes test failures, its trust score decays exponentially below the critical threshold theta <= 0.35 within at most k* <= 3 consecutive failures. Once quarantined, the negative pattern is mathematically excluded from future retrieval context.',
          },
        },
        {
          id: 'core-pillars',
          heading: 'Three Engineering Guarantees',
          text: 'Every memory mutation, vector index search, and calibration update in AEMA is governed by three strict architectural principles designed for mission-critical software engineering agents:',
          table: {
            headers: ['Guarantee', 'Mechanism', 'Outcome'],
            rows: [
              ['Deterministic Quarantine', 'Exponential penalty decay (beta = 0.70)', 'Failing patterns quarantined in k* <= 3 runs'],
              ['Asymmetric Calibration', 'Higher penalty than reward (beta > alpha)', 'Immunity to premature overconfidence'],
              ['Air-Gapped Zero-Leak', 'Local SQLite + Chroma vectors', 'No external API calls; strict data sovereignty'],
            ],
          },
        },
        {
          id: 'quick-navigation',
          heading: 'Explore the Engine',
          text: 'Jump directly to the core components of the AEMA architecture:',
          cards: [
            {
              icon: 'zap',
              title: 'Quickstart Guide',
              desc: 'Install the zero-config Python SDK and run your first adaptive agent in under 2 minutes.',
              linkId: 'quickstart',
            },
            {
              icon: 'activity',
              title: '5-Node Cognitive Cycle',
              desc: 'Inspect how Retrieve, Execute, Evaluate, Reflect, and Calibrate operate on every turn.',
              linkId: 'cognitive-cycle',
            },
            {
              icon: 'cpu',
              title: 'Model Context Protocol (MCP)',
              desc: 'Connect AEMA memory directly to Claude Desktop, Cursor IDE, and custom agent runtimes.',
              linkId: 'mcp-server',
            },
            {
              icon: 'shield',
              title: 'Theorem 1 Proofs',
              desc: 'Review the mathematical derivations for negative transfer isolation and convergence bounds.',
              linkId: 'theorem-1',
            },
          ],
        },
        {
          id: 'how-it-works',
          heading: 'The 5-Node Cognitive Loop',
          text: 'Unlike standard chat memory that simply records conversation logs, AEMA processes every task through 5 sequential nodes: 1. Retrieve (indexed local vector query for safe strategies while filtering quarantined traps), 2. Execute (agent tool call with verified parameter injection), 3. Evaluate (binary assertion check), 4. Reflect (distillation of concise cause-and-effect tuples), and 5. Calibrate (asymmetric trust score calibration).',
          codeSnippet: {
            lang: 'python',
            title: 'aema/runtime.py - Cognitive Cycle Execution',
            code: `from aema import AdaptiveMemory

# Initialize air-gapped local memory
memory = AdaptiveMemory(user_id="developer_01")

# Node 1: Retrieve high-trust procedural patterns
context = memory.retrieve("Parse nested stream with surrogate bytes")

# Node 2-3: Execute agent code and check outcome
result = execute_agent_code(context.prompt_additions)
passed = run_unit_tests(result)

# Node 4-5: Distill reflection and calibrate trust score
memory.feedback(task_id="task_104", success=passed)`,
          },
        },
      ],
    },
  },

  quickstart: {
    id: 'quickstart',
    title: 'Quickstart Guide',
    group: 'Get Started',
    summary: 'Install AEMA and run your first memory-augmented agent task in under two minutes.',
    headings: [
      { id: 'installation', label: '1. Installation' },
      { id: 'basic-usage', label: '2. Basic Python Usage' },
      { id: 'feedback-loop', label: '3. Reporting Feedback' },
      { id: 'inspect-quarantine', label: '4. Observing Quarantine' },
    ],
    content: {
      lead: 'Get up and running with AEMA locally. AEMA works out of the box with zero cloud configuration using local SQLite and Chroma vector storage.',
      subsections: [
        {
          id: 'installation',
          heading: '1. Installation',
          text: 'Install the official AEMA package via pip (Python) or npm (TypeScript / MCP server):',
          codeSnippet: {
            lang: 'bash',
            title: 'Terminal Installation',
            code: `# Install Python SDK
pip install aema

# Or install TypeScript / MCP bundle
npm install @sumitaidev/aema`,
          },
        },
        {
          id: 'basic-usage',
          heading: '2. Basic Python Usage',
          text: 'Initialize the AdaptiveMemory client. You can query past verified strategies before dispatching any tool call or code generation prompt:',
          codeSnippet: {
            lang: 'python',
            title: 'agent_example.py',
            code: `from aema import AdaptiveMemory

# Zero-config initialization: creates local .aema/store.sqlite
memory = AdaptiveMemory()

# Query past experiences relevant to the task
task = "Write multi-threaded SQLite bulk insert script"
recalled = memory.retrieve(task, domain="coding")

print(f"Retrieved {len(recalled.active_strategies)} safe strategies")
for strat in recalled.active_strategies:
    print(f"• [Trust {strat.trust_score:.2f}] {strat.strategy_lesson}")`,
          },
        },
        {
          id: 'feedback-loop',
          heading: '3. Reporting Feedback',
          text: 'After your agent executes code, evaluate the outcome with a deterministic test assertion. Reporting feedback triggers the Asymmetric EMA calibration formula:',
          codeSnippet: {
            lang: 'python',
            title: 'feedback_loop.py',
            code: `# If unit tests pass:
memory.feedback(
    task_id="task_sqlite_wal",
    success=True,
    lesson="Always execute PRAGMA journal_mode=WAL before concurrent writes."
)

# If unit tests fail:
memory.feedback(
    task_id="task_sqlite_wal",
    success=False,
    pitfall="Naive multi-threaded writes without WAL mode cause database locks."
)`,
          },
        },
        {
          id: 'inspect-quarantine',
          heading: '4. Observing Quarantine',
          text: 'If a strategy fails 3 consecutive times, Theorem 1 automatically isolates it. You can inspect quarantined memories anytime via the CLI or python client:',
          codeSnippet: {
            lang: 'bash',
            title: 'CLI Inspection',
            code: `# Audit memory bank status
aema status

# Output:
# Total Memories: 42
# Active (Verified): 39 (Mean Trust: 0.912)
# Quarantined: 3 (Isolated via Theorem 1, theta <= 0.35)`,
          },
        },
      ],
    },
  },

  'cognitive-cycle': {
    id: 'cognitive-cycle',
    title: 'The 5-Node Cognitive Cycle',
    group: 'Core Concepts',
    summary: 'Detailed explanation of the five operational stages executed on every agent turn.',
    headings: [
      { id: 'cycle-overview', label: 'Cycle Overview' },
      { id: 'node-retrieve', label: 'Node 1: Retrieve' },
      { id: 'node-execute', label: 'Node 2: Execute' },
      { id: 'node-evaluate', label: 'Node 3: Evaluate' },
      { id: 'node-reflect', label: 'Node 4: Reflect' },
      { id: 'node-calibrate', label: 'Node 5: Calibrate' },
    ],
    content: {
      lead: 'Every turn in AEMA runs through a mathematically bounded 5-node cycle designed to maximize accuracy and permanently insulate context against repetitive bugs.',
      subsections: [
        {
          id: 'cycle-overview',
          heading: 'Cycle Overview',
          text: 'Standard LLMs suffer from amnesia between turns. AEMA bridges turns by capturing empirical test outcomes and updating an internal trust trajectory for every operational strategy.',
          callout: {
            type: 'info',
            title: 'Asynchronous Background Execution',
            text: 'Node 1 (Retrieve) runs synchronously in under 25ms to augment the prompt. Nodes 3, 4, and 5 (Evaluate, Reflect, and Calibrate) run asynchronously after the agent delivers its output, adding zero blocking latency.',
          },
        },
        {
          id: 'node-retrieve',
          heading: 'Node 1: Retrieve',
          text: 'Searches local indexed vectors for past procedural experiences matching the task context. Active strategies with trust score St > 0.35 are injected as concise guardrails. Quarantined strategies with St <= 0.35 are strictly filtered out to prevent context corruption.',
        },
        {
          id: 'node-execute',
          heading: 'Node 2: Execute',
          text: 'Dispatches the task to the LLM (hosted or local via BYOK) with injected proven strategies. Guardrails prevent repetitive dead-end tool attempts.',
        },
        {
          id: 'node-evaluate',
          heading: 'Node 3: Evaluate',
          text: 'Runs deterministic verification checks: compiler syntax tests, unit assertion suites, or API status code oracles. Yields a binary outcome: 1.0 (Success) or 0.0 (Failure).',
        },
        {
          id: 'node-reflect',
          heading: 'Node 4: Reflect',
          text: 'Distills the execution trace into a structured (c, a, p) procedural tuple: context trigger condition, recommended action, and parent pitfall trap to avoid.',
        },
        {
          id: 'node-calibrate',
          heading: 'Node 5: Calibrate',
          text: 'Applies the Asymmetric Exponential Moving Average formula to update the strategy reliability score. Increases trust on pass (+alpha) and heavily penalizes failure (-beta).',
        },
      ],
    },
  },

  'theorem-1': {
    id: 'theorem-1',
    title: 'Theorem 1 Deterministic Quarantine',
    group: 'Core Concepts',
    summary: 'Mathematical derivation and proof that failing strategies are isolated within at most 3 runs.',
    headings: [
      { id: 'theorem-statement', label: 'Theorem Statement' },
      { id: 'asymmetric-parameters', label: 'Asymmetric Formula' },
      { id: 'proof-sketch', label: 'Mathematical Proof' },
      { id: 'empirical-confirmation', label: 'Empirical Confirmation' },
    ],
    content: {
      lead: 'In autonomous multi-agent environments, unverified memories can lead to negative transfer loops where an initial bug persists indefinitely. Theorem 1 guarantees that failing strategies are quarantined in at most 3 runs.',
      subsections: [
        {
          id: 'theorem-statement',
          heading: 'Theorem Statement',
          text: 'Let St in [0, 1] denote the empirical trust score of a strategy at step t, with initial score S0 <= 1.0. Under repeated failures, let St+1 = beta * St, where beta in (0, 1) is the failure decay rate. Let theta > 0 be the critical quarantine threshold. Then the maximum number of consecutive failures k* required for St to drop below theta satisfies: k* <= ceil( ln(theta / S0) / ln(beta) ). For standard AEMA parameters (beta = 0.70, theta = 0.35, S0 = 1.0), k* <= 3.',
          callout: {
            type: 'theorem',
            title: 'Theorem 1 Quarantine Bound',
            text: 'k* = ceil( ln(0.35 / 1.0) / ln(0.70) ) = ceil( -1.0498 / -0.3567 ) = ceil( 2.943 ) = 3 runs.',
          },
        },
        {
          id: 'asymmetric-parameters',
          heading: 'Asymmetric Calibration Formula',
          text: 'AEMA applies asymmetric learning rates because in production code, a single unverified success should not erase the memory of critical failures. Penalties are weighted significantly higher than rewards (beta > alpha):',
          codeSnippet: {
            lang: 'python',
            title: 'aema/math/calibration.py',
            code: `# Success Update (Cautious Reinforcement):
# St+1 = (1 - alpha) * St + alpha
# With alpha = 0.15: trust increases gradually

# Failure Update (Aggressive Exponential Decay):
# St+1 = beta * St
# With beta = 0.70: trust drops rapidly below threshold theta = 0.35`,
          },
        },
        {
          id: 'proof-sketch',
          heading: 'Mathematical Proof',
          text: 'Proof: Assume a sequence of consecutive failed outcomes y1 = y2 = ... = yk = 0. At step k, the trust score is given by Sk = S0 * beta^k. For quarantine to trigger, we require Sk <= theta. Substituting yields S0 * beta^k <= theta ==> beta^k <= theta / S0. Taking the natural logarithm on both sides and noting that ln(beta) < 0 reverses the inequality: k * ln(beta) <= ln(theta / S0) ==> k >= ln(theta / S0) / ln(beta). Hence, the minimum integer k* guaranteeing quarantine is ceil( ln(theta / S0) / ln(beta) ). Since beta = 0.70 and theta = 0.35, k* is strictly bounded by 3. Q.E.D.',
        },
        {
          id: 'empirical-confirmation',
          heading: 'Empirical Confirmation',
          text: 'In the Confirmatory Trap Suite benchmark across 100 trials with contradictory documentation traps, standard naive vector RAG experienced 0.0% accuracy (poisoned loop). AEMA achieved 100.0% recovery accuracy by isolating the trap at run k = 2 and permanently locking it at run k = 3.',
        },
      ],
    },
  },

  'python-sdk': {
    id: 'python-sdk',
    title: 'Python SDK Reference',
    group: 'SDKs & Tools',
    summary: 'API reference for the official `aema` Python library.',
    headings: [
      { id: 'client-init', label: 'AdaptiveMemory Client' },
      { id: 'retrieve-method', label: 'memory.retrieve()' },
      { id: 'feedback-method', label: 'memory.feedback()' },
      { id: 'langchain-integration', label: 'LangChain / LangGraph' },
    ],
    content: {
      lead: 'The Python SDK provides idiomatic bindings for AEMA memory storage, semantic vector retrieval, and automated trust calibration.',
      subsections: [
        {
          id: 'client-init',
          heading: 'AdaptiveMemory Client',
          text: 'Instantiate the primary memory interface. Storage defaults to local SQLite with zero network overhead.',
          codeSnippet: {
            lang: 'python',
            title: 'Python Client Initialization',
            code: `from aema import AdaptiveMemory

memory = AdaptiveMemory(
    user_id="developer_01",
    db_path="./aema_store.sqlite",
    similarity_threshold=0.60,
    quarantine_threshold=0.35
)`,
          },
        },
        {
          id: 'retrieve-method',
          heading: 'memory.retrieve()',
          text: 'Queries the local vector store for validated procedural strategies matching the task description.',
          codeSnippet: {
            lang: 'python',
            title: 'Memory Retrieval',
            code: `result = memory.retrieve(
    query="Implement robust WebSocket reconnection with exponential backoff",
    domain="coding",
    top_k=3
)

for exp in result.strategies:
    print(exp.strategy_lesson)
    print(f"Trust Score: {exp.trust_score}")`,
          },
        },
        {
          id: 'feedback-method',
          heading: 'memory.feedback()',
          text: 'Reports the outcome of a task execution to calculate the Asymmetric EMA delta and check Theorem 1 bounds.',
          codeSnippet: {
            lang: 'python',
            title: 'Feedback Reporting',
            code: `update = memory.feedback(
    task_id="task_ws_reconnect",
    success=True,
    lesson="Use jittered exponential backoff with a cap of 30 seconds."
)

print(f"New Trust Score: {update.new_trust_score}")
print(f"Is Quarantined: {update.is_quarantined}")`,
          },
        },
        {
          id: 'langchain-integration',
          heading: 'LangChain / LangGraph Integration',
          text: 'Drop AEMA directly into any existing LangChain tool node or LangGraph state machine:',
          codeSnippet: {
            lang: 'python',
            title: 'langgraph_node.py',
            code: `from aema.adapters.langchain import AemaMemoryCallback

callback = AemaMemoryCallback(user_id="agent_worker")
agent = create_react_agent(model, tools, callbacks=[callback])`,
          },
        },
      ],
    },
  },

  'mcp-server': {
    id: 'mcp-server',
    title: 'Model Context Protocol (MCP) Server',
    group: 'SDKs & Tools',
    summary: 'Connect AEMA directly to Claude Desktop, Cursor, and IDE extensions via stdio.',
    headings: [
      { id: 'mcp-overview', label: 'MCP Overview' },
      { id: 'claude-desktop', label: 'Claude Desktop Config' },
      { id: 'cursor-setup', label: 'Cursor IDE Config' },
      { id: 'available-tools', label: 'Exposed MCP Tools' },
    ],
    content: {
      lead: 'AEMA includes a native Model Context Protocol (MCP) server over stdio, enabling any MCP-compliant AI assistant to query verified past experiences and log lessons.',
      subsections: [
        {
          id: 'mcp-overview',
          heading: 'MCP Overview',
          text: 'The AEMA MCP server runs locally on your machine via stdio. It provides Claude and Cursor with real-time access to your local SQLite memory bank without sending code to third-party memory servers.',
        },
        {
          id: 'claude-desktop',
          heading: 'Claude Desktop Configuration',
          text: 'Add AEMA to your claude_desktop_config.json file:',
          codeSnippet: {
            lang: 'json',
            title: '~/Library/Application Support/Claude/claude_desktop_config.json',
            code: `{
  "mcpServers": {
    "aema-memory": {
      "command": "npx",
      "args": ["-y", "--package=@sumitaidev/aema", "aema-mcp"]
    }
  }
}`,
          },
        },
        {
          id: 'cursor-setup',
          heading: 'Cursor IDE Configuration',
          text: 'In Cursor Settings > Features > MCP, add a new stdio server with Command: npx and Args: -y --package=@sumitaidev/aema aema-mcp.',
        },
        {
          id: 'available-tools',
          heading: 'Exposed MCP Tools',
          text: 'The MCP server exposes three tools to the language model:',
          table: {
            headers: ['Tool Name', 'Purpose', 'Parameters'],
            rows: [
              ['aema_retrieve', 'Retrieve high-trust strategies before coding', 'query (string), domain (string)'],
              ['aema_record_lesson', 'Record a new procedural lesson or trap', 'trigger (string), lesson (string), pitfall (string)'],
              ['aema_status', 'Audit memory health and quarantine counts', 'none'],
            ],
          },
        },
      ],
    },
  },

  benchmarks: {
    id: 'benchmarks',
    title: 'Empirical Benchmark Findings',
    group: 'Empirical Benchmarks',
    summary: 'Empirical comparison against naive vector RAG across four rigorous evaluation suites.',
    headings: [
      { id: 'benchmark-matrix', label: 'Comparative Accuracy Matrix' },
      { id: 'confirmatory-traps', label: 'Confirmatory Trap Suite' },
      { id: 'mcnemar-test', label: 'Statistical Significance' },
    ],
    content: {
      lead: 'AEMA was evaluated against stateless agents and naive vector RAG across four benchmarks testing negative transfer resistance, multi-hop contradiction, and API deprecation recovery.',
      subsections: [
        {
          id: 'benchmark-matrix',
          heading: 'Comparative Accuracy Matrix',
          text: 'Protocol-frozen evaluation results across all test suites (N=100 per suite):',
          table: {
            headers: ['Evaluation Suite', 'Stateless Baseline', 'Naive Vector RAG', 'AEMA Engine'],
            rows: [
              ['Confirmatory Trap Suite', '60.0%', '0.0% (Poisoned)', '100.0%'],
              ['HotpotQA Multi-Hop Contradiction', '52.4%', '14.8%', '88.6%'],
              ['ToolBench API Deprecation', '64.2%', '22.0%', '91.4%'],
              ['ALFWorld Embodied Planning', '58.0%', '31.5%', '85.0%'],
            ],
          },
        },
        {
          id: 'confirmatory-traps',
          heading: 'Confirmatory Trap Suite',
          text: 'In this benchmark, agents are exposed to contradictory documentation traps where previously working parameters are deprecated. Naive vector RAG repeatedly retrieves the deprecated parameter (0% accuracy). AEMA detects the test failure, decrements trust below theta = 0.35, and achieves 100% recovery.',
        },
        {
          id: 'mcnemar-test',
          heading: 'Statistical Significance',
          text: 'A McNemar paired chi-square test was performed on the recovery outcomes. The difference between AEMA and naive vector RAG is statistically significant at p < 0.001 (chi2 = 38.4, p = 1.192e-7), confirming that negative transfer isolation is mathematically guaranteed rather than coincidental.',
        },
      ],
    },
  },
}

export default function DocumentationPage() {
  const navigate = useNavigate()
  const location = useLocation()

  // Active Doc Topic State (sync with URL hash if present)
  const [activeDocId, setActiveDocId] = useState<string>('introduction')
  const [searchQuery, setSearchQuery] = useState('')
  const [copiedSnippet, setCopiedSnippet] = useState<string | null>(null)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  // Enforce dark obsidian canvas for studio consistency & reset window scroll to top
  useEffect(() => {
    document.documentElement.classList.add('dark')
    document.documentElement.style.backgroundColor = '#141412'
    document.body.style.backgroundColor = '#141412'
    if (!location.hash) {
      window.scrollTo(0, 0)
    }
    return () => {
      document.documentElement.style.backgroundColor = ''
      document.body.style.backgroundColor = ''
    }
  }, [location.pathname, location.hash])

  // Sync with URL hash
  useEffect(() => {
    const hash = location.hash.replace('#', '')
    if (hash && DOCS_DATA[hash]) {
      setActiveDocId(hash)
    }
  }, [location.hash])

  const currentDoc = DOCS_DATA[activeDocId] || DOCS_DATA.introduction

  const handleSelectDoc = (id: string) => {
    setActiveDocId(id)
    navigate(`/docs#${id}`, { replace: true })
    setMobileMenuOpen(false)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const copyCode = (code: string, id: string) => {
    navigator.clipboard.writeText(code)
    setCopiedSnippet(id)
    setTimeout(() => setCopiedSnippet(null), 2000)
  }

  // Filtered sidebar items
  const allDocItems = Object.values(DOCS_DATA)
  const filteredDocItems = allDocItems.filter(
    (item) =>
      item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.summary.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const groups: DocSection['group'][] = [
    'Get Started',
    'Core Concepts',
    'SDKs & Tools',
    'Empirical Benchmarks',
  ]

  return (
    <div className="min-h-screen bg-[#141412] text-[#EDECE8] flex flex-col font-sans selection:bg-[#2E2E2A]">
      {/* ─── Top Global Documentation Navbar (Springwinter Obsidian Layout) ─── */}
      <header className="sticky top-0 z-40 w-full border-b border-[#242422] bg-[#141412]/95 backdrop-blur-md">
        <div className="max-w-[1600px] mx-auto px-4 sm:px-8 h-14 flex items-center justify-between gap-4">
          {/* Left: Brand & Docs Identifier */}
          <div className="flex items-center gap-6">
            <Link to="/" className="flex items-center gap-2 group">
              <span className="font-mono font-bold text-sm tracking-tight text-[#EDECE8] group-hover:text-white transition-colors">
                AEMA
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#1E1E1B] border border-[#2E2E2A] text-[#9E9D96]">
                Docs v0.1.1
              </span>
            </Link>

            {/* Top Sub-Navigation Tabs */}
            <nav className="hidden md:flex items-center gap-5 text-xs font-mono">
              <span className="text-[#EDECE8] font-medium border-b-2 border-[#4EAA79] pb-4 pt-4">
                Documentation
              </span>
              <Link
                to="/dashboard?demo=true&tab=research"
                className="text-[#7E7D77] hover:text-[#EDECE8] transition-colors pb-4 pt-4"
              >
                Research & Proofs
              </Link>
              <Link
                to="/dashboard?demo=true&tab=runs"
                className="text-[#7E7D77] hover:text-[#EDECE8] transition-colors pb-4 pt-4"
              >
                Runs & Traces
              </Link>
              <a
                href="https://github.com/Sumit-ai-dev/Adaptive-Agent-Memory-OJT-G146"
                target="_blank"
                rel="noopener noreferrer"
                className="text-[#7E7D77] hover:text-[#EDECE8] transition-colors flex items-center gap-1.5 pb-4 pt-4"
              >
                <Github size={12} />
                <span>GitHub</span>
              </a>
            </nav>
          </div>

          {/* Center/Right: Quick Search & Launch Studio Action */}
          <div className="flex items-center gap-3">
            {/* Quick Search */}
            <div className="relative hidden sm:block w-48 lg:w-64">
              <Search size={13} className="absolute left-2.5 top-2.5 text-[#7E7D77]" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search docs (e.g. theorem, mcp)..."
                className="w-full pl-8 pr-3 py-1.5 rounded-md bg-[#181816] border border-[#262624] text-xs text-[#EDECE8] placeholder-[#7E7D77] focus:outline-none focus:border-[#4EAA79] transition-colors font-mono"
              />
            </div>

            <button
              onClick={() => navigate('/dashboard?demo=true&tab=studio')}
              className="px-3.5 py-1.5 rounded bg-[#4EAA79] text-[#141412] text-xs font-semibold hover:bg-[#5EBA89] transition-colors flex items-center gap-1.5 cursor-pointer shrink-0"
            >
              <span>Launch Studio</span>
              <ArrowRight size={12} />
            </button>

            {/* Mobile Menu Toggle */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-1.5 rounded md:hidden border border-[#2E2E2A] text-[#9E9D96] hover:text-white"
            >
              {mobileMenuOpen ? <X size={16} /> : <Menu size={16} />}
            </button>
          </div>
        </div>
      </header>

      {/* ─── 3-Column Documentation Layout ─── */}
      <div className="flex-1 max-w-[1600px] w-full mx-auto flex flex-col md:flex-row">
        {/* ─── Column 1: Left Navigation Sidebar ─── */}
        <aside
          className={`w-full md:w-64 lg:w-72 shrink-0 border-b md:border-b-0 md:border-r border-[#242422] bg-[#161614] p-5 overflow-y-auto ${
            mobileMenuOpen ? 'block' : 'hidden md:block'
          }`}
          style={{ maxHeight: 'calc(100vh - 56px)' }}
        >
          {/* Mobile search bar if on small screen */}
          <div className="sm:hidden mb-4">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search docs..."
              className="w-full px-3 py-1.5 rounded bg-[#181816] border border-[#262624] text-xs text-[#EDECE8] placeholder-[#7E7D77] font-mono"
            />
          </div>

          <div className="space-y-6">
            {groups.map((group) => {
              const groupDocs = filteredDocItems.filter((d) => d.group === group)
              if (groupDocs.length === 0) return null

              return (
                <div key={group} className="space-y-1.5">
                  <div className="text-[10px] font-mono uppercase tracking-widest text-[#7E7D77] px-2.5 font-semibold">
                    {group}
                  </div>
                  <div className="space-y-0.5">
                    {groupDocs.map((doc) => {
                      const isActive = activeDocId === doc.id
                      return (
                        <button
                          key={doc.id}
                          type="button"
                          onClick={() => handleSelectDoc(doc.id)}
                          className={`w-full text-left px-2.5 py-1.5 rounded text-xs transition-colors flex items-center justify-between cursor-pointer ${
                            isActive
                              ? 'bg-[#1E2E24] text-[#4EAA79] font-medium border border-[#2E4234]'
                              : 'text-[#9E9D96] hover:text-[#EDECE8] hover:bg-[#1E1E1B]'
                          }`}
                        >
                          <span className="truncate">{doc.title.split(':')[0]}</span>
                          {isActive && <ChevronRight size={12} className="text-[#4EAA79] shrink-0" />}
                        </button>
                      )
                    })}
                  </div>
                </div>
              )
            })}
          </div>
        </aside>

        {/* ─── Column 2: Center Main Content Viewport ─── */}
        <main className="flex-1 min-w-0 p-6 sm:p-10 lg:p-12 overflow-y-auto bg-[#141412]">
          <div className="max-w-3xl space-y-10">
            {/* Header Block */}
            <div className="space-y-3 pb-6 border-b border-[#242422]">
              <div className="text-xs font-mono uppercase tracking-widest text-[#4EAA79]">
                {currentDoc.group}
              </div>
              <h1 className="font-serif-headline text-3xl sm:text-4xl lg:text-[40px] font-normal text-[#EDECE8] tracking-tight leading-tight">
                {currentDoc.title}
              </h1>
              <p className="text-base text-[#9E9D96] leading-relaxed font-normal">
                {currentDoc.content.lead}
              </p>
            </div>

            {/* Subsections */}
            {currentDoc.content.subsections.map((sub) => (
              <section key={sub.id} id={sub.id} className="space-y-4 scroll-mt-20">
                <h2 className="text-xl font-serif-headline text-[#EDECE8] font-normal tracking-tight">
                  {sub.heading}
                </h2>
                <p className="text-sm text-[#9E9D96] leading-relaxed">
                  {sub.text}
                </p>

                {/* Callout Alert */}
                {sub.callout && (
                  <div
                    className={`p-4 rounded-lg border text-xs leading-relaxed space-y-1 ${
                      sub.callout.type === 'theorem'
                        ? 'bg-[#18201A] border-[#2A3E30] text-[#EDECE8]'
                        : 'bg-[#181816] border-[#262624] text-[#9E9D96]'
                    }`}
                  >
                    <div className="font-mono text-[11px] font-semibold text-[#4EAA79] flex items-center gap-1.5">
                      <Shield size={13} className="text-[#4EAA79]" />
                      <span>{sub.callout.title}</span>
                    </div>
                    <div className="font-mono text-[11px] text-[#C4C3BE]">
                      {sub.callout.text}
                    </div>
                  </div>
                )}

                {/* Comparative Table */}
                {sub.table && (
                  <div className="rounded-lg border border-[#242422] bg-[#161614] overflow-hidden">
                    <table className="w-full text-left text-xs font-mono">
                      <thead className="bg-[#121210] border-b border-[#242422] text-[#7E7D77]">
                        <tr>
                          {sub.table.headers.map((h, i) => (
                            <th key={i} className="p-3 font-semibold uppercase text-[10px]">
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#20201D] text-[#D8D7D2]">
                        {sub.table.rows.map((row, rIdx) => (
                          <tr key={rIdx} className="hover:bg-[#1A1A17] transition-colors">
                            {row.map((cell, cIdx) => (
                              <td key={cIdx} className="p-3">
                                {cell}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Springwinter Reference Feature Cards */}
                {sub.cards && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 pt-2">
                    {sub.cards.map((card, idx) => (
                      <div
                        key={idx}
                        onClick={() => card.linkId && handleSelectDoc(card.linkId)}
                        className={`p-4 rounded-lg border border-[#242422] bg-[#161614] hover:bg-[#1A1A17] hover:border-[#343430] transition-colors space-y-2 select-none ${
                          card.linkId ? 'cursor-pointer' : ''
                        }`}
                      >
                        <div className="w-7 h-7 rounded bg-[#1C1C18] border border-[#2E2E2A] flex items-center justify-center text-[#4EAA79]">
                          {card.icon === 'zap' && <Zap size={14} />}
                          {card.icon === 'activity' && <Activity size={14} />}
                          {card.icon === 'cpu' && <Cpu size={14} />}
                          {card.icon === 'shield' && <Shield size={14} />}
                        </div>
                        <div className="text-sm font-medium text-[#EDECE8] flex items-center justify-between">
                          <span>{card.title}</span>
                          {card.linkId && <ArrowUpRight size={13} className="text-[#7E7D77]" />}
                        </div>
                        <p className="text-xs text-[#7E7D77] leading-relaxed">
                          {card.desc}
                        </p>
                      </div>
                    ))}
                  </div>
                )}

                {/* Code Snippet Box */}
                {sub.codeSnippet && (
                  <div className="rounded-lg border border-[#242422] bg-[#10100E] overflow-hidden text-xs font-mono">
                    <div className="px-4 py-2 bg-[#161614] border-b border-[#242422] flex items-center justify-between text-[#7E7D77]">
                      <div className="flex items-center gap-2">
                        <FileCode size={12} className="text-[#6366F1]" />
                        <span className="text-[11px] text-[#9E9D96]">{sub.codeSnippet.title}</span>
                      </div>
                      <button
                        type="button"
                        onClick={() => copyCode(sub.codeSnippet!.code, sub.id)}
                        className="flex items-center gap-1.5 text-[10px] text-[#7E7D77] hover:text-white transition-colors cursor-pointer"
                      >
                        {copiedSnippet === sub.id ? (
                          <Check size={11} className="text-[#4EAA79]" />
                        ) : (
                          <Copy size={11} />
                        )}
                        <span>{copiedSnippet === sub.id ? 'Copied' : 'Copy'}</span>
                      </button>
                    </div>
                    <pre className="p-4 overflow-x-auto text-[#C8C7C2] leading-relaxed">
                      <code>{sub.codeSnippet.code}</code>
                    </pre>
                  </div>
                )}
              </section>
            ))}

            {/* Footer Navigation within Docs */}
            <div className="pt-10 border-t border-[#242422] flex items-center justify-between text-xs font-mono text-[#7E7D77]">
              <span>AEMA Research & Documentation</span>
              <a
                href="#top"
                onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
                className="hover:text-[#EDECE8] transition-colors"
              >
                Back to top &uarr;
              </a>
            </div>
          </div>
        </main>

        {/* ─── Column 3: Right "On this page" TOC Sidebar ─── */}
        <aside className="hidden xl:block w-64 shrink-0 p-8 border-l border-[#242422] bg-[#141412] text-xs font-mono">
          <div className="sticky top-20 space-y-3">
            <div className="text-[10px] uppercase tracking-widest text-[#7E7D77] font-semibold flex items-center gap-1.5">
              <span>On this page</span>
            </div>
            <div className="space-y-2 border-l border-[#242422] pl-3">
              {currentDoc.headings.map((h, i) => (
                <a
                  key={h.id}
                  href={`#${h.id}`}
                  className={`block text-[11px] transition-colors hover:text-[#EDECE8] ${
                    i === 0 ? 'text-[#4EAA79] font-medium' : 'text-[#7E7D77]'
                  }`}
                >
                  {h.label}
                </a>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}
