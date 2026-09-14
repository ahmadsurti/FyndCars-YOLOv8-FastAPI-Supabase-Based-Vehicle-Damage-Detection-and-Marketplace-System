import {
  Gauge,
  Compass,
  BookmarkCheck,
  Bell,
  PlusCircle,
  Car,
  Star,
  MessagesSquare,
  ShieldCheck,
  Activity,
  FileText,
  Sparkles,
} from 'lucide-react'
import { type SidebarData } from '../types'

export const sidebarData: SidebarData = {
  user: {
    name: 'Ahmad Surti',
    email: 'buyer@fyndcars.dev',
    avatar: '',
    role: 'buyer',
  },
  teams: [
    {
      name: 'fynd(cars)',
      logo: Sparkles,
      plan: 'Verified Marketplace',
    },
  ],
  navGroups: [
    {
      title: 'Marketplace',
      items: [
        {
          title: 'Command Center',
          url: '/app',
          icon: Gauge,
        },
        {
          title: 'Explore Inventory',
          url: '/app/explore',
          icon: Compass,
        },
        {
          title: 'Saved Shortlist',
          url: '/app/saved',
          icon: BookmarkCheck,
        },
        {
          title: 'Search Alerts',
          url: '/app/alerts',
          icon: Bell,
        },
      ],
    },
    {
      title: 'Selling & Garage',
      items: [
        {
          title: '+ Sell a Car',
          url: '/app/sell',
          icon: PlusCircle,
        },
        {
          title: 'My Listings',
          url: '/app/my-listings',
          icon: Car,
        },
        {
          title: 'Reputation & Reviews',
          url: '/app/reviews',
          icon: Star,
        },
      ],
    },
    {
      title: 'Communication',
      items: [
        {
          title: 'Messages',
          url: '/app/messages',
          icon: MessagesSquare,
          badge: '2',
        },
      ],
    },
    {
      title: 'Admin Operations',
      items: [
        {
          title: 'Verification Queue',
          url: '/admin/queue',
          icon: ShieldCheck,
        },
        {
          title: 'Platform Telemetry',
          url: '/admin/stats',
          icon: Activity,
        },
        {
          title: 'Audit Logs',
          url: '/admin/audit',
          icon: FileText,
        },
      ],
    },
  ],
}
