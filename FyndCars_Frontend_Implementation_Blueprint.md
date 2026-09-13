# FyndCars Frontend — Complete Implementation Blueprint

**Status:** Implementation-ready architecture specification  
**Scope:** Greenfield React frontend for the existing FyndCars FastAPI + Supabase backend  
**Target:** Production-minded marketplace MVP engineered to a senior-level frontend standard

> **Audit revision:** All 44 findings from the Backend Cross-Check Audit (C1–C10, L1–L17, D1–D10, M1–M7) have been applied to this document. Every route reference, field constraint, API semantic, and state machine shape reflects the actual backend source.

---

## 0. Purpose and Non-Negotiable Context

FyndCars already has the backend and database. The frontend is a greenfield implementation and must be built around the existing backend contract rather than inventing a parallel application model.

The backend exposes FastAPI REST endpoints backed by Pydantic v2, Supabase Auth/Storage/PostgreSQL, YOLOv8 damage detection, Docling RC extraction, Gemma multimodal verification through OpenRouter, deterministic policy triage, RAG-assisted expert commentary, marketplace messaging, search alerts, subscriptions, reviews, and administrative review workflows.

The frontend therefore needs to be:

- strongly typed against FastAPI OpenAPI;
- runtime-safe only where compile-time TypeScript cannot provide safety;
- server-state-first rather than global-store-first;
- cancellation-aware for large uploads and long AI requests;
- explicit about error classes and retry semantics;
- feature-oriented rather than page-oriented or generic-layer-oriented;
- strict about dependency growth;
- testable against real local FastAPI/Supabase behavior;
- resilient to realtime disconnections and partial network failure.

### Governing backend facts

The backend has three roles (`buyer`, `seller`, `admin`), a synchronous one-shot intake pipeline of approximately 8–20 seconds, 38 active REST endpoints, Supabase Auth JWTs, private storage buckets, and an API boundary where core domain operations go through FastAPI rather than direct Supabase table access.

The seller intake accepts 3–15 vehicle images plus one RC document. The backend enforces a **25MB per-image cap** at the intake endpoint. The backend performs quality gating, Docling extraction, VLM verification, YOLO assessment, and draft creation. The resulting listing may then enter review/edit, submission, and policy triage states.

The buyer marketplace uses offset pagination and multi-parameter filtering. **`GET /listings` returns a plain array with no total count field — numbered pagination is impossible; infinite scroll is the only viable pattern.** Messaging is listing-scoped and uses Supabase Realtime for message delivery. The admin surface contains queue review, audit, document verification, overrides, users, and KPI data.

**Known backend limitations:**
- Storage objects uploaded during intake are NOT cleaned up on intake failure or browser cancellation. The rollback only deletes the DB row. Do not imply to users that cancellation cleans server-side storage.
- `GET /admin/stats` fetches all listing status rows unbounded and will become slow at scale. Use a staleTime of 10+ minutes for this query.
- `POST /assess` is a **single-image stateless diagnostic endpoint** — it creates no draft listing, runs no Docling/VLM, and persists nothing. It is NOT the intake pipeline.

---

# 1. Governing Philosophy

These rules override convenience, trendiness, and generic framework habits.

## Rule 1 — Backend contract is compile-time truth

FastAPI/Pydantic/OpenAPI is the authoritative source for standard API response and request contracts.

`openapi-typescript` generates the frontend contract artifact. The frontend must not manually recreate ordinary backend response models.

Zod is not a second API-schema authority.

## Rule 2 — Server state and client state are different problems

TanStack Query owns server state: listings, assessments, queue data, messages, unread counts, reviews, search-alert matches, subscriptions, and other API-backed data.

Zustand owns only deliberately global client state: transient session metadata, demo role/UI mode, and the intake workflow state machine.

Do not place server responses into Zustand merely because they need to be accessed by multiple components.

## Rule 3 — Runtime validation belongs at genuinely dynamic boundaries

Use compile-time generated OpenAPI types by default.

Use Zod for:

- form/presentation input validation;
- TanStack Router search-parameter validation;
- high-risk dynamic JSON structures such as VLM/JSONB payloads;
- normalized external error bodies where runtime shape must be defended.

Do not recreate every OpenAPI response as a Zod schema.

## Rule 4 — Dependencies must solve a demonstrated problem

Before adding a dependency, attempt the problem in this order:

1. Native browser API.
2. Native React capability.
3. Existing TanStack/ Zustand/ky/project infrastructure.
4. Small local utility.
5. New dependency only when the previous options are meaningfully worse.

Runtime dependency budget: **15 core foundational runtime packages maximum**, with Radix primitives installed only when an active feature needs them.

## Rule 5 — Timeless SOTA beats novelty

A library is not selected because it is fashionable. It is selected because it solves a real FyndCars problem better than the simpler alternative and can be maintained for years by a senior engineer.

Exact package versions are pinned. Major upgrades are deliberate, audited, tested changes rather than automatic churn.

---

# 2. Folder & Module Architecture

Use a feature-oriented architecture. Pages/routes compose feature modules; features own domain behavior; shared infrastructure stays intentionally small.

```text
fynd(cars)/
├── backend/
├── supabase/
├── openapi.json
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── app/
│   │   │   ├── providers.tsx
│   │   │   ├── router.tsx
│   │   │   ├── error-boundary.tsx
│   │   │   └── bootstrap.tsx
│   │   │
│   │   ├── routes/
│   │   │   ├── __root.tsx
│   │   │   ├── index.tsx
│   │   │   ├── auth/
│   │   │   │   ├── login.tsx
│   │   │   │   ├── register.tsx
│   │   │   │   └── route.tsx
│   │   │   ├── listings/
│   │   │   │   ├── index.tsx
│   │   │   │   ├── $listingId.tsx
│   │   │   │   └── route.tsx
│   │   │   ├── seller/
│   │   │   │   ├── dashboard.tsx
│   │   │   │   └── listings/
│   │   │   │       └── new.tsx
│   │   │   ├── messages.tsx
│   │   │   ├── saved-listings.tsx
│   │   │   ├── search-alerts.tsx
│   │   │   └── admin/
│   │   │       ├── dashboard.tsx
│   │   │       ├── queue.tsx
│   │   │       ├── users.tsx
│   │   │       ├── documents.tsx
│   │   │       └── audit.tsx
│   │   │
│   │   ├── features/
│   │   │   ├── auth/
│   │   │   │   ├── api/
│   │   │   │   ├── hooks/
│   │   │   │   ├── components/
│   │   │   │   ├── auth.types.ts
│   │   │   │   └── auth.store.ts
│   │   │   │
│   │   │   ├── listings/
│   │   │   │   ├── api/
│   │   │   │   │   ├── listings.service.ts
│   │   │   │   │   ├── listings.queries.ts
│   │   │   │   │   └── listings.mutations.ts
│   │   │   │   ├── components/
│   │   │   │   ├── schemas/
│   │   │   │   ├── listing.types.ts
│   │   │   │   └── listing.utils.ts
│   │   │   │
│   │   │   ├── inspection/
│   │   │   │   ├── api/
│   │   │   │   ├── components/
│   │   │   │   ├── schemas/
│   │   │   │   └── inspection.types.ts
│   │   │   │
│   │   │   ├── intake/
│   │   │   │   ├── api/
│   │   │   │   ├── components/
│   │   │   │   ├── schemas/
│   │   │   │   ├── workers/
│   │   │   │   ├── intake.store.ts
│   │   │   │   ├── intake.types.ts
│   │   │   │   └── intake.utils.ts
│   │   │   │
│   │   │   ├── marketplace/
│   │   │   ├── messaging/
│   │   │   │   ├── api/
│   │   │   │   ├── components/
│   │   │   │   ├── realtime/
│   │   │   │   └── messaging.types.ts
│   │   │   ├── admin/
│   │   │   ├── search-alerts/
│   │   │   ├── billing/
│   │   │   └── reviews/
│   │   │
│   │   ├── lib/
│   │   │   ├── api/
│   │   │   │   ├── schema.d.ts
│   │   │   │   ├── client.ts
│   │   │   │   ├── errors.ts
│   │   │   │   ├── query-keys.ts
│   │   │   │   └── query-options.ts
│   │   │   ├── auth/
│   │   │   │   ├── session-manager.ts
│   │   │   │   └── auth-events.ts
│   │   │   ├── supabase/
│   │   │   │   └── client.ts
│   │   │   ├── validation/
│   │   │   │   └── pagination.schema.ts
│   │   │   ├── utils/
│   │   │   └── constants/
│   │   │
│   │   ├── types/
│   │   │   ├── domain.ts
│   │   │   ├── ids.ts
│   │   │   └── errors.ts
│   │   │
│   │   ├── components/
│   │   │   ├── ui/
│   │   │   ├── layout/
│   │   │   └── feedback/
│   │   │
│   │   └── styles/
│   │       ├── globals.css
│   │       └── claymorphism-green.css
│   │
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── biome.json
│   ├── playwright.config.ts
│   └── package.json
│
└── package.json
```

