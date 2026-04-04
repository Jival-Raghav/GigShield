// Worker Types
export type Platform = 'swiggy' | 'zomato' | 'amazon' | 'zepto';
export type VehicleType = 'bike' | 'cycle' | 'other';
export type CoverageTier = 'basic' | 'standard' | 'premium';

export interface Worker {
  id: string;
  name: string;
  phone: string;
  upi_id: string | null;
  platform: Platform;
  vehicle_type: VehicleType;
  micro_zone_id: string;
  tenure_weeks: number;
  avg_weekly_income: number;
  trust_score: number;
  cold_start: boolean;
  created_at: string;
  updated_at: string;
}

export interface WorkerCreate {
  name: string;
  phone: string;
  platform: Platform;
  vehicle_type: VehicleType;
  micro_zone_id: string;
  upi_id?: string;
}

export interface WorkerUpdate {
  avg_weekly_income?: number;
  micro_zone_id?: string;
  upi_id?: string;
}

// Policy Types
export interface Policy {
  id: string;
  worker_id: string;
  coverage_tier: CoverageTier;
  coverage_ratio: number;
  max_weekly_coverage: number;
  weekly_premium: number;
  risk_multiplier: number;
  trust_discount: number;
  is_active: boolean;
  valid_from: string;
  valid_to: string;
  created_at: string;
}

export interface PolicyCreate {
  worker_id: string;
  coverage_tier: CoverageTier;
}

export interface PremiumQuote {
  weekly_premium: number;
  expected_loss: number;
  loading_factor: number;
  risk_multiplier: number;
  trust_discount: number;
  coverage_ratio: number;
  max_weekly_coverage: number;
}

export interface PremiumQuoteRequest {
  worker_id: string;
  coverage_tier: CoverageTier;
}

// Baseline Types
export interface BaselineResult {
  baseline_income: number;
  confidence: number;
  data_source: string;
  weeks_of_data: number;
}

// Disruption Types
export type DisruptionType = 'rainfall' | 'aqi' | 'flood' | 'curfew' | 'platform_outage' | 'extreme_temperature';

export interface Disruption {
  id: string;
  zone_id: string;
  disruption_type: DisruptionType;
  severity: number;
  signal_source: string;
  is_confirmed: boolean;
  is_catastrophic: boolean;
  started_at: string;
  ended_at: string | null;
  created_at: string;
}

export interface DisruptionSimulate {
  zone_id: string;
  disruption_type: DisruptionType;
  severity: number;
  signal_source?: string;
}

// Claim Types
export type ClaimStatus = 'pending' | 'validating' | 'approved' | 'held' | 'rejected' | 'paid';

export interface Claim {
  id: string;
  worker_id: string;
  policy_id: string;
  disruption_id: string;
  status: ClaimStatus;
  baf_score: number;
  payout_amount: number;
  income_lost: number;
  eligible_hours: number;
  severity_smoothed: number;
  signal_confidence: number;
  behavior_confidence: number;
  unified_confidence: number;
  spoofing_signals_fired: number;
  syndicate_flag: boolean;
  audit_required: boolean;
  audit_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface ClaimCreate {
  worker_id: string;
  policy_id: string;
  disruption_id: string;
}

export interface ClaimStatusUpdate {
  status: ClaimStatus;
  audit_reason?: string | null;
}

// Payout Types
export type PaymentStatus = 'initiated' | 'processing' | 'completed' | 'failed';

export interface Payout {
  id: string;
  claim_id: string;
  worker_id: string;
  amount: number;
  payment_method: 'upi' | 'bank_transfer';
  payment_status: PaymentStatus;
  razorpay_order_id: string | null;
  initiated_at: string;
  completed_at: string | null;
}

// Auth Types
export interface OtpRequestPayload {
  phone: string;
}

export interface OtpRequestResponse {
  expires_in: number;
  otp_request_id: string;
  otp_debug?: string;
}

export interface OtpVerifyPayload {
  phone: string;
  otp: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_at: string;
  worker_id: string;
  is_admin: boolean;
}

// Admin Types
export interface AdminDashboard {
  total_active_policies: number;
  total_claims_today: number;
  total_payouts_today: number;
  claims_pending_audit: number;
  active_disruptions: number;
  avg_baf_score: number;
  loss_ratio: number;
}

export interface FlaggedClaim extends Claim {
  worker_name?: string;
  zone_id?: string;
}

export interface AdminPayoutLogItem {
  payout_id: string;
  claim_id: string;
  worker_id: string;
  worker_name: string;
  worker_phone: string;
  zone_id: string;
  policy_id: string;
  coverage_tier: CoverageTier;
  amount: number;
  payment_status: PaymentStatus;
  payment_method: 'upi' | 'bank_transfer';
  settlement_mode: 'auto_weekly_settlement' | 'manual_admin_settlement' | 'provider_webhook' | 'legacy';
  settlement_note: string;
  audit_required: boolean;
  audit_reason: string | null;
  initiated_at: string | null;
  completed_at: string | null;
}

// API Error
export interface ApiError {
  detail: string;
  status_code?: number;
}
