import { useState } from 'react'
import { Code, Check, Copy } from 'lucide-react'
import type { TaskExecution } from '../types'

interface ContextInspectorProps {
  execution: TaskExecution | null
}

export default function ContextInspector({ execution }: ContextInspectorProps) {
  const [activeTab, setActiveTab] = useState<'output' | 'prompt' | 'raw'>('output')
  const [copied, setCopied] = useState(false)

  if (!execution) {
    return (
      <div className="rounded-2xl border p-6 text-center bg-white border-[#E6E6E1] dark:bg-[#131722] dark:border-[#252B3B] text-zinc-400">
        <Code size={24} className="mx-auto mb-2 opacity-50" />
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
    <div className="rounded-2xl border bg-white border-[#E6E6E1] dark:bg-[#131722] dark:border-[#252B3B] overflow-hidden">
      {/* Header and Tabs */}
      <div className="px-5 py-3 border-b border-[#E6E6E1] dark:border-[#252B3B] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTab('output')}
            className={`px-3 py-1 rounded-md text-xs font-medium font-mono transition-colors ${
              activeTab === 'output'
                ? 'bg-zinc-100 dark:bg-[#1A1F2C] text-[#18181B] dark:text-[#F4F4F6]'
                : 'text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-300'
            }`}
          >
            Final Output
          </button>
          <button
            onClick={() => setActiveTab('prompt')}
            className={`px-3 py-1 rounded-md text-xs font-medium font-mono transition-colors ${
              activeTab === 'prompt'
                ? 'bg-zinc-100 dark:bg-[#1A1F2C] text-[#18181B] dark:text-[#F4F4F6]'
                : 'text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-300'
            }`}
          >
            Context Augmentation
          </button>
          <button
            onClick={() => setActiveTab('raw')}
            className={`px-3 py-1 rounded-md text-xs font-medium font-mono transition-colors ${
              activeTab === 'raw'
                ? 'bg-zinc-100 dark:bg-[#1A1F2C] text-[#18181B] dark:text-[#F4F4F6]'
                : 'text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-300'
            }`}
          >
            Raw JSON Trace
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
          className="flex items-center gap-1 text-[11px] font-mono text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-300 transition-colors"
        >
          {copied ? <Check size={13} className="text-emerald-500" /> : <Copy size={13} />}
          <span>{copied ? 'Copied' : 'Copy'}</span>
        </button>
      </div>

      {/* Body Area */}
      <div className="p-4 text-xs font-mono overflow-x-auto max-h-[380px] leading-relaxed">
        {activeTab === 'output' && (
          <div className="space-y-3">
            <div className="p-3 rounded-lg bg-zinc-50 dark:bg-[#1A1F2C] border border-[#E6E6E1] dark:border-[#252B3B] text-zinc-800 dark:text-zinc-200 whitespace-pre-wrap">
              {execution.finalOutput || 'No output generated.'}
            </div>

            {execution.reflectionLesson && (
              <div className="p-3 rounded-lg bg-indigo-50/50 dark:bg-indigo-950/20 border border-indigo-200 dark:border-indigo-900/40 text-indigo-950 dark:text-indigo-200">
                <span className="font-semibold block mb-1">Post-Execution Reflection:</span>
                {execution.reflectionLesson}
              </div>
            )}
          </div>
        )}

        {activeTab === 'prompt' && (
          <pre className="p-3 rounded-lg bg-zinc-50 dark:bg-[#1A1F2C] border border-[#E6E6E1] dark:border-[#252B3B] text-zinc-800 dark:text-zinc-200 whitespace-pre-wrap">
            {promptPreview}
          </pre>
        )}

        {activeTab === 'raw' && (
          <pre className="p-3 rounded-lg bg-zinc-50 dark:bg-[#1A1F2C] border border-[#E6E6E1] dark:border-[#252B3B] text-zinc-800 dark:text-zinc-200 whitespace-pre-wrap">
            {JSON.stringify(execution, null, 2)}
          </pre>
        )}
      </div>
    </div>
  )
}