### Ownership rules

`routes/` owns route composition, route-level loading/guards, and URL state. It must not contain business logic that belongs inside features.

`features/*/api/*.service.ts` owns domain HTTP calls.

`features/*/api/*.queries.ts` owns `queryOptions` factories and cache behavior.

`features/*/api/*.mutations.ts` owns mutations and their explicit invalidation rules.

`features/*/schemas/` owns feature-local Zod schemas that are not OpenAPI response schemas.

`lib/api/` owns cross-feature transport infrastructure.

`components/ui/` contains reusable visual primitives, not domain components.

---

# 3. Dependency Manifest

## Core runtime

The architecture targets a deliberately small runtime surface:

```text
react
react-dom
@tanstack/react-router
@tanstack/react-query
zustand
react-hook-form
zod
openapi-typescript-generated types (zero runtime)
ky
@supabase/supabase-js
@sentry/react
lucide-react
@hookform/resolvers
clsx
+ tailwind merge utility if actually needed
+ Radix primitives only when used
```

The exact final runtime count must remain within the agreed **15 foundational-package budget**, excluding on-demand Radix primitives.

### Billing SDK — **LOCKED: Razorpay**

Razorpay is the payment SDK for FyndCars. This decision is final.

**Actual backend payment flow (sourced from `routes/marketplace.py`):**

```
Step 1 — POST /subscriptions
  Body: { plan_type, amount_paid, currency, valid_until? }
  Returns: subscription object with id, status: "pending"
  ↓
Step 2 — Open Razorpay checkout.js modal (client-side, using Razorpay public key)
  Razorpay creates the order client-side. No FastAPI order-creation endpoint exists.
  ↓
Step 3 — PATCH /subscriptions/{subscription_id}/confirm
  Body: { razorpay_order_id, razorpay_payment_id, razorpay_signature }
  Backend verifies HMAC-SHA256 signature using RAZORPAY_KEY_SECRET
  Sets status: "active" on success
```

> **There is NO `POST /subscriptions/checkout` or FastAPI order-creation endpoint.** The backend does NOT call the Razorpay API to create orders. Razorpay order creation happens client-side via the checkout.js SDK using the Razorpay public key.

- Load the Razorpay checkout script **lazily** — inject `<script src="https://checkout.razorpay.com/v1/checkout.js">` only when the user enters the billing flow. Never load it on app startup.
- Razorpay is **not** added to `dependencies`. It is a runtime-injected external script, not an npm package.
- The billing feature module owns the lazy injection logic entirely. No other module touches Razorpay.
- `PATCH /subscriptions/{id}/confirm` is the server-verification step. The frontend POSTs `razorpay_order_id`, `razorpay_payment_id`, and `razorpay_signature` received from the Razorpay callback. The backend does HMAC verification.
- In production, `razorpay_signature` is **required** — the backend will reject with 400 if missing when `RAZORPAY_KEY_SECRET` is set.
- `MUTATION` timeout class applies to both `/subscriptions` POST and `/subscriptions/{id}/confirm` PATCH.
- Never automatically retry either step.

## Development tooling

```text
vite
@vitejs/plugin-react
babel-plugin-react-compiler
eslint
eslint-plugin-react-compiler
@biomejs/biome
typescript
vitest
@testing-library/react
playwright
openapi-typescript
@sentry/vite-plugin
tailwindcss
@tailwindcss/vite
```

Build tooling and code-generation tools belong in `devDependencies`.

### Package installation rules

Do not install every Radix primitive in advance.

Do not add Axios, Redux Toolkit, Jotai, Recoil, XState, tRPC, oRPC, AG Grid, Cypress, Stripe, a second icon set, another CSS framework, or another form library unless an explicit architectural decision later reverses an existing decision.

Do not add `razorpay` as an npm package. The Razorpay SDK is a lazily injected browser script.

---

# 4. TypeScript Configuration

Use a strict, bundler-oriented configuration.

```json
{
  "compilerOptions": {
    "target": "ES2023",
    "lib": ["DOM", "DOM.Iterable", "ES2023"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "strictNullChecks": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitOverride": true,
    "noPropertyAccessFromIndexSignature": true,
    "noFallthroughCasesInSwitch": true,
    "forceConsistentCasingInFileNames": true,
    "isolatedModules": true,
    "skipLibCheck": true
  }
}
```

### Type rules

- `any` is forbidden in application code.
- Prefer `unknown` and narrow it.
- Use `interface` for object shapes when appropriate.
- Use `type` for unions, mapped types, branded primitives, and type composition.
- Prefer generated API types over duplicate manual API models.
- Use branded IDs only for important domain identifiers.
- Use discriminated unions for lifecycle and error states.
- Use `satisfies` where it improves literal preservation while enforcing constraints.
- Do not perform advanced type-level gymnastics unless they eliminate a real class of bugs.
- Public domain functions should have intentionally clear input/output types.

---

# 5. API Contract Layer

## 5.1 OpenAPI generation

FastAPI remains the API contract authority.

Root workflow:

```text
backend source
    ↓
python backend/scripts/dump_openapi.py
    ↓
/openapi.json committed
    ↓
openapi-typescript
    ↓
frontend/src/lib/api/schema.d.ts committed
```

Commands:

```bash
pnpm openapi:dump
pnpm codegen:api
```

CI must regenerate the OpenAPI artifact and fail if the committed artifact differs.

The generated `schema.d.ts` is machine-owned. Do not hand-edit it.

> **D1 — `dump_openapi.py` does not exist yet.** The Phase 2 codegen workflow requires this script to be created as part of Phase 2. Minimal implementation:
> ```python
> import json, sys
> sys.path.insert(0, str(__file__).rsplit('/', 2)[0] + '/backend')
> from api import app
> print(json.dumps(app.openapi(), indent=2))
> ```

## 5.2 Backend schema discipline

