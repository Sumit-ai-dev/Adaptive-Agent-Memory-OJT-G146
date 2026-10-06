import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Send,
  RotateCcw,
  Copy,
  Check,
  Bot,
  User,
  Sparkles,
  AlertCircle,
  Sliders,
  Database,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import {
  AgentConfig,
  TaskExecution,
  RetrievedMemoryItem,
  TrustUpdateItem,
} from '../types'
import { executeAgentTask } from '../services/api'
import WorkspaceHeader from '../components/workspace/WorkspaceHeader'
import AgentConfigDrawer from '../components/workspace/AgentConfigDrawer'
import MemoryContextPanel from '../components/workspace/MemoryContextPanel'
import MarkdownRenderer from '../components/workspace/MarkdownRenderer'
import ExecutionTraceView from '../components/workspace/ExecutionTraceView'

interface ChatMessage {
  id: string
  sender: 'user' | 'assistant'
  content: string
  timestamp: string
  execution?: TaskExecution
  isError?: boolean
}

const STARTER_PROMPTS = [
  {
    title: 'Algorithm Optimization',
    prompt: 'Explain how binary search works and how to avoid integer overflow in midpoint calculation.',
    domain: 'coding' as const,
  },
  {
    title: 'Conflicting Research Claims',
    prompt: 'How should an agent handle multi-step analytical queries with conflicting factual claims in scientific literature?',
    domain: 'research' as const,
  },
  {
    title: 'Database Migrations',
    prompt: 'What strategy should be used for zero-downtime database migrations under high concurrent read/write traffic?',
    domain: 'coding' as const,
  },
]

