import api from './axios';
import type {
  Worker,
  WorkerCreate,
  WorkerUpdate,
  WorkerLocationTraceCreate,
  WorkerLocationTraceResponse,
  WorkerWallet,
  Policy,
  PolicyCreate,
  PremiumQuote,
  PremiumQuoteRequest,
  BaselineResult,
  Disruption,
  DisruptionSimulate,
  DisruptionSimulateResult,
  Claim,
  ClaimCreate,
  ClaimStatusUpdate,
  Payout,
  PayoutGateway,
  OtpRequestPayload,
  OtpRequestResponse,
  OtpVerifyPayload,
  LoginResponse,
  AdminDashboard,
  FraudClusterMapResponse,
  FlaggedClaim,
  AdminPayoutLogItem,
  ClaimTimelineResponse,
  ClaimScenarioInput,
  ClaimScenarioResult,
} from '@/types';

// ============ AUTH ============

export const authApi = {
  requestOtp: async (payload: OtpRequestPayload): Promise<OtpRequestResponse> => {
    const { data } = await api.post<OtpRequestResponse>('/auth/otp/request', payload);
    return data;
  },

  verifyOtp: async (payload: OtpVerifyPayload): Promise<LoginResponse> => {
    const { data } = await api.post<LoginResponse>('/auth/otp/verify', payload);
    return data;
  },
};

// ============ WORKERS ============

export const workersApi = {
  register: async (payload: WorkerCreate): Promise<Worker> => {
    const { data } = await api.post<Worker>('/workers/register', payload);
    return data;
  },

  getById: async (workerId: string): Promise<Worker> => {
    const { data } = await api.get<Worker>(`/workers/${workerId}`);
    return data;
  },

  update: async (workerId: string, payload: WorkerUpdate): Promise<Worker> => {
    const { data } = await api.put<Worker>(`/workers/${workerId}`, payload);
    return data;
  },

  addLocationTrace: async (payload: WorkerLocationTraceCreate): Promise<WorkerLocationTraceResponse> => {
    const { data } = await api.post<WorkerLocationTraceResponse>('/workers/location/trace', payload);
    return data;
  },

  getWallet: async (workerId: string): Promise<WorkerWallet> => {
    const { data } = await api.get<WorkerWallet>(`/workers/${workerId}/wallet`);
    return data;
  },
};

// ============ BASELINE & PREMIUM ============

export const premiumApi = {
  computeBaseline: async (workerId: string): Promise<BaselineResult> => {
    const { data } = await api.post<BaselineResult>(`/baseline/compute/${workerId}`);
    return data;
  },

  getQuote: async (payload: PremiumQuoteRequest): Promise<PremiumQuote> => {
    const { data } = await api.post<PremiumQuote>('/premium/quote', payload);
    return data;
  },
};

// ============ POLICIES ============

export const policiesApi = {
  create: async (payload: PolicyCreate): Promise<Policy> => {
    const { data } = await api.post<Policy>('/policies/create', payload);
    return data;
  },

  delete: async (policyId: string): Promise<Policy> => {
    const { data } = await api.delete<Policy>(`/policies/${policyId}`);
    return data;
  },

  getByWorkerId: async (workerId: string): Promise<Policy[]> => {
    const { data } = await api.get<Policy[]>(`/policies/${workerId}`);
    return data;
  },
};

// ============ TRIGGERS / DISRUPTIONS ============

export const triggersApi = {
  check: async (zoneId: string): Promise<Disruption[]> => {
    const { data } = await api.post<Disruption[]>('/triggers/check', { zone_id: zoneId });
    return data;
  },

  getActive: async (zoneId: string): Promise<Disruption[]> => {
    const { data } = await api.get<Disruption[]>(`/triggers/active/${zoneId}`);
    return data;
  },

  getClaimable: async (zoneId: string): Promise<Disruption[]> => {
    const { data } = await api.get<Disruption[]>(`/triggers/claimable/${zoneId}`);
    return data;
  },

  simulate: async (payload: DisruptionSimulate): Promise<DisruptionSimulateResult> => {
    const { data } = await api.post<DisruptionSimulateResult>('/triggers/simulate', payload);
    return data;
  },
};

// ============ CLAIMS ============

export const claimsApi = {
  initiate: async (payload: ClaimCreate): Promise<Claim> => {
    const { data } = await api.post<Claim>('/claims/initiate', payload);
    return data;
  },

  getById: async (claimId: string): Promise<Claim> => {
    const { data } = await api.get<Claim>(`/claims/${claimId}`);
    return data;
  },

  getByWorkerId: async (workerId: string): Promise<Claim[]> => {
    const { data } = await api.get<Claim[]>(`/claims/worker/${workerId}`);
    return data;
  },

  updateStatus: async (claimId: string, payload: ClaimStatusUpdate): Promise<Claim> => {
    const { data } = await api.post<Claim>(`/claims/${claimId}/status`, payload);
    return data;
  },
};

// ============ PAYOUTS ============

export const payoutsApi = {
  initiate: async (claimId: string, gateway: PayoutGateway = 'upi_simulator'): Promise<Payout> => {
    const { data } = await api.post<Payout>(`/payouts/${claimId}/initiate`, null, {
      params: { gateway },
    });
    return data;
  },
};

// ============ ADMIN ============

export const adminApi = {
  getDashboard: async (): Promise<AdminDashboard> => {
    const { data } = await api.get<AdminDashboard>('/admin/dashboard');
    return data;
  },

  getFlaggedClaims: async (limit = 50, offset = 0): Promise<FlaggedClaim[]> => {
    const { data } = await api.get<FlaggedClaim[]>('/admin/claims/flagged', {
      params: { limit, offset },
    });
    return data;
  },

  getZoneRisk: async (): Promise<{ zone_id: string; disruption_count: number; avg_severity: number }[]> => {
    const { data } = await api.get('/admin/zones/risk');
    return data;
  },

  getFraudClusters: async (): Promise<FraudClusterMapResponse> => {
    const { data } = await api.get<FraudClusterMapResponse>('/admin/fraud/clusters');
    return data;
  },

  updateClaimStatus: async (claimId: string, payload: ClaimStatusUpdate): Promise<Claim> => {
    const { data } = await api.post<Claim>(`/admin/claims/${claimId}/status`, payload);
    return data;
  },

  runSettlement: async (mode: 'previous_week' | 'current_week' = 'current_week'): Promise<{
    mode: string;
    week_start: string;
    week_end: string;
    processed_claims: number;
    created_payouts: number;
    total_settled_amount: number;
  }> => {
    const { data } = await api.post('/admin/settlements/run', null, {
      params: { mode },
    });
    return data;
  },

  getPayoutLog: async (limit = 100): Promise<AdminPayoutLogItem[]> => {
    const { data } = await api.get<AdminPayoutLogItem[]>('/admin/payouts/log', {
      params: { limit },
    });
    return data;
  },

  getClaimTimeline: async (claimId: string): Promise<ClaimTimelineResponse> => {
    const { data } = await api.get<ClaimTimelineResponse>(`/admin/claims/${claimId}/timeline`);
    return data;
  },

  simulateClaim: async (claimId: string, payload: ClaimScenarioInput): Promise<ClaimScenarioResult> => {
    const { data } = await api.post<ClaimScenarioResult>(`/admin/claims/${claimId}/simulate`, payload);
    return data;
  },
};

// Export all APIs
export { api };
