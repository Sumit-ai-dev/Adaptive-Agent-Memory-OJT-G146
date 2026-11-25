import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Check, ChevronDown } from 'lucide-react'
import { PROVIDER_MODEL_OPTIONS, ProviderModelOption } from '../services/api'

interface ProviderModelSelectProps {
  provider: string
  value: string
  onChange: (modelId: string) => void
  align?: 'left' | 'right'
  compact?: boolean
}

export default function ProviderModelSelect({
  provider,
  value,
  onChange,
  align = 'left',
  compact = false,
}: ProviderModelSelectProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [dropdownStyle, setDropdownStyle] = useState<React.CSSProperties>({})
  const triggerRef = useRef<HTMLButtonElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)

  const models: ProviderModelOption[] = PROVIDER_MODEL_OPTIONS[provider] || []
  const activeOption = models.find((m) => m.id === value) || models[0]
  const freeModels = models.filter((m) => m.tier === 'free')
  const paidModels = models.filter((m) => m.tier === 'paid')

  // Recalculate dropdown position relative to trigger button
  const updateDropdownPos = () => {
    if (!triggerRef.current) return
    const rect = triggerRef.current.getBoundingClientRect()
    const dropdownWidth = 288 // w-72

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

  useEffect(() => {
    setIsOpen(false)
  }, [provider])

  const handleOpen = () => {
    updateDropdownPos()
    setIsOpen((prev) => !prev)
  }

  useEffect(() => {
    if (!isOpen) return
    function handleClickOutside(event: MouseEvent) {
      const target = event.target as Node
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(target) &&
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

  if (models.length === 0 || !activeOption) return null

  const renderTierBadge = (tier: 'free' | 'paid') => (
    <span
      className={`text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded font-semibold shrink-0 ${
        tier === 'free'
          ? 'bg-[#1E2E24] text-[#4EAA79] border border-[#2E4234]'
          : 'bg-[#2B2216] text-[#E6A23C] border border-[#453520]'
      }`}
    >
      {tier === 'free' ? 'Free' : 'Paid'}
    </span>
  )

  const renderOption = (m: ProviderModelOption) => {
    const isSelected = m.id === activeOption.id
    return (
      <button
        key={m.id}
        type="button"
        role="option"
        aria-selected={isSelected}
        onClick={() => {
          onChange(m.id)
          setIsOpen(false)
        }}
        className={`w-full flex items-center justify-between gap-2 px-3 py-2 text-left transition-colors duration-100 cursor-pointer ${
          isSelected
            ? 'bg-[#22221E] text-white border-l-2 border-[#4EAA79]'
            : 'hover:bg-[#1E1E1B] text-[#9E9D96] border-l-2 border-transparent'
        }`}
      >
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <span className="text-[11px] font-medium text-[#EDECE8] truncate">{m.label}</span>
            {renderTierBadge(m.tier)}
          </div>
          <div className="text-[10px] text-[#7E7D77] truncate mt-0.5">{m.note}</div>
        </div>
        {isSelected && <Check size={13} className="text-[#4EAA79] shrink-0" />}
      </button>
    )
  }

  const dropdown = (
    <div
      ref={dropdownRef}
      role="listbox"
      aria-label="Available Models"
      style={dropdownStyle}
      className={`max-h-80 overflow-y-auto rounded-lg border border-[#2E2E2A] bg-[#161614] py-1.5 shadow-2xl font-mono transition-all duration-150 ease-out ${
        align === 'right' ? 'origin-top-right' : 'origin-top-left'
      } ${
        isOpen
          ? 'opacity-100 translate-y-0 scale-100 pointer-events-auto'
          : 'opacity-0 -translate-y-1 scale-95 pointer-events-none'
      }`}
    >
      {freeModels.length > 0 && paidModels.length > 0 ? (
        <>
          <div className="px-3 py-1 text-[9px] font-bold uppercase tracking-wider text-[#4EAA79]/90">
            Free API Tier Models
          </div>
          {freeModels.map(renderOption)}
          <div className="my-1 border-t border-[#242422]" />
          <div className="px-3 py-1 text-[9px] font-bold uppercase tracking-wider text-[#E6A23C]/90">
            Paid Tier (Billing Required)
          </div>
          {paidModels.map(renderOption)}
        </>
      ) : (
        models.map(renderOption)
      )}
    </div>
  )

  return (
    <div className="relative">
      <button
        ref={triggerRef}
        type="button"
        onClick={handleOpen}
        aria-label="Select Provider Model"
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        className={
          compact
            ? 'flex items-center gap-1.5 px-2.5 py-1 rounded border border-[#242422] bg-[#141412] hover:bg-[#1A1A17] hover:border-[#32322E] text-[11px] font-mono transition-colors duration-150 cursor-pointer text-[#EDECE8]'
            : 'flex items-center gap-2 px-2.5 py-1.5 rounded-lg border font-mono text-[11px] transition-colors duration-150 cursor-pointer bg-[#141412] border-[#2E2E2A] text-[#EDECE8] hover:bg-[#1E1E1B] hover:border-[#3C3C36]'
        }
      >
        <span className="truncate max-w-[160px] font-medium">{activeOption.label}</span>
        {renderTierBadge(activeOption.tier)}
        <ChevronDown
          size={11}
          className={`text-[#7E7D77] transition-transform duration-150 ease-out shrink-0 ${
            isOpen ? 'rotate-180' : ''
          }`}
        />
      </button>

      {createPortal(dropdown, document.body)}
    </div>
  )
}
