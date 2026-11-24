import { useState, useEffect, useRef } from 'react'
import {
  ChevronDown,
  ChevronRight,
  KeyRound,
  PanelRightClose,
  Activity,
  Check,
  X,
  Pencil,
  Trash2,
  Code,
} from 'lucide-react'
import type { TaskDomain, TaskExecution, ChatMessage, SessionSummary } from '../types'
import { executeAgentTask, fetchSessions, fetchExecutions, deleteSession, renameSession } from '../services/api'
import MarkdownRenderer from './MarkdownRenderer'
import ExecutionStepper from './ExecutionStepper'
import ContextInspector from './ContextInspector'
import { useAuth } from '../context/AuthContext'

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
    prompt: 'When choosing between SQL and NoSQL for a web application, how should we compare them?',
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

interface RunningExecutionState {
  taskInput: string
  stage: 'retrieval' | 'execution' | 'evaluation' | 'reflection' | 'trust_update' | 'complete'
  startTime: number
  elapsedSeconds: number
  tokens: string
  isExpanded: boolean
}

interface ConversationStudioProps {
  onExecutionComplete?: (execution: TaskExecution) => void
}

export default function ConversationStudio({ onExecutionComplete }: ConversationStudioProps) {
  const { user } = useAuth()
  // Session States
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<string>(() => `sess_${Date.now()}`)
  const [sessionTitle, setSessionTitle] = useState<string>('New Conversation')
  const [isInspectorOpen, setIsInspectorOpen] = useState<boolean>(false)

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
  const [selectedExecution, setSelectedExecution] = useState<TaskExecution | null>(null)
  const [runningExecution, setRunningExecution] = useState<RunningExecutionState | null>(null)
  const [showDevDrawer, setShowDevDrawer] = useState<boolean>(false)
  const [expandedThoughtIds, setExpandedThoughtIds] = useState<Record<string, boolean>>({})

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
  }, [messages, isExecuting, runningExecution?.tokens])

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
  }, [user])

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
    setRunningExecution(null)
    setInputText('')
    textareaRef.current?.focus()
  }

  const getStageIndex = (stage: string) => {
    switch (stage) {
      case 'retrieval': return 0
      case 'execution': return 1
      case 'evaluation': return 2
      case 'reflection': return 3
      case 'trust_update': return 4
      case 'complete': return 5
      default: return -1
    }
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

    const startTime = Date.now()
    setRunningExecution({
      taskInput: promptToSend,
      stage: 'retrieval',
      startTime,
      elapsedSeconds: 0,
      tokens: '',
      isExpanded: true,
    })

    const timer = setInterval(() => {
      setRunningExecution((prev) => {
        if (!prev) return null
        return {
          ...prev,
          elapsedSeconds: Math.floor((Date.now() - prev.startTime) / 1000),
        }
      })
    }, 1000)

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
        useStreaming: true,
        onStageChange: (stage) => {
          setRunningExecution((prev) => prev ? { ...prev, stage } : null)
        },
        onToken: (chunk) => {
          setRunningExecution((prev) => prev ? { ...prev, tokens: prev.tokens + chunk } : null)
        },
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
      clearInterval(timer)
      setIsExecuting(false)
      setRunningExecution(null)
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
      className={`flex flex-1 h-full w-full bg-[#0A0A09] text-[#EDECE8] overflow-hidden ${
        isResizing ? 'select-none cursor-col-resize' : ''
      }`}
    >
      {/* ─── 1. THREADS SIDEBAR (QUIET obsidian with draggable width) ────────── */}
      <aside
        className="shrink-0 bg-[#0C0C0B] border-r border-[#1C1C1A] flex flex-col overflow-hidden"
        style={{ width: `${threadsWidth}px` }}
      >
        {/* Threads Header */}
        <div className="px-3 py-2 border-b border-[#1C1C1A] flex items-center justify-between">
          <span className="font-mono text-[10px] uppercase tracking-wider text-[#7E7D77]">
            Threads
          </span>
          <span className="text-[10px] font-mono text-[#555550]">
            {sessions.length} recorded
          </span>
        </div>

        {/* Action: + New Thread */}
        <div className="p-2 border-b border-[#1C1C1A]">
          <button
            onClick={startNewSession}
            className="w-full py-1 px-2.5 rounded border border-[#1E1E1C] bg-[#121210] hover:bg-[#181816] text-xs text-[#EDECE8] font-medium flex items-center justify-between transition-colors cursor-pointer"
          >
            <span>+ New Thread</span>
            <span className="text-[10px] text-[#555550] font-mono">⌘N</span>
          </button>
        </div>

        {/* Thread History List with Inline Rename and Delete */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {sessions.map((s) => {
            const isSelected = s.sessionId === currentSessionId
            const isEditing = editingSessionId === s.sessionId

            return (
              <div
                key={s.sessionId}
                onClick={() => switchSession(s.sessionId)}
                className={`group relative w-full text-left p-2 rounded text-xs transition-colors cursor-pointer flex flex-col gap-0.5 ${
                  isSelected
                    ? 'bg-[#1E1E1B] text-white border border-[#2E2E2A]'
                    : 'text-[#9E9D96] hover:bg-[#1A1A17] hover:text-[#EDECE8]'
                }`}
              >
                {isEditing ? (
                  <div
                    className="flex items-center gap-1 w-full"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <input
                      type="text"
                      autoFocus
                      value={editTitleValue}
                      onChange={(e) => setEditTitleValue(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleSaveRename(s.sessionId)
                        if (e.key === 'Escape') setEditingSessionId(null)
                      }}
                      className="flex-1 bg-[#141412] text-xs text-[#EDECE8] px-1.5 py-0.5 rounded border border-[#4EAA79] outline-none"
                    />
                    <button
                      onClick={() => handleSaveRename(s.sessionId)}
                      className="p-1 text-[#4EAA79] hover:text-white"
                      title="Save title"
                    >
                      <Check size={12} />
                    </button>
                    <button
                      onClick={() => setEditingSessionId(null)}
                      className="p-1 text-[#7E7D77] hover:text-white"
                      title="Cancel"
                    >
                      <X size={12} />
                    </button>
                  </div>
                ) : (
                  <>
                    <div className="flex items-center justify-between">
                      <span className="font-medium truncate pr-1 flex-1">{s.title}</span>
                      <div className="opacity-0 group-hover:opacity-100 flex items-center gap-0.5 transition-opacity">
                        <button
                          onClick={(e) => handleStartRename(s, e)}
                          className="p-1 text-[#7E7D77] hover:text-[#EDECE8] rounded hover:bg-[#282824]"
                          title="Rename thread"
                        >
                          <Pencil size={11} />
                        </button>
                        <button
                          onClick={(e) => handleDeleteThread(s.sessionId, e)}
                          className="p-1 text-[#7E7D77] hover:text-[#D9534F] rounded hover:bg-[#282824]"
                          title="Delete thread"
                        >
                          <Trash2 size={11} />
                        </button>
                      </div>
                    </div>
                    <div className="flex items-center justify-between text-[10px] font-mono text-[#5A5955]">
                      <span>{s.turnCount} turn{s.turnCount === 1 ? '' : 's'}</span>
                      <span>
                        {new Date(s.lastActive).toLocaleDateString([], {
                          month: 'short',
                          day: 'numeric',
                        })}
                      </span>
                    </div>
                  </>
                )}
              </div>
            )
          })}
        </div>
      </aside>

      {/* Resizable Divider Handle: Threads */}
      <div
        onMouseDown={handleStartResizeThreads}
        className="w-1.5 shrink-0 bg-[#242422] hover:bg-[#4EAA79]/80 active:bg-[#4EAA79] cursor-col-resize transition-colors relative z-20 select-none group flex items-center justify-center"
        title="Drag to resize Threads panel"
      >
        <div className="w-0.5 h-6 rounded-full bg-[#3E3E38] group-hover:bg-[#4EAA79] transition-colors" />
      </div>

      {/* ─── 2. MAIN CONVERSATION WORKSPACE ───────────────────────────────── */}
      <div className="flex-1 flex flex-col h-full bg-[#0E0E0D] overflow-hidden">
        {/* Workspace Top Toolbar: Slim & Minimalist (Antigravity Style) */}
        <div className="px-4 py-2 border-b border-[#1C1C1A] flex items-center justify-between text-xs bg-[#0D0D0C]">
          {/* Thread Title Header */}
          <div className="flex items-center gap-2 truncate max-w-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-[#555550] shrink-0" />
            <span className="font-medium text-[#EDECE8] truncate text-xs">{sessionTitle}</span>
            <span className="text-[10px] font-mono text-[#555550]">
              {messages.length} msgs
            </span>
          </div>

          {/* Right Toolbar Controls (All Black, Small, Minimalist) */}
          <div className="flex items-center gap-2">
            {/* Model Selector Dropdown */}
            <div className="relative" ref={modelDropdownRef}>
              <button
                onClick={() => setIsModelDropdownOpen(!isModelDropdownOpen)}
                className="flex items-center gap-1.5 px-2 py-1 rounded border border-[#20201E] bg-[#141412] hover:bg-[#1A1A17] hover:border-[#2C2C28] text-[11px] font-mono transition-colors cursor-pointer text-[#B0AFA8] hover:text-[#EDECE8]"
              >
                {currentModel.logo && (
                  <img src={currentModel.logo} alt="" className="w-3 h-3 object-contain rounded" />
                )}
                <span>{currentModel.name}</span>
                <ChevronDown size={11} className="text-[#555550]" />
              </button>

              {isModelDropdownOpen && (
                <div className="absolute top-full right-0 mt-1 w-52 rounded-lg border border-[#222220] bg-[#121210] shadow-2xl z-30 p-1 font-mono text-xs">
                  {MODEL_OPTIONS.map((m) => (
                    <div
                      key={m.id}
                      onClick={() => {
                        setProvider(m.id)
                        setIsModelDropdownOpen(false)
                      }}
                      className={`p-2 rounded flex items-center justify-between cursor-pointer transition-colors ${
                        provider === m.id ? 'bg-[#1C1C18] text-white' : 'hover:bg-[#161614] text-[#8E8D88]'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        {m.logo && <img src={m.logo} alt="" className="w-3.5 h-3.5 object-contain rounded" />}
                        <div>
                          <div className="font-medium text-[#EDECE8] text-[11px]">{m.name}</div>
                          <div className="text-[9px] text-[#555550]">{m.subname}</div>
                        </div>
                      </div>
                      {provider === m.id && <Check size={11} className="text-[#4EAA79]" />}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Domain Selector */}
            <select
              value={domain}
              onChange={(e) => setDomain(e.target.value as TaskDomain)}
              className="px-2 py-1 rounded border border-[#20201E] bg-[#141412] text-[11px] text-[#8E8D88] hover:text-[#C8C7C1] hover:border-[#2C2C28] font-mono focus:outline-none cursor-pointer"
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
              className={`flex items-center gap-1 px-2 py-1 rounded border text-[11px] font-mono transition-colors cursor-pointer ${
                apiKeys[provider]
                  ? 'border-[#2A3830] bg-[#121A15] text-[#4EAA79]'
                  : 'border-[#20201E] bg-[#141412] text-[#666660] hover:text-[#EDECE8]'
              }`}
              title="API Key"
            >
              <KeyRound size={11} />
              <span>{apiKeys[provider] ? 'Key' : 'Key'}</span>
            </button>

            <div className="w-px h-3.5 bg-[#1C1C1A]" />

            {/* AEMA Memory Toggle */}
            <label className="flex items-center gap-1.5 text-[11px] font-mono cursor-pointer select-none text-[#8E8D88] hover:text-[#EDECE8]">
              <input
                type="checkbox"
                checked={memoryEnabled}
                onChange={(e) => setMemoryEnabled(e.target.checked)}
                className="w-3 h-3 rounded bg-[#141412] border-[#20201E] text-[#4EAA79] focus:ring-0 cursor-pointer"
              />
              <span>Memory</span>
            </label>

            {/* Trap Test Toggle */}
            <label className="flex items-center gap-1.5 text-[11px] font-mono cursor-pointer select-none text-[#666660] hover:text-[#9E9D96]">
              <input
                type="checkbox"
                checked={simulateFailure}
                onChange={(e) => setSimulateFailure(e.target.checked)}
                className="w-3 h-3 rounded bg-[#141412] border-[#20201E] text-[#D9534F] focus:ring-0 cursor-pointer"
              />
              <span>Trap</span>
            </label>

            <div className="w-px h-3.5 bg-[#1C1C1A]" />

            {/* Cognitive Trace Toggle */}
            <button
              onClick={() => setIsInspectorOpen(!isInspectorOpen)}
              className={`flex items-center gap-1.5 px-2 py-1 rounded text-[11px] font-mono transition-colors cursor-pointer border ${
                isInspectorOpen
                  ? 'bg-[#181816] border-[#2C2C28] text-[#EDECE8]'
                  : selectedExecution
                  ? 'bg-[#141412] border-[#262624] text-[#B0AFA8] hover:text-[#EDECE8]'
                  : 'bg-transparent border-[#1E1E1C] text-[#666660] hover:text-[#EDECE8]'
              }`}
            >
              <Activity size={11} className={selectedExecution ? 'text-[#4EAA79]' : isInspectorOpen ? 'text-[#EDECE8]' : ''} />
              <span>Trace</span>
              {selectedExecution && !isInspectorOpen && (
                <span className="w-1.5 h-1.5 rounded-full bg-[#4EAA79] shrink-0" />
              )}
            </button>
          </div>
        </div>

        {/* Chat / Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && !runningExecution ? (
            /* Empty State Hero Banner */
            <div className="max-w-xl mx-auto my-12 text-center space-y-3">
              <div className="inline-block px-2.5 py-1 rounded-full border border-[#2E2E2A] bg-[#161614] text-[11px] font-mono text-[#7E7D77] uppercase tracking-wider mb-2">
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
            <>
              {/* Stream of Completed Messages */}
              {messages.map((msg) => {
                const isUser = msg.role === 'user'
                const exec = msg.execution

                return (
                  <div
                    key={msg.id}
                    className={`flex flex-col space-y-1.5 ${
                      isUser ? 'ml-auto items-end max-w-xl' : 'mr-auto items-start w-full max-w-4xl'
                    }`}
                  >
                    {isUser ? (
                      /* User Message Bubble */
                      <div className="bg-[#20201E] text-[#EDECE8] rounded-2xl px-4 py-2.5 text-xs sm:text-[13px] border border-[#2A2A26]/50 shadow-sm">
                        <p className="whitespace-pre-wrap">{msg.content}</p>
                      </div>
                    ) : (
                      /* Assistant Message (Antigravity Style: Seamless Canvas) */
                      <div className="w-full text-xs sm:text-[13px] leading-relaxed text-[#EDECE8] space-y-2">
                        {/* Antigravity Minimalist Thinking Block */}
                        {exec && (
                          <div className="py-0.5 select-none">
                            <button
                              type="button"
                              onClick={() =>
                                setExpandedThoughtIds((prev) => ({
                                  ...prev,
                                  [msg.id]: !prev[msg.id],
                                }))
                              }
                              className="group inline-flex items-center gap-1.5 text-xs text-[#7E7D77] hover:text-[#C8C7C1] transition-colors cursor-pointer py-0.5"
                            >
                              <span className="font-sans">Thinking</span>
                              <span className="text-[10px] text-[#555550] font-mono">
                                {(exec.latencyMs / 1000).toFixed(1)}s
                              </span>
                              {expandedThoughtIds[msg.id] ? (
                                <ChevronDown size={11} className="text-[#555550] group-hover:text-[#7E7D77]" />
                              ) : (
                                <ChevronRight size={11} className="text-[#555550] group-hover:text-[#7E7D77]" />
                              )}
                            </button>

                            {expandedThoughtIds[msg.id] && (
                              <div className="mt-1 ml-1 pl-3 border-l border-[#20201E] space-y-1 font-mono text-[11px] text-[#7E7D77]">
                                <div className="flex items-center gap-2">
                                  <span className="w-1 h-1 rounded-full bg-[#555550]" />
                                  <span>
                                    {exec.retrievedExperiences?.length
                                      ? `Retrieved ${exec.retrievedExperiences.length} verified memor${exec.retrievedExperiences.length === 1 ? 'y' : 'ies'} (trust: ${(exec.retrievedExperiences[0].empiricalTrust * 100).toFixed(0)}%, sim: ${exec.retrievedExperiences[0].similarityScore.toFixed(2)})`
                                      : 'Zero prior experiences passed trust threshold (similarity > 0.60, trust >= 0.35)'}
                                  </span>
                                </div>
                                <div className="flex items-center gap-2">
                                  <span className="w-1 h-1 rounded-full bg-[#555550]" />
                                  <span>Executed solution via {currentModel.name} ({exec.tokensUsed} tokens)</span>
                                </div>
                                <div className="flex items-center gap-2">
                                  <span className="w-1 h-1 rounded-full bg-[#555550]" />
                                  <span>
                                    Evaluated outcome:{' '}
                                    <span className="text-[#EDECE8]">
                                      {exec.outcomeQuality ? exec.outcomeQuality.toLowerCase() : (exec.outcomeScore && exec.outcomeScore >= 0.7 ? 'positive' : 'neutral')}
                                    </span>
                                  </span>
                                </div>
                                <div className="flex items-center gap-2">
                                  <span className="w-1 h-1 rounded-full bg-[#555550]" />
                                  <span>Distilled procedural reflection (+σ strategy, -π pitfall)</span>
                                </div>
                                <div className="flex items-center gap-2">
                                  <span className="w-1 h-1 rounded-full bg-[#555550]" />
                                  <span>A-EMA reliability scores calibrated (Theorem 1)</span>
                                </div>
                                <div className="pt-0.5">
                                  <button
                                    type="button"
                                    onClick={() => {
                                      setSelectedExecution(exec)
                                      setShowDevDrawer(true)
                                    }}
                                    className="text-[10px] text-[#555550] hover:text-[#9E9D96] transition-colors flex items-center gap-1 cursor-pointer"
                                  >
                                    <span>Inspect trace telemetry</span>
                                    <ChevronRight size={10} />
                                  </button>
                                </div>
                              </div>
                            )}
                          </div>
                        )}

                        {/* Formatted Markdown Output directly on canvas */}
                        <div className="pt-0.5">
                          <MarkdownRenderer content={msg.content} />
                        </div>

                        {/* Interactive Trace Verification Action Bar */}
                        {exec && (
                          <div className="pt-2 flex flex-wrap items-center justify-between gap-2 border-t border-[#1C1C1A]/80 text-[11px] font-mono select-none">
                            <div className="flex items-center gap-2 text-[#666660]">
                              <span>{(exec.latencyMs / 1000).toFixed(1)}s</span>
                              <span>•</span>
                              <span>{exec.completionTokens ? `${exec.completionTokens.toLocaleString()} tokens` : `${exec.tokensUsed.toLocaleString()} tokens`}</span>
                              <span>•</span>
                              <span>{currentModel.name}</span>
                            </div>

                            <button
                              type="button"
                              onClick={() => {
                                setSelectedExecution(exec)
                                setIsInspectorOpen(true)
                              }}
                              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-[#242420] bg-[#141412] hover:bg-[#1A1A17] hover:border-[#383832] text-[#B0AFA8] hover:text-[#EDECE8] transition-all cursor-pointer shadow-sm group"
                              title="Open 5-node cognitive trace and A-EMA calibration inspector"
                            >
                              <span
                                className={`w-1.5 h-1.5 rounded-full ${
                                  exec.outcomeQuality === 'positive' || (exec.outcomeScore && exec.outcomeScore >= 0.7)
                                    ? 'bg-[#4EAA79]'
                                    : exec.outcomeQuality === 'negative'
                                    ? 'bg-[#D9534F]'
                                    : 'bg-[#9E9D96]'
                                }`}
                              />
                              <span className="font-medium text-[11px]">Cognitive Trace</span>
                              {exec.retrievedExperiences && exec.retrievedExperiences.length > 0 && (
                                <span className="text-[10px] text-[#7E7D77]">
                                  ({exec.retrievedExperiences.length} memor{exec.retrievedExperiences.length === 1 ? 'y' : 'ies'})
                                </span>
                              )}
                              <ChevronRight size={11} className="text-[#555550] group-hover:text-[#B0AFA8] group-hover:translate-x-0.5 transition-transform" />
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}

              {/* ─── LIVE RUNNING ASSISTANT (Antigravity Style) ─── */}
              {runningExecution && (
                <div className="flex flex-col mr-auto items-start w-full max-w-4xl py-1 animate-in fade-in duration-150">
                  <div className="select-none">
                    <button
                      type="button"
                      onClick={() =>
                        setRunningExecution((prev) =>
                          prev ? { ...prev, isExpanded: !prev.isExpanded } : null
                        )
                      }
                      className="group inline-flex items-center gap-1.5 text-xs text-[#8E8D88] hover:text-[#EDECE8] transition-colors cursor-pointer py-0.5"
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-[#8E8D88] animate-pulse" />
                      <span className="font-sans">Thinking</span>
                      <span className="text-[10px] text-[#555550] font-mono">
                        {runningExecution.elapsedSeconds}s
                      </span>
                      {runningExecution.isExpanded ? (
                        <ChevronDown size={11} className="text-[#555550]" />
                      ) : (
                        <ChevronRight size={11} className="text-[#555550]" />
                      )}
                    </button>

                    {runningExecution.isExpanded && (
                      <div className="mt-1 ml-1 pl-3 border-l border-[#20201E] space-y-1 font-mono text-[11px] text-[#7E7D77]">
                        <div className="flex items-center gap-2">
                          <span className={`w-1 h-1 rounded-full ${getStageIndex(runningExecution.stage) >= 0 ? 'bg-[#9E9D96]' : 'bg-[#333330]'}`} />
                          <span className={getStageIndex(runningExecution.stage) >= 0 ? 'text-[#C8C7C1]' : 'text-[#555550]'}>
                            Querying experiential memories (min_sim &gt; 0.60, trust &ge; 0.35)
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`w-1 h-1 rounded-full ${getStageIndex(runningExecution.stage) >= 1 ? 'bg-[#9E9D96]' : 'bg-[#333330]'}`} />
                          <span className={getStageIndex(runningExecution.stage) >= 1 ? 'text-[#C8C7C1]' : 'text-[#555550]'}>
                            Generating task solution via {currentModel.name}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`w-1 h-1 rounded-full ${getStageIndex(runningExecution.stage) >= 2 ? 'bg-[#9E9D96]' : 'bg-[#333330]'}`} />
                          <span className={getStageIndex(runningExecution.stage) >= 2 ? 'text-[#C8C7C1]' : 'text-[#555550]'}>
                            Evaluating deterministic outcome verification
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`w-1 h-1 rounded-full ${getStageIndex(runningExecution.stage) >= 3 ? 'bg-[#9E9D96]' : 'bg-[#333330]'}`} />
                          <span className={getStageIndex(runningExecution.stage) >= 3 ? 'text-[#C8C7C1]' : 'text-[#555550]'}>
                            Distilling procedural reflection (+σ, -π)
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`w-1 h-1 rounded-full ${getStageIndex(runningExecution.stage) >= 4 ? 'bg-[#9E9D96]' : 'bg-[#333330]'}`} />
                          <span className={getStageIndex(runningExecution.stage) >= 4 ? 'text-[#C8C7C1]' : 'text-[#555550]'}>
                            Calibrating A-EMA reliability scores (Theorem 1)
                          </span>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Real-Time Streaming Tokens directly on canvas */}
                  {runningExecution.tokens && (
                    <div className="pt-2 text-xs sm:text-[13px] leading-relaxed text-[#EDECE8] w-full">
                      <MarkdownRenderer content={runningExecution.tokens} />
                    </div>
                  )}
                </div>
              )}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Bottom Message Input: Minimalist & Clean */}
        <div className="p-3 sm:p-4 border-t border-[#1C1C1A] bg-[#0D0D0C]">
          <div className="border border-[#20201E] rounded-xl bg-[#131311] p-2 flex flex-col gap-2 focus-within:border-[#2E2E2A] transition-colors">
            <textarea
              ref={textareaRef}
              rows={2}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isExecuting}
              placeholder="Send task instructions or query the agent... (Shift+Enter for newline, Enter to run)"
              className="bg-transparent text-xs sm:text-[13px] text-[#EDECE8] placeholder-[#555550] focus:outline-none resize-none p-1 disabled:opacity-50"
            />
            <div className="flex items-center justify-between pt-1 border-t border-[#1C1C1A]">
              <span className="text-[10px] font-mono text-[#555550]">Enter to execute</span>
              <button
                onClick={() => handleSendMessage()}
                disabled={!inputText.trim() || isExecuting}
                className="px-3 py-1 rounded bg-[#EDECE8] text-[#121210] font-medium text-xs hover:bg-white transition-colors cursor-pointer disabled:opacity-40"
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

      {/* ─── 3. RIGHT INSPECTOR PANEL (100% Focused on Cognitive Trace) ─── */}
      {isInspectorOpen && (
        <aside
          className="shrink-0 bg-[#0E0E0D] border-l border-[#1C1C1A] flex flex-col overflow-y-auto"
          style={{ width: `${inspectorWidth}px` }}
        >
          <div className="px-3 py-2 border-b border-[#1C1C1A] flex items-center justify-between">
            <span className="font-mono text-[10px] uppercase tracking-wider text-[#7E7D77]">
              Cognitive Trace
            </span>
            <button
              onClick={() => setIsInspectorOpen(false)}
              className="p-1 rounded text-[#7E7D77] hover:text-[#EDECE8] transition-colors cursor-pointer"
              title="Close inspector"
            >
              <PanelRightClose size={13} />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-3 space-y-3">
            {selectedExecution ? (
              <>
                {/* Executive Trace Badge */}
                <div className="p-3 rounded-lg border border-[#1E1E1C] bg-[#11110F] font-mono text-xs space-y-2">
                  <div className="flex items-center justify-between text-[#EDECE8] font-medium text-[11px]">
                    <span className="flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#555550]" />
                      {selectedExecution.id}
                    </span>
                    <span className="px-1.5 py-0.5 rounded text-[9px] uppercase font-mono bg-[#1C1C1A] text-[#8E8D88] border border-[#262624]">
                      {selectedExecution.taskDomain}
                    </span>
                  </div>
                  <div className="text-[10px] text-[#555550] truncate">
                    Input: "{selectedExecution.taskInput}"
                  </div>
                  <div className="grid grid-cols-3 gap-2 pt-2 border-t border-[#1C1C1A] text-[10px]">
                    <div>
                      <span className="text-[#555550] block">Latency</span>
                      <span className="font-mono text-[#C8C7C1]">{selectedExecution.latencyMs}ms</span>
                    </div>
                    <div>
                      <span className="text-[#555550] block">Tokens</span>
                      <span className="font-mono text-[#C8C7C1]" title={`Output: ${selectedExecution.completionTokens}, Input: ${selectedExecution.promptTokens}, Total: ${selectedExecution.tokensUsed}`}>
                        {selectedExecution.completionTokens ? `${selectedExecution.completionTokens} out` : selectedExecution.tokensUsed}
                      </span>
                    </div>
                    <div>
                      <span className="text-[#555550] block">Outcome</span>
                      <span
                        className={`font-mono font-semibold uppercase ${
                          selectedExecution.outcomeQuality === 'positive' ||
                          (selectedExecution.outcomeScore && selectedExecution.outcomeScore >= 0.7)
                            ? 'text-[#4EAA79]'
                            : 'text-[#D9534F]'
                        }`}
                      >
                        {selectedExecution.outcomeQuality
                          ? selectedExecution.outcomeQuality.toUpperCase()
                          : selectedExecution.outcomeScore && selectedExecution.outcomeScore >= 0.7
                          ? 'SUCCESS'
                          : 'FAILURE'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* The 5-Node Stepper: Cognitive Lifecycle */}
                <ExecutionStepper currentStage="complete" execution={selectedExecution} />

                {/* Developer Deep-Dive Drawer Button */}
                <button
                  type="button"
                  onClick={() => setShowDevDrawer(true)}
                  className="w-full py-2 px-3 rounded-lg border border-[#1E1E1C] bg-[#11110F] hover:bg-[#161614] text-[#8E8D88] hover:text-[#EDECE8] text-xs font-mono transition-colors flex items-center justify-between group cursor-pointer"
                >
                  <span className="flex items-center gap-2">
                    <Code size={12} className="text-[#7E7D77]" />
                    <span className="text-[11px] font-medium">
                      Inspect System Prompt & Telemetry
                    </span>
                  </span>
                  <span className="text-[10px] text-[#555550] group-hover:text-[#8E8D88] flex items-center gap-0.5">
                    <span>Drawer</span>
                    <ChevronRight size={11} className="group-hover:translate-x-0.5 transition-transform" />
                  </span>
                </button>
              </>
            ) : (
              <div className="p-8 text-center text-xs text-[#555550] font-mono">
                No execution selected. Select a response to view its cognitive trace.
              </div>
            )}
          </div>
        </aside>
      )}

      {/* ─── Developer Inspection Drawer (Antigravity Style) ──────────────── */}
      <ContextInspector
        execution={selectedExecution}
        isOpen={showDevDrawer}
        onClose={() => setShowDevDrawer(false)}
      />

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
