export type RiskLevel = "low" | "medium" | "high";

export interface LoginEventIn {
  user_id: string;
  login_timestamp: string;
  ip_address: string;
  country?: string | null;
  region?: string | null;
  city?: string | null;
  asn?: number | null;
  browser?: string | null;
  os?: string | null;
  device_type?: string | null;
  login_successful: boolean;
}

export interface ScoreOut {
  risk_score: number;
  risk_level: RiskLevel;
  step_up_required: boolean;
  flagged_reasons: string[];
  features: Record<string, number>;
}

export interface LiveFeedEvent extends ScoreOut {
  user_id: string;
  login_timestamp: string;
  ip_address: string;
  country?: string | null;
  city?: string | null;
  device_type?: string | null;
  login_successful: boolean;
}
