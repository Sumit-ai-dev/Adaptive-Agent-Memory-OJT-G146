import { useState, useRef, useEffect } from 'react'
import { Play, Sparkles, Terminal, KeyRound, ChevronDown, Check, Cpu } from 'lucide-react'
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
    <div className="rounded-lg border border-[#242422] p-5 bg-[#161614] text-[#EDECE8] space-y-4">
      {/* Console Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Terminal size={15} className="text-[#4EAA79]" />
          <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-[#EDECE8]">
            Quick Task Launcher
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
            className="w-full p-3 text-xs font-mono rounded-lg border outline-none transition-colors
              bg-[#141412] border-[#2E2E2A] text-[#EDECE8] placeholder-[#5A5955] focus:border-[#4EAA79]"
          />
        </div>

        {/* Optional BYOK API Key Input */}
        {showKeyInput && provider !== 'mock' && provider !== 'ollama' && (
          <div className="space-y-1.5">
            <div className="flex items-center gap-2 p-2 rounded-lg border bg-[#141412] border-[#2E2E2A]">
              <KeyRound size={13} className="text-[#7E7D77] shrink-0" />
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={getKeyPlaceholder()}
                className="w-full text-xs font-mono bg-transparent outline-none text-[#EDECE8] placeholder-[#5A5955]"
              />
              {apiKey && (
                <button
                  type="button"
                  onClick={() => setApiKey('')}
                  className="text-[10px] font-mono text-[#7E7D77] hover:text-[#EDECE8] px-1 cursor-pointer"
                >
                  Clear
                </button>
              )}
            </div>
            {keyWarning && (
              <p className="text-[11px] font-mono text-[#E67E22] px-1">
                {keyWarning}
              </p>
            )}
          </div>
        )}

        {/* Controls Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex flex-wrap items-center gap-2.5">
            {/* Domain Picker */}
            <div className="flex items-center gap-2">
              <span className="font-mono text-[#7E7D77] text-[11px]">DOMAIN:</span>
              <select
                value={domain}
                onChange={(e) => setDomain(e.target.value as TaskDomain)}
                className="px-2.5 py-1.5 rounded-lg border font-mono outline-none text-xs cursor-pointer
                  bg-[#141412] border-[#2E2E2A] text-[#EDECE8]"
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
                <span className="font-mono text-[#7E7D77] text-[11px]">MODEL:</span>
                <button
                  type="button"
                  onClick={() => setIsModelOpen(!isModelOpen)}
                  className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg border font-mono text-xs outline-none transition-colors cursor-pointer
                    bg-[#141412] border-[#2E2E2A] text-[#EDECE8] hover:bg-[#1E1E1B]"
                >
                  <div className="w-3.5 h-3.5 rounded-sm flex items-center justify-center shrink-0 overflow-hidden">
                    {currentModel.logo ? (
                      <img
                        src={currentModel.logo}
                        alt={currentModel.name}
                        className="w-full h-full object-contain"
                      />
                    ) : (
                      <Cpu size={13} className="text-[#7E7D77]" />
                    )}
                  </div>
                  <span className="truncate max-w-[170px] text-[11px] font-medium">
                    {currentModel.name}
                  </span>
                  <ChevronDown
                    size={11}
                    className={`text-[#7E7D77] transition-transform duration-200 shrink-0 ${
                      isModelOpen ? 'rotate-180' : ''
                    }`}
                  />
                </button>
              </div>

              {/* Dropdown Menu */}
              {isModelOpen && (
                <div
                  className="absolute left-0 mt-1.5 w-60 rounded-lg border py-1.5 z-50 shadow-xl
                    bg-[#1A1A17] border-[#2E2E2A] text-[#EDECE8]"
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
                        className={`w-full flex items-center justify-between px-3 py-2 text-left text-xs font-mono transition-colors cursor-pointer ${
                          isSelected
                            ? 'bg-[#22221E] text-white font-medium border-l-2 border-[#4EAA79]'
                            : 'hover:bg-[#20201D] text-[#9E9D96]'
                        }`}
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <div className="w-4 h-4 rounded flex items-center justify-center shrink-0 bg-[#242422] p-0.5 overflow-hidden">
                            {opt.logo ? (
                              <img
                                src={opt.logo}
                                alt={opt.name}
                                className="w-full h-full object-contain"
                              />
                            ) : (
                              <Cpu size={12} className="text-[#7E7D77]" />
                            )}
                          </div>
                          <div className="truncate">
                            <span className="font-medium">{opt.name}</span>
                            <span className="text-[10px] text-[#7E7D77] ml-1.5">
                              ({opt.subname})
                            </span>
                          </div>
                        </div>
                        {isSelected && (
                          <Check size={13} className="text-[#4EAA79] shrink-0 ml-2" />
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
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border font-mono text-[11px] transition-colors cursor-pointer ${
                  apiKey
                    ? 'border-[#3E4E42] text-[#4EAA79] bg-[#1E2E24]'
                    : 'border-[#2E2E2A] bg-[#141412] text-[#7E7D77] hover:text-[#EDECE8] hover:bg-[#1E1E1B]'
                }`}
                title="Enter custom API key for this provider"
              >
                <KeyRound size={12} />
                <span>{apiKey ? 'Key Set' : 'BYOK'}</span>
              </button>
            )}
          </div>

          {/* Memory Mode Toggle */}
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-1.5 px-2.5 py-1 rounded border border-[#2E2E2A] bg-[#141412] text-[11px] font-mono text-[#EDECE8] cursor-pointer hover:bg-[#1E1E1B] transition-colors select-none">
              <input
                type="checkbox"
                checked={memoryEnabled}
                onChange={(e) => setMemoryEnabled(e.target.checked)}
                className="w-3.5 h-3.5 rounded border-[#2E2E2A] bg-[#141412] text-[#4EAA79] accent-[#4EAA79]"
              />
              <span className={memoryEnabled ? 'text-[#4EAA79] font-medium' : 'text-[#7E7D77]'}>
                AEMA
              </span>
            </label>

            <label className="flex items-center gap-1.5 px-2.5 py-1 rounded border border-[#2E2E2A] bg-[#141412] text-[11px] font-mono text-[#EDECE8] cursor-pointer hover:bg-[#1E1E1B] transition-colors select-none" title="Simulate negative transfer trap to observe Theorem 1 quarantine">
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

            {/* Run Button */}
            <button
              type="submit"
              disabled={isRunning}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold text-[#141412] bg-[#EDECE8] hover:bg-white disabled:opacity-50 transition-colors shadow-sm cursor-pointer"
            >
              {isRunning ? (
                <>
                  <Sparkles size={13} className="animate-spin" />
                  <span>Running...</span>
                </>
              ) : (
                <>
                  <Play size={13} />
                  <span>Execute</span>
                </>
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}