export default function AgentWorkspacePage() {
  const { user, loading: authLoading } = useAuth()
  const navigate = useNavigate()

  // Route Guard
  useEffect(() => {
    if (!authLoading && !user) {
      navigate('/', { replace: true })
    }
  }, [user, authLoading, navigate])

  // Agent Runtime Configuration State
  const [config, setConfig] = useState<AgentConfig>({
    domain: 'research',
    memoryEnabled: true,
    memoryMode: 'adaptive',
    provider: 'mock', // default to mock so it runs immediately with 0 keys
    model: 'mock-deterministic-v1',
    apiKey: '',
  })

  // Chat conversation state
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputPrompt, setInputPrompt] = useState('')
  const [isExecuting, setIsExecuting] = useState(false)
  const [lastExecutedPrompt, setLastExecutedPrompt] = useState<string | null>(null)
  const [copiedId, setCopiedId] = useState<string | null>(null)

  // Active Memory & Trace Panel state (synchronized to latest assistant turn or selected turn)
  const [activeRetrievedMemories, setActiveRetrievedMemories] = useState<RetrievedMemoryItem[]>([])
  const [activeTrustUpdates, setActiveTrustUpdates] = useState<TrustUpdateItem[]>([])

  // Responsive column drawer toggles for tablet/mobile
  const [showConfigDrawer, setShowConfigDrawer] = useState(false)
  const [showMemoryPanel, setShowMemoryPanel] = useState(false)

  // Auto-scroll anchor
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isExecuting])

  const handleSend = async (textToSend?: string) => {
    const prompt = (textToSend || inputPrompt).trim()
    if (!prompt || isExecuting) return

    setInputPrompt('')
    setLastExecutedPrompt(prompt)

    const userMessageId = `msg-${Date.now()}`
    const userMsg: ChatMessage = {
      id: userMessageId,
      sender: 'user',
      content: prompt,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }

    setMessages((prev) => [...prev, userMsg])
    setIsExecuting(true)

    try {
      // Execute REAL backend LangGraph engine via POST /api/agent/execute
      const executionResult = await executeAgentTask({
        taskInput: prompt,
        config,
      })

      const assistantContent =
        executionResult.finalAnswer ||
        executionResult.finalOutput ||
        'Task completed with 0 errors.'

      const assistantMsg: ChatMessage = {
        id: `assistant-${executionResult.id || Date.now()}`,
        sender: 'assistant',
        content: assistantContent,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        execution: executionResult,
      }

      setMessages((prev) => [...prev, assistantMsg])

      // Synchronize right-side memory panel
      setActiveRetrievedMemories(executionResult.retrievedMemories || [])
      setActiveTrustUpdates(executionResult.trustUpdates || [])
    } catch (err: unknown) {
      const errorText =
        err instanceof Error ? err.message : 'Execution pipeline failed'

      const errorMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        sender: 'assistant',
        content: `Error executing task: ${errorText}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        isError: true,
      }

      setMessages((prev) => [...prev, errorMsg])
    } finally {
      setIsExecuting(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleCopyMessage = async (id: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedId(id)
      setTimeout(() => setCopiedId(null), 2000)
    } catch {
      // fallback
    }
  }

  const handleRetry = () => {
    if (lastExecutedPrompt) {
      handleSend(lastExecutedPrompt)
    }
  }

  if (authLoading) {
    return (
      <div className="min-h-screen bg-[#0a0010] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-purple-400 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!user) return null

  return (
    <div className="min-h-screen bg-[#0a0010] text-white flex flex-col selection:bg-purple-500/30 overflow-hidden">
      {/* Background ambient lighting */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-40 left-1/4 w-[600px] h-[600px] bg-purple-600/10 rounded-full blur-[140px]" />
        <div className="absolute top-1/3 right-10 w-[500px] h-[500px] bg-emerald-600/10 rounded-full blur-[150px]" />
      </div>

      {/* Persistent Navigation Header */}
      <WorkspaceHeader />

      {/* Secondary Controls Bar on Mobile/Tablet */}
      <div className="lg:hidden flex items-center justify-between px-4 py-2 bg-[#0d0018] border-b border-white/10 text-xs">
        <button
          onClick={() => setShowConfigDrawer(!showConfigDrawer)}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/5 border border-white/10 text-white/70"
        >
          <Sliders size={13} />
          <span>Agent Config</span>
        </button>
        <button
          onClick={() => setShowMemoryPanel(!showMemoryPanel)}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-purple-500/15 border border-purple-500/30 text-purple-300"
        >
          <Database size={13} />
          <span>Memories ({activeRetrievedMemories.length})</span>
        </button>
      </div>

      {/* 3-COLUMN WORKSPACE BODY */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* LEFT COLUMN: Agent Configuration */}
        <aside
          className={`w-72 flex-shrink-0 z-30 transition-transform lg:translate-x-0 ${
            showConfigDrawer ? 'translate-x-0 absolute inset-y-0 left-0' : '-translate-x-full lg:static absolute'
          }`}
        >
          <AgentConfigDrawer
            config={config}
            disabled={isExecuting}
            onChange={(newConfig) => setConfig(newConfig)}
          />
        </aside>

        {/* CENTER COLUMN: Real AI Chat Conversation */}
        <main className="flex-1 flex flex-col bg-[#0a0010]/40 backdrop-blur-sm overflow-hidden relative">
          {/* Chat Messages Container */}
          <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 space-y-6">
            {messages.length === 0 ? (
              // Empty State
              <div className="h-full flex flex-col items-center justify-center text-center max-w-xl mx-auto py-12 space-y-6">
                <div className="w-14 h-14 rounded-2xl bg-purple-500/15 border border-purple-500/30 flex items-center justify-center text-purple-300 shadow-xl anim-pulse-ring">
                  <Bot size={28} />
                </div>

                <div className="space-y-2">
                  <h2 className="text-xl font-display font-bold text-white tracking-tight">
                    Experiential Agent Workspace
                  </h2>
                  <p className="text-sm font-sans text-white/50 leading-relaxed">
                    This agent uses real persistent experiences from previous executions to calibrate answers.
                    Ask a technical query or test one of the verified lesson triggers below.
                  </p>
                </div>

                {/* Starter Prompts */}
                <div className="w-full grid grid-cols-1 gap-2.5 pt-2 text-left">
                  {STARTER_PROMPTS.map((sp, idx) => (
                    <button
                      key={idx}
                      onClick={() => {
                        setConfig((prev) => ({ ...prev, domain: sp.domain }))
                        handleSend(sp.prompt)
                      }}
                      className="p-3.5 rounded-2xl glass hover:bg-white/[0.08] border border-white/10 hover:border-purple-400/40 transition-all text-xs group cursor-pointer"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-semibold text-white group-hover:text-purple-300 transition-colors">
                          {sp.title}
                        </span>
                        <span className="text-[10px] font-mono text-purple-400 uppercase tracking-wider px-2 py-0.5 rounded bg-purple-500/10">
                          {sp.domain}
                        </span>
                      </div>
                      <p className="text-white/50 text-[11px] font-sans line-clamp-1">
                        {sp.prompt}
                      </p>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              // Messages trajectory
              messages.map((msg) => (
                <div key={msg.id} className="space-y-3">
                  <div
                    className={`flex items-start gap-3.5 max-w-3xl ${
                      msg.sender === 'user' ? 'ml-auto flex-row-reverse' : 'mr-auto'
                    }`}
                  >
                    {/* Avatar icon */}
                    <div
                      className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 text-white shadow ${
                        msg.sender === 'user'
                          ? 'bg-purple-600 border border-purple-400/40'
                          : msg.isError
                          ? 'bg-red-500/20 border border-red-500/40 text-red-300'
                          : 'anim-gradient-bg border border-white/20'
                      }`}
                    >
                      {msg.sender === 'user' ? (
                        <User size={15} />
                      ) : msg.isError ? (
                        <AlertCircle size={15} />
                      ) : (
                        <Bot size={15} />
                      )}
                    </div>

                    {/* Message Bubble */}
                    <div
                      className={`p-4 rounded-2xl text-sm leading-relaxed max-w-[85%] ${
                        msg.sender === 'user'
                          ? 'bg-purple-600/25 border border-purple-500/40 text-white shadow-lg'
                          : msg.isError
                          ? 'bg-red-500/10 border border-red-500/30 text-red-200'
                          : 'glass border border-white/10 text-white shadow-xl'
                      }`}
                    >
                      {/* Sender label and timestamp */}
                      <div className="flex items-center justify-between gap-4 mb-1.5 text-[10px] font-mono text-white/40">
                        <span className="font-semibold text-white/70">
                          {msg.sender === 'user' ? 'You' : 'Adaptive Agent'}
                        </span>
                        <span>{msg.timestamp}</span>
                      </div>

                      {/* Content */}
                      {msg.sender === 'user' ? (
                        <p className="whitespace-pre-wrap font-sans text-sm">{msg.content}</p>
                      ) : (
                        <MarkdownRenderer content={msg.content} />
                      )}

                      {/* Actions footer for Assistant Messages */}
                      {msg.sender === 'assistant' && !msg.isError && (
                        <div className="flex items-center justify-between pt-2.5 mt-2.5 border-t border-white/10 text-[11px] font-mono text-white/50">
                          <div className="flex items-center gap-3">
                            <button
                              onClick={() => handleCopyMessage(msg.id, msg.content)}
                              className="flex items-center gap-1 hover:text-white transition-colors cursor-pointer"
                              title="Copy response"
                            >
                              {copiedId === msg.id ? (
                                <>
                                  <Check size={12} className="text-emerald-400" />
                                  <span className="text-emerald-400">Copied</span>
                                </>
                              ) : (
                                <>
                                  <Copy size={12} />
                                  <span>Copy</span>
                                </>
                              )}
                            </button>

                            <button
                              onClick={handleRetry}
                              className="flex items-center gap-1 hover:text-white transition-colors cursor-pointer"
                              title="Retry task execution"
                            >
                              <RotateCcw size={12} />
                              <span>Retry</span>
                            </button>
                          </div>

                          {msg.execution?.latencyMs && (
                            <span className="text-[10px]">
                              {msg.execution.latencyMs}ms
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Collapsible 5-Node Execution Trace below the response */}
                  {msg.execution && msg.execution.trajectory && (
                    <div className="max-w-3xl ml-11">
                      <ExecutionTraceView
                        trajectory={msg.execution.trajectory}
                        latencyMs={msg.execution.latencyMs}
                        tokensUsed={msg.execution.tokensUsed}
                        outcomeScore={msg.execution.outcomeScore}
                      />
                    </div>
                  )}
                </div>
              ))
            )}

            {/* In-Flight Execution Loader */}
            {isExecuting && (
              <div className="flex items-start gap-3.5 max-w-3xl mr-auto animate-pulse">
                <div className="w-8 h-8 rounded-xl anim-gradient-bg flex items-center justify-center flex-shrink-0 text-white shadow">
                  <Bot size={15} />
                </div>
                <div className="p-4 rounded-2xl glass border border-purple-500/30 text-white shadow-xl space-y-2 min-w-[240px]">
                  <div className="flex items-center gap-2 text-xs font-mono text-purple-300">
                    <Sparkles size={13} className="animate-spin text-purple-400" />
                    <span>Executing 5-node cyclical workflow...</span>
                  </div>
                  <div className="h-1.5 w-full bg-white/10 rounded-full overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-purple-500 via-fuchsia-500 to-cyan-400 animate-marquee" />
                  </div>
                  <div className="text-[10px] font-mono text-white/40">
                    retrieving experiences → evaluating → updating trust
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Prompt Input Area */}
          <div className="p-4 sm:p-6 border-t border-white/10 bg-[#0a0010]/80 backdrop-blur-xl">
            <div className="max-w-4xl mx-auto space-y-2">
              <div className="relative flex items-center rounded-2xl border border-white/15 bg-white/[0.04] focus-within:border-purple-400/60 focus-within:ring-2 focus-within:ring-purple-500/20 transition-all shadow-xl">
                <textarea
                  rows={2}
                  value={inputPrompt}
                  disabled={isExecuting}
                  onChange={(e) => setInputPrompt(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask your agent anything..."
                  className="w-full bg-transparent text-white placeholder:text-white/30 text-sm px-4 py-3 focus:outline-none resize-none font-sans"
                />

                <div className="pr-3 flex items-center gap-2">
                  <button
                    onClick={() => handleSend()}
                    disabled={!inputPrompt.trim() || isExecuting}
                    id="agent-send-button"
                    className="w-10 h-10 rounded-xl anim-gradient-bg hover:scale-105 active:scale-95 text-white flex items-center justify-center transition-all disabled:opacity-40 disabled:hover:scale-100 disabled:cursor-not-allowed shadow-md cursor-pointer"
                  >
                    <Send size={16} />
                  </button>
                </div>
              </div>

              {/* Sub-input footer */}
              <div className="flex items-center justify-between text-[11px] font-mono text-white/40 px-1">
                <span>Your agent can learn from previous experiences.</span>
                <span className="hidden sm:inline">Enter to send • Shift+Enter for newline</span>
              </div>
            </div>
          </div>
        </main>

        {/* RIGHT COLUMN: Memory & Experience Context Panel */}
        <aside
          className={`w-80 flex-shrink-0 z-30 transition-transform lg:translate-x-0 ${
            showMemoryPanel ? 'translate-x-0 absolute inset-y-0 right-0' : 'translate-x-full lg:static absolute'
          }`}
        >
          <MemoryContextPanel
            retrievedMemories={activeRetrievedMemories}
            trustUpdates={activeTrustUpdates}
            memoryEnabled={config.memoryEnabled}
          />
        </aside>
      </div>
    </div>
  )
}