Where practical, use typed Pydantic models and literal/enum constraints rather than broad `dict` or unrestricted semantic strings.

The backend should expose concrete models for structures such as damage statistics, decision traces, statuses, and assessment decisions so that TypeScript receives useful literal unions rather than `string` or `Record<string, unknown>` everywhere.

## 5.3 Three-layer API architecture

```text
OpenAPI types
     ↓
ky transport + auth + error normalization
     ↓
domain service functions
     ↓
TanStack Query queryOptions / mutation hooks
     ↓
React components
```

### Transport layer

`src/lib/api/client.ts` owns:

- base API URL;
- Supabase session access;
- Authorization header attachment;
- semantic retries;
- timeout policy;
- AbortSignal support;
- HTTP error normalization;
- no business-domain logic.

### Service layer

`src/features/*/api/*.service.ts` owns HTTP calls for a domain.

Example responsibility:

```ts
async getById(id: ListingId, signal?: AbortSignal): Promise<ListingDetail>
```

Service functions must:

- accept optional `AbortSignal`;
- use the typed API contract;
- normalize transport errors through the central API layer;
- contain zero TanStack Query knowledge;
- never call `queryClient`;
- never manipulate React state.

### Query/mutation integration

Only the query/mutation layer knows about TanStack Query.

---

## 5.4 Request timeout matrix

| Class | Duration | Examples | Retry |
|---|---:|---|---|
| FAST | 5s | health, policy, catalog, unread count | 1 safe retry |
| STANDARD | 15s | listings, detail, messages, `/queue`, `/admin/stats` | GET-only retry |
| MUTATION | 30s | listing edits, queue overrides, reviews, `/assess` (diagnostic) | no automatic retry |
| INTAKE_AI | 90s | `POST /listings/auto-extract` | no automatic retry |

> **C2 / Audit fix:** `POST /assess` is a single-image stateless YOLO diagnostic endpoint. It is **MUTATION/STANDARD** class, not INTAKE_AI. Only `POST /listings/auto-extract` is the real intake pipeline and belongs in INTAKE_AI.

Timeout policy must be selected intentionally by endpoint class rather than inferred blindly from HTTP method.

Timeout and user cancellation are distinct states.

---

## 5.5 Retry rules

Safe GET queries may retry a small number of times on transient failures such as:

- 408
- 429
- 500
- 502
- 503
- 504
- network interruption

Potentially idempotent mutations get no blind automatic retry unless their semantics prove retry-safe.

Never automatically retry:

- `POST /listings/auto-extract` (the real intake pipeline);
- listing submission;
- listing sale finalization;
- subscriptions/payment confirmation;
- `POST /queue/{listing_id}/override` (admin override — idempotency not guaranteed);
- other operations whose repeated execution could create costly or irreversible side effects.

---

## 5.6 Single-flight authentication refresh

Supabase is the sole token persistence authority.

The API transport must never maintain a separate token cache in Zustand/localStorage.

When concurrent requests encounter expired authentication, all waiters join the same in-flight `refreshPromise`.

Conceptual flow:

```text
request
  ↓
read current Supabase session
  ↓
401?
  ├─ no → return response
  └─ yes
      ↓
  join refreshPromise
      ↓
  refresh once
      ↓
  retry original request once
      ↓
  refresh failure → session invalidation + auth boundary
```

Do not allow refresh loops.

Do not recursively retry a request forever.

---

## 5.7 Error hierarchy

Errors must distinguish transport failures from HTTP/API failures.

Recommended application model:

```text
AppError
├── HttpApiError
├── NetworkError
├── TimeoutError
├── AbortError
└── AuthError
```

All errors should support discriminated narrowing.

Example:

```ts
export type AppError =
  | {
      kind: 'HTTP';
      status: number;
      code: string;
      message: string;
      details?: Record<string, string | string[]>;
    }
  | {
      kind: 'NETWORK';
      message: string;
      isOffline: boolean;
    }
  | {
      kind: 'TIMEOUT';
      durationMs: number;
      message: string;
    }
  | {
      kind: 'ABORT';
      reason: string;
    }
  | {
      kind: 'AUTH';
      code: 'SESSION_EXPIRED' | 'UNAUTHORIZED' | 'FORBIDDEN';
      message: string;
    };
```

Actual implementation may use classes internally, but the application boundary must preserve discriminated, type-safe handling.

### Runtime parsing of error bodies

Error payloads are external data and may be malformed. Parse them safely with Zod/unknown narrowing before accessing fields.

Never write:

```ts
const errorData: any = ...
```

---

# 6. Query Architecture

## 6.1 `queryOptions` is mandatory

Queries must not be declared inline in arbitrary components.

Every meaningful query gets an exported factory:

```ts
export const listingDetailQueryOptions = (id: ListingId) =>
  queryOptions({
    queryKey: listingKeys.detail(id),
    queryFn: ({ signal }) => listingsService.getById(id, signal),
    staleTime: 5 * 60_000,
  });
```

The factory owns:

- query key;
- query function;
- stale time;
- cache behavior;
- retry semantics when specialized;
- `select` behavior where justified.

## 6.2 Query key factories

Ad-hoc query key arrays are forbidden.

Use centralized factories.

```ts
export const listingKeys = {
  all: ['listings'] as const,
  lists: () => [...listingKeys.all, 'list'] as const,
  list: (filters: ListingFilterParams) =>
    [...listingKeys.lists(), canonicalizeParams(filters)] as const,
  details: () => [...listingKeys.all, 'detail'] as const,
  detail: (id: ListingId) => [...listingKeys.details(), id] as const,
  assessment: (id: ListingId) => [...listingKeys.detail(id), 'assessment'] as const,
};
```

## 6.3 Canonical parameter normalization

Filter parameters must be normalized before query-key creation:

- sort object keys;
- remove `undefined`;
- remove `null` where semantically equivalent to omission;
- remove empty-string placeholders where appropriate;
- preserve meaningful falsy values such as `0`;
- use a dedicated normalized filter type rather than unsafe `as T` shortcuts where possible.

The canonical filter representation must be reused for API query-string serialization to avoid cache/request identity drift.

## 6.4 Mutation invalidation

Each mutation declares its exact invalidation consequences.

Example:

```ts
onSuccess: (_, id) => {
  queryClient.invalidateQueries({ queryKey: listingKeys.detail(id) });
  queryClient.invalidateQueries({ queryKey: listingKeys.lists() });
  queryClient.invalidateQueries({ queryKey: queueKeys.all });
}
```

Services never invalidate caches.

## 6.5 Offset pagination adapter

The backend currently uses `limit` + `offset`.

The frontend should hide offset arithmetic inside a reusable adapter such as:

```text
useOffsetInfiniteQuery
```

Components consume pages rather than manually calculating offsets.

A terminal empty fetch is acceptable under the current API contract when the last page contains exactly the page size.

> **D4 — No total count in `GET /listings`.** The response is a plain array with no `total`, `count`, or cursor. Numbered pagination ("Page 5 of 23") is architecturally impossible under the current backend contract. **Infinite scroll is the only viable pagination pattern for the marketplace feed.** If the backend later adds pagination metadata, the adapter should migrate without changing consuming components.

## 6.6 Route preloading

Core data routes should call `queryClient.ensureQueryData(...)` through TanStack Router loaders.

Static presentation/auth routes do not need data loaders unless they later gain meaningful server state.

---

# 7. State Management

## 7.1 Zustand responsibilities

Zustand is deliberately narrow.

Allowed global client state:

