import * as React from 'react'
import { Outlet, useLocation, useNavigate } from '@tanstack/react-router'
import {
  Gauge,
  Compass,
  Bookmark,
  Bell,
  PlusCircle,
  Car,
  Star,
  MessageSquare,
  ShieldCheck,
  Activity,
  FileText,
  Plus,
} from 'lucide-react'
import { DashboardLayout } from '@/dashboard-shell/components/layout/DashboardLayout'
import { Button } from '@/dashboard-shell/components/ui/button'
import { useAuthStore } from '@/lib/auth/auth-store'
import type { SidebarNavGroup } from '@/dashboard-shell/components/layout/DashboardSidebar'

const ROUTE_MAP: Record<string, string> = {
  overview: '/app',
  explore: '/app/explore',
  saved: '/app/saved',
  alerts: '/app/alerts',
  sell: '/app/sell',
  'my-listings': '/app/my-listings',
  reviews: '/app/reviews',
  messages: '/app/messages',
  'admin-queue': '/admin/queue',
  'admin-stats': '/admin/stats',
  'admin-audit': '/admin/audit',
}

const TITLE_MAP: Record<string, string> = {
  overview: 'Command Center',
  explore: 'Explore Inventory',
  saved: 'Saved Shortlist',
  alerts: 'Search Alerts',
  sell: 'Sell a Car',
  'my-listings': 'My Garage',
  reviews: 'Reputation & Reviews',
  messages: 'Direct Messages',
  'admin-queue': 'Verification Review Queue',
  'admin-stats': 'Platform Telemetry',
  'admin-audit': 'Audit Logs',
}

function resolveActiveId(pathname: string): string {
  if (pathname === '/app' || pathname === '/app/') return 'overview'
  if (pathname.startsWith('/app/explore')) return 'explore'
  if (pathname.startsWith('/app/saved')) return 'saved'
  if (pathname.startsWith('/app/alerts')) return 'alerts'
  if (pathname.startsWith('/app/sell')) return 'sell'
  if (pathname.startsWith('/app/my-listings')) return 'my-listings'
  if (pathname.startsWith('/app/reviews')) return 'reviews'
  if (pathname.startsWith('/app/messages')) return 'messages'
  if (pathname.startsWith('/admin/queue')) return 'admin-queue'
  if (pathname.startsWith('/admin/stats')) return 'admin-stats'
  if (pathname.startsWith('/admin/audit')) return 'admin-audit'
  return 'overview'
}

type AuthenticatedLayoutProps = {
  children?: React.ReactNode
}

export function AuthenticatedLayout({ children }: AuthenticatedLayoutProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const { profile, user, signOut } = useAuthStore()
  const activeId = resolveActiveId(location.pathname)
  const isAdmin = profile?.role === 'admin'

  const navGroups: SidebarNavGroup[] = [
    {
      label: 'Marketplace',
      items: [
        { id: 'overview', title: 'Overview', icon: Gauge },
        { id: 'explore', title: 'Explore Inventory', icon: Compass },
        { id: 'saved', title: 'Saved Shortlist', icon: Bookmark },
        { id: 'alerts', title: 'Search Alerts', icon: Bell },
      ],
    },
    {
      label: 'Selling',
      items: [
        { id: 'sell', title: 'List a Car', icon: PlusCircle },
        { id: 'my-listings', title: 'My Garage', icon: Car },
        { id: 'reviews', title: 'Reviews & Reputation', icon: Star },
      ],
    },
    {
      label: 'Inbox',
      items: [
        { id: 'messages', title: 'Messages', icon: MessageSquare },
      ],
    },
    ...(isAdmin
      ? [
          {
            label: 'Admin Operations',
            items: [
              { id: 'admin-queue', title: 'Verification Queue', icon: ShieldCheck },
              { id: 'admin-stats', title: 'Platform Telemetry', icon: Activity },
              { id: 'admin-audit', title: 'Audit Logs', icon: FileText },
            ],
          },
        ]
      : []),
  ]

  const handleSelectItem = (id: string) => {
    const targetPath = ROUTE_MAP[id]
    if (targetPath && targetPath !== location.pathname) {
      navigate({ to: targetPath })
    }
  }

  const handleSignOut = async () => {
    await signOut()
    navigate({ to: '/' })
  }

  return (
    <DashboardLayout
      sidebarProps={{
        brand: {
          name: 'fynd(cars)',
          subtitle: 'Automotive Platform',
        },
        groups: navGroups,
        activeId,
        onSelectItem: handleSelectItem,
        onNewItem: () => navigate({ to: '/app/sell' }),
        newItemLabel: 'List a Car',
        user: {
          name: profile?.fullName || user?.email?.split('@')[0] || 'User',
          email: user?.email || 'user@fyndcars.dev',
        },
        onSignOut: handleSignOut,
      }}
      headerProps={{
        title: TITLE_MAP[activeId] ?? 'Workspace',
        actions: (
          <Button
            size="sm"
            className="h-7 text-xs gap-1.5 rounded-lg bg-primary hover:bg-primary/90 text-primary-foreground font-medium cursor-pointer"
            onClick={() => navigate({ to: '/app/sell' })}
          >
            <Plus className="size-3.5" />
            <span>List Car</span>
          </Button>
        ),
      }}
      contentLayout="fluid"
    >
      {children ?? <Outlet />}
    </DashboardLayout>
  )
}
