import { useState } from 'react'
import {
  Sliders,
  Key,
  Database,
  CheckCircle2,
  Lock,
  Eye,
  EyeOff,
  Sparkles,
} from 'lucide-react'
import { AgentConfig, TaskDomain, ModelProvider } from '../../types'
import { SUPPORTED_PROVIDERS } from '../../services/api'

interface AgentConfigDrawerProps {
  config: AgentConfig
  onChange: (newConfig: AgentConfig) => void
  disabled?: boolean
}

const DOMAIN_OPTIONS: { id: TaskDomain; label: string; desc: string }[] = [
  { id: 'research', label: 'Research', desc: 'Fact synthesis & citation verification' },
  { id: 'coding', label: 'Coding', desc: 'Resilient algorithms & refactoring' },
  { id: 'analysis', label: 'Analysis', desc: 'Statistical outlier mitigation' },
  { id: 'planning', label: 'Planning', desc: 'DAG task scheduling & rate limits' },
  { id: 'general', label: 'General', desc: 'Cross-domain reasoning' },
]

export default function AgentConfigDrawer({
  config,
  onChange,
  disabled = false,
}: AgentConfigDrawerProps) {
  const [showApiKey, setShowApiKey] = useState(false)
  const [keySavedIndicator, setKeySavedIndicator] = useState(false)

  const currentProvider =
    SUPPORTED_PROVIDERS.find((p) => p.id === config.provider) ||
    SUPPORTED_PROVIDERS[0]

  const handleProviderChange = (providerId: ModelProvider) => {
    const prov =
      SUPPORTED_PROVIDERS.find((p) => p.id === providerId) ||
      SUPPORTED_PROVIDERS[0]
    onChange({
      ...config,
      provider: providerId,
      model: prov.defaultModel,
      // reset key when switching providers
      apiKey: config.provider === providerId ? config.apiKey : '',
    })
  }

  const handleApiKeyChange = (key: string) => {
    onChange({
      ...config,
      apiKey: key,
    })
    setKeySavedIndicator(true)
    setTimeout(() => setKeySavedIndicator(false), 2000)
  }

  return (
    <div className="h-full flex flex-col bg-[#0b0014]/80 backdrop-blur-xl border-r border-white/10 p-4 overflow-y-auto space-y-5 text-xs">
      {/* Header */}
      <div className="pb-3 border-b border-white/10">
        <div className="flex items-center gap-2 mb-1">
          <div className="w-6 h-6 rounded-lg bg-purple-500/15 border border-purple-500/30 flex items-center justify-center text-purple-400">
            <Sliders size={13} />
          </div>
          <h3 className="font-display font-bold text-white text-xs tracking-tight">
            Agent Configuration
          </h3>
        </div>
        <p className="text-[10px] text-white/40 font-mono">
          Dynamic runtime parameters & BYOK
        </p>
      </div>

      {/* Task Domain */}
      <div className="space-y-1.5">
        <label className="text-white/60 font-mono text-[11px] uppercase tracking-wider block">
          Task Domain
        </label>
        <div className="grid grid-cols-1 gap-1.5">
          {DOMAIN_OPTIONS.map((d) => (
            <button
              key={d.id}
              type="button"
              disabled={disabled}
              onClick={() => onChange({ ...config, domain: d.id })}
              className={`p-2 rounded-xl text-left border transition-all cursor-pointer ${
                config.domain === d.id
                  ? 'bg-purple-500/20 border-purple-500/40 text-white'
                  : 'bg-white/[0.02] hover:bg-white/[0.05] border-white/5 text-white/60'
              }`}
            >
              <div className="font-semibold text-xs text-white">{d.label}</div>
              <div className="text-[10px] text-white/40 font-sans">{d.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Model Provider */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <label className="text-white/60 font-mono text-[11px] uppercase tracking-wider">
            Provider (Gateway)
          </label>
          <span className="text-[10px] font-mono text-emerald-400 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Verified
          </span>
        </div>
        <select
          value={config.provider}
          disabled={disabled}
          onChange={(e) => handleProviderChange(e.target.value as ModelProvider)}
          className="w-full bg-[#140026] text-white border border-white/10 rounded-xl px-3 py-2 text-xs font-mono focus:outline-none focus:border-purple-400 transition-colors"
        >
          {SUPPORTED_PROVIDERS.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
        <p className="text-[10px] text-white/40 font-sans leading-tight">
          {currentProvider.description}
        </p>
      </div>

      {/* Model Selection */}
      <div className="space-y-1.5">
        <label className="text-white/60 font-mono text-[11px] uppercase tracking-wider block">
          Model Identifier
        </label>
        <select
          value={config.model}
          disabled={disabled}
          onChange={(e) => onChange({ ...config, model: e.target.value })}
          className="w-full bg-[#140026] text-white border border-white/10 rounded-xl px-3 py-2 text-xs font-mono focus:outline-none focus:border-purple-400 transition-colors"
        >
          {currentProvider.models.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </div>

      {/* BYOK API Key Input (if provider requires key or user wants custom key) */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <label className="text-white/60 font-mono text-[11px] uppercase tracking-wider flex items-center gap-1">
            <Key size={11} />
            <span>BYOK API Key</span>
          </label>
          {keySavedIndicator && (
            <span className="text-emerald-400 text-[10px] font-mono flex items-center gap-0.5">
              <CheckCircle2 size={10} />
              Set
            </span>
          )}
        </div>

        <div className="relative">
          <input
            type={showApiKey ? 'text' : 'password'}
            placeholder={
              currentProvider.requiresKey
                ? 'Enter API key for session'
                : 'Optional custom API key'
            }
            value={config.apiKey || ''}
            disabled={disabled}
            onChange={(e) => handleApiKeyChange(e.target.value)}
            className="w-full bg-[#140026] text-white border border-white/10 rounded-xl pl-3 pr-8 py-2 text-xs font-mono focus:outline-none focus:border-purple-400 transition-colors placeholder:text-white/20"
          />
          <button
            type="button"
            onClick={() => setShowApiKey(!showApiKey)}
            className="absolute right-2.5 top-2.5 text-white/40 hover:text-white transition-colors cursor-pointer"
          >
            {showApiKey ? <EyeOff size={13} /> : <Eye size={13} />}
          </button>
        </div>

        <div className="flex items-center gap-1 text-[10px] text-white/30 font-mono">
          <Lock size={10} />
          <span>In-memory only. Never persisted or logged.</span>
        </div>
      </div>

      {/* Memory Control */}
      <div className="space-y-2 pt-2 border-t border-white/10">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-white font-semibold">
            <Database size={13} className="text-emerald-400" />
            <span>Persistent Memory</span>
          </div>
          <button
            type="button"
            disabled={disabled}
            onClick={() =>
              onChange({
                ...config,
                memoryEnabled: !config.memoryEnabled,
                memoryMode: !config.memoryEnabled ? 'adaptive' : 'off',
              })
            }
            className={`w-9 h-5 rounded-full transition-colors relative cursor-pointer ${
              config.memoryEnabled ? 'bg-emerald-500' : 'bg-white/20'
            }`}
          >
            <div
              className={`w-4 h-4 rounded-full bg-white transition-transform absolute top-0.5 ${
                config.memoryEnabled ? 'right-0.5' : 'left-0.5'
              }`}
            />
          </button>
        </div>

        {config.memoryEnabled && (
          <div className="space-y-1.5">
            <label className="text-white/40 font-mono text-[10px] uppercase tracking-wider block">
              Ablation Calibration Mode
            </label>
            <div className="grid grid-cols-2 gap-1.5">
              <button
                type="button"
                disabled={disabled}
                onClick={() => onChange({ ...config, memoryMode: 'adaptive' })}
                className={`py-1.5 px-2 rounded-lg border text-center font-mono text-[10px] transition-all cursor-pointer ${
                  config.memoryMode === 'adaptive'
                    ? 'bg-purple-500/20 border-purple-500/40 text-purple-300 font-bold'
                    : 'bg-white/[0.02] border-white/5 text-white/50'
                }`}
              >
                Adaptive (A-EMA)
              </button>
              <button
                type="button"
                disabled={disabled}
                onClick={() => onChange({ ...config, memoryMode: 'naive' })}
                className={`py-1.5 px-2 rounded-lg border text-center font-mono text-[10px] transition-all cursor-pointer ${
                  config.memoryMode === 'naive'
                    ? 'bg-purple-500/20 border-purple-500/40 text-purple-300 font-bold'
                    : 'bg-white/[0.02] border-white/5 text-white/50'
                }`}
              >
                Naive (Vector RAG)
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Information Box */}
      <div className="mt-auto p-3 rounded-xl bg-white/[0.02] border border-white/5 text-[10px] text-white/40 font-sans space-y-1">
        <div className="flex items-center gap-1 text-white/60 font-semibold font-mono">
          <Sparkles size={11} className="text-purple-400" />
          <span>Experience Reliability</span>
        </div>
        <p>
          Every task response is evaluated. Positive outcomes strengthen confidence; failures quarantine harmful advice.
        </p>
      </div>
    </div>
  )
}
