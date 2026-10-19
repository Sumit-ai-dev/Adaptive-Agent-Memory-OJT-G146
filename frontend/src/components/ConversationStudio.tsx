import { useState, useEffect, useRef } from 'react'
import {
  MessageSquare,
  Plus,
  Send,
  Shield,
  Sparkles,
  ChevronDown,
  Cpu,
  KeyRound,
  PanelLeftClose,
  PanelLeftOpen,
  PanelRightClose,
  RefreshCw,
  ChevronRight,
  Database,
  Terminal,
  Activity,
  Check,
  X,
  User,
  Clock,
} from 'lucide-react'
import type { TaskDomain, TaskExecution, ChatMessage, SessionSummary } from '../types'
import { executeAgentTask, fetchSessions, fetchExecutions } from '../services/api'
import MarkdownRenderer from './MarkdownRenderer'
import ExecutionStepper from './ExecutionStepper'
import ContextInspector from './ContextInspector'

type ProviderType = 'gemini' | 'groq' | 'ollama' | 'openai' | 'mock'

interface ModelOption {
  id: ProviderType
  name: string
  subname: string
  logo?: string
  isIcon?: boolean
}

const MODEL_OPTIONS: ModelOption[] = [
  { id: 'groq', name: 'Groq Cloud', subname: 'Fast (Default)', logo: '/images/models/groq.webp' },
  { id: 'gemini', name: 'Google Gemini Flash', subname: 'Hosted', logo: '/images/models/gemini.webp' },
  { id: 'openai', name: 'GPT-4o Mini', subname: 'OpenAI', logo: '/images/models/openai.webp' },
  { id: 'ollama', name: 'Ollama Local', subname: 'llama3.2', logo: '/images/models/ollama.webp' },
  { id: 'mock', name: 'Deterministic Mock', subname: 'Offline / Test', isIcon: true },
]

const DOMAIN_OPTIONS: { id: TaskDomain; label: string }[] = [
  { id: 'coding', label: 'Coding' },
  { id: 'research', label: 'Research' },
  { id: 'analysis', label: 'Analysis' },
  { id: 'planning', label: 'Planning' },
  { id: 'general', label: 'General' },
]

const STARTER_PROMPTS = [
  {
    title: 'Safe JSON Parsing Pattern',
    prompt: 'Implement a recursive Python function to safely extract values from deeply nested JSON with fallbacks.',
    domain: 'coding' as TaskDomain,
  },
  {
    title: 'Multi-Hop Research Synthesis',
    prompt: 'Analyze trade-offs between dense semantic retrieval and sparse BM25 indexing in agent architectures.',
    domain: 'research' as TaskDomain,
  },
  {
    title: 'Negative Transfer Trap Test',
    prompt: 'Execute a coding task that intentionally tests handling of deprecated API parameters and trap isolation.',
    domain: 'coding' as TaskDomain,
  },
]

interface ConversationMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  execution?: TaskExecution
}

interface ConversationStudioProps {
  onExecutionComplete?: (execution: TaskExecution) => void
}

