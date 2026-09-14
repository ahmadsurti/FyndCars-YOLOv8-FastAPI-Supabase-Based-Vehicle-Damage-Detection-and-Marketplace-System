import { Link } from '@tanstack/react-router'
import { Sparkles, ExternalLink } from 'lucide-react'
import {
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
} from '@/components/ui/sidebar'

export function TeamSwitcher() {
  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <SidebarMenuButton
          size="lg"
          asChild
          className="hover:bg-white/[0.04] transition-colors rounded-lg p-2"
        >
          <Link to="/app" className="flex items-center gap-2.5">
            <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm shadow-primary/30">
              <Sparkles className="size-4" />
            </div>
            <div className="grid flex-1 text-start leading-tight">
              <span className="truncate font-semibold tracking-tight text-foreground font-sans text-sm">
                fynd<span className="text-primary">(cars)</span>
              </span>
              <span className="truncate text-[10px] text-muted-foreground font-mono uppercase tracking-wider">
                Automotive Noir
              </span>
            </div>
          </Link>
        </SidebarMenuButton>
      </SidebarMenuItem>
    </SidebarMenu>
  )
}