- transient auth metadata (`userId`, `role`, `email`, `isAuthenticated`);
- demo role mode if needed;
- intake workflow state machine;
- other state that is genuinely global, client-only, and not server-owned.

Do not store API response collections in Zustand.

Do not duplicate Supabase tokens in Zustand or localStorage.

Do not persist File/Blob/ArrayBuffer data.

## 7.2 Intake state machine

The intake flow is represented by a discriminated union.

```ts
export type IntakeState =
  | { step: 'IDLE' }
  | {
      step: 'SELECTING_FILES';
      photos: File[];
      rcDoc: File | null;
    }
  | {
      step: 'PREPROCESSING';
      progress: number;
    }
  | {
      step: 'AI_INGESTION_RUNNING';
      elapsedMs: number;
    }
  | {
      step: 'REVIEW_DOSSIER';
      listingId: ListingId;
      /**
       * Raw intake response from POST /listings/auto-extract.
       * This is an AGGREGATED SUMMARY, not a DamageDetection array.
       * Shape: { listing_id, extracted_specs, damage_assessment: { total_damages,
       * highest_severity, estimated_repair_cost, decision }, verification_verdict,
       * vlm_discrepancies, missing_fields }.
       *
       * C3/L1 audit fix: individual bounding-box details require a SEPARATE call
       * to GET /listings/{id}/assessment after intake completes.
       *
       * L2 audit fix: missing_fields is a hardcoded constant
       * ["price", "city", "transmission", "description"] — always show all four
       * fields in the review form regardless of this value.
       *
       * L3/L4/L5/L6 audit fix: transmission=null, city="", price=1.0, body_type=null
       * are backend constants — never pre-populate these as "AI-extracted" values.
       * Always show them as required blank inputs in the review form.
       *
       * L7 audit fix: color may be null if VLM degrades. Pre-populate if present;
       * never require it as a primary input.
       */
      intakeResponse: IntakeApiResponse;
      /** Populated by the separate GET /listings/{id}/assessment call. */
      assessment: ListingAssessment | null;
    }
  | {
      step: 'SUBMITTED';
      finalStatus: 'active' | 'pending' | 'escalated';
    }
  | {
      step: 'ERROR';
      error: AppError;
    };

/** Aggregated summary returned by POST /listings/auto-extract */
export interface IntakeApiResponse {
  listing_id: string;
  extracted_specs: ExtractedSpecs;
  damage_assessment: {
    total_damages: number;
    highest_severity: string;
    estimated_repair_cost: number;
    decision: 'AUTO_APPROVE' | 'HUMAN_REVIEW' | 'ESCALATE';
  };
  verification_verdict: unknown;
  vlm_discrepancies: unknown[];
  /** Hardcoded constant: always ["price","city","transmission","description"] */
  missing_fields: string[];
}
```

The store must expose explicit transition actions rather than arbitrary mutation of state.

### Reset rules

- New intake starts from `IDLE`.
- Successful submission moves to `SUBMITTED`.
- The intake store is reset only after the success state has been rendered/acknowledged by the flow and no required local recovery data remains.
- Navigating away before completion must preserve only the minimum transient state needed for deliberate cancellation/recovery; do not persist raw File objects.
- Errors preserve enough state to permit manual retry/review rather than silently discarding user work.

## 7.3 Supabase session authority

`@supabase/supabase-js` owns the real auth session.

The frontend should have one session-manager integration responsible for:

- initial session resolution;
- auth-state event subscription;
- refresh coordination;
- derived metadata synchronization into Zustand;
- logout/session invalidation.

Other modules consume derived auth state instead of inventing parallel session listeners.

### L16 — Role field path (security-critical)

**Role must be read from `app_metadata.role`, NOT `user_metadata.role`.**

```ts
// CORRECT
const role = session.user.app_metadata?.role ?? 'buyer';

// WRONG — user_metadata is user-editable and is a security misread
const role = session.user.user_metadata?.role ?? 'buyer'; // NEVER DO THIS
```

`user_metadata` is writable by the user. Only `app_metadata` is backend-controlled and reflects the actual role assigned by the platform.

### L17 — Dev demo token format

The backend resolves demo roles by string-searching the token value:

```python
role = "admin" if "admin" in token else "seller" if "seller" in token else "buyer"
```

Demo Role Switcher tokens must contain the role word literally. `Bearer demo-admin-token` → admin. `Bearer demo-seller-token` → seller. `Bearer demo-token` → buyer. Token format must be deterministic and tested.

---

# 8. Routing Architecture

Use TanStack Router as the routing system.

Routes are file-oriented and should mirror domain/navigation boundaries.

Core route groups:

```text
/auth/*
/listings
/listings/$listingId
/seller/dashboard
/seller/listings/new
/messages
/saved-listings
/search-alerts
/admin/dashboard
/admin/queue
/admin/users
/admin/documents
/admin/audit
```

> **C4 / C6 / D10 Audit fixes:**
> - The admin queue **data endpoint** is `/queue` (not `/admin/queue`). The frontend *route* `/admin/queue` is fine as a URL, but all service calls must target the `/queue` API prefix.
> - There is **no `GET /admin/documents` backend endpoint**. The `/admin/documents` frontend route must be implemented as a sub-view of the queue or listing detail (rendering `listing_documents` embedded in the queue/listing response). Do not call `api.get('admin/documents')` — it will 404.
> - `GET /admin/audit` (full platform log, 200-row limit) and `GET /queue/audit-log` (queue-specific log, 100-row limit, different joins) are **two separate endpoints** requiring two separate service functions and query factories.

## Route responsibilities

Each protected route may declare role requirements.

Authentication failure should redirect unauthenticated users to:

```text
/auth/login?redirect=<original-path>
```

Authenticated but unauthorized users should render an explicit access-denied boundary rather than redirecting recursively.

## URL state

Marketplace filters are URL state.

Use `validateSearch` with Zod to parse incoming search parameters.

Normalize them into a clean `ListingFilterParams` domain object before passing them to TanStack Query.

The API layer must not know about raw router-search representation.

### D2 — `features` filter serialization

The backend `features` query parameter is a **comma-separated string**, not a URL array:

```
✅ GET /listings?features=sunroof,hatchback
❌ GET /listings?features[]=sunroof&features[]=hatchback
```

The `ListingFilterParams` Zod schema must serialize a `string[]` to a joined comma string before passing to ky.

### D3 — `sort` valid literals

The `sort` parameter accepts exactly **6 values**. Any other value causes HTTP 400:

```ts
type SortOption = 'newest' | 'oldest' | 'price_asc' | 'price_desc' | 'year_desc' | 'mileage_asc';
```

The `ListingSearchParams` Zod schema must restrict to this exact union. The sort selector UI must use these keys.

---

# 9. Realtime Layer

## 9.1 Hard boundary

React components must never create their own raw Supabase Realtime subscriptions.

Subscriptions belong to feature-specific realtime adapters.

```text
Supabase Realtime
       ↓
feature realtime adapter
       ↓
normalize / dedupe / authorization assumptions
       ↓
TanStack Query cache
       ↓
React components
```

## 9.2 Chat behavior

### L8 — Two separate message data flows

Messages have two distinct data paths that must both be implemented:

1. **Initial load:** `GET /messages?listing_id=X` through FastAPI — returns sorted, deduplicated history. This is the TanStack Query initial population.
2. **Live delivery:** Supabase Realtime CDC INSERT on `public.messages` — bypasses FastAPI entirely. The realtime adapter appends events directly to the TanStack Query cache.

