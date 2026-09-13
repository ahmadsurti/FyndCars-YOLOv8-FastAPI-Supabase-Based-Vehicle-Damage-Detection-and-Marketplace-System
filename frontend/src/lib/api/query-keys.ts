export const listingKeys = {
  all: ['listings'] as const,
  lists: () => [...listingKeys.all, 'list'] as const,
  list: (filters: Record<string, unknown>) => [...listingKeys.lists(), filters] as const,
  mine: () => [...listingKeys.all, 'mine'] as const,
  details: () => [...listingKeys.all, 'detail'] as const,
  detail: (id: string) => [...listingKeys.details(), id] as const,
  assessment: (id: string) => [...listingKeys.detail(id), 'assessment'] as const,
  views: (id: string) => [...listingKeys.detail(id), 'views'] as const,
  catalog: {
    all: ['catalog'] as const,
    makes: () => [...listingKeys.catalog.all, 'makes'] as const,
    models: (make: string) => [...listingKeys.catalog.all, 'models', make] as const,
    variants: (make: string, model: string) => [...listingKeys.catalog.all, 'variants', make, model] as const,
  },
}

export const queueKeys = {
  all: ['queue'] as const,
  list: (params?: { limit?: number; offset?: number }) => [...queueKeys.all, 'list', params] as const,
  audit: (params?: { limit?: number; offset?: number }) => [...queueKeys.all, 'audit', params] as const,
}

export const adminKeys = {
  all: ['admin'] as const,
  stats: () => [...adminKeys.all, 'stats'] as const,
  users: (params?: { limit?: number; offset?: number }) => [...adminKeys.all, 'users', params] as const,
  audit: (params?: { limit?: number; offset?: number }) => [...adminKeys.all, 'audit', params] as const,
  subscriptions: () => [...adminKeys.all, 'subscriptions'] as const,
}

export const marketplaceKeys = {
  saved: () => ['saved-listings'] as const,
  messages: (listingId?: string) => ['messages', listingId] as const,
  unreadCount: () => ['messages', 'unread-count'] as const,
  reviews: (sellerId: string) => ['sellers', sellerId, 'reviews'] as const,
  alerts: () => ['search-alerts'] as const,
  alertMatches: (alertId: string) => ['search-alerts', alertId, 'matches'] as const,
  subscriptions: () => ['subscriptions'] as const,
}
