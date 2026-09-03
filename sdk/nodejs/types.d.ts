export interface Subscores {
  device_health: number;
  network_reputation: number;
  travel_velocity: number;
  behavioral_biometrics: number;
  financial_velocity: number;
}

export interface RiskDecision {
  customer_id: string;
  trust_score: number;
  decision: 'allow' | 'challenge' | 'block';
  reasons: string[];
  subscores: Subscores;
  latency_ms: number;
  w3c_trace_id?: string;
}

export interface EvaluateParams {
  customerId: string;
  telemetryToken?: string;
  amount?: number;
  currency?: string;
  customSignals?: Record<string, any>;
}

export interface TrustDNAOptions {
  secretKey: string;
  baseUrl?: string;
  timeout?: number;
}

export class TrustDNA {
  constructor(options: TrustDNAOptions);
  risk: {
    evaluate(params: EvaluateParams): Promise<RiskDecision>;
  };
}

export default TrustDNA;