export default function ConversationStudio({ onExecutionComplete }: ConversationStudioProps) {
  // Session States
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<string>(() => `sess_${Date.now()}`)
  const [sessionTitle, setSessionTitle] = useState<string>('New Conversation')
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(true)
  const [isInspectorOpen, setIsInspectorOpen] = useState<boolean>(false)

  // Message & Stream States
  const [messages, setMessages] = useState<ConversationMessage[]>([])
  const [inputText, setInputText] = useState('')
  const [isExecuting, setIsExecuting] = useState(false)
  const [currentStage, setCurrentStage] = useState<'retrieval' | 'execution' | 'evaluation' | 'reflection' | 'trust_update' | 'idle' | 'complete'>('idle')
  const [selectedExecution, setSelectedExecution] = useState<TaskExecution | null>(null)
  const [expandedTraceMsgId, setExpandedTraceMsgId] = useState<string | null>(null)

  // Configuration States
  const [domain, setDomain] = useState<TaskDomain>('coding')
  const [provider, setProvider] = useState<ProviderType>('groq')
  const [memoryEnabled, setMemoryEnabled] = useState(true)
  const [simulateFailure, setSimulateFailure] = useState(false)
  const [isModelDropdownOpen, setIsModelDropdownOpen] = useState(false)
  const [showKeyModal, setShowKeyModal] = useState(false)
  const [apiKeys, setApiKeys] = useState<Record<string, string>>(() => {
    try {
      const saved = localStorage.getItem('aema_byok_keys')
      return saved ? JSON.parse(saved) : {}
    } catch {
      return {}
    }
  })

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const modelDropdownRef = useRef<HTMLDivElement>(null)

  // Auto-scroll on message changes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isExecuting])

  // Click outside to close dropdowns
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (modelDropdownRef.current && !modelDropdownRef.current.contains(event.target as Node)) {
        setIsModelDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Load existing sessions on mount
  useEffect(() => {
    loadSessions()
  }, [])

  const loadSessions = async () => {
    const list = await fetchSessions(30)
    setSessions(list)
  }

  // Restore session executions when currentSessionId changes
  const switchSession = async (sessionId: string) => {
    if (sessionId === currentSessionId && messages.length > 0) return
    setCurrentSessionId(sessionId)
    const matchingSession = sessions.find((s) => s.sessionId === sessionId)
    setSessionTitle(matchingSession?.title || 'Conversation')

    // Fetch executions for this session from SQLite
    const runs = await fetchExecutions(50, sessionId)
    if (runs && runs.length > 0) {
      // Sort chronologically (oldest to newest)
      const sorted = [...runs].sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime())
      const reconstructed: ConversationMessage[] = []
      sorted.forEach((run, idx) => {
        // User turn
        reconstructed.push({
          id: `msg_u_${run.id}_${idx}`,
          role: 'user',
          content: run.taskInput,
          timestamp: run.createdAt,
        })
        // Assistant turn
        reconstructed.push({
          id: `msg_a_${run.id}_${idx}`,
          role: 'assistant',
          content: run.finalAnswer || run.finalOutput || 'No output generated',
          timestamp: run.createdAt,
          execution: run,
        })
      })
      setMessages(reconstructed)
      setSelectedExecution(sorted[sorted.length - 1])
    } else {
      setMessages([])
      setSelectedExecution(null)
    }
  }

  const startNewSession = () => {
    const newId = `sess_${Date.now()}`
    setCurrentSessionId(newId)
    setSessionTitle('New Conversation')
    setMessages([])
    setSelectedExecution(null)
    setInputText('')
    textareaRef.current?.focus()
  }

  const handleSendMessage = async (customPrompt?: string) => {
    const promptToSend = (customPrompt || inputText).trim()
    if (!promptToSend || isExecuting) return

    setInputText('')
    setIsExecuting(true)
    setCurrentStage('retrieval')

    // If first message in this session, update session title
    if (messages.length === 0) {
      const shortTitle = promptToSend.slice(0, 42) + (promptToSend.length > 42 ? '...' : '')
      setSessionTitle(shortTitle)
    }

    // Add user message to UI stream immediately
    const userMsgId = `user_${Date.now()}`
    const userMsg: ConversationMessage = {
      id: userMsgId,
      role: 'user',
      content: promptToSend,
      timestamp: new Date().toISOString(),
    }
    const updatedMessages = [...messages, userMsg]
    setMessages(updatedMessages)

    // Build chat history payload for backend (role, content)
    const historyPayload: ChatMessage[] = updatedMessages.map((m) => ({
      role: m.role,
      content: m.content,
    }))

    try {
      const activeKey = apiKeys[provider] || undefined
      const exec = await executeAgentTask({
        taskInput: promptToSend,
        taskDomain: domain,
        memoryEnabled,
        provider,
        apiKey: activeKey,
        sessionId: currentSessionId,
        messages: historyPayload,
        simulateFailure,
        onStageChange: (stage) => setCurrentStage(stage),
      })

      // Add assistant response to UI stream
      const asstMsg: ConversationMessage = {
        id: `asst_${Date.now()}`,
        role: 'assistant',
        content: exec.finalAnswer || exec.finalOutput || 'Completed with verified strategies.',
        timestamp: exec.createdAt,
        execution: exec,
      }
      setMessages((prev) => [...prev, asstMsg])
      setSelectedExecution(exec)
      onExecutionComplete?.(exec)

      // Refresh recent sessions list
      loadSessions()
    } catch (err) {
      const errorMsg: ConversationMessage = {
        id: `asst_err_${Date.now()}`,
        role: 'assistant',
        content: `Error executing task turn: ${err instanceof Error ? err.message : String(err)}`,
        timestamp: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, errorMsg])
    } finally {
      setIsExecuting(false)
      setCurrentStage('idle')
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const saveApiKey = (keyVal: string) => {
    const updated = { ...apiKeys, [provider]: keyVal.trim() }
    setApiKeys(updated)
    try {
      localStorage.setItem('aema_byok_keys', JSON.stringify(updated))
    } catch (e) {
      console.warn('Could not save BYOK key:', e)
    }
    setShowKeyModal(false)
  }

  const currentModel = MODEL_OPTIONS.find((m) => m.id === provider) || MODEL_OPTIONS[0]

  return (
    <div className="flex h-[calc(100vh-140px)] min-h-[640px] rounded-2xl border border-[#E6E6E1] dark:border-[#252B3B] bg-[#FAFAFA] dark:bg-[#0D1017] overflow-hidden shadow-sm">
      {/* ─── 1. SESSIONS SIDEBAR (COLLAPSIBLE) ─────────────────────────────── */}
      <div
        className={`${
          isSidebarOpen ? 'w-64' : 'w-0'
        } shrink-0 transition-all duration-300 ease-in-out border-r border-[#E6E6E1] dark:border-[#252B3B] bg-white dark:bg-[#131722] flex flex-col overflow-hidden`}
      >
        <div className="p-3 border-b border-[#E6E6E1] dark:border-[#252B3B] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MessageSquare size={16} className="text-indigo-600 dark:text-indigo-400" />
            <span className="text-xs font-semibold tracking-wide text-zinc-900 dark:text-zinc-100">
              Conversations
            </span>
          </div>
          <button
            onClick={() => setIsSidebarOpen(false)}
            className="p-1 rounded-lg text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
            title="Collapse sidebar"
          >
            <PanelLeftClose size={15} />
          </button>
        </div>

        {/* New Chat Button */}
        <div className="p-3">
          <button
            onClick={startNewSession}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-sm transition-all cursor-pointer"
          >
            <Plus size={15} />
            <span>New Chat</span>
          </button>
        </div>

        {/* Session List */}
        <div className="flex-1 overflow-y-auto px-2 py-1 space-y-1">
          {sessions.length === 0 && messages.length === 0 ? (
            <div className="p-4 text-center text-xs text-zinc-400 font-mono">
              No recent sessions.
            </div>
          ) : (
            sessions.map((s) => {
              const isActive = s.sessionId === currentSessionId
              return (
                <div
                  key={s.sessionId}
                  onClick={() => switchSession(s.sessionId)}
                  className={`group flex flex-col p-2.5 rounded-xl cursor-pointer text-left transition-all ${
                    isActive
                      ? 'bg-indigo-50/70 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800/60 shadow-xs'
                      : 'hover:bg-zinc-100/70 dark:hover:bg-[#1A1F2C] border border-transparent'
                  }`}
                >
                  <div className="flex items-center justify-between gap-1">
                    <span
                      className={`text-xs font-medium truncate ${
                        isActive
                          ? 'text-indigo-700 dark:text-indigo-300 font-semibold'
                          : 'text-zinc-700 dark:text-zinc-300'
                      }`}
                    >
                      {s.title}
                    </span>
                    <span className="shrink-0 text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-zinc-100 dark:bg-zinc-800 text-zinc-500">
                      {s.turnCount}
                    </span>
                  </div>
                  <span className="text-[10px] text-zinc-400 mt-1 flex items-center gap-1">
                    <Clock size={10} />
                    {new Date(s.lastActive).toLocaleDateString([], { month: 'short', day: 'numeric' })}
                  </span>
                </div>
              )
            })
          )}
        </div>
      </div>

      {/* ─── 2. MAIN CONVERSATION STREAM AREA ─────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 bg-transparent relative">
        {/* Top Control Bar */}
        <div className="px-4 py-2.5 border-b border-[#E6E6E1] dark:border-[#252B3B] bg-white/80 dark:bg-[#131722]/80 backdrop-blur-md flex flex-wrap items-center justify-between gap-2 z-10">
          <div className="flex items-center gap-2 min-w-0">
            {!isSidebarOpen && (
              <button
                onClick={() => setIsSidebarOpen(true)}
                className="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
                title="Open sessions sidebar"
              >
                <PanelLeftOpen size={16} />
              </button>
            )}
            <div className="flex items-center gap-1.5 truncate">
              <span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0" />
              <span className="text-xs font-semibold text-zinc-800 dark:text-zinc-200 truncate">
                {sessionTitle}
              </span>
            </div>
          </div>

          {/* Model, Domain, BYOK Controls */}
          <div className="flex items-center gap-2 flex-wrap">
            {/* Domain Dropdown */}
            <select
              value={domain}
              onChange={(e) => setDomain(e.target.value as TaskDomain)}
              className="px-2.5 py-1 text-xs font-medium rounded-lg border border-[#E6E6E1] dark:border-[#252B3B] bg-white dark:bg-[#181D29] text-zinc-700 dark:text-zinc-300 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              {DOMAIN_OPTIONS.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.label}
                </option>
              ))}
            </select>

            {/* Provider Dropdown */}
            <div className="relative" ref={modelDropdownRef}>
              <button
                type="button"
                onClick={() => setIsModelDropdownOpen(!isModelDropdownOpen)}
                className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-lg border border-[#E6E6E1] dark:border-[#252B3B] bg-white dark:bg-[#181D29] text-zinc-700 dark:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors cursor-pointer"
              >
                <Cpu size={13} className="text-indigo-600 dark:text-indigo-400" />
                <span>{currentModel.name}</span>
                <ChevronDown size={12} className="text-zinc-400" />
              </button>

              {isModelDropdownOpen && (
                <div className="absolute right-0 mt-1 w-52 rounded-xl border border-[#E6E6E1] dark:border-[#252B3B] bg-white dark:bg-[#181D29] shadow-lg py-1 z-50">
                  {MODEL_OPTIONS.map((opt) => (
                    <button
                      key={opt.id}
                      onClick={() => {
                        setProvider(opt.id)
                        setIsModelDropdownOpen(false)
                      }}
                      className={`w-full flex items-center justify-between px-3 py-2 text-xs text-left hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors ${
                        provider === opt.id ? 'text-indigo-600 dark:text-indigo-400 font-semibold bg-indigo-50/50 dark:bg-indigo-950/30' : 'text-zinc-700 dark:text-zinc-300'
                      }`}
                    >
                      <div>
                        <div className="font-medium">{opt.name}</div>
                        <div className="text-[10px] text-zinc-400">{opt.subname}</div>
                      </div>
                      {provider === opt.id && <Check size={14} />}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* BYOK Button */}
            <button
              onClick={() => setShowKeyModal(true)}
              className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-lg border border-[#E6E6E1] dark:border-[#252B3B] bg-white dark:bg-[#181D29] text-zinc-700 dark:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors cursor-pointer"
              title="Configure Bring Your Own Key"
            >
              <KeyRound size={12} className={apiKeys[provider] ? 'text-emerald-500' : 'text-zinc-400'} />
              <span>BYOK</span>
            </button>

            {/* Memory Enabled Toggle */}
            <label className="flex items-center gap-1 text-[11px] text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={memoryEnabled}
                onChange={(e) => setMemoryEnabled(e.target.checked)}
                className="w-3.5 h-3.5 rounded text-indigo-600 focus:ring-indigo-500 border-zinc-300 dark:border-zinc-700"
              />
              <span className={memoryEnabled ? 'text-indigo-600 dark:text-indigo-400 font-medium' : ''}>
                AEMA Memory
              </span>
            </label>

            {/* Simulate Failure Toggle */}
            <label className="flex items-center gap-1 text-[11px] text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={simulateFailure}
                onChange={(e) => setSimulateFailure(e.target.checked)}
                className="w-3.5 h-3.5 rounded text-rose-600 focus:ring-rose-500 border-zinc-300 dark:border-zinc-700"
              />
              <span className={simulateFailure ? 'text-rose-600 dark:text-rose-400 font-medium' : ''}>
                Simulate Trap
              </span>
            </label>

            {/* Toggle Inspector Pane Button */}
            <button
              onClick={() => setIsInspectorOpen(!isInspectorOpen)}
              className={`flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-lg border transition-colors cursor-pointer ${
                isInspectorOpen
                  ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400'
                  : 'border-[#E6E6E1] dark:border-[#252B3B] bg-white dark:bg-[#181D29] text-zinc-700 dark:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-800'
              }`}
              title="Toggle AEMA Cognitive Inspector Pane"
            >
              <Activity size={13} />
              <span>Inspector</span>
            </button>
          </div>
        </div>

        {/* Conversation Stream Scroll Area */}
        <div className="flex-1 overflow-y-auto px-4 md:px-8 py-6 space-y-6">
          {messages.length === 0 ? (
            /* Empty State Hero */
            <div className="max-w-2xl mx-auto mt-8 p-8 rounded-2xl border border-[#E6E6E1] dark:border-[#252B3B] bg-white dark:bg-[#131722] text-center shadow-xs">
              <div className="w-12 h-12 rounded-2xl bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 flex items-center justify-center mx-auto mb-4 border border-indigo-100 dark:border-indigo-900/40">
                <Shield size={24} />
              </div>
              <h3 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
                AEMA Experiential Conversation Studio
              </h3>
              <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-2 max-w-md mx-auto leading-relaxed">
                Multi-turn autonomous execution with persistent reliability memory. Every turn queries verified procedural lessons (<span className="text-indigo-600 font-semibold">+σ</span>), avoids known pitfalls (<span className="text-rose-500 font-semibold">-π</span>), and updates empirical trust via A-EMA.
              </p>

              {/* Starter Prompt Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-6 text-left">
                {STARTER_PROMPTS.map((starter, i) => (
                  <div
                    key={i}
                    onClick={() => {
                      setDomain(starter.domain)
                      handleSendMessage(starter.prompt)
                    }}
                    className="p-3.5 rounded-xl border border-[#E6E6E1] dark:border-[#252B3B] bg-[#FAFAFA] dark:bg-[#181D29] hover:border-indigo-400 dark:hover:border-indigo-600 cursor-pointer transition-all group"
                  >
                    <div className="text-xs font-semibold text-zinc-800 dark:text-zinc-200 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 flex items-center justify-between">
                      <span>{starter.title}</span>
                      <ChevronRight size={13} className="opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                    <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-1 line-clamp-2">
                      {starter.prompt}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            /* Stream of Messages */
            messages.map((msg) => {
              const isUser = msg.role === 'user'
              const exec = msg.execution

              return (
                <div
                  key={msg.id}
                  className={`flex gap-3 max-w-3xl ${isUser ? 'ml-auto justify-end' : 'mr-auto justify-start'}`}
                >
                  {!isUser && (
                    <div className="w-8 h-8 rounded-xl bg-indigo-600 text-white flex items-center justify-center shrink-0 mt-0.5 shadow-xs">
                      <Shield size={16} />
                    </div>
                  )}

                  <div className={`flex flex-col space-y-1.5 ${isUser ? 'items-end' : 'items-start'}`}>
                    {/* Message Bubble */}
                    <div
                      className={`px-4 py-3 rounded-2xl text-xs leading-relaxed max-w-2xl transition-all ${
                        isUser
                          ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 rounded-tr-xs shadow-xs'
                          : 'bg-white text-zinc-900 dark:bg-[#131722] dark:text-zinc-100 border border-[#E6E6E1] dark:border-[#252B3B] rounded-tl-xs shadow-xs'
                      }`}
                    >
                      {isUser ? (
                        <p className="whitespace-pre-wrap font-sans">{msg.content}</p>
                      ) : (
                        <MarkdownRenderer content={msg.content} />
                      )}
                    </div>

                    {/* Per-Response AEMA Execution Bar (Hybrid Option A & B) */}
                    {!isUser && exec && (
                      <div className="w-full flex flex-col space-y-1.5">
                        <div className="flex items-center gap-2 flex-wrap text-[11px]">
                          {/* Trace Selector Pill */}
                          <button
                            onClick={() => {
                              setSelectedExecution(exec)
                              setIsInspectorOpen(true)
                            }}
                            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border font-mono text-[11px] transition-all cursor-pointer ${
                              selectedExecution?.id === exec.id
                                ? 'bg-indigo-50 border-indigo-300 text-indigo-700 dark:bg-indigo-950/60 dark:border-indigo-800 dark:text-indigo-300'
                                : 'bg-zinc-100 dark:bg-zinc-800/80 border-zinc-200 dark:border-zinc-700 text-zinc-600 dark:text-zinc-400 hover:border-zinc-400'
                            }`}
                          >
                            <Terminal size={11} />
                            <span>Trace #{exec.id.replace('exec_', '')}</span>
                          </button>

                          {/* Outcome Quality Badge */}
                          <span
                            className={`px-2 py-0.5 rounded-md font-mono text-[10px] font-bold uppercase ${
                              exec.outcomeScore && exec.outcomeScore >= 0.8
                                ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-400'
                                : exec.outcomeScore && exec.outcomeScore <= 0.3
                                ? 'bg-rose-100 text-rose-800 dark:bg-rose-950/50 dark:text-rose-400'
                                : 'bg-amber-100 text-amber-800 dark:bg-amber-950/50 dark:text-amber-400'
                            }`}
                          >
                            R: {typeof exec.outcomeScore === 'number' ? exec.outcomeScore.toFixed(2) : '1.00'}
                          </span>

                          {/* Memory Count */}
                          {exec.retrievedExperiences && exec.retrievedExperiences.length > 0 && (
                            <span className="text-zinc-500 dark:text-zinc-400 flex items-center gap-1 font-mono text-[10px]">
                              <Database size={10} />
                              {exec.retrievedExperiences.length} {exec.retrievedExperiences.length === 1 ? 'memory' : 'memories'}
                            </span>
                          )}

                          {/* Inline strategy quick toggle */}
                          {exec.retrievedExperiences?.[0]?.experience && (
                            <button
                              onClick={() => setExpandedTraceMsgId(expandedTraceMsgId === msg.id ? null : msg.id)}
                              className="text-[10px] text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer font-medium"
                            >
                              {expandedTraceMsgId === msg.id ? 'Hide Strategy ▲' : 'Show Strategy ▼'}
                            </button>
                          )}
                        </div>

                        {/* Expandable Strategy Preview (Option B Accordion) */}
                        {expandedTraceMsgId === msg.id && exec.retrievedExperiences?.[0]?.experience && (
                          <div className="p-3 rounded-xl border border-indigo-100 dark:border-indigo-950/70 bg-indigo-50/40 dark:bg-indigo-950/20 text-xs space-y-1.5 animate-fadeIn">
                            <div className="font-semibold text-indigo-900 dark:text-indigo-200 flex items-center gap-1.5">
                              <Sparkles size={12} className="text-indigo-600 dark:text-indigo-400" />
                              <span>Verified Operational Strategy (+σ):</span>
                            </div>
                            <p className="text-zinc-700 dark:text-zinc-300 font-mono text-[11px]">
                              "{exec.retrievedExperiences[0].experience.strategyLesson}"
                            </p>
                            {exec.retrievedExperiences[0].experience.pitfallWarning && (
                              <div className="pt-1 text-rose-700 dark:text-rose-300 text-[11px] font-mono">
                                <span className="font-bold">Avoid Pitfall (-π):</span> "{exec.retrievedExperiences[0].experience.pitfallWarning}"
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {isUser && (
                    <div className="w-8 h-8 rounded-xl bg-zinc-200 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 flex items-center justify-center shrink-0 mt-0.5">
                      <User size={15} />
                    </div>
                  )}
                </div>
              )
            })
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Live Execution Progression Strip (During active processing) */}
        {isExecuting && (
          <div className="px-4 py-2 border-t border-[#E6E6E1] dark:border-[#252B3B] bg-indigo-50/80 dark:bg-indigo-950/40 flex items-center justify-between text-xs animate-pulse">
            <div className="flex items-center gap-2 text-indigo-700 dark:text-indigo-300 font-medium">
              <RefreshCw size={14} className="animate-spin text-indigo-600" />
              <span>AEMA Cycle Active: Stage [{currentStage.toUpperCase().replace('_', ' ')}]</span>
            </div>
            <span className="text-[11px] font-mono text-indigo-600 dark:text-indigo-400">
              Applying Bilateral Constraints...
            </span>
          </div>
        )}

        {/* Bottom Message Composer */}
        <div className="p-3 md:p-4 border-t border-[#E6E6E1] dark:border-[#252B3B] bg-white dark:bg-[#131722]">
          <div className="relative flex items-end rounded-2xl border border-[#E6E6E1] dark:border-[#252B3B] bg-[#FAFAFA] dark:bg-[#181D29] focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-500/20 transition-all p-1.5">
            <textarea
              ref={textareaRef}
              rows={2}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isExecuting}
              placeholder="Ask AEMA agent or give a task... (Shift+Enter for newline, Enter to submit)"
              className="flex-1 bg-transparent px-3 py-2 text-xs text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 resize-none focus:outline-none disabled:opacity-60"
            />
            <button
              onClick={() => handleSendMessage()}
              disabled={!inputText.trim() || isExecuting}
              className={`p-2.5 rounded-xl font-semibold flex items-center justify-center transition-all cursor-pointer ${
                inputText.trim() && !isExecuting
                  ? 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm'
                  : 'bg-zinc-200 dark:bg-zinc-800 text-zinc-400 cursor-not-allowed'
              }`}
              title="Send message"
            >
              {isExecuting ? <RefreshCw size={15} className="animate-spin" /> : <Send size={15} />}
            </button>
          </div>
        </div>
      </div>

      {/* ─── 3. RIGHT INSPECTOR SPLIT-PANE / DRAWER ───────────────────────── */}
      {isInspectorOpen && (
        <div className="w-80 md:w-96 shrink-0 border-l border-[#E6E6E1] dark:border-[#252B3B] bg-white dark:bg-[#131722] flex flex-col overflow-hidden transition-all duration-300">
          <div className="p-3 border-b border-[#E6E6E1] dark:border-[#252B3B] flex items-center justify-between bg-zinc-50/50 dark:bg-[#181D29]/50">
            <div className="flex items-center gap-1.5">
              <Activity size={15} className="text-indigo-600 dark:text-indigo-400" />
              <span className="text-xs font-semibold text-zinc-900 dark:text-zinc-100">
                AEMA Trace Inspector
              </span>
            </div>
            <button
              onClick={() => setIsInspectorOpen(false)}
              className="p-1 rounded-lg text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
              title="Close Inspector"
            >
              <PanelRightClose size={15} />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {selectedExecution ? (
              <>
                <div className="p-3 rounded-xl bg-zinc-50 dark:bg-[#181D29] border border-[#E6E6E1] dark:border-[#252B3B] space-y-1">
                  <div className="flex items-center justify-between text-[11px] font-mono">
                    <span className="font-semibold">{selectedExecution.id}</span>
                    <span className="text-indigo-600 dark:text-indigo-400 font-bold uppercase">{selectedExecution.taskDomain}</span>
                  </div>
                  <div className="text-[11px] text-zinc-500 truncate">
                    Input: "{selectedExecution.taskInput}"
                  </div>
                </div>

                <ExecutionStepper currentStage="complete" execution={selectedExecution} />
                <ContextInspector execution={selectedExecution} />
              </>
            ) : (
              <div className="p-8 text-center text-xs text-zinc-400 font-mono">
                No execution selected. Click "Trace" on any response in the stream to inspect its cognitive cycle.
              </div>
            )}
          </div>
        </div>
      )}

      {/* ─── BYOK Modal ───────────────────────────────────────────────────── */}
      {showKeyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-2xl border border-[#E6E6E1] dark:border-[#252B3B] bg-white dark:bg-[#131722] p-5 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <KeyRound size={18} className="text-indigo-600 dark:text-indigo-400" />
                <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                  Configure BYOK API Key ({currentModel.name})
                </h3>
              </div>
              <button
                onClick={() => setShowKeyModal(false)}
                className="p-1 rounded-lg text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200"
              >
                <X size={16} />
              </button>
            </div>

            <p className="text-xs text-zinc-500 leading-relaxed">
              Your API key is stored strictly in your browser's local memory and sent directly to the backend for this session. It is never stored permanently.
            </p>

            <input
              type="password"
              defaultValue={apiKeys[provider] || ''}
              placeholder={`Enter ${currentModel.name} API Key...`}
              id="byok-input"
              className="w-full px-3 py-2 text-xs rounded-xl border border-[#E6E6E1] dark:border-[#252B3B] bg-zinc-50 dark:bg-[#181D29] text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-mono"
            />

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setShowKeyModal(false)}
                className="px-3 py-1.5 rounded-xl border border-zinc-200 dark:border-zinc-800 text-xs font-medium text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  const input = document.getElementById('byok-input') as HTMLInputElement
                  saveApiKey(input?.value || '')
                }}
                className="px-4 py-1.5 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-sm"
              >
                Save Key
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
