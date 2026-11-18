import { useState } from 'react'
import { Code, Check, Copy } from 'lucide-react'
import type { TaskExecution } from '../types'
import MarkdownRenderer from './MarkdownRenderer'

interface ContextInspectorProps {
  execution: TaskExecution | null
}

export default function ContextInspector({ execution }: ContextInspectorProps) {
  const [activeTab, setActiveTab] = useState<'output' | 'prompt' | 'raw'>('output')
  const [copied, setCopied] = useState(false)

  if (!execution) {
    return (
      <div className="rounded-lg border border-[#242422] p-6 text-center bg-[#161614] text-[#7E7D77]">
        <Code size={20} className="mx-auto mb-2 opacity-50" />
        <span className="text-xs font-mono">No execution selected. Run a task or select a trace.</span>
      </div>
    )
  }

  const memoryInjected = execution.retrievedExperiences?.[0]?.experience

  const promptPreview = execution.memoryEnabled && memoryInjected
    ? `System: You are an autonomous agent with reliability-aware experiential memory.
Prior verified strategy (Trust ${(memoryInjected.trustScore * 100).toFixed(1)}%):
"${memoryInjected.strategyLesson}"
${memoryInjected.pitfallWarning ? `Avoid known hazard pitfall: "${memoryInjected.pitfallWarning}"` : ''}

User Prompt:
${execution.taskInput}`
    : `System: You are a standard stateless autonomous LLM agent without experiential memory.

User Prompt:
${execution.taskInput}`

  const copyText = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="rounded-lg border border-[#242422] bg-[#161614] text-[#EDECE8] overflow-hidden">
      {/* Header and Tabs */}
      <div className="px-3 py-2 border-b border-[#242422] flex items-center justify-between bg-[#1A1A17]">
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setActiveTab('output')}
            className={`px-2.5 py-1 rounded text-xs font-medium font-mono transition-colors cursor-pointer ${
              activeTab === 'output'
                ? 'bg-[#22221E] text-white border border-[#2E2E2A]'
                : 'text-[#7E7D77] hover:text-[#EDECE8]'
            }`}
          >
            Output
          </button>
          <button
            onClick={() => setActiveTab('prompt')}
            className={`px-2.5 py-1 rounded text-xs font-medium font-mono transition-colors cursor-pointer ${
              activeTab === 'prompt'
                ? 'bg-[#22221E] text-white border border-[#2E2E2A]'
                : 'text-[#7E7D77] hover:text-[#EDECE8]'
            }`}
          >
            Context
          </button>
          <button
            onClick={() => setActiveTab('raw')}
            className={`px-2.5 py-1 rounded text-xs font-medium font-mono transition-colors cursor-pointer ${
              activeTab === 'raw'
                ? 'bg-[#22221E] text-white border border-[#2E2E2A]'
                : 'text-[#7E7D77] hover:text-[#EDECE8]'
            }`}
          >
            Raw JSON
          </button>
        </div>

        <button
          onClick={() =>
            copyText(
              activeTab === 'output'
                ? execution.finalOutput || ''
                : activeTab === 'prompt'
                ? promptPreview
                : JSON.stringify(execution, null, 2)
            )
          }
          className="flex items-center gap-1 text-[11px] font-mono text-[#7E7D77] hover:text-[#EDECE8] transition-colors cursor-pointer"
        >
          {copied ? <Check size={12} className="text-[#4EAA79]" /> : <Copy size={12} />}
          <span>{copied ? 'Copied' : 'Copy'}</span>
        </button>
      </div>

      {/* Body Area */}
      <div className="p-3 text-xs font-mono overflow-x-auto max-h-[380px] leading-relaxed">
        {activeTab === 'output' && (
          <div className="space-y-2.5">
            <div className="p-3 rounded-lg bg-[#141412] border border-[#242422] text-[#EDECE8]">
              <MarkdownRenderer content={execution.finalOutput || 'No output generated.'} />
            </div>

            {execution.reflectionLesson && (
              <div className="p-3 rounded-lg bg-[#1E1E1B] border border-[#2E2E2A] text-[#EDECE8]">
                <span className="font-semibold block mb-1 text-[#4EAA79]">Post-Execution Reflection:</span>
                {execution.reflectionLesson}
              </div>
            )}
          </div>
        )}

        {activeTab === 'prompt' && (
          <pre className="p-3 rounded-lg bg-[#141412] border border-[#242422] text-[#EDECE8] whitespace-pre-wrap">
            {promptPreview}
          </pre>
        )}

        {activeTab === 'raw' && (
          <pre className="p-3 rounded-lg bg-[#141412] border border-[#242422] text-[#EDECE8] whitespace-pre-wrap">
            {JSON.stringify(execution, null, 2)}
          </pre>
        )}
      </div>
    </div>
  )
}
