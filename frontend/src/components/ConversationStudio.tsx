import { useState, useEffect, useRef } from 'react'
import {
  ChevronDown,
  KeyRound,
  PanelRightClose,
  RefreshCw,
  Activity,
  Check,
  X,
  Pencil,
  Trash2,
} from 'lucide-react'
import type { TaskDomain, TaskExecution, ChatMessage, SessionSummary } from '../types'
import { executeAgentTask, fetchSessions, fetchExecutions, deleteSession, renameSession } from '../services/api'
import MarkdownRenderer from './MarkdownRenderer'
import ExecutionStepper from './ExecutionStepper'
import ContextInspector from './ContextInspector'

type ProviderType = 'gemini' | 'groq' | 'ollama' | 'openai' | 'mock'

interface ModelOption {
  id: ProviderType
  name: string
  subname: string
  logo?: string
}

const MODEL_OPTIONS: ModelOption[] = [
  { id: 'groq', name: 'Llama-3.3-70B', subname: 'Groq Cloud (Fast)', logo: '/images/models/groq.webp' },
  { id: 'gemini', name: 'Gemini 1.5 Flash', subname: 'Google Cloud', logo: '/images/models/gemini.webp' },
  { id: 'openai', name: 'GPT-4o Mini', subname: 'OpenAI', logo: '/images/models/openai.webp' },
  { id: 'ollama', name: 'Llama-3.2', subname: 'Ollama Local', logo: '/images/models/ollama.webp' },
  { id: 'mock', name: 'Mock Engine', subname: 'Offline Test' },
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
    title: 'API Deprecation Trap Test',
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
  const [isInspectorOpen, setIsInspectorOpen] = useState<boolean>(true)

  // Thread Rename and Delete States
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null)
  const [editTitleValue, setEditTitleValue] = useState<string>('')

  const handleStartRename = (s: SessionSummary, e: React.MouseEvent) => {
    e.stopPropagation()
    setEditingSessionId(s.sessionId)
    setEditTitleValue(s.title)
  }

  const handleSaveRename = async (sessionId: string) => {
    const trimmed = editTitleValue.trim()
    if (!trimmed) {
      setEditingSessionId(null)
      return
    }

    setSessions((prev) =>
      prev.map((s) => (s.sessionId === sessionId ? { ...s, title: trimmed } : s))
    )
    if (sessionId === currentSessionId) {
      setSessionTitle(trimmed)
    }
    setEditingSessionId(null)

    await renameSession(sessionId, trimmed)
  }

  const handleDeleteThread = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setSessions((prev) => prev.filter((s) => s.sessionId !== sessionId))

    if (sessionId === currentSessionId) {
      startNewSession()
    }

    await deleteSession(sessionId)
  }

  // Resizable Panel States (with min/max bounds and localStorage persistence)
  const [threadsWidth, setThreadsWidth] = useState<number>(() => {
    try {
      const saved = localStorage.getItem('aema_studio_threads_width')
      return saved ? Math.min(380, Math.max(180, Number(saved))) : 240
    } catch {
      return 240
    }
  })
  const [inspectorWidth, setInspectorWidth] = useState<number>(() => {
    try {
      const saved = localStorage.getItem('aema_studio_inspector_width')
      return saved ? Math.min(520, Math.max(280, Number(saved))) : 340
    } catch {
      return 340
    }
  })
  const [isResizing, setIsResizing] = useState<'threads' | 'inspector' | null>(null)

  const handleStartResizeThreads = (e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizing('threads')
    const startX = e.clientX
    const startW = threadsWidth

    const onMouseMove = (moveEvent: MouseEvent) => {
      const delta = moveEvent.clientX - startX
      const nextW = Math.min(380, Math.max(180, startW + delta))
      setThreadsWidth(nextW)
      try {
        localStorage.setItem('aema_studio_threads_width', String(nextW))
      } catch {}
    }

    const onMouseUp = () => {
      setIsResizing(null)
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
    }

    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
  }

  const handleStartResizeInspector = (e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizing('inspector')
    const startX = e.clientX
    const startW = inspectorWidth

    const onMouseMove = (moveEvent: MouseEvent) => {
      const delta = startX - moveEvent.clientX
      const nextW = Math.min(520, Math.max(280, startW + delta))
      setInspectorWidth(nextW)
      try {
        localStorage.setItem('aema_studio_inspector_width', String(nextW))
      } catch {}
    }

    const onMouseUp = () => {
      setIsResizing(null)
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
    }

    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
  }

  // Message & Stream States
  const [messages, setMessages] = useState<ConversationMessage[]>([])
  const [inputText, setInputText] = useState('')
  const [isExecuting, setIsExecuting] = useState(false)
  const [currentStage, setCurrentStage] = useState<'retrieval' | 'execution' | 'evaluation' | 'reflection' | 'trust_update' | 'idle' | 'complete'>('idle')
  const [selectedExecution, setSelectedExecution] = useState<TaskExecution | null>(null)

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

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isExecuting])

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (modelDropdownRef.current && !modelDropdownRef.current.contains(event.target as Node)) {
        setIsModelDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  useEffect(() => {
    loadSessions()
  }, [])

  const loadSessions = async () => {
    const list = await fetchSessions(30)
    setSessions(list)
  }

  const switchSession = async (sessionId: string) => {
    if (sessionId === currentSessionId && messages.length > 0) return
    setCurrentSessionId(sessionId)
    const matchingSession = sessions.find((s) => s.sessionId === sessionId)
    setSessionTitle(matchingSession?.title || 'Conversation')

    const runs = await fetchExecutions(50, sessionId)
    if (runs && runs.length > 0) {
      const sorted = [...runs].sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime())
      const reconstructed: ConversationMessage[] = []
      sorted.forEach((run, idx) => {
        reconstructed.push({
          id: `msg_u_${run.id}_${idx}`,
          role: 'user',
          content: run.taskInput,
          timestamp: run.createdAt,
        })
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

  const handleSendMessage = async (customPrompt?: string, overrideDomain?: TaskDomain) => {
    const promptToSend = (customPrompt || inputText).trim()
    if (!promptToSend || isExecuting) return

    const effectiveDomain = overrideDomain || domain
    if (overrideDomain && overrideDomain !== domain) {
      setDomain(overrideDomain)
    }

    setInputText('')
    setIsExecuting(true)
    setCurrentStage('retrieval')

    if (messages.length === 0) {
      const shortTitle = promptToSend.slice(0, 42) + (promptToSend.length > 42 ? '...' : '')
      setSessionTitle(shortTitle)
    }

    const userMsgId = `user_${Date.now()}`
    const userMsg: ConversationMessage = {
      id: userMsgId,
      role: 'user',
      content: promptToSend,
      timestamp: new Date().toISOString(),
    }
    const updatedMessages = [...messages, userMsg]
    setMessages(updatedMessages)

    const historyPayload: ChatMessage[] = updatedMessages.map((m) => ({
      role: m.role,
      content: m.content,
    }))

    try {
      const activeKey = apiKeys[provider] || undefined
      const exec = await executeAgentTask({
        taskInput: promptToSend,
        taskDomain: effectiveDomain,
        memoryEnabled,
        provider,
        apiKey: activeKey,
        sessionId: currentSessionId,
        messages: historyPayload,
        simulateFailure,
        onStageChange: (stage) => setCurrentStage(stage),
      })

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
      loadSessions()
    } catch (err) {
      const errorMsg: ConversationMessage = {
        id: `asst_err_${Date.now()}`,
        role: 'assistant',
        content: `Error executing task: ${err instanceof Error ? err.message : String(err)}`,
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
    <div
      className={`flex flex-1 h-full w-full bg-[#141412] text-[#EDECE8] overflow-hidden ${
        isResizing ? 'select-none cursor-col-resize' : ''
      }`}
    >
      {/* ─── 1. THREADS SIDEBAR (QUIET obsidian with draggable width) ────────── */}
      <div
        className="shrink-0 bg-[#161614] flex flex-col overflow-hidden"
        style={{ width: `${threadsWidth}px` }}
      >
        {/* Header (No duplicate collapse icon) */}
        <div className="p-3 border-b border-[#242422] flex items-center justify-between">
          <span className="font-mono text-[11px] uppercase tracking-wider text-[#7E7D77]">
            Threads
          </span>
          <span className="font-mono text-[10px] text-[#5A5955]">
            {sessions.length} recorded
          </span>
        </div>

        {/* New Thread Action */}
        <div className="p-2.5 border-b border-[#242422]">
          <button
            onClick={startNewSession}
            className="w-full py-1.5 px-2.5 rounded border border-[#2E2E2A] bg-[#1E1E1B] hover:bg-[#252522] text-[#EDECE8] font-medium text-xs text-left flex items-center justify-between transition-colors cursor-pointer"
          >
            <span>+ New Thread</span>
            <span className="font-mono text-[10px] text-[#7E7D77]">&crarr;</span>
          </button>
        </div>

        {/* Thread List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
          {sessions.length === 0 && messages.length === 0 ? (
            <div className="p-4 text-center text-[11px] text-[#7E7D77] font-mono">
              No previous threads.
            </div>
          ) : (
            sessions.map((s) => {
              const isActive = s.sessionId === currentSessionId
              const isEditing = editingSessionId === s.sessionId

              return (
                <div
                  key={s.sessionId}
                  onClick={() => {
                    if (!isEditing) switchSession(s.sessionId)
                  }}
                  className={`group relative px-2.5 py-2 rounded text-xs transition-colors cursor-pointer ${
                    isActive
                      ? 'bg-[#22221E] text-white font-medium border border-[#2E2E2A]'
                      : 'text-[#9E9D96] hover:text-[#EDECE8] hover:bg-[#1E1E1B]'
                  }`}
                >
                  {isEditing ? (
                    <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="text"
                        value={editTitleValue}
                        onChange={(e) => setEditTitleValue(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleSaveRename(s.sessionId)
                          if (e.key === 'Escape') setEditingSessionId(null)
                        }}
                        autoFocus
                        className="flex-1 min-w-0 bg-[#141412] border border-[#3E3E38] rounded px-1.5 py-0.5 text-xs text-white focus:outline-none focus:border-[#4EAA79]"
                      />
                      <button
                        type="button"
                        onClick={() => handleSaveRename(s.sessionId)}
                        className="text-[#4EAA79] hover:text-white p-0.5 rounded cursor-pointer"
                        title="Save rename"
                      >
                        <Check size={12} />
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditingSessionId(null)}
                        className="text-[#7E7D77] hover:text-white p-0.5 rounded cursor-pointer"
                        title="Cancel"
                      >
                        <X size={12} />
                      </button>
                    </div>
                  ) : (
                    <>
                      <div className="flex items-center justify-between gap-1">
                        <div className="truncate font-medium text-[11px] flex-1">
                          {s.title}
                        </div>

                        {/* ChatGPT-style Hover Actions: Rename and Delete */}
                        <div className="flex items-center gap-0.5 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button
                            type="button"
                            onClick={(e) => handleStartRename(s, e)}
                            className="p-1 rounded text-[#7E7D77] hover:text-white hover:bg-[#282824] transition-colors cursor-pointer"
                            title="Rename thread"
                          >
                            <Pencil size={11} />
                          </button>
                          <button
                            type="button"
                            onClick={(e) => handleDeleteThread(s.sessionId, e)}
                            className="p-1 rounded text-[#7E7D77] hover:text-[#D9534F] hover:bg-[#2E1E1E] transition-colors cursor-pointer"
                            title="Delete thread"
                          >
                            <Trash2 size={11} />
                          </button>
                        </div>
                      </div>

                      <div className="flex items-center justify-between text-[10px] text-[#7E7D77] font-mono mt-0.5">
                        <span>{s.turnCount} {s.turnCount === 1 ? 'turn' : 'turns'}</span>
                        <span>{new Date(s.lastActive).toLocaleDateString([], { month: 'short', day: 'numeric' })}</span>
                      </div>
                    </>
                  )}
                </div>
              )
            })
          )}
        </div>
      </div>

      {/* Resizable Divider Handle: Threads */}
      <div
        onMouseDown={handleStartResizeThreads}
        className="w-1.5 shrink-0 bg-[#242422] hover:bg-[#4EAA79]/80 active:bg-[#4EAA79] cursor-col-resize transition-colors relative z-20 select-none group flex items-center justify-center"
        title="Drag to resize Threads panel"
      >
        <div className="w-0.5 h-6 rounded-full bg-[#3E3E38] group-hover:bg-[#4EAA79] transition-colors" />
      </div>

      {/* ─── 2. MAIN CONVERSATIONAL WORKSPACE ─────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 bg-[#141412] relative overflow-hidden">
        {/* Top Control Bar (Clean Two-Tier Structure: Session Status + Dedicated Tooling Strip) */}
        <div className="border-b border-[#242422] bg-[#161614] shrink-0 relative z-30">
          {/* Tier 1: Session Identity & Inspector Toggle */}
          <div className="h-11 px-4 flex items-center justify-between border-b border-[#20201D] gap-3">
            <div className="flex items-center gap-2.5 min-w-0">
              <span className={`w-2 h-2 rounded-full shrink-0 ${isExecuting ? 'bg-[#E67E22] animate-pulse' : 'bg-[#4EAA79]'}`} />
              <span className="text-xs font-semibold text-[#EDECE8] truncate max-w-md">
                {sessionTitle}
              </span>
              <span className="text-[10px] font-mono text-[#7E7D77] shrink-0 px-1.5 py-0.5 rounded bg-[#1A1A17] border border-[#242422]">
                {messages.length} {messages.length === 1 ? 'msg' : 'msgs'}
              </span>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => setIsInspectorOpen(!isInspectorOpen)}
                className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono rounded border transition-colors cursor-pointer ${
                  isInspectorOpen
                    ? 'border-[#3E3E38] bg-[#22221E] text-white font-medium'
                    : 'border-[#2E2E2A] bg-[#181816] text-[#7E7D77] hover:text-[#EDECE8]'
                }`}
                title="Toggle Cognitive Inspector"
              >
                <Activity size={12} className={isInspectorOpen ? 'text-[#4EAA79]' : ''} />
                <span>Cognitive Trace</span>
              </button>
            </div>
          </div>

          {/* Tier 2: Clean Engine Selection & Guardrail Toggles */}
          <div className="h-10 px-4 flex items-center justify-between text-xs font-mono bg-[#141412] gap-3 relative z-30 overflow-visible">
            {/* Left: Engine & Domain Configuration */}
            <div className="flex items-center gap-2 shrink-0">
              {/* Model Selector with Logo */}
              <div className="relative z-40" ref={modelDropdownRef}>
                <button
                  type="button"
                  onClick={() => setIsModelDropdownOpen(!isModelDropdownOpen)}
                  className="flex items-center gap-1.5 px-2.5 py-1 text-xs rounded border border-[#2E2E2A] bg-[#181816] text-[#EDECE8] hover:bg-[#1E1E1B] transition-colors cursor-pointer"
                >
                  {currentModel.logo ? (
                    <img src={currentModel.logo} alt="" className="w-3.5 h-3.5 object-contain rounded shrink-0" />
                  ) : (
                    <span className="w-3.5 h-3.5 rounded bg-[#2A2A26] text-[#A3A29D] flex items-center justify-center text-[8px] font-bold shrink-0">
                      M
                    </span>
                  )}
                  <span className="font-medium">{currentModel.name}</span>
                  <ChevronDown size={11} className="text-[#7E7D77]" />
                </button>

                {isModelDropdownOpen && (
                  <div className="absolute left-0 top-full mt-1.5 w-60 rounded-lg border border-[#2E2E2A] bg-[#1A1A17] shadow-2xl py-1.5 z-50 font-mono text-xs">
                    {MODEL_OPTIONS.map((opt) => (
                      <button
                        key={opt.id}
                        onClick={() => {
                          setProvider(opt.id)
                          setIsModelDropdownOpen(false)
                        }}
                        className={`w-full flex items-center justify-between px-3 py-2 text-left hover:bg-[#242420] transition-colors ${
                          provider === opt.id ? 'text-[#EDECE8] font-semibold bg-[#22221E]' : 'text-[#9E9D96]'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          {opt.logo ? (
                            <img src={opt.logo} alt="" className="w-4 h-4 object-contain rounded shrink-0" />
                          ) : (
                            <span className="w-4 h-4 rounded bg-[#2A2A26] text-[#A3A29D] flex items-center justify-center text-[9px] font-bold shrink-0">
                              M
                            </span>
                          )}
                          <div>
                            <div>{opt.name}</div>
                            <div className="text-[10px] text-[#7E7D77]">{opt.subname}</div>
                          </div>
                        </div>
                        {provider === opt.id && <Check size={12} className="text-[#4EAA79]" />}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Domain Selector */}
              <select
                value={domain}
                onChange={(e) => setDomain(e.target.value as TaskDomain)}
                className="px-2.5 py-1 text-xs font-mono rounded border border-[#2E2E2A] bg-[#181816] text-[#EDECE8] focus:outline-none cursor-pointer"
              >
                {DOMAIN_OPTIONS.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.label}
                  </option>
                ))}
              </select>

              {/* BYOK Button */}
              <button
                onClick={() => setShowKeyModal(true)}
                className={`flex items-center gap-1.5 px-2 py-1 rounded border text-[11px] font-mono transition-colors cursor-pointer ${
                  apiKeys[provider]
                    ? 'border-[#2E4234] bg-[#1E2E24] text-[#4EAA79]'
                    : 'border-[#2E2E2A] bg-[#181816] text-[#7E7D77] hover:text-[#EDECE8]'
                }`}
                title="Configure custom BYOK API Key"
              >
                <KeyRound size={12} />
                <span>{apiKeys[provider] ? 'Key Set' : 'BYOK'}</span>
              </button>
            </div>

            {/* Right: Guardrails Toggles */}
            <div className="flex items-center gap-2 shrink-0">
              {/* Memory Toggle */}
              <label className="flex items-center gap-1.5 px-2.5 py-1 rounded border border-[#2E2E2A] bg-[#181816] text-[11px] font-mono text-[#EDECE8] cursor-pointer hover:bg-[#1E1E1B] transition-colors select-none">
                <input
                  type="checkbox"
                  checked={memoryEnabled}
                  onChange={(e) => setMemoryEnabled(e.target.checked)}
                  className="w-3.5 h-3.5 rounded border-[#2E2E2A] bg-[#141412] text-[#4EAA79] accent-[#4EAA79]"
                />
                <span className={memoryEnabled ? 'text-[#4EAA79] font-medium' : 'text-[#7E7D77]'}>
                  AEMA Memory
                </span>
              </label>

              {/* Trap Test Toggle */}
              <label className="flex items-center gap-1.5 px-2.5 py-1 rounded border border-[#2E2E2A] bg-[#181816] text-[11px] font-mono text-[#EDECE8] cursor-pointer hover:bg-[#1E1E1B] transition-colors select-none">
                <input
                  type="checkbox"
                  checked={simulateFailure}
                  onChange={(e) => setSimulateFailure(e.target.checked)}
                  className="w-3.5 h-3.5 rounded border-[#2E2E2A] bg-[#141412] text-[#D9534F] accent-[#D9534F]"
                />
                <span className={simulateFailure ? 'text-[#D9534F] font-medium' : 'text-[#7E7D77]'}>
                  Trap Test
                </span>
              </label>
            </div>
          </div>
        </div>

        {/* Message Scroll Area */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
          {messages.length === 0 ? (
            /* Quiet Empty State */
            <div className="max-w-xl mx-auto mt-12 text-center space-y-4">
              <div className="text-xs font-mono uppercase tracking-widest text-[#7E7D77]">
                Autonomous Execution Studio
              </div>
              <h3 className="font-serif-headline text-2xl font-normal text-[#EDECE8]">
                Ready for task instructions
              </h3>
              <p className="text-xs text-[#7E7D77] leading-relaxed max-w-md mx-auto">
                Prompts retrieve verified operational strategies (<span className="text-[#4EAA79]">+&sigma;</span>), bypass known traps (<span className="text-[#D9534F]">-&pi;</span>), and update reliability scores via A-EMA.
              </p>

              {/* Starter Prompts */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mt-6 text-left">
                {STARTER_PROMPTS.map((starter, i) => (
                  <div
                    key={i}
                    onClick={() => {
                      setDomain(starter.domain)
                      handleSendMessage(starter.prompt, starter.domain)
                    }}
                    className="p-3 rounded border border-[#242422] bg-[#161614] hover:bg-[#1E1E1B] hover:border-[#383834] cursor-pointer transition-colors"
                  >
                    <div className="text-xs font-medium text-[#EDECE8]">{starter.title}</div>
                    <p className="text-[10px] text-[#7E7D77] mt-1 line-clamp-2 font-mono">
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
                  className={`flex flex-col space-y-1.5 max-w-3xl ${
                    isUser ? 'ml-auto items-end' : 'mr-auto items-start'
                  }`}
                >
                  <div className="font-mono text-[10px] text-[#7E7D77] px-1 flex items-center gap-1.5">
                    {!isUser && currentModel.logo && (
                      <img src={currentModel.logo} alt="" className="w-3 h-3 object-contain rounded shrink-0" />
                    )}
                    <span>{isUser ? 'User' : `AEMA • ${currentModel.name}`}</span>
                  </div>

                  <div
                    className={`p-4 rounded-lg text-xs leading-relaxed max-w-2xl ${
                      isUser
                        ? 'bg-[#1E1E1B] border border-[#2E2E2A] text-white'
                        : 'bg-[#161614] border border-[#242422] text-[#EDECE8]'
                    }`}
                  >
                    {isUser ? (
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    ) : (
                      <MarkdownRenderer content={msg.content} />
                    )}
                  </div>

                  {/* Assistant Run Meta */}
                  {!isUser && exec && (
                    <div className="flex items-center gap-3 text-[11px] font-mono text-[#7E7D77] px-1">
                      <button
                        onClick={() => {
                          setSelectedExecution(exec)
                          setIsInspectorOpen(true)
                        }}
                        className="hover:text-white transition-colors cursor-pointer text-[#4EAA79]"
                      >
                        Inspect Trace #{exec.id.replace('exec_', '')} &rarr;
                      </button>
                      <span>•</span>
                      <span>Outcome: {exec.outcomeScore && exec.outcomeScore >= 0.7 ? 'SUCCESS' : 'FAILURE'}</span>
                      {exec.retrievedExperiences && exec.retrievedExperiences.length > 0 && (
                        <>
                          <span>•</span>
                          <span>{exec.retrievedExperiences.length} memories used</span>
                        </>
                      )}
                    </div>
                  )}
                </div>
              )
            })
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Live Active Bar */}
        {isExecuting && (
          <div className="px-4 py-2 border-t border-[#242422] bg-[#1A1A17] flex items-center justify-between text-xs font-mono text-[#EDECE8]">
            <div className="flex items-center gap-2">
              <RefreshCw size={13} className="animate-spin text-[#E67E22]" />
              <span>Cognitive Cycle: Stage [{currentStage.toUpperCase()}]</span>
            </div>
            <span className="text-[10px] text-[#7E7D77]">Processing...</span>
          </div>
        )}

        {/* Bottom Message Input */}
        <div className="p-4 border-t border-[#242422] bg-[#161614]">
          <div className="border border-[#2E2E2A] rounded-lg bg-[#181816] p-2 flex flex-col gap-2">
            <textarea
              ref={textareaRef}
              rows={2}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isExecuting}
              placeholder="Send task instructions or query the agent... (Shift+Enter for newline, Enter to run)"
              className="bg-transparent text-xs text-[#EDECE8] placeholder-[#5A5955] focus:outline-none resize-none p-1 disabled:opacity-50"
            />
            <div className="flex items-center justify-between pt-1 border-t border-[#22221F]">
              <span className="text-[10px] font-mono text-[#5A5955]">Enter to execute</span>
              <button
                onClick={() => handleSendMessage()}
                disabled={!inputText.trim() || isExecuting}
                className="px-3 py-1 rounded bg-[#EDECE8] text-[#141412] font-medium text-xs hover:bg-white transition-colors cursor-pointer disabled:opacity-40"
              >
                {isExecuting ? 'Running...' : 'Execute Run'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Resizable Divider Handle: Inspector */}
      {isInspectorOpen && (
        <div
          onMouseDown={handleStartResizeInspector}
          className="w-1.5 shrink-0 bg-[#242422] hover:bg-[#4EAA79]/80 active:bg-[#4EAA79] cursor-col-resize transition-colors relative z-20 select-none group flex items-center justify-center"
          title="Drag to resize Cognitive Trace panel"
        >
          <div className="w-0.5 h-6 rounded-full bg-[#3E3E38] group-hover:bg-[#4EAA79] transition-colors" />
        </div>
      )}

      {/* ─── 3. RIGHT INSPECTOR PANEL (CALM TIMELINE with draggable width) ─── */}
      {isInspectorOpen && (
        <aside
          className="shrink-0 bg-[#161614] flex flex-col overflow-y-auto"
          style={{ width: `${inspectorWidth}px` }}
        >
          <div className="p-3 border-b border-[#242422] flex items-center justify-between">
            <span className="font-mono text-[11px] uppercase tracking-wider text-[#7E7D77]">
              Cognitive Trace
            </span>
            <button
              onClick={() => setIsInspectorOpen(false)}
              className="p-1 rounded text-[#7E7D77] hover:text-[#EDECE8] transition-colors cursor-pointer"
              title="Close inspector"
            >
              <PanelRightClose size={14} />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {selectedExecution ? (
              <>
                <div className="p-3 rounded border border-[#242422] bg-[#141412] font-mono text-xs space-y-1">
                  <div className="flex items-center justify-between text-[#EDECE8] font-bold">
                    <span>{selectedExecution.id}</span>
                    <span className="text-[#4EAA79] uppercase">{selectedExecution.taskDomain}</span>
                  </div>
                  <div className="text-[11px] text-[#7E7D77] truncate">
                    Input: "{selectedExecution.taskInput}"
                  </div>
                </div>

                <ExecutionStepper currentStage="complete" execution={selectedExecution} />
                <ContextInspector execution={selectedExecution} />
              </>
            ) : (
              <div className="p-8 text-center text-xs text-[#7E7D77] font-mono">
                No execution selected. Run a task or select a response to view its 5-node trace.
              </div>
            )}
          </div>
        </aside>
      )}

      {/* ─── BYOK Modal ───────────────────────────────────────────────────── */}
      {showKeyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-lg border border-[#242422] bg-[#161614] p-5 shadow-2xl space-y-4 text-[#EDECE8]">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-semibold uppercase tracking-wider text-[#EDECE8]">
                API Key Configuration ({currentModel.name})
              </span>
              <button
                onClick={() => setShowKeyModal(false)}
                className="text-[#7E7D77] hover:text-white"
              >
                <X size={15} />
              </button>
            </div>

            <p className="text-xs text-[#7E7D77] leading-relaxed">
              Keys are stored strictly in your local browser cache and forwarded for this session. They are never retained on the server.
            </p>

            <input
              type="password"
              defaultValue={apiKeys[provider] || ''}
              placeholder={`Enter ${currentModel.name} Key...`}
              id="byok-input"
              className="w-full px-3 py-2 text-xs rounded border border-[#2E2E2A] bg-[#141412] text-[#EDECE8] focus:outline-none font-mono"
            />

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setShowKeyModal(false)}
                className="px-3 py-1.5 rounded border border-[#2E2E2A] text-xs font-medium text-[#7E7D77] hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  const input = document.getElementById('byok-input') as HTMLInputElement
                  saveApiKey(input?.value || '')
                }}
                className="px-4 py-1.5 rounded bg-[#EDECE8] text-[#141412] text-xs font-medium hover:bg-white"
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
