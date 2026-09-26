
interface LogoProps {
  className?: string
  size?: number
  color?: string
}

// ─── 1. Claude (Anthropic) ──────────────────────────────────────────────────
export function ClaudeLogo({ className = '', size = 20, color = '#D97706' }: LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="Anthropic Claude"
    >
      <path
        d="M13.8 2.2L12 6.8 10.2 2.2C9.9 1.4 8.9 1.1 8.2 1.5c-.7.4-1 1.4-.6 2.1l2.4 5.3H5.3c-.8 0-1.5.6-1.6 1.4-.1.8.4 1.6 1.2 1.8l5.4 1.2-4.1 3.7c-.6.6-.7 1.5-.2 2.2.5.7 1.4.8 2.1.3l4.5-3.3v5.6c0 .8.6 1.5 1.5 1.5.8 0 1.5-.7 1.5-1.5v-5.6l4.5 3.3c.7.5 1.6.4 2.1-.3.5-.7.4-1.6-.2-2.2l-4.1-3.7 5.4-1.2c.8-.2 1.3-1 1.2-1.8-.1-.8-.8-1.4-1.6-1.4h-4.7l2.4-5.3c.4-.7.1-1.7-.6-2.1-.7-.4-1.7-.1-2 .7z"
        fill={color}
      />
    </svg>
  )
}

// ─── 2. OpenAI ───────────────────────────────────────────────────────────────
export function OpenAILogo({ className = '', size = 20, color = 'currentColor' }: LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="OpenAI"
    >
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M20.5 9.77a5.55 5.55 0 0 0-.46-4.43 5.6 5.6 0 0 0-5.83-2.65A5.6 5.6 0 0 0 9.77 1.5a5.55 5.55 0 0 0-4.43 2.7 5.6 5.6 0 0 0-1.15 6.3 5.55 5.55 0 0 0-1.5 4.98 5.6 5.6 0 0 0 3.8 4.7 5.55 5.55 0 0 0 4.43 2.7 5.6 5.6 0 0 0 4.44-1.2 5.55 5.55 0 0 0 4.43-2.7 5.6 5.6 0 0 0 1.15-6.3 5.55 5.55 0 0 0-.44-3.18zm-7.5 11.23a4.08 4.08 0 0 1-2.48-.84l.13-.07 4.14-2.39a.78.78 0 0 0 .39-.68v-5.85l1.75 1.01a.07.07 0 0 1 .04.06v5.04a4.1 4.1 0 0 1-3.97 3.72zm-8.36-4.14a4.08 4.08 0 0 1-.5-2.58c.03-.64.2-1.26.5-1.83l.13.08 4.14 2.39c.24.14.39.4.39.68v5.85l-1.75-1.01a.07.07 0 0 1-.04-.06v-3.52zm-1.88-8.9a4.08 4.08 0 0 1 1.98-1.74l-.13.07-4.14 2.39a.78.78 0 0 0-.39.68v5.85l1.75-1.01a.07.07 0 0 1 .04-.06v-5.04c0-.39.3-.72.69-.76l.2-.42zm14.37 2.39l-4.14-2.39a.78.78 0 0 0-.78 0l-5.07 2.93 1.75 1.01a.07.07 0 0 1 .04.06v4.78l1.75-1.01a.78.78 0 0 0 .39-.68v-4.7zm1.88 4.76a4.08 4.08 0 0 1-.5 2.58 4.1 4.1 0 0 1-2.48 1.97v-4.94a.78.78 0 0 0-.39-.68l-5.07-2.93 1.75-1.01a.07.07 0 0 1 .07 0l4.36 2.52a4.1 4.1 0 0 1 2.26 2.49zm-8.01-3.63l-2.07-1.2 2.07-1.2 2.07 1.2-2.07 1.2zm-2.5 1.44l-1.75-1.01a.07.07 0 0 1-.04-.06v-4.78l-1.75 1.01a.78.78 0 0 0-.39.68v4.7l4.14 2.39a.78.78 0 0 0 .78 0l2.07-1.2-2.07-1.2-1.03-.53z"
        fill={color}
      />
    </svg>
  )
}

// ─── 3. Ollama ───────────────────────────────────────────────────────────────
export function OllamaLogo({ className = '', size = 20, color = 'currentColor' }: LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="Ollama"
    >
      {/* Official Ollama minimal llama contour */}
      <path
        d="M8.5 3a1.5 1.5 0 0 0-1.5 1.5V8a4 4 0 0 0 4 4h1v1.5a1.5 1.5 0 0 1-1.5 1.5H8a1 1 0 0 0-1 1v4a1 1 0 0 0 2 0v-3h1.5A3.5 3.5 0 0 0 14 13.5V12h1a4 4 0 0 0 4-4V4.5A1.5 1.5 0 0 0 17.5 3h-1A1.5 1.5 0 0 0 15 4.5V6H9V4.5A1.5 1.5 0 0 0 7.5 3h1zm2 5a1 1 0 1 1-2 0 1 1 0 0 1 2 0zm5 0a1 1 0 1 1-2 0 1 1 0 0 1 2 0z"
        fill={color}
      />
    </svg>
  )
}

