/** Shared API contracts, mirroring the FastAPI Pydantic schemas. */

export type Role = 'admin' | 'reviewer' | 'viewer';

export type KycStatus = 'pending' | 'in_review' | 'approved' | 'rejected' | 'escalated';
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';
export type DocumentType =
  | 'passport'
  | 'drivers_license'
  | 'national_id'
  | 'proof_of_address'
  | 'business_registration';

export type RefundStatus = 'pending' | 'approved' | 'rejected' | 'info_requested';
export type RefundReason =
  | 'duplicate_charge'
  | 'service_not_rendered'
  | 'fraud'
  | 'customer_request'
  | 'processing_error';

export type FlagEnvironment = 'production' | 'staging' | 'development';

export type AuditAction =
  | 'created'
  | 'updated'
  | 'status_changed'
  | 'assigned'
  | 'note_added'
  | 'toggled'
  | 'deleted';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
}

export interface UserSummary {
  id: number;
  full_name: string;
  email: string;
  role: Role;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface AuditLogEntry {
  id: number;
  entity_type: string;
  entity_id: number;
  action: AuditAction;
  field: string | null;
  previous_value: string | null;
  new_value: string | null;
  reason: string | null;
  actor_id: number | null;
  actor_email: string;
  created_at: string;
}

export interface KycDocument {
  id: number;
  document_type: DocumentType;
  file_name: string;
  verified: boolean;
  uploaded_at: string;
}

export interface KycNote {
  id: number;
  body: string;
  created_at: string;
  author: UserSummary;
}

export interface KycReviewListItem {
  id: number;
  case_reference: string;
  customer_name: string;
  submitted_at: string;
  risk_score: number;
  risk_level: RiskLevel;
  primary_document_type: DocumentType;
  status: KycStatus;
  assigned_reviewer: UserSummary | null;
}

export interface KycReviewDetail extends KycReviewListItem {
  customer_email: string;
  customer_country: string;
  business_name: string | null;
  risk_summary: string;
  sanctions_hit: boolean;
  pep_match: boolean;
  decision_reason: string | null;
  decided_at: string | null;
  created_at: string;
  updated_at: string;
  documents: KycDocument[];
  notes: KycNote[];
}

export interface KycQueueCounts {
  pending: number;
  in_review: number;
  approved: number;
  rejected: number;
  escalated: number;
  total: number;
}

export interface KycFilters {
  status?: KycStatus;
  risk_level?: RiskLevel;
  reviewer_id?: number;
  unassigned?: boolean;
  submitted_from?: string;
  submitted_to?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export interface RefundListItem {
  id: number;
  refund_reference: string;
  customer_name: string;
  amount: string;
  currency: string;
  reason: RefundReason;
  status: RefundStatus;
  requested_at: string;
  processed_at: string | null;
}

export interface CustomerRefundHistoryItem {
  id: number;
  refund_reference: string;
  amount: string;
  status: RefundStatus;
  requested_at: string;
}

export interface RefundDetail extends RefundListItem {
  customer_email: string;
  transaction_reference: string;
  reason_detail: string | null;
  decision_reason: string | null;
  processed_by: UserSummary | null;
  processing_hours: number | null;
  created_at: string;
  updated_at: string;
  customer_history: CustomerRefundHistoryItem[];
  approval_chain: AuditLogEntry[];
}

export interface RefundSummary {
  total_count: number;
  total_amount: string;
  pending_count: number;
  pending_amount: string;
  approved_count: number;
  approved_amount: string;
  rejected_count: number;
  rejected_amount: string;
  info_requested_count: number;
  average_processing_hours: number | null;
}

export interface RefundTrendPoint {
  day: string;
  count: number;
  amount: string;
}

export interface RefundFilters {
  status?: RefundStatus;
  reason?: RefundReason;
  min_amount?: string;
  max_amount?: string;
  requested_from?: string;
  requested_to?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export interface FeatureFlagState {
  environment: FlagEnvironment;
  enabled: boolean;
  rollout_percentage: number;
}

export interface FeatureFlag {
  id: number;
  key: string;
  name: string;
  description: string;
  default_enabled: boolean;
  environments: FeatureFlagState[];
  modified_by: UserSummary | null;
  created_at: string;
  updated_at: string;
}

export interface FeatureFlagFilters {
  search?: string;
  environment?: FlagEnvironment;
  enabled?: boolean;
  page?: number;
  page_size?: number;
}
