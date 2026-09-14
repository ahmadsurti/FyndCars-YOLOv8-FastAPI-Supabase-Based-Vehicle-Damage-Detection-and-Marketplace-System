import { useEffect, useState } from 'react'
import { cn } from '@/lib/utils'
import { Separator } from '@/components/ui/separator'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { Button } from '@/components/ui/button'
import { Search, Bell, Sparkles } from 'lucide-react'
import { useSearch } from '@/context/search-provider'
import { ConfigDrawer } from '@/components/config-drawer'
import { Link } from '@tanstack/react-router'

type HeaderProps = React.HTMLAttributes<HTMLElement> & {
  fixed?: boolean
}

export function Header({ className, fixed = true, children, ...props }: HeaderProps) {
  const [offset, setOffset] = useState(0)
  const { setOpen: setOpenSearch } = useSearch()

  useEffect(() => {
    const onScroll = () => {
      setOffset(document.body.scrollTop || document.documentElement.scrollTop)
    }

    document.addEventListener('scroll', onScroll, { passive: true })
    return () => document.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <header
      className={cn(
        'z-40 h-14 border-b border-border/40 bg-background/80 backdrop-blur-md',
        fixed && 'sticky top-0 w-full',
        offset > 10 ? 'shadow-xs' : '',
        className
      )}
      {...props}
    >
      <div className="flex h-full items-center justify-between px-4 gap-3">
        <div className="flex items-center gap-2 sm:gap-3">
          <SidebarTrigger className="hover:bg-white/[0.06] text-muted-foreground hover:text-foreground" />
          <Separator orientation="vertical" className="h-4 bg-border/60" />
          {children}
        </div>

        <div className="flex items-center gap-2">
          {/* Cmd+K Search Palette Trigger */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setOpenSearch(true)}
            className="h-8 w-44 sm:w-64 justify-start text-xs text-muted-foreground bg-white/[0.02] border-border/60 hover:bg-white/[0.05] hover:text-foreground px-2.5 rounded-lg"
          >
            <Search className="size-3.5 mr-2 opacity-60" />
            <span className="truncate">Search inventory, make...</span>
            <kbd className="ms-auto pointer-events-none inline-flex h-4 select-none items-center gap-0.5 rounded border border-border/80 bg-muted/60 px-1.5 font-mono text-[9px] font-medium text-muted-foreground">
              <span className="text-[10px]">⌘</span>K
            </kbd>
          </Button>

          {/* Quick List Car CTA */}
          <Button
            asChild
            size="sm"
            className="hidden sm:inline-flex h-8 text-xs font-medium rounded-lg bg-primary hover:bg-primary/90 text-primary-foreground shadow-xs"
          >
            <Link to="/app/sell">
              <Sparkles className="size-3 mr-1.5" />
              + List Car
            </Link>
          </Button>

          {/* Messages Alert */}
          <Button
            asChild
            variant="ghost"
            size="icon"
            className="size-8 rounded-lg text-muted-foreground hover:text-foreground hover:bg-white/[0.06] relative"
          >
            <Link to="/app/messages" aria-label="Unread Messages">
              <Bell className="size-4" />
              <span className="absolute top-1.5 right-1.5 size-2 rounded-full bg-primary ring-2 ring-background" />
            </Link>
          </Button>

          {/* Workspace Settings / Config Drawer */}
          <ConfigDrawer />
        </div>
      </div>
    </header>
  )
}
