import { Ship } from 'lucide-react'
import { cn } from '@/lib/utils'

export function Sidebar({ children }) {
  return (
    <aside className="fixed inset-y-0 left-0 z-40 hidden w-60 flex-col border-r bg-card lg:flex">
      {children}
    </aside>
  )
}

export function SidebarHeader() {
  return (
    <div className="flex items-center gap-2.5 border-b px-5 py-4">
      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
        <Ship className="h-4 w-4" />
      </div>
      <div>
        <div className="text-sm font-semibold leading-none">Berth</div>
        <div className="mt-1 text-xs text-muted-foreground">Engineering work, docked</div>
      </div>
    </div>
  )
}

export function SidebarSection({ title, action, children }) {
  return (
    <div className="px-3 py-3">
      <div className="mb-1.5 flex items-center justify-between px-2">
        <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{title}</span>
        {action}
      </div>
      <div className="space-y-0.5">{children}</div>
    </div>
  )
}

export function SidebarItem({ active, onClick, children, trailing }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'group flex w-full items-center gap-2.5 rounded-md px-2 py-1.5 text-left text-sm transition-colors hover:bg-accent',
        active && 'bg-accent font-medium'
      )}
    >
      <span className="min-w-0 flex-1 truncate">{children}</span>
      {trailing}
    </button>
  )
}

export function PageShell({ children }) {
  return <div className="min-h-screen pl-60">{children}</div>
}

export function PageHeader({ eyebrow, title, description, actions }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div>
        <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{eyebrow}</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  )
}
