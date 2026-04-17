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

export interface WorkerLocationTraceCreate {
  latitude: number;
  longitude: number;
  accuracy_meters?: number;
  source?: string;
}

export interface WorkerLocationTraceResponse {
  mapped_parent_zone_id?: string | null;
  mapped_fine_zone_id?: string | null;
  accepted: boolean;
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
  projected_weekly_income?: number;
  intelligence_pressure?: number;
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
  started_at?: string;
  ended_at?: string;
}

export interface DisruptionSimulateResult {
  disruption: Disruption;
  claims_initiated: number;
  claims_auto_paid: number;
}
  income_lost: number;
  eligible_hours: number;
  severity_smoothed: number;
  signal_confidence: number;
  behavior_confidence: number;
  unified_confidence: number;
  spoofing_signals_fired: number;
export interface WalletTransaction {
  id: string;
  amount: number;
  entry_type: 'credit' | 'debit';
  description: string;
  payout_id: string | null;
  claim_id: string | null;
  created_at: string;
}

export interface WorkerWallet {
  worker_id: string;
  balance: number;
  updated_at: string;
  recent_transactions: WalletTransaction[];
}
  syndicate_flag: boolean;
  audit_required: boolean;
  audit_reason: string | null;
  fraud_score?: number;
  fraud_band?: 'low' | 'medium' | 'high';
  fraud_explanation?: string | null;
  fraud_explanation_confidence?: number | null;
  fraud_explanation_source?: string | null;
  fraud_component_scores?: Record<string, number> | null;
  fraud_top_reasons?: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface ClaimCreate {
  worker_id: string;
  policy_id: string;
  disruption_id: string;
  latitude?: number;
  longitude?: number;
  accuracy_meters?: number;
  ip_address?: string;
}

export interface ClaimStatusUpdate {
  status: ClaimStatus;
  audit_reason?: string | null;
}

// Payout Types
export type PaymentStatus = 'initiated' | 'processing' | 'completed' | 'failed';
export type PayoutGateway = 'upi_simulator' | 'razorpay_test' | 'stripe_sandbox';

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
  phone: string;
  display_name: string;
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
  projected_claims_next_week?: number;
  projected_payout_next_week?: number;
  forecast_confidence?: number;
  top_risk_zone?: string | null;
  top_risk_zone_projected_claims?: number;
  top_risk_zone_projected_payout?: number;
  top_risk_zones?: Array<{
    zone_id: string;
    active_policy_count: number;
    expected_disruption_days: number;
    expected_severity: number;
    projected_claims_next_week: number;
    projected_payout_next_week: number;
    forecast_confidence: number;
  }>;
  zone_forecast_7d?: Array<{
    zone_id: string;
    forecast: Array<{
      zone_id: string;
      forecast_date: string;
      day_offset: number;
      signal_pressure: number;
      holiday_active: boolean;
      windspeed_10m_max_kph: number;
      precipitation_sum_mm: number;
      news_risk: number;
      fire_risk: number;
      projected_disruption_days: number;
      projected_severity: number;
      forecast_confidence: number;
    }>;
  }>;
}

export interface FraudClusterSummary {
  cluster_id: string;
  size: number;
  avg_trust_score: number;
  avg_baf_score: number;
  avg_audit_rate: number;
  avg_negative_rate: number;
  avg_claim_frequency: number;
  suspicious_claim_ratio: number;
  cluster_score: number;
  behavior_label: string;
  top_zones: string[];
  top_worker_names: string[];
  top_reasons: string[];
}

export interface FraudClusterZone {
  zone_id: string;
  parent_zone_id: string;
  worker_count: number;
  claim_count: number;
  suspicious_claim_count: number;
  suspicious_claim_ratio: number;
  avg_trust_score: number;
  avg_fraud_score: number;
  dominant_cluster: string;
  cluster_size: number;
}

export interface FraudClusterMapResponse {
  generated_at: string;
  total_workers: number;
  total_claims: number;
  clusters: FraudClusterSummary[];
  zones: FraudClusterZone[];
}

export interface ClaimTimelineEvent {
  timestamp: string | null;
  category: string;
  title: string;
  details: string;
}

export interface ClaimTimelineResponse {
  claim_id: string;
  worker_id: string;
  zone_id: string;
  fraud_score: number;
  fraud_band: 'low' | 'medium' | 'high';
  timeline: ClaimTimelineEvent[];
}

export interface ClaimScenarioInput {
  rainfall_mm?: number | null;
  aqi?: number | null;
  curfew_level?: string | null;
  worker_movement?: string | null;
  gps_zone?: string | null;
  ip_zone?: string | null;
  wind_speed_kph?: number | null;
  disruption_severity?: number | null;
  external_pressure?: number | null;
}

export interface ClaimScenarioResult {
  claim_id: string;
  base: {
    fraud_score: number;
    fraud_band: 'low' | 'medium' | 'high';
    payout_amount: number;
  };
  scenario: {
    fraud_score: number;
    fraud_band: 'low' | 'medium' | 'high';
    payout_amount: number;
    payout_income_lost: number;
    eligible_hours: number;
    severity_smoothed: number;
    audit_required: boolean;
    top_reasons: string[];
    explanation: string;
  };
  delta: {
    fraud_score: number;
    payout_amount: number;
  };
  error?: string;
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
