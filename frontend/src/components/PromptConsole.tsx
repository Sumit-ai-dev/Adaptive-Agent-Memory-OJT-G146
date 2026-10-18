import { useState, useRef, useEffect } from 'react'
import { Play, Sparkles, AlertOctagon, Terminal, KeyRound, ChevronDown, Check, Cpu } from 'lucide-react'
import type { TaskDomain } from '../types'

type ProviderType = 'gemini' | 'groq' | 'ollama' | 'openai' | 'mock'

interface ModelOption {
  id: ProviderType
  name: string
  subname: string
  logo?: string
  isIcon?: boolean
}

const MODEL_OPTIONS: ModelOption[] = [
  {
    id: 'groq',
    name: 'Groq Cloud',
    subname: 'Fast - Default',
    logo: '/images/models/groq.webp',
  },
  {
    id: 'gemini',
    name: 'Google Gemini Flash',
    subname: 'Hosted',
    logo: '/images/models/gemini.webp',
  },
  {
    id: 'openai',
    name: 'GPT-4o Mini',
    subname: 'OpenAI',
    logo: '/images/models/openai.webp',
  },
  {
    id: 'ollama',
    name: 'Ollama Local',
    subname: 'llama3.2',
    logo: '/images/models/ollama.webp',
  },
  {
    id: 'mock',
    name: 'Deterministic Mock',
    subname: 'Offline',
    isIcon: true,
  },
]

interface PromptConsoleProps {
  onRunTask: (params: {
    prompt: string
    domain: TaskDomain
    memoryEnabled: boolean
    provider?: string
    apiKey?: string
    simulateFailure?: boolean
  }) => void
  isRunning: boolean
}

