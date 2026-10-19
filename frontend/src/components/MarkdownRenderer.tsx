import React, { useState } from 'react'
import { Copy, Check } from 'lucide-react'

interface MarkdownRendererProps {
  content: string
  className?: string
}

interface BlockCodeProps {
  language: string
  code: string
}

function CodeBlock({ language, code }: BlockCodeProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="my-2.5 rounded-lg overflow-hidden border border-zinc-200 dark:border-[#252B3B] bg-zinc-900 text-zinc-100 dark:bg-[#0C0E14] text-xs font-mono shadow-sm">
      <div className="flex items-center justify-between px-3 py-1.5 bg-zinc-800/80 dark:bg-[#131722] border-b border-zinc-700/50 dark:border-[#252B3B] text-[11px] text-zinc-400">
        <span className="font-semibold uppercase tracking-wider text-[10px] text-zinc-400">
          {language || 'text'}
        </span>
        <button
          onClick={handleCopy}
          type="button"
          className="flex items-center gap-1 hover:text-white transition-colors cursor-pointer text-[10px]"
          title="Copy code block"
        >
          {copied ? (
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
      </div>
      <pre className="p-3 overflow-x-auto leading-relaxed text-zinc-200 dark:text-zinc-300">
        <code>{code}</code>
      </pre>
    </div>
  )
}

function renderInlineFormatting(text: string): React.ReactNode[] {
  // Regex parsing: inline code (`...`), bold (**...** or __...__), italic (*...* or _..._)
  const tokens: React.ReactNode[] = []
  let remaining = text
  let keyIdx = 0

  while (remaining.length > 0) {
    // Check for inline code: `code`
    const codeMatch = remaining.match(/^(.*?)`([^`]+)`(.*)$/s)
    // Check for bold: **bold** or __bold__
    const boldMatch = remaining.match(/^(.*?)(\*\*|__)(.*?)\2(.*)$/s)

    // Determine which token appears earlier
    const codeIndex = remaining.indexOf('`')
    const boldIndex = remaining.search(/(\*\*|__)/)

    if (codeIndex !== -1 && (boldIndex === -1 || codeIndex < boldIndex)) {
      if (codeMatch) {
        if (codeMatch[1]) {
          tokens.push(...renderInlineFormatting(codeMatch[1]))
        }
        tokens.push(
          <code
            key={`inline-code-${keyIdx++}`}
            className="px-1.5 py-0.5 rounded bg-zinc-200/70 dark:bg-[#252B3B] font-mono text-[11px] text-indigo-600 dark:text-indigo-400 border border-zinc-300/50 dark:border-[#323B4F]"
          >
            {codeMatch[2]}
          </code>
        )
        remaining = codeMatch[3]
        continue
      }
    } else if (boldIndex !== -1) {
      if (boldMatch) {
        if (boldMatch[1]) {
          tokens.push(...renderInlineFormatting(boldMatch[1]))
        }
        tokens.push(
          <strong
            key={`bold-${keyIdx++}`}
            className="font-bold text-zinc-900 dark:text-[#F4F4F6]"
          >
            {boldMatch[3]}
          </strong>
        )
        remaining = boldMatch[4]
        continue
      }
    }

    // Check for italic: *italic* or _italic_
    const italicMatch = remaining.match(/^(.*?)(\*|_)(.*?)\2(.*)$/s)
    if (italicMatch && italicMatch[3].trim().length > 0) {
      if (italicMatch[1]) {
        tokens.push(italicMatch[1])
      }
      tokens.push(
        <em key={`italic-${keyIdx++}`} className="italic">
          {italicMatch[3]}
        </em>
      )
      remaining = italicMatch[4]
      continue
    }

    // No further formatting
    tokens.push(remaining)
    break
  }

  return tokens
}

