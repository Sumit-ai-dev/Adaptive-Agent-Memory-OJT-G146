import { useState } from 'react'
import { Code, Check, Copy, X, Terminal, FileJson } from 'lucide-react'
import type { TaskExecution } from '../types'

interface ContextInspectorProps {
  execution: TaskExecution | null
  isOpen?: boolean
  onClose?: () => void
}

export default function ContextInspector({ execution, isOpen, onClose }: ContextInspectorProps) {
  const [activeTab, setActiveTab] = useState<'prompt' | 'raw'>('prompt')
  const [copied, setCopied] = useState(false)

  // In modal mode (when isOpen is explicitly provided), respect open/close state
  if (isOpen !== undefined && !isOpen) return null

  if (!execution) {
    if (isOpen !== undefined) return null
    return (
      <div className="rounded-xl border border-[#242422] p-8 text-center bg-[#161614] text-[#7E7D77] font-mono text-xs">
        <Code size={18} className="mx-auto mb-2 opacity-40 text-[#4EAA79]" />
        <span>No execution selected. Select a cognitive trace to inspect telemetry.</span>
      </div>
    )
  }

  const memoryInjected = execution.retrievedExperiences?.[0]?.experience

  const promptPreview = execution.memoryEnabled && memoryInjected
    ? `System: You are an autonomous agent with reliability-aware experiential memory.

[INJECTED PROCEDURAL MEMORY]
Prior verified strategy (Trust ${(memoryInjected.trustScore * 100).toFixed(1)}%):
"${memoryInjected.strategyLesson}"
${memoryInjected.pitfallWarning ? `Avoid known hazard pitfall:\n"${memoryInjected.pitfallWarning}"` : ''}

[USER TASK SPECIFICATION]
Domain: ${execution.taskDomain}
Prompt:
${execution.taskInput}`
    : `System: You are a standard stateless autonomous LLM agent without experiential memory.

[USER TASK SPECIFICATION]
Domain: ${execution.taskDomain}
Prompt:
${execution.taskInput}`

  const copyText = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const rawJsonStr = JSON.stringify(execution, null, 2)

  const isModal = isOpen !== undefined

  const cardContent = (
    <div className={`w-full ${isModal ? 'max-w-3xl max-h-[85vh]' : ''} rounded-xl border border-[#2E2E2A] bg-[#161614] text-[#EDECE8] shadow-2xl flex flex-col overflow-hidden`}>
      {/* Header */}
      <div className="px-5 py-3.5 border-b border-[#242422] flex items-center justify-between bg-[#1A1A17]">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-[#22221E] border border-[#2E2E2A] flex items-center justify-center text-[#4EAA79]">
            <Code size={15} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold text-[#EDECE8]">
                Developer Telemetry & Context Inspector
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#4EAA79]/15 text-[#4EAA79] border border-[#4EAA79]/30 uppercase font-semibold">
                {execution.taskDomain}
              </span>
            </div>
            <span className="text-[11px] font-mono text-[#7E7D77]">
              Trace #{execution.id.replace('exec_', '')}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => copyText(activeTab === 'prompt' ? promptPreview : rawJsonStr)}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#22221E] hover:bg-[#2A2A26] border border-[#2E2E2A] text-xs font-mono text-[#EDECE8] transition-colors cursor-pointer"
            title="Copy current view"
          >
            {copied ? <Check size={12} className="text-[#4EAA79]" /> : <Copy size={12} />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>

          {isModal && onClose && (
            <button
              onClick={onClose}
              className="p-1 rounded-lg hover:bg-[#22221E] text-[#7E7D77] hover:text-[#EDECE8] transition-colors cursor-pointer"
              title="Close drawer"
            >
              <X size={16} />
            </button>
          )}
        </div>
      </div>

      {/* Tab Switcher */}
      <div className="px-5 py-2 border-b border-[#242422] flex items-center justify-between bg-[#141412] text-xs font-mono">
        <div className="flex items-center gap-1">
          <button
            onClick={() => setActiveTab('prompt')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-colors cursor-pointer ${
              activeTab === 'prompt'
                ? 'bg-[#22221E] text-[#EDECE8] border border-[#2E2E2A]'
                : 'text-[#7E7D77] hover:text-[#EDECE8]'
            }`}
          >
            <Terminal size={13} className={activeTab === 'prompt' ? 'text-[#4EAA79]' : ''} />
            <span>Injected Prompt Context</span>
          </button>

          <button
            onClick={() => setActiveTab('raw')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-colors cursor-pointer ${
              activeTab === 'raw'
                ? 'bg-[#22221E] text-[#EDECE8] border border-[#2E2E2A]'
                : 'text-[#7E7D77] hover:text-[#EDECE8]'
            }`}
          >
            <FileJson size={13} className={activeTab === 'raw' ? 'text-[#E67E22]' : ''} />
            <span>Raw Telemetry JSON</span>
          </button>
        </div>

        <div className="text-[11px] text-[#7E7D77]">
          {activeTab === 'prompt' ? (
            <span>Verified Strategy Injection Audit</span>
          ) : (
            <span>Full TaskExecution Payload</span>
          )}
        </div>
      </div>

      {/* Content Body */}
      <div className="flex-1 overflow-y-auto p-5 text-xs font-mono leading-relaxed bg-[#121210] max-h-[500px]">
        {activeTab === 'prompt' && (
          <div className="space-y-3">
            <div className="p-2.5 rounded-lg border border-[#2A3B30] bg-[#16221A] text-[11px] text-[#A6D8B8] flex items-center justify-between">
              <span>
                {execution.memoryEnabled && memoryInjected
                  ? 'Active memory retrieved and injected into LLM system prompt context.'
                  : 'Stateless baseline: no experiential memory injected into prompt.'}
              </span>
              {memoryInjected && (
                <span className="font-bold text-[#4EAA79]">
                  Trust S₀={(memoryInjected.trustScore * 100).toFixed(1)}%
                </span>
              )}
            </div>

            <pre className="p-4 rounded-lg bg-[#181815] border border-[#242422] text-[#EDECE8] whitespace-pre-wrap overflow-x-auto leading-relaxed shadow-inner">
              {promptPreview}
            </pre>
          </div>
        )}

        {activeTab === 'raw' && (
          <pre className="p-4 rounded-lg bg-[#181815] border border-[#242422] text-[#EDECE8] whitespace-pre-wrap overflow-x-auto leading-relaxed shadow-inner">
            {rawJsonStr}
          </pre>
        )}
      </div>
    </div>
  )

  if (isModal) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-in fade-in duration-150">
        {cardContent}
      </div>
    )
  }

  return cardContent
}