export default function PromptConsole({ onRunTask, isRunning }: PromptConsoleProps) {
  const [prompt, setPrompt] = useState('')
  const [domain, setDomain] = useState<TaskDomain>('coding')
  const [memoryEnabled, setMemoryEnabled] = useState(true)
  const [simulateFailure, setSimulateFailure] = useState(false)
  const [provider, setProvider] = useState<ProviderType>('groq')
  const [isModelOpen, setIsModelOpen] = useState(false)
  const modelDropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (modelDropdownRef.current && !modelDropdownRef.current.contains(event.target as Node)) {
        setIsModelOpen(false)
      }
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setIsModelOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [])

  const currentModel = MODEL_OPTIONS.find((m) => m.id === provider) || MODEL_OPTIONS[0]
  const [apiKeys, setApiKeys] = useState<Record<string, string>>(() => {
    try {
      const saved = localStorage.getItem('aema_byok_keys')
      return saved ? JSON.parse(saved) : {}
    } catch {
      return {}
    }
  })
  const [showKeyInput, setShowKeyInput] = useState(false)

  const apiKey = apiKeys[provider] || ''
  const setApiKey = (val: string) => {
    setApiKeys((prev) => {
      const next = { ...prev, [provider]: val }
      try {
        localStorage.setItem('aema_byok_keys', JSON.stringify(next))
      } catch {}
      return next
    })
  }

  // Detect mismatched API key types to prevent confusing provider errors
  const keyWarning = (() => {
    if (!apiKey) return null
    if (provider === 'groq' && apiKey.startsWith('AIza')) {
      return 'Warning: This looks like a Google Gemini key (AIza...). Groq keys start with "gsk_". Get a free key at console.groq.com.'
    }
    if (provider === 'gemini' && apiKey.startsWith('gsk_')) {
      return 'Warning: This looks like a Groq key (gsk_...). Gemini keys start with "AIza...". Get a key at aistudio.google.com.'
    }
    if (provider === 'openai' && !apiKey.startsWith('sk-')) {
      return 'Note: OpenAI API keys typically start with "sk-".'
    }
    return null
  })()

  const getKeyPlaceholder = () => {
    switch (provider) {
      case 'gemini':
        return 'Enter Gemini API key (starts with AIzaSy...)'
      case 'groq':
        return 'Enter Groq API key (starts with gsk_... from console.groq.com)'
      case 'openai':
        return 'Enter OpenAI API key (starts with sk-...)'
      default:
        return `Enter ${provider.toUpperCase()}_API_KEY...`
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!prompt.trim() || isRunning) return

    onRunTask({
      prompt: prompt.trim(),
      domain,
      memoryEnabled,
      provider,
      apiKey: apiKey.trim() || undefined,
      simulateFailure,
    })
  }

  return (
    <div className="rounded-2xl border p-5 bg-white border-[#E6E6E1] dark:bg-[#131722] dark:border-[#252B3B] space-y-4">
      {/* Console Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Terminal size={16} className="text-indigo-600 dark:text-indigo-400" />
          <h3 className="text-sm font-semibold text-[#18181B] dark:text-[#F4F4F6]">
            Execution Console
          </h3>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Task Input Area */}
        <div>
          <textarea
            required
            rows={3}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe an agent task to execute..."
            className="w-full p-3 text-xs font-mono rounded-xl border outline-none transition-colors
              bg-zinc-50 border-[#E6E6E1] text-[#18181B] focus:border-indigo-600 focus:bg-white
              dark:bg-[#1A1F2C] dark:border-[#252B3B] dark:text-[#F4F4F6] dark:focus:border-indigo-400 dark:focus:bg-[#131722]"
          />
        </div>

        {/* Optional BYOK API Key Input */}
        {showKeyInput && provider !== 'mock' && provider !== 'ollama' && (
          <div className="space-y-1.5">
            <div className="flex items-center gap-2 p-2.5 rounded-xl border bg-zinc-50 dark:bg-[#1A1F2C] border-[#E6E6E1] dark:border-[#252B3B]">
              <KeyRound size={14} className="text-zinc-400 shrink-0" />
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={getKeyPlaceholder()}
                className="w-full text-xs font-mono bg-transparent outline-none text-[#18181B] dark:text-[#F4F4F6] placeholder-zinc-400"
              />
              {apiKey && (
                <button
                  type="button"
                  onClick={() => setApiKey('')}
                  className="text-[10px] font-mono text-zinc-400 hover:text-zinc-600 px-1 cursor-pointer"
                >
                  Clear
                </button>
              )}
            </div>
            {keyWarning && (
              <p className="text-[11px] font-mono text-amber-600 dark:text-amber-400 px-1">
                {keyWarning}
              </p>
            )}
          </div>
        )}

        {/* Controls Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex flex-wrap items-center gap-3">
            {/* Domain Picker */}
            <div className="flex items-center gap-2">
              <span className="font-mono text-zinc-400 text-[11px]">DOMAIN:</span>
              <select
                value={domain}
                onChange={(e) => setDomain(e.target.value as TaskDomain)}
                className="px-2.5 py-1.5 rounded-lg border font-mono outline-none
                  bg-white border-[#E6E6E1] text-[#18181B]
                  dark:bg-[#1A1F2C] dark:border-[#252B3B] dark:text-[#F4F4F6]"
              >
                <option value="coding">Coding</option>
                <option value="research">Research</option>
                <option value="analysis">Analysis</option>
                <option value="planning">Planning</option>
                <option value="general">General</option>
              </select>
            </div>

            {/* Model Provider Picker with Logos */}
            <div className="relative" ref={modelDropdownRef}>
              <div className="flex items-center gap-2">
                <span className="font-mono text-zinc-400 text-[11px]">MODEL:</span>
                <button
                  type="button"
                  onClick={() => setIsModelOpen(!isModelOpen)}
                  className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg border font-mono text-xs outline-none transition-colors cursor-pointer
                    bg-white border-[#E6E6E1] text-[#18181B] hover:border-indigo-400
                    dark:bg-[#1A1F2C] dark:border-[#252B3B] dark:text-[#F4F4F6] dark:hover:border-indigo-500"
                >
                  <div className="w-4 h-4 rounded-sm flex items-center justify-center shrink-0 overflow-hidden">
                    {currentModel.logo ? (
                      <img
                        src={currentModel.logo}
                        alt={currentModel.name}
                        className="w-full h-full object-contain"
                      />
                    ) : (
                      <Cpu size={14} className="text-zinc-400" />
                    )}
                  </div>
                  <span className="truncate max-w-[170px] text-[11px] font-medium">
                    {currentModel.name}
                    <span className="text-zinc-400 ml-1 font-normal font-mono text-[10px]">
                      ({currentModel.subname})
                    </span>
                  </span>
                  <ChevronDown
                    size={12}
                    className={`text-zinc-400 transition-transform duration-200 shrink-0 ${
                      isModelOpen ? 'rotate-180' : ''
                    }`}
                  />
                </button>
              </div>

              {/* Dropdown Menu */}
              {isModelOpen && (
                <div
                  className="absolute left-0 mt-1.5 w-64 rounded-xl border py-1.5 z-50 shadow-xl backdrop-blur-md
                    bg-white/95 border-[#E6E6E1] text-[#18181B]
                    dark:bg-[#141926]/95 dark:border-[#252B3B] dark:text-[#F4F4F6]"
                >
                  {MODEL_OPTIONS.map((opt) => {
                    const isSelected = opt.id === provider
                    return (
                      <button
                        key={opt.id}
                        type="button"
                        onClick={() => {
                          setProvider(opt.id)
                          setIsModelOpen(false)
                        }}
                        className={`w-full flex items-center justify-between px-3 py-2 text-left text-xs transition-colors cursor-pointer ${
                          isSelected
                            ? 'bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 font-medium'
                            : 'hover:bg-zinc-100 dark:hover:bg-[#1E2536] text-[#18181B] dark:text-[#F4F4F6]'
                        }`}
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          <div className="w-5 h-5 rounded-md flex items-center justify-center shrink-0 bg-zinc-100 dark:bg-zinc-800/80 p-0.5 border border-zinc-200/60 dark:border-zinc-700/60 overflow-hidden">
                            {opt.logo ? (
                              <img
                                src={opt.logo}
                                alt={opt.name}
                                className="w-full h-full object-contain"
                              />
                            ) : (
                              <Cpu size={13} className="text-zinc-400" />
                            )}
                          </div>
                          <div className="truncate">
                            <span className="font-medium">{opt.name}</span>
                            <span className="text-[10px] text-zinc-400 ml-1.5 font-mono">
                              ({opt.subname})
                            </span>
                          </div>
                        </div>
                        {isSelected && (
                          <Check size={14} className="text-indigo-600 dark:text-indigo-400 shrink-0 ml-2" />
                        )}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>

            {/* BYOK Key Toggle */}
            {provider !== 'mock' && provider !== 'ollama' && (
              <button
                type="button"
                onClick={() => setShowKeyInput(!showKeyInput)}
                className={`flex items-center gap-1.5 px-2 py-1.5 rounded-lg border font-mono text-[11px] transition-colors ${
                  apiKey
                    ? 'border-emerald-300 text-emerald-700 bg-emerald-50 dark:border-emerald-800 dark:text-emerald-400 dark:bg-emerald-950/40'
                    : 'border-zinc-200 dark:border-zinc-800 text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200'
                }`}
                title="Enter custom API key for this provider (optional if configured in backend environment)"
              >
                <KeyRound size={12} />
                <span>{apiKey ? 'API Key Set' : 'BYOK Key'}</span>
              </button>
            )}
          </div>

          {/* Memory Mode Toggle */}
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={memoryEnabled}
                onChange={(e) => setMemoryEnabled(e.target.checked)}
                className="rounded accent-indigo-600"
              />
              <span className="font-medium text-zinc-700 dark:text-zinc-300">
                AEMA Memory (Adaptive)
              </span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer" title="Simulate negative transfer trap to observe Theorem 1 quarantine">
              <input
                type="checkbox"
                checked={simulateFailure}
                onChange={(e) => setSimulateFailure(e.target.checked)}
                className="rounded accent-rose-600"
              />
              <span className="font-medium text-rose-600 dark:text-rose-400 flex items-center gap-1">
                <AlertOctagon size={13} />
                <span>Simulate Failure Trap</span>
              </span>
            </label>
          </div>

          {/* Run Button */}
          <button
            type="submit"
            disabled={isRunning}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold text-white transition-all
              bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 dark:bg-indigo-600 dark:hover:bg-indigo-500 shadow-sm cursor-pointer"
          >
            {isRunning ? (
              <>
                <Sparkles size={14} className="animate-spin" />
                <span>Executing Cycle...</span>
              </>
            ) : (
              <>
                <Play size={14} />
                <span>Execute Cycle</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  )
}