For message INSERT events:

1. identify the relevant listing-scoped thread;
2. validate/narrow the external event payload;
3. **deduplicate by `message.id` — this is load-bearing, not optional** (see L9 below);
4. append through `queryClient.setQueryData`;
5. update related unread/message indicators as appropriate.

Message cache must never contain duplicate IDs.

### L9 — Realtime deduplication is load-bearing

`GET /messages` deduplicates within a single response server-side. However, when TanStack Query refetches full history (e.g., on window focus), it returns all messages again. Without frontend deduplication by `message.id`, a realtime-append followed by a refetch will produce duplicates in the cache. The deduplication layer is not optional.

## 9.3 Queue/listing status behavior

For listing status changes and review queue events, prefer targeted invalidation rather than complex cache patching.

Reason: listing/assessment/admin records are multi-entity and the backend remains the canonical state.

## 9.4 Disconnect fallback

When an active realtime channel becomes disconnected/timed out:

- detect the degraded connection state;
- enable a short polling fallback for the active view;
- stop polling when realtime reconnects;
- avoid duplicated append events during the transition.

The fallback must not become a permanent background poll for inactive screens.

## 9.5 Security requirements

Realtime subscriptions must respect Supabase RLS and channel authorization.

Only records/channels authorized for the current user should be observable.

Frontend code is not considered the security boundary; database policies and channel authorization are authoritative.

---

# 10. Image Upload Pipeline

The seller intake accepts up to 15 large images plus an RC document.

## Processing architecture

```text
User File
   ↓
original File preserved
   ↓
Web Worker
   ↓
OffscreenCanvas resize/encode
   ↓
optimized Blob
   ↓
multipart request
   ↓
FastAPI
```

## Worker rules

- Never mutate the logical original file.
- Keep processing off the main thread where browser support allows.
- Use the agreed maximum dimension/quality configuration as an empirically validated starting point.
- Fall back safely for browsers without `OffscreenCanvas` support.
- Never assume compression preserves model accuracy without benchmark evidence.

## Abort semantics

Every domain service that performs network work accepts an optional `AbortSignal`.

Cancellation should travel through:

```text
UI cancellation
   ↓
AbortController.abort()
   ↓
worker/request cancellation where supported
   ↓
ky
   ↓
FastAPI request termination as far as transport semantics permit
```

### Timeout is not cancellation

Timeout means the operation exceeded its allowed duration.

Abort means the user/application intentionally cancelled it.

The application must distinguish these states so cancellation is not presented as a server failure.

## Upload retry rule

Do not blind-retry the complete autonomous intake upload. Preserve user-selected inputs and make any repeat submission deliberate.

---

# 11. UI & Styling Infrastructure

This section is intentionally implementation infrastructure, not product design.

## 11.1 Styling stack

Use Tailwind CSS v4 plus the existing `claymorphism-green.css` design tokens.

Keep tokens centralized.

Do not introduce a second CSS framework.

Do not create parallel ad-hoc token systems inside feature folders.

## 11.2 Radix / shadcn rules

Use shadcn-distributed components with Radix primitives where the feature actually needs them.

Install primitives on demand.

Do not batch-install the entire Radix ecosystem.

Domain components should compose shared primitives instead of forking primitives repeatedly.

## 11.3 Icons

Use `lucide-react` as the single icon system.

Do not mix icon libraries or add arbitrary unmanaged icon bundles.

## 11.4 Accessibility

Accessibility belongs in primitives, interactions, and keyboard behavior from the beginning rather than as a final polish task.

Radix handles interaction primitives; feature components must still provide correct labels, descriptions, focus handling, and semantic content.

---

# 12. Testing Strategy

Testing is behavior-focused and contract-aware.

## 12.1 Vitest unit tests

Use for deterministic logic such as:

- canonical query parameters;
- pagination adapter behavior;
- retry classification;
- error normalization;
- branded/domain utility functions;
- image metadata calculations;
- state-transition helpers.

Do not test private implementation details merely because they exist.

## 12.2 Type-level tests

Use `expectTypeOf` for high-value compile-time contracts, including:

- generated API response types;
- domain aliases;
- branded IDs;
- query option output typing;
- TanStack Router search parameter typing;
- important generic utility boundaries.

The purpose is to detect accidental widening to `string`, `unknown`, or `any` where precision matters.

## 12.3 Testing Library integration tests

Test user-visible behavior:

- loading states;
- error states;
- form validation;
- role-based access states;
- query-driven rendering;
- realtime-driven UI changes;
- cancellation behavior;
- intake state transitions.

Do not assert Zustand internals or private component state.

## 12.4 Playwright E2E

Default environment:

- local frontend;
- local FastAPI;
- local/test Supabase;
- demo/test identities;
- configurable `E2E_BASE_URL` for staging smoke tests.

Production credentials are prohibited.

Never use:

- production Supabase service-role keys;
- production Razorpay credentials;
- production user accounts;
- production data in automated browser tests.

## 12.5 Required fixture matrix

The test fixture suite must cover at minimum:

### Roles

- buyer;
- seller;
- admin.

### Intake

- successful intake;
- pixel-quality rejection;
- incomplete/missing extracted fields;
- VLM degraded/fallback output;
- YOLO damage result;
- final AUTO_APPROVE;
- HUMAN_REVIEW;
- ESCALATE;
- user cancellation;
- timeout.

### Governance

- admin queue entry;
- approve override;
- reject override;
- mandatory audit reason validation;
- unauthorized access to admin endpoints.

### Marketplace

- filter/search;
- pagination/infinite loading;
- save/unsave;
- message send;
- unread state;
- realtime disconnect fallback;
- verified review flow.

### Billing

- checkout initiation;
- successful confirmation;
- rejected/failed payment path.

---

# 13. Observability

## 13.1 Sentry

Use `@sentry/react` for frontend exception monitoring and appropriate performance telemetry.

Use `@sentry/vite-plugin` to upload source maps during release builds.

Source maps remain hidden from public asset serving.

## 13.2 PII policy

The following must never be included in telemetry payloads or breadcrumbs:

- registration number;
- plate number;
- chassis VIN;
- engine number;
- raw message bodies;
- access tokens;
- refresh tokens;
- image base64 data;
- document contents;
- user phone numbers;
- other raw legal/identity document fields.

Do not blindly send arbitrary `ApiError.details` to Sentry. Scrub before capture.

### L10 / D5 — Admin endpoint PII coverage

`GET /queue` embeds seller `full_name` and `email` in every row. `GET /admin/users` includes `phone`. **Sentry PII scrubbing must explicitly cover these admin endpoint response shapes**, not only listing/VLM payloads. The scrubbing policy applies to any telemetry breadcrumb that might capture admin API responses.

## 13.3 Error classification

Preserve the distinction between:

- API/HTTP failure;
- network failure;
- timeout;
- user cancellation;
- authentication/session failure.

Telemetry should retain the classification while excluding sensitive payloads.

---

# 14. Implementation Phases

The frontend must be implemented in dependency order. Do not jump forward into downstream features before their infrastructure gates are satisfied.

## Phase 0 — Repository and tooling foundation

### Build

Create:

- root pnpm workspace;
- `frontend/` application;
- React 19 + Vite;
- TypeScript strict configuration;
- Tailwind v4;
- Biome;
- React Compiler integration;
- baseline directory structure;
- path alias configuration;
- environment validation foundation.

### Acceptance criteria

