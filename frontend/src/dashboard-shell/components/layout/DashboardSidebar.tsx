import * as React from "react"
import { ChevronsUpDown, LogOut, Plus, Search, SquarePen } from "lucide-react"
import { Avatar, AvatarFallback, AvatarImage } from "../ui/avatar"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../ui/dropdown-menu"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  useSidebar,
} from "../ui/sidebar"
import { useLayout } from "../../context/layout-provider"

/* ─── Types ───────────────────────────────────────────────── */
export interface SidebarItem {
  id: string
  title: string
  icon?: React.ComponentType<{ className?: string }>
  badge?: string | number
}

export interface SidebarNavGroup {
  label: string
  items: SidebarItem[]
}

export interface SidebarUser {
  name: string
  email: string
  avatarUrl?: string
}

export interface DashboardSidebarProps {
  brand?: { name: string; subtitle?: string; logo?: React.ReactNode }
  groups?: SidebarNavGroup[]
  items?: SidebarItem[]
  itemsLabel?: string
  activeId?: string | null
  onSelectItem?: (id: string) => void
  onNewItem?: () => void
  newItemLabel?: string
  onSearchClick?: () => void
  user?: SidebarUser
  onSignOut?: () => void
  customFooter?: React.ReactNode
}

/* ─── User Menu (Footer) ──────────────────────────────────── */
function NavUser({ user, onSignOut }: { user: SidebarUser; onSignOut?: () => void }) {
  const { isMobile } = useSidebar()
  const initials = (user.name || user.email).slice(0, 2).toUpperCase()

  return (
    <DropdownMenu modal={false}>
      <DropdownMenuTrigger asChild>
        <SidebarMenuButton
          size="lg"
          tooltip={user.name}
          className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground cursor-pointer"
          aria-label="User menu"
        >
          <Avatar className="h-8 w-8 rounded-lg shrink-0">
            {user.avatarUrl && <AvatarImage src={user.avatarUrl} alt={user.name} />}
            <AvatarFallback className="rounded-lg text-xs font-semibold bg-primary/15 text-primary">
              {initials}
            </AvatarFallback>
          </Avatar>
          <div className="grid flex-1 text-left text-sm leading-tight min-w-0">
            <span className="truncate font-semibold text-sm">{user.name}</span>
            <span className="truncate text-xs text-sidebar-foreground/70">{user.email}</span>
          </div>
          <ChevronsUpDown className="ml-auto size-4 shrink-0 text-sidebar-foreground/50" />
        </SidebarMenuButton>
      </DropdownMenuTrigger>

      <DropdownMenuContent
        side={isMobile ? "bottom" : "right"}
        align="end"
        sideOffset={4}
        className="w-(--radix-dropdown-menu-trigger-width) min-w-56 rounded-lg"
      >
        <div className="flex items-center gap-2 px-1 py-1.5 text-left text-sm">
          <Avatar className="h-8 w-8 rounded-lg shrink-0">
            {user.avatarUrl && <AvatarImage src={user.avatarUrl} alt={user.name} />}
            <AvatarFallback className="rounded-lg text-xs font-semibold bg-primary/15 text-primary">
              {initials}
            </AvatarFallback>
          </Avatar>
          <div className="grid flex-1 text-left leading-tight min-w-0">
            <span className="truncate font-semibold">{user.name}</span>
            <span className="truncate text-xs text-muted-foreground">{user.email}</span>
          </div>
        </div>

        {onSignOut && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem variant="destructive" onClick={onSignOut} className="cursor-pointer">
              <LogOut className="size-4 mr-2" />
              Sign out
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

/* ─── DashboardSidebar ────────────────────────────────────── */
export function DashboardSidebar({
  brand = { name: "Dashboard", subtitle: "Workspace" },
  groups,
  items = [],
  itemsLabel = "Items",
  activeId,
  onSelectItem,
  onNewItem,
  newItemLabel = "New Item",
  onSearchClick,
  user,
  onSignOut,
  customFooter,
}: DashboardSidebarProps) {
  const { collapsible, variant } = useLayout()

  // Normalise: if flat items are passed, wrap them as a single group
  const navGroups: SidebarNavGroup[] = groups ?? (items.length > 0 ? [{ label: itemsLabel, items }] : [])

  return (
    <Sidebar collapsible={collapsible} variant={variant}>
      {/* ── Header ── */}
      <SidebarHeader className="gap-2">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild tooltip={brand.name}>
              <div className="flex items-center gap-2 cursor-default select-none">
                {brand.logo ?? (
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/15 border border-primary/20 shrink-0">
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                      <rect x="0.5" y="0.5" width="5.5" height="5.5" rx="1.2" fill="currentColor" className="text-primary" opacity="0.9" />
                      <rect x="8"   y="0.5" width="5.5" height="5.5" rx="1.2" fill="currentColor" className="text-primary" opacity="0.4" />
                      <rect x="0.5" y="8"   width="5.5" height="5.5" rx="1.2" fill="currentColor" className="text-primary" opacity="0.4" />
                      <rect x="8"   y="8"   width="5.5" height="5.5" rx="1.2" fill="currentColor" className="text-primary" opacity="0.9" />
                    </svg>
                  </div>
                )}
                <div className="grid flex-1 text-left text-sm leading-tight group-data-[collapsible=icon]:hidden">
                  <span className="truncate font-bold tracking-tight">{brand.name}</span>
                  {brand.subtitle && (
                    <span className="truncate text-xs text-sidebar-foreground/60 font-medium">{brand.subtitle}</span>
                  )}
                </div>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>

        <SidebarMenu>
          {onSearchClick && (
            <SidebarMenuItem>
              <SidebarMenuButton onClick={onSearchClick} tooltip="Search (⌘K)" className="cursor-pointer">
                <Search className="size-4 shrink-0" />
                <span>Search…</span>
                <kbd className="ml-auto pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border border-sidebar-border bg-sidebar px-1.5 font-mono text-[10px] font-medium text-sidebar-foreground/60 group-data-[collapsible=icon]:hidden">
                  ⌘K
                </kbd>
              </SidebarMenuButton>
            </SidebarMenuItem>
          )}
          {onNewItem && (
            <SidebarMenuItem>
              <SidebarMenuButton
                onClick={onNewItem}
                tooltip={newItemLabel}
                className="bg-primary/10 text-primary hover:bg-primary/20 hover:text-primary font-medium cursor-pointer"
              >
                <SquarePen className="size-4 shrink-0" />
                <span>{newItemLabel}</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          )}
        </SidebarMenu>
      </SidebarHeader>

      {/* ── Nav Groups ── */}
      <SidebarContent>
        {navGroups.map((group) => (
          <SidebarGroup key={group.label}>
            <SidebarGroupLabel>{group.label}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {group.items.map((item) => {
                  const Icon = item.icon
                  return (
                    <SidebarMenuItem key={item.id}>
                      <SidebarMenuButton
                        isActive={item.id === activeId}
                        onClick={() => onSelectItem?.(item.id)}
                        tooltip={item.title}
                        className={item.id === activeId ? "font-medium cursor-pointer" : "cursor-pointer"}
                      >
                        {Icon && <Icon className="size-4 shrink-0" />}
                        <span className="truncate">{item.title}</span>
                        {item.badge != null && (
                          <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded bg-sidebar-accent text-sidebar-accent-foreground font-mono">
                            {item.badge}
                          </span>
                        )}
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  )
                })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}

        {navGroups.length === 0 && (
          <div className="flex flex-col items-center justify-center px-3 py-6 text-center">
            <p className="text-xs text-sidebar-foreground/50">No navigation items</p>
            {onNewItem && (
              <button
                type="button"
                onClick={onNewItem}
                className="mt-2.5 inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium text-primary hover:bg-primary/10 transition-colors cursor-pointer"
              >
                <Plus className="size-3.5" />
                <span>{newItemLabel}</span>
              </button>
            )}
          </div>
        )}
      </SidebarContent>

      {/* ── Footer ── */}
      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            {user ? <NavUser user={user} onSignOut={onSignOut} /> : (customFooter ?? null)}
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>

      <SidebarRail />
    </Sidebar>
  )
}
