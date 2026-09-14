import { useState } from 'react'
import { Link } from '@tanstack/react-router'
import {
  ChevronsUpDown,
  LogOut,
  Sparkles,
  ShieldCheck,
  User,
  Car,
} from 'lucide-react'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from '@/components/ui/sidebar'
import { SignOutDialog } from '@/components/sign-out-dialog'
import { useAuthStore } from '@/lib/auth/auth-store'

export function NavUser() {
  const { isMobile } = useSidebar()
  const [openSignOut, setOpenSignOut] = useState(false)
  const { profile, user } = useAuthStore()

  const displayName = profile?.fullName || user?.email?.split('@')[0] || 'Member'
  const displayEmail = user?.email || 'user@fyndcars.dev'
  const role = profile?.role || 'buyer'

  const initials = displayName
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2) || 'FC'

  return (
    <>
      <SidebarMenu>
        <SidebarMenuItem>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <SidebarMenuButton
                size="lg"
                className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground border border-white/[0.04] rounded-lg p-2 hover:bg-white/[0.04]"
              >
                <Avatar className="h-8 w-8 rounded-md border border-white/[0.08] bg-primary/20 text-primary font-mono text-xs">
                  <AvatarImage src="" alt={displayName} />
                  <AvatarFallback className="rounded-md font-mono">{initials}</AvatarFallback>
                </Avatar>
                <div className="grid flex-1 text-start text-xs leading-tight">
                  <span className="truncate font-medium text-foreground">{displayName}</span>
                  <span className="truncate text-[10px] text-muted-foreground uppercase font-mono tracking-wider">{role}</span>
                </div>
                <ChevronsUpDown className="ms-auto size-3.5 text-muted-foreground" />
              </SidebarMenuButton>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              className="w-(--radix-dropdown-menu-trigger-width) min-w-56 rounded-xl bg-[#08090c] border-sidebar-border text-foreground"
              side={isMobile ? 'bottom' : 'right'}
              align="end"
              sideOffset={4}
            >
              <DropdownMenuLabel className="p-0 font-normal">
                <div className="flex items-center gap-2.5 px-3 py-2 text-start text-sm border-b border-border/50">
                  <Avatar className="h-8 w-8 rounded-md bg-primary/20 text-primary font-mono text-xs">
                    <AvatarFallback className="rounded-md font-mono">{initials}</AvatarFallback>
                  </Avatar>
                  <div className="grid flex-1 text-start text-xs leading-tight">
                    <span className="truncate font-semibold text-foreground">{displayName}</span>
                    <span className="truncate text-[11px] text-muted-foreground">{displayEmail}</span>
                  </div>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuGroup>
                <DropdownMenuItem asChild>
                  <Link to="/app/my-listings" className="cursor-pointer">
                    <Car className="size-4 mr-2" />
                    <span>My Garage</span>
                  </Link>
                </DropdownMenuItem>
                {role === 'admin' && (
                  <DropdownMenuItem asChild>
                    <Link to="/admin/queue" className="cursor-pointer text-primary">
                      <ShieldCheck className="size-4 mr-2" />
                      <span>Admin Queue</span>
                    </Link>
                  </DropdownMenuItem>
                )}
                <DropdownMenuItem asChild>
                  <Link to="/app" className="cursor-pointer">
                    <Sparkles className="size-4 mr-2" />
                    <span>Command Center</span>
                  </Link>
                </DropdownMenuItem>
              </DropdownMenuGroup>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                variant="destructive"
                onClick={() => setOpenSignOut(true)}
                className="cursor-pointer text-red-400 focus:text-red-400 focus:bg-red-500/10"
              >
                <LogOut className="size-4 mr-2" />
                <span>Sign Out</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </SidebarMenuItem>
      </SidebarMenu>

      <SignOutDialog open={openSignOut} onOpenChange={setOpenSignOut} />
    </>
  )
}
