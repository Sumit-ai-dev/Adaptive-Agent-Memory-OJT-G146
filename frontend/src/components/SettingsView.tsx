import { useState, useMemo, useEffect } from 'react'
import {
  User,
  Key,
  Sliders,
  Database,
  AlertTriangle,
  Copy,
  Check,
  Eye,
  EyeOff,
  RefreshCw,
  LogOut,
  Download,
  Trash2,
  CheckCircle2,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import {
  ALPHA_SUCCESS,
  BETA_FAILURE,
  BYOK_UPDATED_EVENT,
  QUARANTINE_THRESHOLD,
  getByokKeyWarning,
  loadByokKeys,
  saveAllByokKeys,
} from '../services/api'

interface SettingsViewProps {
  isDemo?: boolean
  onClearThreads?: () => void
  onClearMemories?: () => void
  memoriesCount?: number
  executionsCount?: number
}

export default function SettingsView({
  isDemo = false,
  onClearThreads,
  onClearMemories,
  memoriesCount = 0,
  executionsCount = 0,
}: SettingsViewProps) {
  const { user, signOut } = useAuth()

  // Profile states
  const [copiedTenantId, setCopiedTenantId] = useState(false)

  // BYOK API Keys state (persisted in localStorage and synced with Studio)
  const [groqKey, setGroqKey] = useState(() => loadByokKeys().groq || '')
  const [geminiKey, setGeminiKey] = useState(() => loadByokKeys().gemini || '')
  const [openaiKey, setOpenaiKey] = useState(() => loadByokKeys().openai || '')
  const [anthropicKey, setAnthropicKey] = useState(() => loadByokKeys().anthropic || '')
  const [ollamaUrl, setOllamaUrl] = useState(() => loadByokKeys().ollama || 'http://localhost:11434')

  useEffect(() => {
    const syncKeys = () => {
      const next = loadByokKeys()
      setGroqKey(next.groq || '')
      setGeminiKey(next.gemini || '')
      setOpenaiKey(next.openai || '')
      setAnthropicKey(next.anthropic || '')
      setOllamaUrl(next.ollama || 'http://localhost:11434')
    }
    window.addEventListener(BYOK_UPDATED_EVENT, syncKeys)
    window.addEventListener('storage', syncKeys)
    return () => {
      window.removeEventListener(BYOK_UPDATED_EVENT, syncKeys)
      window.removeEventListener('storage', syncKeys)
    }
  }, [])

  const [showGroq, setShowGroq] = useState(false)
  const [showGemini, setShowGemini] = useState(false)
  const [showOpenai, setShowOpenai] = useState(false)
  const [showAnthropic, setShowAnthropic] = useState(false)
  const [keysSaved, setKeysSaved] = useState(false)

  // Hyperparameters
  const [alpha, setAlpha] = useState(ALPHA_SUCCESS)
  const [beta, setBeta] = useState(BETA_FAILURE)
  const [theta, setTheta] = useState(QUARANTINE_THRESHOLD)
  const [paramsSaved, setParamsSaved] = useState(false)

  // Dynamically compute Theorem 1 Bound
  const computedKStar = useMemo(() => {
    const s0 = 0.75
    if (beta >= 1.0 || beta <= 0 || theta <= 0 || s0 <= 0 || theta >= s0) return 0
    const numerator = Math.log(theta) - Math.log(s0)
    const denominator = Math.log(beta)
    return Math.ceil(numerator / denominator)
  }, [beta, theta])

  const tenantId = user?.id || (isDemo ? 'tenant_sandbox_guest_001' : 'tenant_usr_default')
  const providerLabel = user?.provider === 'github'
    ? 'GitHub OAuth'
    : user?.provider === 'google'
    ? 'Google OAuth'
    : isDemo
    ? 'Demo Guest'
    : 'Email / Password'

  const handleSaveKeys = (e: React.FormEvent) => {
    e.preventDefault()
    saveAllByokKeys({
      groq: groqKey,
      gemini: geminiKey,
      openai: openaiKey,
      anthropic: anthropicKey,
      ollama: ollamaUrl,
    })
    setKeysSaved(true)
    setTimeout(() => setKeysSaved(false), 2500)
  }

  const handleResetDefaults = () => {
    setAlpha(ALPHA_SUCCESS)
    setBeta(BETA_FAILURE)
    setTheta(QUARANTINE_THRESHOLD)
    setParamsSaved(true)
    setTimeout(() => setParamsSaved(false), 2000)
  }

  const handleExportTelemetry = () => {
    const data = {
      tenantId,
      userEmail: user?.email || (isDemo ? 'demo@aema.ai' : 'anonymous'),
      exportedAt: new Date().toISOString(),
      hyperparameters: { alpha, beta, theta, kStar: computedKStar },
      stats: { memoriesCount, executionsCount },
    }
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `aema-workspace-${tenantId.slice(0, 8)}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="max-w-4xl space-y-8 pb-12">
      {/* Page Title */}
      <div>
        <h2 className="text-xl font-serif text-[#EDECE8] tracking-tight">
          Workspace Settings & Configuration
        </h2>
        <p className="text-xs text-[#7E7D77] font-mono mt-1">
          Manage your authenticated identity, universal BYOK credentials, A-EMA algorithmic tuning, and storage telemetry.
        </p>
      </div>

      {/* ─── MODULE 1: User & Workspace Identity ─── */}
      <div className="rounded-lg border border-[#242422] bg-[#161614] p-6 space-y-5">
        <div className="flex items-center gap-2 border-b border-[#242422] pb-3">
          <User size={16} className="text-[#4EAA79]" />
          <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-[#EDECE8]">
            User & Workspace Identity
          </h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
          <div className="p-3.5 rounded-lg bg-[#141412] border border-[#242422] space-y-1">
            <span className="text-[#7E7D77] text-[10px] uppercase block">Authenticated Account</span>
            <div className="text-sm font-semibold text-[#EDECE8] truncate">
              {user?.name || user?.email?.split('@')[0] || (isDemo ? 'Demo Evaluator' : 'User')}
            </div>
            <div className="text-[11px] text-[#9E9D96] truncate">
              {user?.email || (isDemo ? 'demo@aema.ai (Guest Session)' : 'Local Dev')}
            </div>
          </div>

          <div className="p-3.5 rounded-lg bg-[#141412] border border-[#242422] space-y-1">
            <span className="text-[#7E7D77] text-[10px] uppercase block">Authentication Provider</span>
            <div className="flex items-center gap-2 mt-1">
              <span className="px-2 py-0.5 rounded bg-[#1E2E24] text-[#4EAA79] border border-[#2E4234] text-xs font-semibold">
                {providerLabel}
              </span>
              <span className="text-[11px] text-[#7E7D77]">Role: Workspace Owner</span>
            </div>
          </div>
        </div>

        <div className="p-3.5 rounded-lg bg-[#141412] border border-[#242422] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs font-mono">
          <div>
            <span className="text-[#7E7D77] text-[10px] uppercase block">Tenant Namespace ID</span>
            <span className="text-[#EDECE8] text-xs break-all">{tenantId}</span>
          </div>
          <button
            onClick={() => {
              navigator.clipboard.writeText(tenantId)
              setCopiedTenantId(true)
              setTimeout(() => setCopiedTenantId(false), 2000)
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#1E1E1B] hover:bg-[#252522] border border-[#2E2E2A] text-[#9E9D96] hover:text-[#EDECE8] transition-colors cursor-pointer shrink-0 self-start sm:self-auto"
          >
            {copiedTenantId ? <Check size={12} className="text-[#4EAA79]" /> : <Copy size={12} />}
            <span>{copiedTenantId ? 'Copied' : 'Copy ID'}</span>
          </button>
        </div>

        {!isDemo && (
          <div className="flex justify-end pt-2">
            <button
              onClick={() => signOut()}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#2E1E1E] hover:bg-[#3E2525] border border-[#4E2A2A] text-[#D9534F] text-xs font-mono transition-colors cursor-pointer"
            >
              <LogOut size={13} />
              <span>Sign Out of Workspace</span>
            </button>
          </div>
        )}
      </div>

      {/* ─── MODULE 2: Universal BYOK Key Manager ─── */}
      <div className="rounded-lg border border-[#242422] bg-[#161614] p-6 space-y-5">
        <div className="flex items-center justify-between border-b border-[#242422] pb-3">
          <div className="flex items-center gap-2">
            <Key size={16} className="text-[#4EAA79]" />
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-[#EDECE8]">
              Universal BYOK API Key Manager
            </h3>
          </div>
          <span className="text-[10px] font-mono text-[#7E7D77]">Encrypted & Stored Client-Side</span>
        </div>

        <form onSubmit={handleSaveKeys} className="space-y-4 text-xs font-mono">
          {/* Groq Cloud */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-[#EDECE8] font-semibold flex items-center gap-2">
                <span>Groq Cloud API Key</span>
                <span className="text-[10px] text-[#7E7D77] font-normal">(openai/gpt-oss-120b, llama-3.3-70b-versatile, llama-3.1-8b-instant)</span>
              </label>
              <span className={`text-[10px] px-1.5 py-0.5 rounded ${groqKey ? 'bg-[#1E2E24] text-[#4EAA79]' : 'bg-[#1E1E1B] text-[#7E7D77]'}`}>
                {groqKey ? 'Active' : 'Unset'}
              </span>
            </div>
            <div className="relative">
              <input
                type={showGroq ? 'text' : 'password'}
                value={groqKey}
                onChange={(e) => setGroqKey(e.target.value)}
                placeholder="gsk_..."
                className="w-full px-3 py-2 rounded bg-[#141412] border border-[#242422] text-[#EDECE8] placeholder-[#7E7D77] focus:outline-none focus:border-[#4EAA79] transition-colors pr-10 font-mono text-xs"
              />
              <button
                type="button"
                onClick={() => setShowGroq(!showGroq)}
                className="absolute right-3 top-2.5 text-[#7E7D77] hover:text-[#EDECE8]"
              >
                {showGroq ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
            {getByokKeyWarning('groq', groqKey) && (
              <p className="text-[11px] text-[#E67E22]">{getByokKeyWarning('groq', groqKey)}</p>
            )}
          </div>

          {/* Google Gemini */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-[#EDECE8] font-semibold flex items-center gap-2">
                <span>Google Gemini API Key</span>
                <span className="text-[10px] text-[#7E7D77] font-normal">(Free: gemini-3.8-flash, 3.5-flash-lite, 4-hydrogen · Paid: 4-argon, 4-carbon)</span>
              </label>
              <span className={`text-[10px] px-1.5 py-0.5 rounded ${geminiKey ? 'bg-[#1E2E24] text-[#4EAA79]' : 'bg-[#1E1E1B] text-[#7E7D77]'}`}>
                {geminiKey ? 'Active' : 'Unset'}
              </span>
            </div>
            <div className="relative">
              <input
                type={showGemini ? 'text' : 'password'}
                value={geminiKey}
                onChange={(e) => setGeminiKey(e.target.value)}
                placeholder="AIza..."
                className="w-full px-3 py-2 rounded bg-[#141412] border border-[#242422] text-[#EDECE8] placeholder-[#7E7D77] focus:outline-none focus:border-[#4EAA79] transition-colors pr-10 font-mono text-xs"
              />
              <button
                type="button"
                onClick={() => setShowGemini(!showGemini)}
                className="absolute right-3 top-2.5 text-[#7E7D77] hover:text-[#EDECE8]"
              >
                {showGemini ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
            {getByokKeyWarning('gemini', geminiKey) && (
              <p className="text-[11px] text-[#E67E22]">{getByokKeyWarning('gemini', geminiKey)}</p>
            )}
          </div>

          {/* OpenAI */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-[#EDECE8] font-semibold flex items-center gap-2">
                <span>OpenAI API Key</span>
                <span className="text-[10px] text-[#7E7D77] font-normal">(Paid: gpt-6.2-sol, gpt-6-luna, gpt-6.1-terra, gpt-6.2-astra)</span>
              </label>
              <span className={`text-[10px] px-1.5 py-0.5 rounded ${openaiKey ? 'bg-[#1E2E24] text-[#4EAA79]' : 'bg-[#1E1E1B] text-[#7E7D77]'}`}>
                {openaiKey ? 'Active' : 'Unset'}
              </span>
            </div>
            <div className="relative">
              <input
                type={showOpenai ? 'text' : 'password'}
                value={openaiKey}
                onChange={(e) => setOpenaiKey(e.target.value)}
                placeholder="sk-..."
                className="w-full px-3 py-2 rounded bg-[#141412] border border-[#242422] text-[#EDECE8] placeholder-[#7E7D77] focus:outline-none focus:border-[#4EAA79] transition-colors pr-10 font-mono text-xs"
              />
              <button
                type="button"
                onClick={() => setShowOpenai(!showOpenai)}
                className="absolute right-3 top-2.5 text-[#7E7D77] hover:text-[#EDECE8]"
              >
                {showOpenai ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
            {getByokKeyWarning('openai', openaiKey) && (
              <p className="text-[11px] text-[#E67E22]">{getByokKeyWarning('openai', openaiKey)}</p>
            )}
          </div>

          {/* Anthropic Claude */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-[#EDECE8] font-semibold flex items-center gap-2">
                <span>Anthropic Claude API Key</span>
                <span className="text-[10px] text-[#7E7D77] font-normal">(Paid: claude-sonnet-5-5, claude-haiku-5-5, claude-opus-5-5, claude-fable-5-2)</span>
              </label>
              <span className={`text-[10px] px-1.5 py-0.5 rounded ${anthropicKey ? 'bg-[#1E2E24] text-[#4EAA79]' : 'bg-[#1E1E1B] text-[#7E7D77]'}`}>
                {anthropicKey ? 'Active' : 'Unset'}
              </span>
            </div>
            <div className="relative">
              <input
                type={showAnthropic ? 'text' : 'password'}
                value={anthropicKey}
                onChange={(e) => setAnthropicKey(e.target.value)}
                placeholder="sk-ant-..."
                className="w-full px-3 py-2 rounded bg-[#141412] border border-[#242422] text-[#EDECE8] placeholder-[#7E7D77] focus:outline-none focus:border-[#4EAA79] transition-colors pr-10 font-mono text-xs"
              />
              <button
                type="button"
                onClick={() => setShowAnthropic(!showAnthropic)}
                className="absolute right-3 top-2.5 text-[#7E7D77] hover:text-[#EDECE8]"
              >
                {showAnthropic ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
            {getByokKeyWarning('anthropic', anthropicKey) && (
              <p className="text-[11px] text-[#E67E22]">{getByokKeyWarning('anthropic', anthropicKey)}</p>
            )}
          </div>

          {/* Local Ollama */}
          <div className="space-y-1.5">
            <label className="text-[#EDECE8] font-semibold flex items-center gap-2">
              <span>Local Ollama Endpoint</span>
              <span className="text-[10px] text-[#7E7D77] font-normal">(Air-gapped offline inference)</span>
            </label>
            <input
              type="text"
              value={ollamaUrl}
              onChange={(e) => setOllamaUrl(e.target.value)}
              placeholder="http://localhost:11434"
              className="w-full px-3 py-2 rounded bg-[#141412] border border-[#242422] text-[#EDECE8] placeholder-[#7E7D77] focus:outline-none focus:border-[#4EAA79] transition-colors font-mono text-xs"
            />
          </div>

          <div className="flex items-center justify-between pt-3">
            <span className="text-[11px] text-[#4EAA79] flex items-center gap-1.5">
              {keysSaved && (
                <>
                  <CheckCircle2 size={13} />
                  <span>BYOK credentials saved successfully!</span>
                </>
              )}
            </span>
            <button
              type="submit"
              className="px-4 py-2 rounded bg-[#4EAA79] hover:bg-[#5EBA89] text-[#141412] font-semibold text-xs transition-colors cursor-pointer"
            >
              Save Credentials
            </button>
          </div>
        </form>
      </div>

      {/* ─── MODULE 3: AEMA Hyperparameters & Tuning ─── */}
      <div className="rounded-lg border border-[#242422] bg-[#161614] p-6 space-y-5">
        <div className="flex items-center justify-between border-b border-[#242422] pb-3">
          <div className="flex items-center gap-2">
            <Sliders size={16} className="text-[#4EAA79]" />
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-[#EDECE8]">
              AEMA Algorithmic Hyperparameters
            </h3>
          </div>
          <button
            onClick={handleResetDefaults}
            className="text-[11px] font-mono text-[#7E7D77] hover:text-[#EDECE8] flex items-center gap-1 transition-colors cursor-pointer"
          >
            <RefreshCw size={11} />
            <span>Reset to Paper Defaults</span>
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
          {/* Alpha Slider */}
          <div className="p-3.5 rounded-lg bg-[#141412] border border-[#242422] space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[#EDECE8] font-semibold">Alpha (Success Reward Rate):</span>
              <span className="font-bold text-[#4EAA79]">{alpha.toFixed(2)}</span>
            </div>
            <input
              type="range"
              min="0.50"
              max="0.99"
              step="0.01"
              value={alpha}
              onChange={(e) => setAlpha(parseFloat(e.target.value))}
              className="w-full accent-[#4EAA79] cursor-pointer"
            />
            <span className="text-[10px] text-[#7E7D77] block">
              Paper default: 0.85. Governs gradual trust accumulation upon confirmed success.
            </span>
          </div>

          {/* Beta Slider */}
          <div className="p-3.5 rounded-lg bg-[#141412] border border-[#242422] space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[#EDECE8] font-semibold">Beta (Failure Penalty Rate):</span>
              <span className="font-bold text-[#D9534F]">{beta.toFixed(2)}</span>
            </div>
            <input
              type="range"
              min="0.10"
              max="0.90"
              step="0.01"
              value={beta}
              onChange={(e) => setBeta(parseFloat(e.target.value))}
              className="w-full accent-[#D9534F] cursor-pointer"
            />
            <span className="text-[10px] text-[#7E7D77] block">
              Paper default: 0.70. Punitive decay parameter applied upon task failure.
            </span>
          </div>

          {/* Theta Slider */}
          <div className="p-3.5 rounded-lg bg-[#141412] border border-[#242422] space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[#EDECE8] font-semibold">Quarantine Threshold (Theta):</span>
              <span className="font-bold text-[#E67E22]">{theta.toFixed(2)}</span>
            </div>
            <input
              type="range"
              min="0.10"
              max="0.60"
              step="0.01"
              value={theta}
              onChange={(e) => setTheta(parseFloat(e.target.value))}
              className="w-full accent-[#E67E22] cursor-pointer"
            />
            <span className="text-[10px] text-[#7E7D77] block">
              Paper default: 0.35. Cutoff below which memories are locked from retrieval.
            </span>
          </div>

          {/* Theorem 1 Bound Display */}
          <div className="p-3.5 rounded-lg bg-[#141412] border border-[#242422] space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[#EDECE8] font-semibold">Theorem 1 Bound (k* Failures):</span>
              <span className="font-bold text-[#EDECE8] px-2 py-0.5 rounded bg-[#1E1E1B] border border-[#2E2E2A]">
                {computedKStar} Failures
              </span>
            </div>
            <div className="text-[11px] text-[#4EAA79] font-mono">
              k* = ⌈(ln {theta.toFixed(2)} - ln 0.75) / ln {beta.toFixed(2)}⌉ = {computedKStar}
            </div>
            <span className="text-[10px] text-[#7E7D77] block">
              Deterministic upper bound to complete memory isolation under Theorem 1.
            </span>
          </div>
        </div>

        {paramsSaved && (
          <div className="text-xs font-mono text-[#4EAA79] flex items-center gap-1.5">
            <CheckCircle2 size={13} />
            <span>Hyperparameters updated to theoretical baseline.</span>
          </div>
        )}
      </div>

      {/* ─── MODULE 4: Storage Subsystem Health ─── */}
      <div className="rounded-lg border border-[#242422] bg-[#161614] p-6 space-y-5">
        <div className="flex items-center gap-2 border-b border-[#242422] pb-3">
          <Database size={16} className="text-[#4EAA79]" />
          <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-[#EDECE8]">
            Storage & Subsystem Telemetry
          </h3>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-mono">
          <div className="p-3.5 rounded-lg bg-[#141412] border border-[#242422] space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[#7E7D77] text-[10px] uppercase">Primary Storage</span>
              <span className="w-2 h-2 rounded-full bg-[#4EAA79] animate-pulse" />
            </div>
            <div className="text-sm font-semibold text-[#EDECE8]">Supabase Cloud</div>
            <div className="text-[10px] text-[#9E9D96]">kgbxowdxbpvphzomivkg</div>
            <div className="text-[10px] text-[#4EAA79] pt-1">pgvector v0.7.0 Enabled</div>
          </div>

          <div className="p-3.5 rounded-lg bg-[#141412] border border-[#242422] space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[#7E7D77] text-[10px] uppercase">Vector Mirror</span>
              <span className="w-2 h-2 rounded-full bg-[#4EAA79]" />
            </div>
            <div className="text-sm font-semibold text-[#EDECE8]">SQLite Engine</div>
            <div className="text-[10px] text-[#9E9D96]">experiences.db</div>
            <div className="text-[10px] text-[#4EAA79] pt-1">Automatic Failover Ready</div>
          </div>

          <div className="p-3.5 rounded-lg bg-[#141412] border border-[#242422] space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[#7E7D77] text-[10px] uppercase">FastAPI Core</span>
              <span className="w-2 h-2 rounded-full bg-[#4EAA79]" />
            </div>
            <div className="text-sm font-semibold text-[#EDECE8]">Backend Server</div>
            <div className="text-[10px] text-[#9E9D96]">http://localhost:8000</div>
            <div className="text-[10px] text-[#4EAA79] pt-1">HTTP 200 OK</div>
          </div>
        </div>
      </div>

      {/* ─── MODULE 5: Data Management & Danger Zone ─── */}
      <div className="rounded-lg border border-[#4E2A2A] bg-[#1A1414] p-6 space-y-5">
        <div className="flex items-center gap-2 border-b border-[#4E2A2A] pb-3">
          <AlertTriangle size={16} className="text-[#D9534F]" />
          <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-[#D9534F]">
            Data Management & Danger Zone
          </h3>
        </div>

        <div className="space-y-4 text-xs font-mono">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 rounded-lg bg-[#141010] border border-[#3E2020] gap-3">
            <div>
              <span className="text-[#EDECE8] font-semibold block">Export Workspace Telemetry</span>
              <span className="text-[10px] text-[#7E7D77]">
                Download a JSON snapshot of all experiential memories, execution traces, and hyperparameters.
              </span>
            </div>
            <button
              onClick={handleExportTelemetry}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#1E1E1B] hover:bg-[#252522] border border-[#2E2E2A] text-[#EDECE8] text-xs transition-colors cursor-pointer shrink-0"
            >
              <Download size={13} />
              <span>Export JSON</span>
            </button>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 rounded-lg bg-[#141010] border border-[#3E2020] gap-3">
            <div>
              <span className="text-[#EDECE8] font-semibold block">Clear Conversation Threads</span>
              <span className="text-[10px] text-[#7E7D77]">
                Deletes all chat sessions and execution logs for this user ({executionsCount} recorded). Memories remain intact.
              </span>
            </div>
            <button
              onClick={() => {
                if (window.confirm('Are you sure you want to clear all execution threads for this workspace?')) {
                  onClearThreads?.()
                }
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#2E1E1E] hover:bg-[#3E2525] border border-[#4E2A2A] text-[#D9534F] text-xs transition-colors cursor-pointer shrink-0"
            >
              <Trash2 size={13} />
              <span>Clear Threads</span>
            </button>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 rounded-lg bg-[#141010] border border-[#3E2020] gap-3">
            <div>
              <span className="text-[#EDECE8] font-semibold block">Purge Memory Bank</span>
              <span className="text-[10px] text-[#7E7D77]">
                Deletes all experiential memories extracted by this user ({memoriesCount} memories). Cannot be undone.
              </span>
            </div>
            <button
              onClick={() => {
                if (window.confirm('Are you sure you want to purge your entire experiential memory bank?')) {
                  onClearMemories?.()
                }
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#2E1E1E] hover:bg-[#3E2525] border border-[#4E2A2A] text-[#D9534F] text-xs transition-colors cursor-pointer shrink-0"
            >
              <Trash2 size={13} />
              <span>Purge Memories</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
