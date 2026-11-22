import React, { useState } from 'react'
import { Copy, Check, Info, AlertTriangle, Lightbulb } from 'lucide-react'

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
    <div className="my-2.5 rounded-lg overflow-hidden border border-[#2E2E2A] bg-[#141412] text-[#EDECE8] text-xs font-mono shadow-sm">
      <div className="flex items-center justify-between px-3 py-1.5 bg-[#1A1A17] border-b border-[#242422] text-[11px] text-[#7E7D77]">
        <span className="font-semibold uppercase tracking-wider text-[10px] text-[#9E9D96]">
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
              <Check size={12} className="text-[#4EAA79]" />
              <span className="text-[#4EAA79]">Copied</span>
            </>
          ) : (
            <>
              <Copy size={12} />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      <pre className="p-3 overflow-x-auto leading-relaxed text-[#EDECE8]">
        <code>{code}</code>
      </pre>
    </div>
  )
}

interface TableBlockProps {
  headers: string[]
  alignments: ('left' | 'center' | 'right')[]
  rows: string[][]
}

function TableBlock({ headers, alignments, rows }: TableBlockProps) {
  const getAlignClass = (align?: 'left' | 'center' | 'right') => {
    if (align === 'center') return 'text-center'
    if (align === 'right') return 'text-right'
    return 'text-left'
  }

  return (
    <div className="my-3 overflow-hidden rounded-lg border border-[#2E2E2A] bg-[#141412] shadow-sm">
      <div className="overflow-x-auto max-w-full">
        <table className="w-full text-left border-collapse text-xs">
          {headers.length > 0 && (
            <thead>
              <tr className="bg-[#1A1A17] border-b border-[#2E2E2A]">
                {headers.map((h, i) => (
                  <th
                    key={`th-${i}`}
                    className={`px-3.5 py-2.5 font-semibold text-[#EDECE8] text-[11px] tracking-wider uppercase ${getAlignClass(
                      alignments[i]
                    )} whitespace-nowrap`}
                  >
                    {renderInlineFormatting(h)}
                  </th>
                ))}
              </tr>
            </thead>
          )}
          <tbody className="divide-y divide-[#242422]">
            {rows.map((row, rIdx) => (
              <tr
                key={`tr-${rIdx}`}
                className="hover:bg-[#1A1A17]/70 transition-colors"
              >
                {row.map((cell, cIdx) => (
                  <td
                    key={`td-${rIdx}-${cIdx}`}
                    className={`px-3.5 py-2.5 text-[#D4D3CE] text-xs leading-relaxed align-top ${getAlignClass(
                      alignments[cIdx]
                    )}`}
                  >
                    {renderInlineFormatting(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function CalloutBlock({ type, title, text }: { type: 'tip' | 'note' | 'warning'; title?: string; text: string }) {
  const isTip = type === 'tip'
  const isWarning = type === 'warning'

  const borderClass = isWarning
    ? 'border-[#8C4A1E] bg-[#22160E]/70'
    : isTip
    ? 'border-[#2D4F38] bg-[#132017]/70'
    : 'border-[#2C3B4E] bg-[#121A24]/70'

  const badgeClass = isWarning
    ? 'bg-[#E67E22]/20 text-[#E67E22] border-[#E67E22]/30'
    : isTip
    ? 'bg-[#4EAA79]/20 text-[#4EAA79] border-[#4EAA79]/30'
    : 'bg-[#5B9BD5]/20 text-[#5B9BD5] border-[#5B9BD5]/30'

  const IconComponent = isWarning ? AlertTriangle : isTip ? Lightbulb : Info

  return (
    <div className={`my-3 p-3 rounded-lg border ${borderClass} text-xs text-[#EDECE8] flex items-start gap-2.5 shadow-sm`}>
      <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider border shrink-0 mt-0.5 flex items-center gap-1 ${badgeClass}`}>
        <IconComponent size={11} />
        <span>{title || (isWarning ? 'Warning' : isTip ? 'Tip' : 'Note')}</span>
      </span>
      <div className="flex-1 leading-relaxed text-[#D4D3CE] mt-0.5">
        {renderInlineFormatting(text)}
      </div>
    </div>
  )
}

export function renderInlineFormatting(text: string): React.ReactNode[] {
  if (!text) return []
  const tokens: React.ReactNode[] = []
  let remaining = text
  let keyIdx = 0

  while (remaining.length > 0) {
    // 1. Look for earliest marker
    const brMatch = remaining.match(/^(.*?)<br\s*\/?>/i)
    const codeMatch = remaining.match(/^(.*?)`([^`]+)`/s)
    const boldMatch = remaining.match(/^(.*?)(\*\*|__)(.*?)\2/s)
    const strikeMatch = remaining.match(/^(.*?)~~(.*?)~~/s)
    const linkMatch = remaining.match(/^(.*?)\[(.*?)\]\((.*?)\)/s)
    const italicMatch = remaining.match(/^(.*?)(\*|_)(.*?)\2/s)

    // Find the match that occurs at the earliest index in remaining string
    let earliestType: string | null = null
    let earliestIndex = Infinity
    let earliestMatch: any = null

    if (brMatch && brMatch[1].length < earliestIndex) {
      earliestIndex = brMatch[1].length
      earliestType = 'br'
      earliestMatch = brMatch
    }
    if (codeMatch && codeMatch[1].length < earliestIndex) {
      earliestIndex = codeMatch[1].length
      earliestType = 'code'
      earliestMatch = codeMatch
    }
    if (boldMatch && boldMatch[1].length < earliestIndex) {
      earliestIndex = boldMatch[1].length
      earliestType = 'bold'
      earliestMatch = boldMatch
    }
    if (strikeMatch && strikeMatch[1].length < earliestIndex) {
      earliestIndex = strikeMatch[1].length
      earliestType = 'strike'
      earliestMatch = strikeMatch
    }
    if (linkMatch && linkMatch[1].length < earliestIndex) {
      earliestIndex = linkMatch[1].length
      earliestType = 'link'
      earliestMatch = linkMatch
    }
    if (italicMatch && italicMatch[1].length < earliestIndex && italicMatch[3].trim().length > 0) {
      earliestIndex = italicMatch[1].length
      earliestType = 'italic'
      earliestMatch = italicMatch
    }

    if (!earliestType) {
      tokens.push(remaining)
      break
    }

    // Push preceding text if any
    const prefix = earliestMatch[1]
    if (prefix) {
      tokens.push(...renderInlineFormatting(prefix))
    }

    // Handle token
    if (earliestType === 'br') {
      tokens.push(<br key={`br-${keyIdx++}`} />)
      remaining = remaining.slice(earliestMatch[0].length)
    } else if (earliestType === 'code') {
      tokens.push(
        <code
          key={`code-${keyIdx++}`}
          className="px-1.5 py-0.5 rounded bg-[#1E1E1B] font-mono text-[11px] text-[#EDECE8] border border-[#2E2E2A]"
        >
          {earliestMatch[2]}
        </code>
      )
      remaining = remaining.slice(earliestMatch[0].length)
    } else if (earliestType === 'bold') {
      tokens.push(
        <strong key={`bold-${keyIdx++}`} className="font-bold text-[#EDECE8]">
          {renderInlineFormatting(earliestMatch[3])}
        </strong>
      )
      remaining = remaining.slice(earliestMatch[0].length)
    } else if (earliestType === 'strike') {
      tokens.push(
        <del key={`strike-${keyIdx++}`} className="line-through text-[#7E7D77]">
          {renderInlineFormatting(earliestMatch[2])}
        </del>
      )
      remaining = remaining.slice(earliestMatch[0].length)
    } else if (earliestType === 'link') {
      tokens.push(
        <a
          key={`link-${keyIdx++}`}
          href={earliestMatch[3]}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[#4EAA79] underline underline-offset-2 hover:text-[#5EBA89] transition-colors"
        >
          {earliestMatch[2]}
        </a>
      )
      remaining = remaining.slice(earliestMatch[0].length)
    } else if (earliestType === 'italic') {
      tokens.push(
        <em key={`italic-${keyIdx++}`} className="italic text-[#D4D3CE]">
          {renderInlineFormatting(earliestMatch[3])}
        </em>
      )
      remaining = remaining.slice(earliestMatch[0].length)
    }
  }

  return tokens
}

function isTableSeparator(line: string): boolean {
  return /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$/.test(line)
}

function isTableRow(line: string): boolean {
  const trimmed = line.trim()
  return (
    (trimmed.startsWith('|') || (trimmed.includes('|') && trimmed.endsWith('|'))) &&
    !trimmed.startsWith('```') &&
    !trimmed.startsWith('#')
  )
}

function splitTableRow(rowStr: string): string[] {
  let clean = rowStr.trim()
  if (clean.startsWith('|')) clean = clean.slice(1)
  if (clean.endsWith('|')) clean = clean.slice(0, -1)
  return clean
    .replace(/\\\|/g, '___ESCAPED_PIPE___')
    .split('|')
    .map(c => c.replace(/___ESCAPED_PIPE___/g, '|').trim())
}

function getTableAlignments(sepStr: string): ('left' | 'center' | 'right')[] {
  const cells = splitTableRow(sepStr)
  return cells.map(c => {
    const trimmed = c.trim()
    const leftColon = trimmed.startsWith(':')
    const rightColon = trimmed.endsWith(':')
    if (leftColon && rightColon) return 'center'
    if (rightColon) return 'right'
    return 'left'
  })
}

export default function MarkdownRenderer({ content, className = '' }: MarkdownRendererProps) {
  if (!content) {
    return <span className="text-[#7E7D77] italic">No output generated.</span>
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

    // 2. Horizontal Rule: ---, ***, ___
    if (/^\s*(?:-{3,}|\*{3,}|_{3,})\s*$/.test(line)) {
      blocks.push(
        <hr
          key={`hr-${lineIdx}`}
          className="my-4 border-t border-[#2E2E2A]"
        />
      )
      lineIdx++
      continue
    }

    // 3. Table Block
    if (isTableRow(line) && lineIdx + 1 < lines.length && isTableSeparator(lines[lineIdx + 1])) {
      const headerLine = lines[lineIdx]
      const sepLine = lines[lineIdx + 1]
      const headers = splitTableRow(headerLine)
      const alignments = getTableAlignments(sepLine)
      lineIdx += 2

      const rows: string[][] = []
      while (
        lineIdx < lines.length &&
        isTableRow(lines[lineIdx]) &&
        !isTableSeparator(lines[lineIdx])
      ) {
        const rawRow = splitTableRow(lines[lineIdx])
        // Pad row cells if fewer than headers
        while (rawRow.length < headers.length) {
          rawRow.push('')
        }
        rows.push(rawRow)
        lineIdx++
      }

      blocks.push(
        <TableBlock
          key={`table-${lineIdx}`}
          headers={headers}
          alignments={alignments}
          rows={rows}
        />
      )
      continue
    }

    // 4. Headings: #, ##, ###, ####
    const h1Match = line.match(/^#\s+(.*)$/)
    const h2Match = line.match(/^##\s+(.*)$/)
    const h3Match = line.match(/^###\s+(.*)$/)
    const h4Match = line.match(/^####\s+(.*)$/)

    if (h1Match) {
      blocks.push(
        <h1
          key={`h1-${lineIdx}`}
          className="text-base font-bold text-[#EDECE8] mt-4 mb-2 pb-1.5 border-b border-[#242422] first:mt-0 font-sans tracking-tight"
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
          className="text-sm font-bold text-[#EDECE8] mt-4 mb-2 first:mt-0 font-sans tracking-tight"
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
          className="text-xs font-bold text-[#EDECE8] mt-3.5 mb-1.5 first:mt-0 font-sans uppercase tracking-wider"
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
          className="text-xs font-semibold text-[#EDECE8] mt-2.5 mb-1 first:mt-0 font-sans"
        >
          {renderInlineFormatting(h4Match[1])}
        </h4>
      )
      lineIdx++
      continue
    }

    // 5. Callouts: Tip:, Note:, Warning:, Important:, Caution:
    const calloutMatch = line.match(/^\s*(Tip|Note|Warning|Important|Caution):\s*(.*)$/i)
    if (calloutMatch) {
      const typeWord = calloutMatch[1].toLowerCase()
      const calloutType = (typeWord === 'warning' || typeWord === 'caution' || typeWord === 'important')
        ? 'warning'
        : typeWord === 'tip'
        ? 'tip'
        : 'note'

      blocks.push(
        <CalloutBlock
          key={`callout-${lineIdx}`}
          type={calloutType}
          title={calloutMatch[1]}
          text={calloutMatch[2]}
        />
      )
      lineIdx++
      continue
    }

    // 6. Blockquotes / Callouts: > text
    if (line.trim().startsWith('>')) {
      const quoteLines: string[] = []
      while (lineIdx < lines.length && lines[lineIdx].trim().startsWith('>')) {
        quoteLines.push(lines[lineIdx].replace(/^\s*>\s?/, ''))
        lineIdx++
      }
      blocks.push(
        <blockquote
          key={`quote-${lineIdx}`}
          className="my-2.5 pl-3.5 py-1.5 border-l-2 border-[#4EAA79] bg-[#161614] text-[#EDECE8] rounded-r text-xs italic leading-relaxed"
        >
          {renderInlineFormatting(quoteLines.join(' '))}
        </blockquote>
      )
      continue
    }

    // 7. Bullet list items: - or *
    if (line.match(/^(\s*)[-*]\s+(.*)$/)) {
      const listItems: React.ReactNode[] = []
      while (lineIdx < lines.length && lines[lineIdx].match(/^(\s*)[-*]\s+(.*)$/)) {
        const itemMatch = lines[lineIdx].match(/^(\s*)[-*]\s+(.*)$/)!
        const indentLevel = Math.floor(itemMatch[1].length / 2)
        listItems.push(
          <li
            key={`li-${lineIdx}`}
            className="flex items-start gap-2 my-1 leading-relaxed text-[#EDECE8]"
            style={{ marginLeft: `${indentLevel * 14}px` }}
          >
            <span className="text-[#4EAA79] font-bold select-none shrink-0 mt-0.5">•</span>
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

    // 8. Numbered list items: 1. 2. etc.
    if (line.match(/^(\s*)(\d+)\.\s+(.*)$/)) {
      const numItems: React.ReactNode[] = []
      while (lineIdx < lines.length && lines[lineIdx].match(/^(\s*)(\d+)\.\s+(.*)$/)) {
        const itemMatch = lines[lineIdx].match(/^(\s*)(\d+)\.\s+(.*)$/)!
        const num = itemMatch[2]
        numItems.push(
          <li
            key={`oli-${lineIdx}`}
            className="flex items-start gap-2 my-1 leading-relaxed text-[#EDECE8]"
          >
            <span className="text-[#E67E22] font-mono font-semibold select-none shrink-0 text-[11px] min-w-[18px]">
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

    // 9. Blank / Empty lines (spacing)
    if (line.trim() === '') {
      lineIdx++
      continue
    }

    // 10. Regular paragraph text (accumulate contiguous non-empty lines)
    const paraLines: string[] = []
    while (
      lineIdx < lines.length &&
      lines[lineIdx].trim() !== '' &&
      !lines[lineIdx].trim().startsWith('```') &&
      !lines[lineIdx].trim().startsWith('#') &&
      !lines[lineIdx].trim().startsWith('>') &&
      !/^\s*(?:-{3,}|\*{3,}|_{3,})\s*$/.test(lines[lineIdx]) &&
      !lines[lineIdx].match(/^\s*(Tip|Note|Warning|Important|Caution):\s*/i) &&
      !lines[lineIdx].match(/^(\s*)[-*]\s+/) &&
      !lines[lineIdx].match(/^(\s*)\d+\.\s+/) &&
      !(isTableRow(lines[lineIdx]) && lineIdx + 1 < lines.length && isTableSeparator(lines[lineIdx + 1]))
    ) {
      paraLines.push(lines[lineIdx])
      lineIdx++
    }

    if (paraLines.length > 0) {
      blocks.push(
        <p
          key={`p-${lineIdx}`}
          className="my-2 leading-relaxed text-[#EDECE8] font-sans text-xs"
        >
          {renderInlineFormatting(paraLines.join(' '))}
        </p>
      )
    } else {
      lineIdx++
    }
  }

  return <div className={`markdown-body space-y-1 ${className}`}>{blocks}</div>
}
