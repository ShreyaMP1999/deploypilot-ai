export type Tenant = { id: string; name: string };
export type Config = Tenant & {
  industry: string;
  workflow: string;
  integrations: string[];
  environment: string;
  policy: Record<string, unknown>;
  policy_version: number;
  agent_mode: string;
};
export type Source = {
  id: string;
  customer: string;
  total_cents?: number;
  purchased_at?: string;
  category?: string;
  privileged?: boolean;
  identity_verified?: boolean;
  refunded_cents: number;
};
export type Run = {
  id: string;
  tenant_id: string;
  state: string;
  request: { text: string; record_id: string; amount_cents: number | null };
  created_at: string;
  context: Record<string, unknown>;
  recommendation: {
    classification?: string;
    summary?: string;
    response_draft?: string;
    uncertain?: boolean;
  };
  decision: { outcome?: string; reason?: string; required_role?: string };
  action: Record<string, unknown>;
  result: Record<string, unknown> | null;
  approval: {
    status: string;
    required_role: string;
    note: string | null;
    actor_id: string | null;
    decided_at: string | null;
  } | null;
  model: string;
  prompt_version: string;
  latency_ms: number;
  input_tokens: number;
  output_tokens: number;
  estimated_cost: number;
  error: string | null;
  events: {
    id: string;
    event: string;
    detail: Record<string, unknown>;
    created_at: string;
  }[];
};
export type Metrics = {
  total_requests: number;
  awaiting_approval: number;
  completed: number;
  escalation_rate: number | null;
  average_latency_ms: number | null;
  estimated_cost: number;
  tokens: number;
  cost_configured: boolean;
  activity: { date: string; processed: number; completed: number }[];
  states: Record<string, number>;
};
export type EvalRun = {
  id: string;
  model: string;
  prompt_version: string;
  created_at: string;
  results: {
    total: number;
    passed: number;
    decision_accuracy: number;
    approval_capture_rate: number | null;
    average_latency_ms: number;
    classification_accuracy: number | null;
    unauthorized_action_rate: number | null;
    workflow_completion_rate: number | null;
    tokens: number;
    estimated_cost: number;
    llm_status: string;
    failures: {
      id: string;
      category: string;
      expected: string;
      actual: string;
    }[];
  };
};