- frontend starts locally with `pnpm dev`;
- production build succeeds;
- `pnpm typecheck` passes;
- Biome passes;
- no implicit `any` introduced;
- React Compiler CI lint rule works;
- basic test suite executes.

---

## Phase 1 — Supabase and authentication infrastructure

### Build

Create:

- `src/lib/supabase/client.ts`;
- `src/lib/auth/session-manager.ts`;
- auth event integration;
- Zustand auth metadata store;
- auth route boundary;
- session refresh single-flight mechanism.

### Acceptance criteria

- login produces a Supabase session;
- startup restores the session through Supabase;
- auth events update derived Zustand metadata;
- concurrent 401s trigger one refresh operation;
- refresh failure reaches a stable unauthenticated state;
- no auth tokens are copied into Zustand/localStorage;
- role mismatch produces access denial rather than redirect loops.

---

## Phase 2 — OpenAPI contract and API transport

### Build

Create:

- OpenAPI dump script integration;
- committed `openapi.json`;
- committed `schema.d.ts`;
- `src/lib/api/client.ts`;
- `src/lib/api/errors.ts`;
- timeout/retry matrix;
- domain service conventions.

### Acceptance criteria

- generated types exactly correspond to current backend contract;
- CI drift check fails when OpenAPI changes without regeneration;
- GET retry semantics work;
- intake/payment mutations do not auto-retry;
- timeout and abort are distinguishable;
- malformed error payloads do not crash the error parser;
- all service functions accept `AbortSignal` where network operations exist.

---

## Phase 3 — Query infrastructure and routing foundation

### Build

Create:

- TanStack Query client;
- query-key factories;
- canonical filter normalization;
- reusable `queryOptions` convention;
- TanStack Router tree;
- route auth guards;
- route-level `ensureQueryData` preloading.

### Acceptance criteria

- core data routes preload without duplicated request logic;
- query keys are centrally defined;
- filters normalize deterministically;
- no inline raw query configuration remains in core features;
- authenticated/unauthenticated routing is stable.

---

## Phase 4 — Marketplace data layer

### Build

Implement listings domain:

- listing service;
- list query options;
- detail query options;
- assessment query options (single-record response — C3 fix);
- offset infinite query adapter (infinite scroll only — D4 fix, no total count available);
- catalog services/queries;
- listing mutation hooks — edit form must expose **exactly these 11 seller-editable fields** (C9 fix): `title`, `description`, `price`, `city`, `transmission`, `body_type`, `features`, `mileage_km`, `owner_count`, `variant`, `color`. The fields `make`, `model`, `year`, `fuel_type`, `status`, `verification_status` are VLM-extracted or lifecycle-controlled and **must not appear in the seller edit form**;
- `owner_count` Zod validation: `z.number().int().min(1).max(10)` — the DB constraint is `<= 10` (C10 fix); the Python model incorrectly allows up to 20 but the DB will reject 11–20 with a constraint violation;
- `verification_status` displayed as **read-only derived state** on listing cards — never sent from frontend (D9 fix). Set exclusively by `POST /listings/{id}/submit` and `POST /queue/{id}/override`;
- `GET /listings/mine` as the **seller dashboard data source** (M3 fix) — this is how the seller dashboard loads the seller’s own listings;
- `POST /listings/{id}/images` — post-intake individual image addition (M1 fix), takes JSON `{ storage_path }` for an already-uploaded Supabase path, also triggers per-image auto-assessment;
- `POST /listings/{id}/documents` — post-intake document addition (M2 fix);
- `POST /listings/{id}/view` and `GET /listings/{id}/views` — view analytics endpoints (M4 fix);
- URL search schema.

> **C7 — `listing_documents` RLS behavior:** Buyers calling `GET /listings/{id}` receive `listing_documents: []` (empty array) due to RLS — not a permissions error. The field exists in the response schema but is empty for buyer-role callers. The frontend must not treat an empty `listing_documents` array as a data error for buyers.

### Acceptance criteria

- marketplace can fetch listings from FastAPI;
- faceted parameters survive reload through URL state;
- infinite pagination works with offset backend semantics;
- detail pages preload correctly;
- invalidation updates list/detail/assessment relationships;
- filters do not create duplicate cache identities due to equivalent parameter forms.

---

## Phase 5 — Intake infrastructure

### Build

Implement:

- intake Zustand state machine;
- file selection validation with **25MB per-image client-side pre-compression cap** (C1 fix — not 20MB);
- worker creation;
- OffscreenCanvas preprocessing;
- multipart request service targeting `POST /listings/auto-extract`;
- cancellation;
- 90-second intake timeout;
- high-risk response parsing of the **aggregated summary response** (not `DamageDetection[]`);
- storage of raw `IntakeApiResponse` in `REVIEW_DOSSIER` state;
- trigger of separate `GET /listings/{id}/assessment` query after successful intake to fetch per-damage bounding-box details (L1 / C3 fix).

> **D7 — Known limitation:** Storage objects are not cleaned up on intake failure or browser cancellation. Document this limitation in the cancellation UX. Do not imply to the user that cancelling removes server-side uploads.

### Acceptance criteria

- 3–15 images can be selected;
- client rejects images exceeding 25MB before upload;
- RC document can be selected;
- preprocessing never blocks the main thread under supported browsers;
- cancellation aborts the active operation but does not imply server-side cleanup;
- intake timeout is distinguishable from user cancellation;
- successful intake transitions to `REVIEW_DOSSIER` with raw `IntakeApiResponse` stored;
- a separate assessment query is triggered to fetch bounding-box details;
- VLM/JSONB dynamic fields are runtime-validated;
- `missing_fields` constant is ignored — all four review fields shown unconditionally;
- `transmission`, `city`, `price`, `body_type` never pre-populated from AI output.

---

## Phase 6 — Inspection and assessment data layer

### Build

Implement typed inspection models and service/query boundaries for:

- **`GET /listings/{id}/assessment`** — returns a **single record** (not an array) where `damages_detected` is a JSONB array inside that one record (C3 fix);
- the assessment query factory handles a single record shape;
- damage detections (from `damages_detected` on the single assessment record);
- decision trace;
- damage statistics;
- VLM verification;
- expert commentary;
- model/policy versions.

> **M7 — RESOLVED: Server-rendered from `annotated-images` bucket (PRIVATE — signed URLs required).**
>
> **Source of truth:** `004_storage_and_messages.sql` line 5 declares `annotated-images` as **private**. RLS policies grant `SELECT` only to authenticated users with `role = 'admin'` or `role in ('seller', 'admin')`. **Buyers have zero read access to this bucket.**
>
> The inspection dossier renders damage overlay images directly from the `annotated-images` Supabase storage bucket. The YOLOv8 bounding-box overlays are pre-rendered server-side; the frontend fetches and displays them as standard `<img>` elements using short-lived signed URLs.
>
> **Implementation rules locked in:**
> - Generate signed URLs via `supabase.storage.from('annotated-images').createSignedUrl(path, expirySeconds)`. Public URLs do not work — the bucket is private.
> - The annotated image path is keyed by `listing_id` / `assessment_id` (confirm exact path convention with backend during Phase 6).
> - Signed URLs have a TTL. Generate them at render time, not at cache-store time. Do not cache signed URLs in TanStack Query with a staleTime longer than the URL TTL.
> - Render as `<img>` — no `<canvas>`, no WebGL, no coordinate overlay logic on the frontend.
> - The `damages_detected` JSONB array is used for **text/data display only** (damage type, severity, repair cost) — not for drawing bounding boxes.
> - If a signed URL cannot be generated or the annotated image is absent (YOLO did not produce an overlay), fall back gracefully to the original listing image from `car-images`. Never crash.
> - **Buyers never see annotated images.** The inspection dossier with annotated images is visible only to the listing's seller and admins. Do not attempt to fetch or render annotated images for buyer-role users.
> - Do not implement client-side canvas overlay. This option is permanently closed.

