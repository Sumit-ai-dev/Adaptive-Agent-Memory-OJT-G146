import { useState, useEffect } from 'react'
import { Play, Sparkles, Terminal, KeyRound } from 'lucide-react'
import type { TaskDomain } from '../types'
import {
  BYOK_UPDATED_EVENT,
  MODEL_PREFS_UPDATED_EVENT,
  PROVIDER_DEFAULT_MODELS,
  SupportedProvider,
  getByokKeyPlaceholder,
  getByokKeyWarning,
  getProviderApiKey,
  loadByokKeys,
  loadProviderPreference,
  loadSelectedModels,
  saveByokKey,
  saveProviderPreference,
  saveSelectedModel,
} from '../services/api'
import ProviderSelect from './ProviderSelect'
import ProviderModelSelect from './ProviderModelSelect'

type ProviderType = SupportedProvider

interface PromptConsoleProps {
  onRunTask: (params: {
    prompt: string
    domain: TaskDomain
    memoryEnabled: boolean
    provider?: string
    model?: string
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
  const [provider, setProvider] = useState<ProviderType>(() => loadProviderPreference())
  const [selectedModels, setSelectedModels] = useState<Record<string, string>>(() => loadSelectedModels())
  const activeModel = selectedModels[provider] || PROVIDER_DEFAULT_MODELS[provider]

  useEffect(() => {
    function handleByokSync() {
      setApiKeys(loadByokKeys())
    }
    function handleModelPrefsSync() {
      setProvider(loadProviderPreference())
      setSelectedModels(loadSelectedModels())
    }
    window.addEventListener(BYOK_UPDATED_EVENT, handleByokSync)
    window.addEventListener(MODEL_PREFS_UPDATED_EVENT, handleModelPrefsSync)
    window.addEventListener('storage', handleByokSync)
    window.addEventListener('storage', handleModelPrefsSync)
    return () => {
      window.removeEventListener(BYOK_UPDATED_EVENT, handleByokSync)
      window.removeEventListener(MODEL_PREFS_UPDATED_EVENT, handleModelPrefsSync)
      window.removeEventListener('storage', handleByokSync)
      window.removeEventListener('storage', handleModelPrefsSync)
    }
  }, [])

  const [apiKeys, setApiKeys] = useState<Record<string, string>>(() => loadByokKeys())
  const [showKeyInput, setShowKeyInput] = useState(false)

  const apiKey = getProviderApiKey(apiKeys, provider) || ''
  const setApiKey = (val: string) => {
    setApiKeys(saveByokKey(provider, val))
  }

  // Detect mismatched API key types to prevent confusing provider errors
  const keyWarning = getByokKeyWarning(provider, apiKey)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!prompt.trim() || isRunning) return

    onRunTask({
      prompt: prompt.trim(),
      domain,
      memoryEnabled,
      provider,
      model: activeModel,
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
                placeholder={getByokKeyPlaceholder(provider)}
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
            <div className="flex items-center gap-2">
              <span className="font-mono text-[#7E7D77] text-[11px]">MODEL:</span>
              <ProviderSelect
                value={provider}
                onChange={(nextProv) => {
                  setProvider(nextProv)
                  saveProviderPreference(nextProv)
                }}
                align="left"
              />
            </div>

            {/* Provider Model Variant Selector */}
            <ProviderModelSelect
              provider={provider}
              value={activeModel}
              onChange={(modelId) => setSelectedModels(saveSelectedModel(provider, modelId))}
              align="left"
            />

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