// ─── 4. Grok (xAI) ───────────────────────────────────────────────────────────
export function GrokLogo({ className = '', size = 20, color = 'currentColor' }: LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="Grok xAI"
    >
      <path
        d="M3.5 3.5l6.8 9.5-6.8 7.5h2.2l5.6-6.2 4.8 6.2h6.4l-7.3-10.2L21.4 3.5h-2.2l-5.1 5.7-4.4-5.7H3.5zm3.2 1.6h2.5l11.6 15.3h-2.5L6.7 5.1z"
        fill={color}
      />
    </svg>
  )
}

// ─── 5. DeepSeek ─────────────────────────────────────────────────────────────
export function DeepSeekLogo({ className = '', size = 20, color = '#1D72FE' }: LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="DeepSeek"
    >
      {/* DeepSeek whale / dolphin jumping glyph */}
      <path
        d="M21.5 11.2c-.8-1.5-2.2-2.7-3.9-3.4-.6-.2-1.3-.4-2-.4-1.2 0-2.4.3-3.4.9l-2.6 1.5-3.3-2.1c-.8-.5-1.8-.6-2.7-.2-.9.4-1.5 1.1-1.7 2.1l-.8 3.8c-.2 1 .1 2 .8 2.7l3.6 3.6c.7.7 1.7 1.1 2.7 1.1.8 0 1.6-.2 2.3-.7l6.8-4.5c1.8-1.2 3.1-2.9 3.8-4.9z"
        fill={color}
      />
      <circle cx="8" cy="11.5" r="1.2" fill="#FFFFFF" />
    </svg>
  )
}

// ─── 6. Google Gemini ─────────────────────────────────────────────────────────
export function GeminiLogo({ className = '', size = 20, color = '#4E82EE' }: LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="Google Gemini"
    >
      <path
        d="M12 2C12 7.52 7.52 12 2 12c5.52 0 10 4.48 10 10 0-5.52 4.48-10 10-10-5.52 0-10-4.48-10-10z"
        fill={color}
      />
    </svg>
  )
}

// ─── 7. LangChain ────────────────────────────────────────────────────────────
export function LangChainLogo({ className = '', size = 20, color = '#2DD4BF' }: LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="LangChain"
    >
      <path
        d="M6 8a4 4 0 0 1 4-4h2a4 4 0 0 1 4 4v1h-2V8a2 2 0 0 0-2-2h-2a2 2 0 0 0-2 2v2a2 2 0 0 0 2 2h1v2h-1a4 4 0 0 1-4-4V8zm12 8a4 4 0 0 1-4 4h-2a4 4 0 0 1-4-4v-1h2v1a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2v-2a2 2 0 0 0-2-2h-1v-2h1a4 4 0 0 1 4 4v1z"
        fill={color}
      />
    </svg>
  )
}

// ─── 8. LlamaIndex ───────────────────────────────────────────────────────────
export function LlamaIndexLogo({ className = '', size = 20, color = '#A855F7' }: LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="LlamaIndex"
    >
      <path
        d="M7 3h3v5l3 3v7h-3v-5l-3-3V3zm7 7h3v10h-3V10z"
        fill={color}
      />
    </svg>
  )
}

// ─── 9. PyTorch ──────────────────────────────────────────────────────────────
export function PyTorchLogo({ className = '', size = 20, color = '#EE4C2C' }: LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="PyTorch"
    >
      <path
        d="M13.2 2.1c.3.5.1 1.2-.4 1.5-1.5.9-2.5 2.5-2.5 4.3 0 2.8 2.2 5 5 5 1.5 0 2.8-.6 3.8-1.7.4-.4 1.1-.5 1.5-.1.4.4.5 1.1.1 1.5-1.4 1.5-3.3 2.3-5.4 2.3-4 0-7.2-3.2-7.2-7.2 0-2.5 1.3-4.8 3.5-6.1.5-.3 1.2-.1 1.6.5zm3.8.4a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0z"
        fill={color}
      />
    </svg>
  )
}

// ─── 10. HuggingFace ─────────────────────────────────────────────────────────
export function HuggingFaceLogo({ className = '', size = 20, color = '#FFD21E' }: LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="HuggingFace"
    >
      <circle cx="12" cy="12" r="9" fill={color} />
      <circle cx="9" cy="10" r="1.5" fill="#292929" />
      <circle cx="15" cy="10" r="1.5" fill="#292929" />
      <path
        d="M8.5 14.5c1 1.5 2.5 2 3.5 2s2.5-.5 3.5-2"
        stroke="#292929"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      {/* hugging hands */}
      <path
        d="M4 14c.5-1 2-2 3-1.5M20 14c-.5-1-2-2-3-1.5"
        stroke="#292929"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
    </svg>
  )
}