### Acceptance criteria

- assessment query factory handles a single-record response (not an array);
- `damages_detected` JSONB array is parsed and rendered as structured data (labels, severity, cost);
- annotated images are fetched from the `annotated-images` private bucket via **signed URLs** (not public URLs);
- signed URLs are generated at render time — not stored in TanStack Query cache beyond their TTL;
- annotated image UI is **not rendered for buyer-role users** (bucket RLS blocks their access);
- fallback to original `car-images` listing image when annotated URL is absent or sign fails;
- no `<canvas>` or coordinate drawing code exists in the codebase;
- assessment payloads are type-safe;
- high-risk dynamic structures are validated;
- decision unions exhaustively handle AUTO_APPROVE/HUMAN_REVIEW/ESCALATE;
- missing optional data does not crash rendering logic.

---

## Phase 7 — Messaging + realtime infrastructure

### Build

Implement:

- message services;
- query options;
- mutation hooks;
- unread count query;
- feature-level realtime adapter;
- ID deduplication;
- cache append for messages;
- invalidation for related status updates;
- connection fallback polling.

### Acceptance criteria

- message inserts appear without manual refresh;
- duplicate events never duplicate messages;
- read receipts update correctly;
- disconnect triggers polling fallback;
- reconnect stops fallback polling;
- components contain no raw Supabase channel lifecycle logic.

---

## Phase 8 — Admin data and mutation infrastructure

### Build

Implement:

- **queue queries** targeting `GET /queue` (not `/admin/queue` — C4/D10 fix) — note the response embeds ALL assessment rows (`assessments(*)`), all images, and seller PII (L10 fix);
- **two separate audit-log query factories** (C5 fix):
  - `GET /admin/audit` — full platform audit log, `assessment_overrides` + `profiles` + `listings` joins, 200-row max;
  - `GET /queue/audit-log` — queue-specific audit log, different joins, 100-row max;
- user queries (response includes `phone` — PII scrubbing applies, D5 fix);
- **document verification mutations** using `PATCH /admin/documents/{document_id}/verify` — no `GET /admin/documents` endpoint exists, documents are accessed through queue/listing detail responses (C6 fix);
- **admin statistics queries** using `GET /admin/stats` with `staleTime` ≥ 10 minutes (D6 fix — unbounded query);
- **`GET /admin/subscriptions`** query (M5 fix);
- override mutations using `POST /queue/{listing_id}/override` — `reason` field requires minimum 10 characters (L11 fix: `z.string().min(10)`);
- role mutation.

> **L10 — Queue response shape:** `GET /queue` returns enriched rows with `listing_images(*)`, `assessments(*)` (ALL assessment rows, not just latest), and `profiles(full_name, email)`. The query type for this endpoint must model the enriched shape, not a plain listing array. Sentry PII scrubbing must cover `full_name` and `email` from these responses.

> **L15 — View analytics gate:** `GET /listings/{id}/views` is seller/admin only. The listing detail page must conditionally load this query only when `user.id === listing.seller_id || user.role === 'admin'`. Never load it for buyer-role users (results in 403).

### Acceptance criteria

- admin routes reject non-admin identities;
- all service calls targeting queue use `/queue` prefix, not `/admin/queue`;
- two separate query factories exist for the two audit endpoints;
- queue reflects pending/escalated listings with enriched assessment/seller shape;
- override form validates reason with `z.string().min(10)`;
- successful override invalidates relevant query families;
- admin stats query uses staleTime ≥ 10 minutes;
- audit data remains server-authoritative;
- document verification operates through `PATCH /admin/documents/{id}/verify`.

---

## Phase 9 — Marketplace extensions and billing

### Build

Implement:

- **saved listings** — `POST /saved-listings` returns 200 (already saved) or 201 (new save) — both are success states (L12 fix). Optimistic update must not create a duplicate if status 200 is returned. `DELETE /saved-listings/{listing_id}` always returns 204 even if not found — optimistic removal is safe (L13);
- **view logging** — `POST /listings/{id}/view` accepts anonymous callers (uses `get_optional_user`) — do not require auth; still send Authorization header if present (L14 fix). `GET /listings/{id}/views` is seller/admin only — conditionally loaded only for `seller_id` owners or admins (L15 fix);
- search alerts;
- **reviews** — two separate endpoints requiring separate service functions (D8 fix):
  - `POST /listings/{listing_id}/reviews` — submit review (buyer, sold listing only);
  - `GET /sellers/{seller_id}/reviews` — public seller trust profile with avg rating;
- **subscriptions** — `SubscriptionCreate` Zod schema must validate `plan_type` against exactly 3 valid literal values (C8 fix):
  ```ts
  plan_type: z.enum(['seller_unlimited_listings', 'pro_buyer_alerts', 'ai_inspection_bundle'])
  ```
- `DELETE /subscriptions/{id}` — cancel subscription (M6 fix);
- `GET /admin/subscriptions` — admin subscription list (M5 fix);
- isolated billing feature module;
- **Step 1 — `POST /subscriptions`** — creates a pending subscription intent in the DB. Body: `{ plan_type, amount_paid, currency, valid_until? }`. Returns `{ id, status: "pending", ... }`;
- **Step 2 — Razorpay checkout.js modal** (client-side, lazily injected script). The Razorpay order is created **client-side via the SDK** — there is no FastAPI order-creation endpoint. Use the Razorpay public key (`RAZORPAY_KEY_ID` env var) to initialise the modal;
- **Step 3 — `PATCH /subscriptions/{subscription_id}/confirm`** — sends `{ razorpay_order_id, razorpay_payment_id, razorpay_signature }` from the Razorpay callback to FastAPI. Backend HMAC-verifies the signature and sets `status: "active"`. In production `razorpay_signature` is required — backend returns 400 if absent;
- subscription state refreshed from the server response of the confirm PATCH only.

### Acceptance criteria

- bookmark POST mutation treats both 200 and 201 as success without creating duplicates;
- bookmark DELETE mutation performs optimistic removal (204 is always the response);
- view logging does not require authentication;
- view analytics (`GET /listings/{id}/views`) is not loaded for buyer-role users;
- `plan_type` Zod validation rejects any string not in the three-value enum;
- reviews use two separate service functions and query factories;
- subscription cancellation endpoint is implemented (`DELETE /subscriptions/{id}`);
- Razorpay script loads lazily — not present in the initial bundle;
- billing flow sequence is exactly: `POST /subscriptions` → Razorpay modal (client-side) → `PATCH /subscriptions/{id}/confirm`;
- no FastAPI "order creation" call is made — Razorpay order is client-side only;
- `razorpay_signature` is always sent in production — never omit it;
- confirm PATCH is never automatically retried;
- subscription state is only updated from the server response of the confirm PATCH, never assumed from Razorpay callback alone;
- no Razorpay npm package in `package.json`;
- payment logic does not leak into listing/vehicle modules.

---

## Phase 10 — Testing, observability, hardening

### Build

Implement:

