import { Link } from '@tanstack/react-router'
import { ArrowLeft } from 'lucide-react'
import { Button } from '@/dashboard-shell/components/ui/button'

interface ComingSoonProps {
  title?: string
  description?: string
  phase?: string
}

export function ComingSoon({
  title = 'Module In Pipeline',
  description = 'This screen is part of the next development phase in the master roadmap.',
  phase = 'Phase 3 / 4',
}: ComingSoonProps) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center text-center p-8 max-w-lg mx-auto min-h-[60vh]">
      <div className="inline-flex items-center gap-2 rounded-full border border-border/80 bg-muted/30 px-3 py-1 text-[11px] font-mono uppercase tracking-wider text-muted-foreground mb-4">
        <span>{phase}</span>
      </div>
      <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground mb-2">
        {title}
      </h1>
      <p className="text-sm text-muted-foreground mb-6 max-w-sm">
        {description}
      </p>
      <Button asChild variant="outline" size="sm" className="rounded-lg text-xs gap-2">
        <Link to="/app">
          <ArrowLeft className="size-3.5" />
          <span>Return to Command Center</span>
        </Link>
      </Button>
    </div>
  )
}
