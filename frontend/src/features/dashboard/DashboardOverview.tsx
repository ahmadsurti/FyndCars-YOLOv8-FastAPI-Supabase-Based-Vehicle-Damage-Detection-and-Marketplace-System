import { Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { Compass, Plus, ArrowUpRight, ShieldCheck } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/dashboard-shell/components/ui/button'
import { Skeleton } from '@/dashboard-shell/components/ui/skeleton'
import { useAuthStore } from '@/lib/auth/auth-store'
import { api } from '@/lib/api/client'
import { listingKeys, marketplaceKeys } from '@/lib/api/query-keys'

interface ListingSummary {
  id: string
  make: string
  model: string
  year: number
  variant?: string
  price: number
  city?: string
  mileage_km?: number
  fuel_type?: string
  transmission?: string
  status: string
  verified_clean?: boolean
  total_damages?: number
  images?: { image_url: string; is_primary: boolean }[]
}

const PIPELINE_GATES = [
  { id: 'Gate 0',  label: 'Clarity & Lux',  sub: 'OpenCV Filter'      },
  { id: 'Gate 1a', label: 'Damage Scan',     sub: 'YOLOv8 Detection'   },
  { id: 'Gate 1b', label: 'Docling OCR',     sub: 'RC Entity Extract'  },
  { id: 'Gate 1c', label: 'Gemma VLM',       sub: 'Odometer Guard'     },
] as const

function KpiCard({
  label,
  href,
  linkLabel,
  loading,
  value,
  sub,
}: {
  label: string
  href: string
  linkLabel: string
  loading: boolean
  value: React.ReactNode
  sub: string
}) {
  return (
    <Card className="rounded-xl border border-border/70 bg-card p-4 shadow-sm">
      <CardContent className="p-0 flex flex-col justify-between h-full gap-2">
        <div className="flex items-center justify-between text-xs font-medium text-muted-foreground">
          <span>{label}</span>
          <Link to={href} className="text-primary hover:underline text-[11px] flex items-center">
            {linkLabel} <ArrowUpRight className="size-3 ml-0.5" />
          </Link>
        </div>
        {loading ? (
          <Skeleton className="h-7 w-12 rounded" />
        ) : (
          <div className="text-2xl font-bold font-mono text-foreground">{value}</div>
        )}
        <span className="text-[11px] text-muted-foreground">{sub}</span>
      </CardContent>
    </Card>
  )
}

function CarCard({ car }: { car: ListingSummary }) {
  const img =
    car.images?.find((i) => i.is_primary)?.image_url ??
    car.images?.[0]?.image_url ??
    '/placeholder-car.jpg'

  return (
    <Card className="rounded-xl border border-border/70 bg-card hover:border-primary/50 transition-colors duration-200 overflow-hidden shadow-sm flex flex-col">
      <div className="relative aspect-[16/10] w-full overflow-hidden bg-muted">
        <img
          src={img}
          alt={`${car.make} ${car.model}`}
          className="size-full object-cover object-center"
          loading="lazy"
        />
        <div className="absolute top-2.5 left-2.5 right-2.5 flex items-center justify-between">
          <span className={`rounded-md px-2 py-0.5 text-[10px] font-mono text-white border-0 shadow-sm ${car.verified_clean ? 'bg-emerald-600/90' : 'bg-amber-600/90'}`}>
            {car.verified_clean ? '100% Clean' : `AI Inspected (${car.total_damages ?? 0} flags)`}
          </span>
          <span className="rounded-md bg-black/60 backdrop-blur-sm px-2 py-0.5 text-[11px] font-mono text-white">
            {car.year}
          </span>
        </div>
        <div className="absolute bottom-2.5 left-2.5 right-2.5 flex items-baseline justify-between text-white drop-shadow">
          <span className="text-lg font-bold font-mono">${car.price.toLocaleString()}</span>
          {car.city && <span className="text-xs font-sans opacity-90">{car.city}</span>}
        </div>
      </div>
      <div className="p-4 flex-1 flex flex-col justify-between gap-3">
        <div>
          <h3 className="font-semibold text-foreground text-sm leading-tight">{car.make} {car.model}</h3>
          {car.variant && (
            <p className="text-xs text-muted-foreground mt-0.5 truncate">{car.variant}</p>
          )}
        </div>
        <div className="grid grid-cols-3 gap-1 py-1.5 px-2 rounded-md bg-muted/40 text-muted-foreground text-xs font-mono text-center">
          <div>{car.mileage_km ? `${(car.mileage_km / 1000).toFixed(0)}k km` : 'Low km'}</div>
          <div>{car.fuel_type ?? 'Petrol'}</div>
          <div>{car.transmission?.slice(0, 4) ?? 'Auto'}</div>
        </div>
        <div className="pt-2 border-t border-border/50 flex items-center justify-between">
          <span className="text-[11px] font-mono text-muted-foreground">Verified Report</span>
          <Button asChild variant="ghost" size="sm" className="h-7 text-xs text-primary px-2">
            <Link to="/app/explore">View <ArrowUpRight className="size-3 ml-0.5" /></Link>
          </Button>
        </div>
      </div>
    </Card>
  )
}

export function DashboardOverview() {
  const { profile, user } = useAuthStore()
  const displayName = profile?.fullName ?? user?.email?.split('@')[0] ?? 'Member'

  const { data: myListingsData, isLoading: loadingListings } = useQuery({
    queryKey: listingKeys.mine(),
    queryFn: () => api.get('listings/mine').json<{ listings: ListingSummary[] }>().catch(() => ({ listings: [] })),
    staleTime: 30_000,
  })

  const { data: savedData, isLoading: loadingSaved } = useQuery({
    queryKey: marketplaceKeys.saved(),
    queryFn: () => api.get('saved-listings').json<{ saved_listings: unknown[] }>().catch(() => ({ saved_listings: [] })),
    staleTime: 30_000,
  })

  const { data: alertsData, isLoading: loadingAlerts } = useQuery({
    queryKey: marketplaceKeys.alerts(),
    queryFn: () => api.get('search-alerts').json<{ search_alerts: unknown[] }>().catch(() => ({ search_alerts: [] })),
    staleTime: 30_000,
  })

  const { data: feedData, isLoading: loadingFeed } = useQuery({
    queryKey: listingKeys.list({ status_filter: 'active', limit: 6 }),
    queryFn: () =>
      api
        .get('listings', { searchParams: { status_filter: 'active', limit: 6, sort: 'newest' } })
        .json<{ listings: ListingSummary[]; total: number }>()
        .catch(() => ({ listings: [], total: 0 })),
    staleTime: 60_000,
  })

  const myListings    = myListingsData?.listings ?? []
  const savedCount    = savedData?.saved_listings?.length ?? 0
  const alertsCount   = alertsData?.search_alerts?.length ?? 0
  const activeCount   = myListings.filter((l) => l.status === 'active').length
  const draftListings = myListings.filter((l) => l.status === 'draft')
  const feed          = feedData?.listings ?? []

  return (
    <div className="flex flex-col gap-6 p-6 max-w-7xl mx-auto w-full">
      {/* Greeting */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-border/60">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Welcome back, {displayName}</h1>
          <p className="text-xs text-muted-foreground mt-0.5">Real-time telemetry and marketplace operations.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button asChild variant="outline" size="sm" className="h-8 text-xs gap-1.5 rounded-lg">
            <Link to="/app/explore"><Compass className="size-3.5" /><span>Explore Inventory</span></Link>
          </Button>
          <Button asChild size="sm" className="h-8 text-xs gap-1.5 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90">
            <Link to="/app/sell"><Plus className="size-3.5" /><span>List a Car</span></Link>
          </Button>
        </div>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <KpiCard
          label="Saved Shortlist"
          href="/app/saved"
          linkLabel="View"
          loading={loadingSaved}
          value={savedCount}
          sub="Cars bookmarked for price alerts"
        />
        <KpiCard
          label="Active Alerts"
          href="/app/alerts"
          linkLabel="Manage"
          loading={loadingAlerts}
          value={alertsCount}
          sub="Automated intake triggers"
        />
        <KpiCard
          label="Garage Listings"
          href="/app/my-listings"
          linkLabel="Garage"
          loading={loadingListings}
          value={
            <>
              {activeCount}
              <span className="text-xs font-normal text-muted-foreground ml-1.5 font-sans">
                / {myListings.length} total
              </span>
            </>
          }
          sub={draftListings.length > 0 ? `${draftListings.length} draft pending review` : 'All listings active'}
        />
      </div>

      {/* AI Intake Pipeline */}
      <Card className="rounded-xl border border-border/70 bg-card p-5 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <ShieldCheck className="size-4 text-primary" />
              <h2 className="text-sm font-semibold text-foreground">Automated Inspection Pipeline</h2>
            </div>
            <p className="text-xs text-muted-foreground max-w-xl">
              Upload photos and Registration Certificate. Neural models perform defect segmentation, OCR entity extraction, and odometer verification in under 4 seconds.
            </p>
          </div>
          <div className="shrink-0">
            {draftListings.length > 0 ? (
              <Button asChild size="sm" variant="outline" className="h-8 text-xs rounded-lg">
                <Link to="/app/my-listings">
                  Resume Draft ({draftListings[0]?.make} {draftListings[0]?.model})
                </Link>
              </Button>
            ) : (
              <Button asChild size="sm" className="h-8 text-xs rounded-lg bg-primary text-primary-foreground hover:bg-primary/90">
                <Link to="/app/sell">Start AI Intake Scan</Link>
              </Button>
            )}
          </div>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4 pt-4 border-t border-border/50">
          {PIPELINE_GATES.map((g) => (
            <div key={g.id} className="rounded-lg border border-border/60 bg-muted/20 p-2.5 text-center">
              <div className="text-[10px] font-mono text-muted-foreground uppercase">{g.id}</div>
              <div className="text-xs font-semibold text-foreground mt-0.5">{g.label}</div>
              <div className="text-[10px] text-muted-foreground mt-0.5">{g.sub}</div>
            </div>
          ))}
        </div>
      </Card>

      {/* Verified Inventory Feed */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-foreground">Verified Inventory</h2>
            <p className="text-xs text-muted-foreground">
              Vehicles inspected through the automated pipeline with verified clean title.
            </p>
          </div>
          <Link to="/app/explore" className="text-xs text-primary hover:underline flex items-center">
            View all <ArrowUpRight className="size-3 ml-0.5" />
          </Link>
        </div>

        {loadingFeed ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <Card key={i} className="rounded-xl border border-border/70 bg-card overflow-hidden p-0 shadow-sm">
                <Skeleton className="h-44 w-full" />
                <div className="p-4 space-y-2">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-3 w-1/2" />
                </div>
              </Card>
            ))}
          </div>
        ) : feed.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {feed.map((car) => <CarCard key={car.id} car={car} />)}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-12 rounded-xl border border-dashed border-border/60 text-center gap-3">
            <p className="text-sm font-medium text-foreground">No active inventory yet</p>
            <p className="text-xs text-muted-foreground max-w-xs">
              Be the first to list a verified vehicle. Start the AI intake scan to get your car on the marketplace.
            </p>
            <Button asChild size="sm" className="mt-1 h-8 text-xs gap-1.5 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90">
              <Link to="/app/sell"><Plus className="size-3.5" /> List the first car</Link>
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