- fixture matrix;
- type tests;
- behavioral tests;
- Playwright flows;
- Sentry initialization;
- source map upload;
- PII scrubbing;
- production build validation;
- dependency audit.

### Acceptance criteria

- `typecheck` passes;
- Biome passes;
- compiler-specific lint passes;
- unit/type tests pass;
- critical Playwright flows pass;
- no production secrets are referenced by tests;
- Sentry captures errors without protected identity data;
- build output is production-ready.

---

# 15. Anti-Patterns Registry

These patterns are explicit architecture violations.

## A. Duplicating OpenAPI response types in Zod

**Forbidden:** creating a complete Zod copy of every FastAPI response model.

**Why:** creates a second contract authority and schema drift.

**Allowed:** forms, router search schemas, high-risk dynamic JSON, external error parsing.

## B. `any` in application code

**Forbidden:** `any` used to bypass compiler errors.

**Why:** destroys the type guarantees this architecture is intentionally built around.

Use `unknown`, proper types, or a justified narrow boundary.

## C. Server state in Zustand

**Forbidden:** storing listings, assessments, queue rows, or messages as the canonical source in Zustand.

**Why:** TanStack Query already provides caching, lifecycle, invalidation, and deduplication.

## D. Services calling `queryClient`

**Forbidden:** domain service functions directly invalidating or mutating Query cache.

**Why:** couples HTTP/domain logic to a specific UI state library.

## E. Inline query objects scattered through components

**Forbidden:** repeated `useQuery({ queryKey, queryFn, ... })` definitions for core domain queries.

**Why:** cache semantics become inconsistent and difficult to audit.

Use exported `queryOptions` factories.

## F. Ad-hoc query keys

**Forbidden:** manually typed strings/arrays such as `['listing', id]` spread across files.

**Why:** invalidation becomes unreliable and cache topology becomes undocumented.

Use key factories.

## G. Direct Supabase Realtime subscriptions inside components

**Forbidden:** `supabase.channel(...).on(...).subscribe()` inside UI components.

**Why:** duplicates lifecycle logic and creates cache synchronization chaos.

Use feature realtime adapters.

## H. Blind mutation retries

**Forbidden:** automatically retrying intake, payment, sale, override, or submission mutations.

**Why:** repeated side effects can be expensive or irreversible.

## I. Token duplication

**Forbidden:** copying Supabase `access_token` or `refresh_token` into Zustand or another localStorage authority.

**Why:** creates competing session state and weakens the auth boundary.

## J. Generic global `isLoading` / `error` stores

**Forbidden:** one Zustand store representing all API loading/errors.

**Why:** destroys request-level independence and duplicates TanStack Query state.

## K. Axios introduction without architectural review

**Forbidden:** adding Axios because a developer is familiar with it.

**Why:** ky is already the selected transport and covers the required hooks/retry/cancellation behavior.

## L. Multiple icon systems

**Forbidden:** mixing Lucide, Font Awesome, Heroicons, and arbitrary SVG packages.

**Why:** dependency sprawl and inconsistent rendering.

## M. Installing all Radix primitives up front

**Forbidden:** batch installation of unused primitives.

**Why:** violates dependency governance.

## N. Type-level gymnastics for entertainment

**Forbidden:** complex recursive conditional/mapped/template-literal types without a demonstrated bug class they eliminate.

**Why:** compilation complexity and maintenance burden outweigh theoretical cleverness.

## O. Blind optimistic mutations

**Forbidden:** optimistic updates for admin overrides, payment confirmation, submission, sale finalization, or other high-consequence operations.

**Why:** the authoritative state must come from the backend.

## P. Treating timeout as generic failure

**Forbidden:** showing the same UI treatment for timeout, user cancellation, offline failure, and HTTP 500.

**Why:** these states imply different user actions and operational meaning.

## Q. Logging sensitive API payloads to Sentry

**Forbidden:** capturing VINs, plates, RC fields, message bodies, raw image data, or auth tokens.

**Why:** creates unnecessary privacy/security exposure.

## R. Assuming TypeScript validates network responses

**Forbidden:** treating `.json<SomeType>()` as runtime validation.

**Why:** TypeScript generics disappear at runtime.

Use runtime validation only at intentionally selected dynamic boundaries.

## S. Persisting raw intake files

**Forbidden:** localStorage persistence of `File`, `Blob`, `ArrayBuffer`, or large temporary image state.

**Why:** browser storage and memory characteristics make this unsafe and unnecessary.

## T. Adding a dependency before trying platform capabilities

**Forbidden:** installing a library before evaluating browser APIs, React primitives, existing project tooling, and a small local utility.

**Why:** dependency accumulation is one of the easiest ways to destroy a long-lived frontend architecture.

---

# 16. Day-One File Creation Order

The first implementation session should create infrastructure in this order:

```text
1. frontend/package.json
2. frontend/tsconfig.json
3. frontend/vite.config.ts
4. frontend/biome.json
5. frontend/src/app/bootstrap.tsx
6. frontend/src/app/providers.tsx
7. frontend/src/lib/supabase/client.ts
8. frontend/src/lib/auth/session-manager.ts
9. frontend/src/lib/api/schema.d.ts
10. frontend/src/lib/api/errors.ts
11. frontend/src/lib/api/client.ts
12. frontend/src/lib/api/query-keys.ts
13. frontend/src/app/router.tsx
14. frontend/src/routes/__root.tsx
15. first protected/auth routes
16. first feature service
17. first queryOptions factory
18. first route loader using ensureQueryData
```

Do not start by building visual components around fake data.

The first demonstrable vertical slice should be:

```text
Supabase session
    ↓
FastAPI authenticated request
    ↓
OpenAPI-typed service
    ↓
queryOptions factory
    ↓
TanStack Router loader
    ↓
React route
```

Once that works, feature implementation can scale on top of a stable infrastructure spine.

---

# 17. Definition of Done for Frontend Work

A frontend task is not complete until:

- modified TypeScript files typecheck cleanly;
- relevant tests pass;
- new API interactions use the generated contract;
- query keys come from factories;
- query configuration comes from queryOptions factories;
- services remain independent of TanStack Query;
- mutations declare explicit invalidation/optimistic behavior;
- AbortSignal is propagated where network operations support cancellation;
- errors are represented by the established error hierarchy;
- no new `any` was introduced;
- no forbidden dependency/pattern was introduced;
- sensitive telemetry fields remain scrubbed;
- the appropriate phase acceptance criteria still pass.

Recommended validation baseline:

```bash
pnpm typecheck
pnpm lint
pnpm test
pnpm test:e2e
pnpm build
```

When an architectural change affects OpenAPI integration:

```bash
pnpm openapi:dump
pnpm codegen:api
git diff --exit-code openapi.json frontend/src/lib/api/schema.d.ts
```

---

# 18. Final Architecture Principle

FyndCars should feel like one coherent system from browser to Python backend:

```text
React
  ↓
TanStack Router
  ↓
TanStack Query
  ↓
Domain API Services
  ↓
ky Transport
  ↓
FastAPI + Pydantic
  ↓
Supabase / YOLO / Docling / OpenRouter
```

The frontend does not compete with the backend for authority.

The frontend does not turn every problem into global state.

The frontend does not turn every runtime payload into duplicated schemas.

The frontend does not add libraries for novelty.

It builds a strongly typed, observable, cancellable, testable interface around the system that already exists.

**Final governing principle:**

> A technology is not adopted because it is modern; it is adopted because it solves a demonstrated FyndCars problem better than the simpler alternative.