export default function MarkdownRenderer({ content, className = '' }: MarkdownRendererProps) {
  if (!content) {
    return <span className="text-zinc-400 italic">No output generated.</span>
  }

  const lines = content.split('\n')
  const blocks: React.ReactNode[] = []
  let lineIdx = 0

  while (lineIdx < lines.length) {
    const line = lines[lineIdx]

    // 1. Fenced Code Block: ```lang ... ```
    if (line.trim().startsWith('```')) {
      const language = line.trim().slice(3).trim()
      const codeLines: string[] = []
      lineIdx++
      while (lineIdx < lines.length && !lines[lineIdx].trim().startsWith('```')) {
        codeLines.push(lines[lineIdx])
        lineIdx++
      }
      // Skip closing ```
      lineIdx++
      blocks.push(
        <CodeBlock
          key={`block-code-${lineIdx}`}
          language={language}
          code={codeLines.join('\n')}
        />
      )
      continue
    }

    // 2. Headings: #, ##, ###, ####
    const h1Match = line.match(/^#\s+(.*)$/)
    const h2Match = line.match(/^##\s+(.*)$/)
    const h3Match = line.match(/^###\s+(.*)$/)
    const h4Match = line.match(/^####\s+(.*)$/)

    if (h1Match) {
      blocks.push(
        <h1
          key={`h1-${lineIdx}`}
          className="text-base font-bold text-zinc-900 dark:text-[#F4F4F6] mt-4 mb-2 pb-1 border-b border-zinc-200 dark:border-[#252B3B] first:mt-0 font-sans tracking-tight"
        >
          {renderInlineFormatting(h1Match[1])}
        </h1>
      )
      lineIdx++
      continue
    }

    if (h2Match) {
      blocks.push(
        <h2
          key={`h2-${lineIdx}`}
          className="text-sm font-bold text-zinc-900 dark:text-[#F4F4F6] mt-3.5 mb-1.5 first:mt-0 font-sans tracking-tight"
        >
          {renderInlineFormatting(h2Match[1])}
        </h2>
      )
      lineIdx++
      continue
    }

    if (h3Match) {
      blocks.push(
        <h3
          key={`h3-${lineIdx}`}
          className="text-xs font-bold text-zinc-800 dark:text-zinc-200 mt-3 mb-1 first:mt-0 font-sans uppercase tracking-wider"
        >
          {renderInlineFormatting(h3Match[1])}
        </h3>
      )
      lineIdx++
      continue
    }

    if (h4Match) {
      blocks.push(
        <h4
          key={`h4-${lineIdx}`}
          className="text-xs font-semibold text-zinc-800 dark:text-zinc-200 mt-2 mb-0.5 first:mt-0 font-sans"
        >
          {renderInlineFormatting(h4Match[1])}
        </h4>
      )
      lineIdx++
      continue
    }

    // 3. Blockquotes / Callouts: > text
    if (line.trim().startsWith('>')) {
      const quoteText = line.replace(/^\s*>\s?/, '')
      blocks.push(
        <blockquote
          key={`quote-${lineIdx}`}
          className="my-2 pl-3 py-1 border-l-2 border-indigo-500 bg-indigo-50/40 dark:bg-indigo-950/20 text-zinc-700 dark:text-zinc-300 rounded-r text-xs italic"
        >
          {renderInlineFormatting(quoteText)}
        </blockquote>
      )
      lineIdx++
      continue
    }

    // 4. Bullet list items: - or *
    if (line.match(/^(\s*)[-*]\s+(.*)$/)) {
      const listItems: React.ReactNode[] = []
      while (lineIdx < lines.length && lines[lineIdx].match(/^(\s*)[-*]\s+(.*)$/)) {
        const itemMatch = lines[lineIdx].match(/^(\s*)[-*]\s+(.*)$/)!
        const indentLevel = Math.floor(itemMatch[1].length / 2)
        listItems.push(
          <li
            key={`li-${lineIdx}`}
            className="flex items-start gap-2 my-1 leading-relaxed text-zinc-700 dark:text-zinc-300"
            style={{ marginLeft: `${indentLevel * 14}px` }}
          >
            <span className="text-indigo-600 dark:text-indigo-400 font-bold select-none shrink-0 mt-0.5">•</span>
            <div className="flex-1">{renderInlineFormatting(itemMatch[2])}</div>
          </li>
        )
        lineIdx++
      }
      blocks.push(
        <ul key={`ul-${lineIdx}`} className="my-2 space-y-0.5">
          {listItems}
        </ul>
      )
      continue
    }

    // 5. Numbered list items: 1. 2. etc.
    if (line.match(/^(\s*)(\d+)\.\s+(.*)$/)) {
      const numItems: React.ReactNode[] = []
      while (lineIdx < lines.length && lines[lineIdx].match(/^(\s*)(\d+)\.\s+(.*)$/)) {
        const itemMatch = lines[lineIdx].match(/^(\s*)(\d+)\.\s+(.*)$/)!
        const num = itemMatch[2]
        numItems.push(
          <li
            key={`oli-${lineIdx}`}
            className="flex items-start gap-2 my-1 leading-relaxed text-zinc-700 dark:text-zinc-300"
          >
            <span className="text-indigo-600 dark:text-indigo-400 font-mono font-semibold select-none shrink-0 text-[11px] min-w-[18px]">
              {num}.
            </span>
            <div className="flex-1">{renderInlineFormatting(itemMatch[3])}</div>
          </li>
        )
        lineIdx++
      }
      blocks.push(
        <ol key={`ol-${lineIdx}`} className="my-2 space-y-0.5">
          {numItems}
        </ol>
      )
      continue
    }

    // 6. Blank / Empty lines (spacing)
    if (line.trim() === '') {
      lineIdx++
      continue
    }

    // 7. Regular paragraph text (accumulate contiguous non-empty lines)
    const paraLines: string[] = []
    while (
      lineIdx < lines.length &&
      lines[lineIdx].trim() !== '' &&
      !lines[lineIdx].trim().startsWith('```') &&
      !lines[lineIdx].trim().startsWith('#') &&
      !lines[lineIdx].trim().startsWith('>') &&
      !lines[lineIdx].match(/^(\s*)[-*]\s+/) &&
      !lines[lineIdx].match(/^(\s*)\d+\.\s+/)
    ) {
      paraLines.push(lines[lineIdx])
      lineIdx++
    }

    if (paraLines.length > 0) {
      blocks.push(
        <p
          key={`p-${lineIdx}`}
          className="my-2 leading-relaxed text-zinc-700 dark:text-zinc-300 font-sans text-xs"
        >
          {renderInlineFormatting(paraLines.join(' '))}
        </p>
      )
    }
  }

  return <div className={`markdown-body space-y-1 ${className}`}>{blocks}</div>
}
