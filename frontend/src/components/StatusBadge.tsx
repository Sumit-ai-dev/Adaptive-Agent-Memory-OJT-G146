import type { AvailabilityBadge, ExperienceStatus } from '../types'

interface StatusBadgeProps {
  status: AvailabilityBadge | ExperienceStatus
  size?: 'sm' | 'md'
  className?: string
}

export default function StatusBadge({ status, size = 'sm', className = '' }: StatusBadgeProps) {
  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs'

  switch (status) {
    case 'Available Now':
    case 'active':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-mono font-medium rounded-md border ${sizeClasses} ${className}
            bg-emerald-50 text-emerald-800 border-emerald-200
            dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800/60`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          {status === 'active' ? 'Active' : 'Available Now'}
        </span>
      )

    case 'Demo':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-mono font-medium rounded-md border ${sizeClasses} ${className}
            bg-indigo-50 text-indigo-800 border-indigo-200
            dark:bg-indigo-950/40 dark:text-indigo-300 dark:border-indigo-800/60`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
          Demo Mode
        </span>
      )

    case 'candidate':
    case 'provisional':
    case 'Preview':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-mono font-medium rounded-md border ${sizeClasses} ${className}
            bg-amber-50 text-amber-800 border-amber-200
            dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800/60`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
          {status === 'candidate' ? 'Candidate' : status === 'provisional' ? 'Candidate (Provisional)' : 'Preview'}
        </span>
      )

    case 'quarantined':
    case 'deprecated':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-mono font-medium rounded-md border ${sizeClasses} ${className}
            bg-rose-50 text-rose-800 border-rose-200
            dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-800/60`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
          {status === 'deprecated' ? 'Deprecated (Quarantined)' : 'Quarantined'}
        </span>
      )

    case 'Planned':
    default:
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-mono font-medium rounded-md border ${sizeClasses} ${className}
            bg-zinc-100 text-zinc-700 border-zinc-200
            dark:bg-zinc-800/60 dark:text-zinc-400 dark:border-zinc-700`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-zinc-400" />
          Planned
        </span>
      )
  }
}
