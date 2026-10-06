import React, { useState } from 'react'
import { Copy, Check } from 'lucide-react'

interface MarkdownRendererProps {
  content: string
}

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  if (!content) return null

  // Split content into code blocks and normal markdown segments
  const segments = parseContent(content)

  return (
    <div className="space-y-3 text-sm leading-relaxed text-white/90 font-sans break-words">
      {segments.map((seg, idx) => {
        if (seg.type === 'code') {
          return (
            <CodeBlock
              key={idx}
              language={seg.language || 'text'}
              code={seg.content}
            />
          )
        }

        return <TextSegment key={idx} text={seg.content} />
      })}
    </div>
  )
}

function CodeBlock({ language, code }: { language: string; code: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // fallback
    }
  }

  return (
    <div className="my-3 rounded-xl overflow-hidden border border-white/10 bg-[#06000c] shadow-lg">
      <div className="flex items-center justify-between px-3.5 py-1.5 bg-white/5 border-b border-white/10 text-xs font-mono text-white/50">
        <span className="uppercase tracking-wider text-[11px] text-purple-300">
          {language}
        </span>
        <button
          onClick={handleCopy}
          type="button"
          className="flex items-center gap-1 px-2 py-0.5 rounded hover:bg-white/10 text-white/60 hover:text-white transition-colors cursor-pointer text-[11px]"
          title="Copy code"
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
      <pre className="p-4 overflow-x-auto text-xs font-mono text-emerald-300 leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  )
}

function TextSegment({ text }: { text: string }) {
  const lines = text.split('\n')

  return (
    <div className="space-y-2">
      {lines.map((line, idx) => {
        const trimmed = line.trim()
        if (!trimmed) {
          return <div key={idx} className="h-2" />
        }

        // Heading 3
        if (line.startsWith('### ')) {
          return (
            <h3
              key={idx}
              className="text-base font-display font-bold text-purple-200 mt-3 mb-1"
            >
              {renderInline(line.slice(4))}
            </h3>
          )
        }

        // Heading 2
        if (line.startsWith('## ')) {
          return (
            <h2
              key={idx}
              className="text-lg font-display font-bold text-white mt-4 mb-2 border-b border-white/10 pb-1"
            >
              {renderInline(line.slice(3))}
            </h2>
          )
        }

        // Heading 1
        if (line.startsWith('# ')) {
          return (
            <h1
              key={idx}
              className="text-xl font-display font-bold text-white mt-4 mb-2"
            >
              {renderInline(line.slice(2))}
            </h1>
          )
        }

        // Unordered list item
        if (line.startsWith('- ') || line.startsWith('* ')) {
          return (
            <div key={idx} className="flex items-start gap-2 ml-2">
              <span className="text-purple-400 mt-1.5 text-[8px]">●</span>
              <span>{renderInline(line.slice(2))}</span>
            </div>
          )
        }

        // Ordered list item
        const numMatch = line.match(/^(\d+)\.\s+(.*)$/)
        if (numMatch) {
          return (
            <div key={idx} className="flex items-start gap-2 ml-2">
              <span className="text-purple-300 font-mono text-xs font-semibold mt-0.5">
                {numMatch[1]}.
              </span>
              <span>{renderInline(numMatch[2])}</span>
            </div>
          )
        }

        // Regular paragraph line
        return <p key={idx}>{renderInline(line)}</p>
      })}
    </div>
  )
}

function renderInline(text: string): React.ReactNode {
  // Parse inline elements: `code`, **bold**, *italic*
  const parts: React.ReactNode[] = []
  let remaining = text
  let key = 0

  while (remaining.length > 0) {
    // Inline code: `code`
    const codeMatch = remaining.match(/`([^`]+)`/)
    // Bold: **text**
    const boldMatch = remaining.match(/\*\*([^*]+)\*\*/)

    let earliestIdx = remaining.length
    let matchType = ''
    let matchLen = 0
    let matchContent = ''

    if (codeMatch && codeMatch.index !== undefined && codeMatch.index < earliestIdx) {
      earliestIdx = codeMatch.index
      matchType = 'code'
      matchLen = codeMatch[0].length
      matchContent = codeMatch[1]
    }

    if (boldMatch && boldMatch.index !== undefined && boldMatch.index < earliestIdx) {
      earliestIdx = boldMatch.index
      matchType = 'bold'
      matchLen = boldMatch[0].length
      matchContent = boldMatch[1]
    }

    if (matchType === '') {
      parts.push(<span key={key++}>{remaining}</span>)
      break
    }

    if (earliestIdx > 0) {
      parts.push(<span key={key++}>{remaining.slice(0, earliestIdx)}</span>)
    }

    if (matchType === 'code') {
      parts.push(
        <code
          key={key++}
          className="px-1.5 py-0.5 mx-0.5 rounded bg-purple-500/15 text-purple-200 border border-purple-500/30 font-mono text-xs"
        >
          {matchContent}
        </code>
      )
    } else if (matchType === 'bold') {
      parts.push(
        <strong key={key++} className="font-semibold text-white">
          {matchContent}
        </strong>
      )
    }

    remaining = remaining.slice(earliestIdx + matchLen)
  }

  return <>{parts}</>
}

interface ContentSegment {
  type: 'text' | 'code'
  language?: string
  content: string
}

function parseContent(content: string): ContentSegment[] {
  const segments: ContentSegment[] = []
  const regex = /```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = regex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      segments.push({
        type: 'text',
        content: content.substring(lastIndex, match.index),
      })
    }
    segments.push({
      type: 'code',
      language: match[1] || 'code',
      content: match[2].trimEnd(),
    })
    lastIndex = match.index + match[0].length
  }

  if (lastIndex < content.length) {
    segments.push({
      type: 'text',
      content: content.substring(lastIndex),
    })
  }

  return segments
}
