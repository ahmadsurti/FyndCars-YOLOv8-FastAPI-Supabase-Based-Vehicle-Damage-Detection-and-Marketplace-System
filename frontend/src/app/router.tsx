import { createRootRoute, createRoute, createRouter, Outlet } from '@tanstack/react-router'
import { LandingPage } from '@/features/landing/LandingPage'
import { AuthenticatedLayout } from '@/components/layout/authenticated-layout'
import { DashboardOverview } from '@/features/dashboard/DashboardOverview'
import { ComingSoon } from '@/components/coming-soon'

const rootRoute = createRootRoute({
  component: Outlet,
})

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: LandingPage,
})

// Unified /app parent route with AuthenticatedLayout
const appRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: 'app',
  component: AuthenticatedLayout,
})

const appOverviewRoute = createRoute({
  getParentRoute: () => appRoute,
  path: '/',
  component: DashboardOverview,
})

const exploreRoute = createRoute({
  getParentRoute: () => appRoute,
  path: 'explore',
  component: () => (
    <ComingSoon
      title="Explore Marketplace"
      description="Infinite-scroll vehicle feed with catalog-driven cascading filters, YOLO damage tags, and high-res verified photo galleries."
      phase="Phase 4: Buyer Flow & Marketplace"
    />
  ),
})

const savedRoute = createRoute({
  getParentRoute: () => appRoute,
  path: 'saved',
  component: () => (
    <ComingSoon
      title="Saved Shortlist"
      description="Your bookmarked clean vehicles, price movement alerts, and saved search filters."
      phase="Phase 4: Buyer Flow & Marketplace"
    />
  ),
})

const alertsRoute = createRoute({
  getParentRoute: () => appRoute,
  path: 'alerts',
  component: () => (
    <ComingSoon
      title="Search Alerts"
      description="Automated email & in-app alerts triggered when newly inspected vehicles matching your criteria pass YOLOv8 & Docling gates."
      phase="Phase 4: Buyer Flow & Marketplace"
    />
  ),
})

const sellRoute = createRoute({
  getParentRoute: () => appRoute,
  path: 'sell',
  component: () => (
    <ComingSoon
      title="Sell a Car — AI Intake Stepper"
      description="Multi-step intake dropzone: 3-15 vehicle photos + RC document, real-time 4-gate AI scan animation, specs autofill, and fraud guard."
      phase="Phase 3: Seller Flow — AI-Powered Intake Pipeline"
    />
  ),
})

const myListingsRoute = createRoute({
  getParentRoute: () => appRoute,
  path: 'my-listings',
  component: () => (
    <ComingSoon
      title="My Garage & Inventory"
      description="Filterable tabs (Active, Pending Review, Drafts, Sold), 7-day view analytics, and 1-click Mark as Sold workflow."
      phase="Phase 3: Seller Flow — AI-Powered Intake Pipeline"
    />
  ),
})

const reviewsRoute = createRoute({
  getParentRoute: () => appRoute,
  path: 'reviews',
  component: () => (
    <ComingSoon
      title="Reputation & Verified Reviews"
      description="Verified buyer review scores, seller rating telemetry, and anti-fraud reputation badges."
      phase="Phase 4: Buyer Flow & Marketplace"
    />
  ),
})

const messagesRoute = createRoute({
  getParentRoute: () => appRoute,
  path: 'messages',
  component: () => (
    <ComingSoon
      title="Direct Messages & Inquiries"
      description="Real-time buyer-seller chat threads attached to specific vehicle VINs and verification reports."
      phase="Phase 4: Buyer Flow & Marketplace"
    />
  ),
})

// Elevated /admin parent route
const adminRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: 'admin',
  component: AuthenticatedLayout,
})

const adminQueueRoute = createRoute({
  getParentRoute: () => adminRoute,
  path: 'queue',
  component: () => (
    <ComingSoon
      title="Admin Verification Review Queue"
      description="Triage queue for human-review and escalated listings with split-screen YOLO bbox inspector and 1-click override decisions."
      phase="Phase 5: Admin Portal & Operations Hub"
    />
  ),
})

const adminStatsRoute = createRoute({
  getParentRoute: () => adminRoute,
  path: 'stats',
  component: () => (
    <ComingSoon
      title="Platform Telemetry & Audit"
      description="Real-time platform performance metrics, AI pass/fail rates, latency telemetry, and user management."
      phase="Phase 5: Admin Portal & Operations Hub"
    />
  ),
})

const adminAuditRoute = createRoute({
  getParentRoute: () => adminRoute,
  path: 'audit',
  component: () => (
    <ComingSoon
      title="Admin Audit Logs"
      description="Immutable activity audit trail tracking listing overrides, status changes, and user permission updates."
      phase="Phase 5: Admin Portal & Operations Hub"
    />
  ),
})

const routeTree = rootRoute.addChildren([
  indexRoute,
  appRoute.addChildren([
    appOverviewRoute,
    exploreRoute,
    savedRoute,
    alertsRoute,
    sellRoute,
    myListingsRoute,
    reviewsRoute,
    messagesRoute,
  ]),
  adminRoute.addChildren([
    adminQueueRoute,
    adminStatsRoute,
    adminAuditRoute,
  ]),
])

export const router = createRouter({ routeTree })

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
