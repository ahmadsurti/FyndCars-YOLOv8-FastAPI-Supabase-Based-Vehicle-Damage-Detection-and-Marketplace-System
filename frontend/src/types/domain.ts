import type { components } from '@/lib/api/schema'

export type Role = 'admin' | 'seller' | 'buyer'
export type Region = 'India' | 'USA' | 'UK' | 'EU'

export type ListingStatus = 'draft' | 'pending' | 'active' | 'rejected' | 'sold' | 'escalated'
export type VerificationStatus = 'unverified' | 'verified_clean' | 'flagged_discrepancy' | 'admin_override'

export type DecisionType = 'AUTO_APPROVE' | 'HUMAN_REVIEW' | 'ESCALATE'
export type SeverityLevel = 'minor' | 'moderate' | 'severe'

export interface ListingImage {
  id: string
  listing_id: string
  storage_path: string
  is_primary: boolean
  order_index: number
  uploaded_at?: string
}

export interface ListingDocument {
  id: string
  listing_id: string
  document_type: string
  document_name?: string | null
  storage_path: string
  verification_status: 'pending' | 'verified' | 'rejected'
  rejection_reason?: string | null
  uploaded_at?: string
}

export type DamageDetection = components['schemas']['DamageDetection']
export type DecisionTrace = components['schemas']['DecisionTrace']

export interface ListingAssessment {
  id: string
  listing_id: string
  image_id?: string | null
  assessment_id_ext?: string
  damages_detected: DamageDetection[]
  total_damages: number
  decision: DecisionType
  decision_confidence?: number | null
  decision_trace?: DecisionTrace[]
  damage_stats?: Record<string, unknown> | null
  expert_commentary?: string | null
  model_version?: string
  policy_version?: string
  cv_backend?: string
  processing_time_ms?: number
  annotated_image_path?: string | null
  created_at?: string
}

export interface Listing {
  id: string
  seller_id: string
  make: string
  model: string
  year: number
  variant?: string | null
  title: string
  price: number
  currency: string
  fuel_type: string
  transmission: string
  mileage_km: number
  owner_count: number
  city: string
  body_type?: string | null
  color?: string | null
  description?: string | null
  features?: string[]
  status: ListingStatus
  verification_status: VerificationStatus
  vlm_report?: Record<string, unknown>
  ocr_odometer_km?: number | null
  plate_number?: string | null
  buyer_id?: string | null
  sold_at?: string | null
  created_at: string
  updated_at: string
  listing_images?: ListingImage[]
  listing_documents?: ListingDocument[]
  assessments?: ListingAssessment[]
  profiles?: { full_name?: string; email?: string }
}

export type ListingDetail = Listing

export type ReviewQueueItem = Listing

export interface OverrideAuditItem {
  id: string
  assessment_id: string
  listing_id: string
  assessor_id: string
  original_decision: string
  override_decision: string
  reason: string
  created_at: string
  profiles?: { full_name?: string; email?: string }
  listings?: { title?: string; make?: string; model?: string; year?: number }
}

export interface PlatformStats {
  total_listings: number
  by_status: Record<string, number>
  auto_approval_rate_percent: number
  total_overrides: number
  total_users: number
}

export interface UserProfile {
  id: string
  full_name?: string | null
  phone?: string | null
  role: Role
  region: Region
  created_at: string
  updated_at: string
}

export interface AuthUser {
  id: string
  email: string
  role: Role
  fullName?: string
  avatarUrl?: string
}
