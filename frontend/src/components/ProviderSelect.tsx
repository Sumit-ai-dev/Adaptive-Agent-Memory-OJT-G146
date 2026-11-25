import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Check, ChevronDown, Cpu } from 'lucide-react'
import { PROVIDER_UI_OPTIONS, SupportedProvider } from '../services/api'

interface ProviderSelectProps {
  value: SupportedProvider
  onChange: (provider: SupportedProvider) => void
  align?: 'left' | 'right'
  compact?: boolean
}

export default function ProviderSelect({
  value,
  onChange,
  align = 'left',
  compact = false,
}: ProviderSelectProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [dropdownStyle, setDropdownStyle] = useState<React.CSSProperties>({ position: 'fixed' })
  const triggerRef = useRef<HTMLButtonElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  const current = PROVIDER_UI_OPTIONS.find((opt) => opt.id === value) || PROVIDER_UI_OPTIONS[0]

  // Recalculate dropdown position relative to trigger button
  const updateDropdownPos = () => {
    if (!triggerRef.current) return
    const rect = triggerRef.current.getBoundingClientRect()
    const dropdownWidth = 256 // w-64

    let left = align === 'right' ? rect.right - dropdownWidth : rect.left
    // Clamp to viewport
    if (left + dropdownWidth > window.innerWidth - 8) {
      left = window.innerWidth - dropdownWidth - 8
    }
    if (left < 8) left = 8

    setDropdownStyle({
      position: 'fixed',
      top: rect.bottom + 6,
      left,
      width: dropdownWidth,
      zIndex: 9999,
    })
  }

  const handleOpen = () => {
    updateDropdownPos()
    setIsOpen((prev) => !prev)
  }

  useEffect(() => {
    if (!isOpen) return
    function handleClickOutside(event: MouseEvent) {
      const target = event.target as Node
      if (
        containerRef.current &&
        !containerRef.current.contains(target) &&
        triggerRef.current &&
        !triggerRef.current.contains(target)
      ) {
        setIsOpen(false)
      }
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') setIsOpen(false)
    }
    function handleScroll() {
      updateDropdownPos()
    }
    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleKeyDown)
    window.addEventListener('scroll', handleScroll, true)
    window.addEventListener('resize', updateDropdownPos)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('scroll', handleScroll, true)
      window.removeEventListener('resize', updateDropdownPos)
    }
  }, [isOpen])

  const dropdown = (
    <div
      ref={containerRef}
      role="listbox"
      aria-label="Select Provider"
      style={dropdownStyle}
      className={`rounded-lg border border-[#2E2E2A] bg-[#161614] py-1.5 shadow-2xl font-mono transition-all duration-150 ease-out ${
        align === 'right' ? 'origin-top-right' : 'origin-top-left'
      } ${
        isOpen
          ? 'opacity-100 translate-y-0 scale-100 pointer-events-auto'
          : 'opacity-0 -translate-y-1 scale-95 pointer-events-none'
      }`}
    >
      {PROVIDER_UI_OPTIONS.map((opt) => {
        const isSelected = opt.id === value
        return (
          <button
            key={opt.id}
            type="button"
            role="option"
            aria-selected={isSelected}
            onClick={() => {
              onChange(opt.id)
              setIsOpen(false)
            }}
            className={`w-full flex items-center justify-between gap-2 px-3 py-2 text-left transition-colors duration-100 cursor-pointer ${
              isSelected
                ? 'bg-[#22221E] text-white border-l-2 border-[#4EAA79]'
                : 'hover:bg-[#1E1E1B] text-[#9E9D96] border-l-2 border-transparent'
            }`}
          >
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-5 h-5 rounded flex items-center justify-center shrink-0 bg-[#242422] p-0.5 overflow-hidden">
                {opt.logo ? (
                  <img src={opt.logo} alt={opt.name} className="w-full h-full object-contain" />
                ) : (
                  <Cpu size={12} className="text-[#7E7D77]" />
                )}
              </div>
              <div className="min-w-0">
                <div className="text-[11px] font-medium text-[#EDECE8] truncate">{opt.name}</div>
                <div className="text-[10px] text-[#7E7D77] truncate">{opt.subname}</div>
              </div>
            </div>
            {isSelected && <Check size={13} className="text-[#4EAA79] shrink-0" />}
          </button>
        )
      })}
    </div>
  )

  return (
    <div className="relative">
      <button
        ref={triggerRef}
        type="button"
        onClick={handleOpen}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        className={
          compact
            ? 'flex items-center gap-1.5 px-2.5 py-1 rounded border border-[#242422] bg-[#141412] hover:bg-[#1A1A17] hover:border-[#32322E] text-[11px] font-mono transition-colors duration-150 cursor-pointer text-[#EDECE8]'
            : 'flex items-center gap-2 px-2.5 py-1.5 rounded-lg border font-mono text-xs transition-colors duration-150 cursor-pointer bg-[#141412] border-[#2E2E2A] text-[#EDECE8] hover:bg-[#1E1E1B] hover:border-[#3C3C36]'
        }
      >
        <div className="w-3.5 h-3.5 rounded-sm flex items-center justify-center shrink-0 overflow-hidden">
          {current.logo ? (
            <img src={current.logo} alt={current.name} className="w-full h-full object-contain" />
          ) : (
            <Cpu size={12} className="text-[#7E7D77]" />
          )}
        </div>
        <span className="truncate max-w-[140px] text-[11px] font-medium">{current.name}</span>
        <ChevronDown
          size={11}
          className={`text-[#7E7D77] transition-transform duration-150 ease-out shrink-0 ${
            isOpen ? 'rotate-180' : ''
          }`}
        />
      </button>

      {isOpen && createPortal(dropdown, document.body)}
    </div>
  )
}
