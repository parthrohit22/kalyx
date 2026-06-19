export type AnchorComparisonStatus =
  | 'MATCH'
  | 'AHEAD'
  | 'BEHIND'
  | 'DIVERGENCE'
  | 'NO_ANCHOR'
  | 'UNREACHABLE';

export interface AnchorStatusResponse {
  status: AnchorComparisonStatus | string;
  ledger_id: string;
  anchor_url: string;
  local_index?: number | null;
  local_hash?: string | null;
  pi_index?: number | null;
  pi_hash?: string | null;
  reason?: string | null;
  message?: string | null;
}

export interface AnchorSubmissionResponse {
  status: string;
  ledger_id: string;
  anchor_url: string;
  accepted: boolean;
  checkpoint_index?: number | null;
  checkpoint_hash?: string | null;
  checkpoint_written?: boolean | null;
  checkpoint_reason?: string | null;
  checkpoint_state?: string | null;
  verification_status?: string | null;
  anchor_index?: number | null;
  pi_anchor_index?: number | null;
  pi_anchor_hash?: string | null;
  pi_previous_anchor_hash?: string | null;
  accepted_at?: string | null;
  latest_checkpoint_index?: number | null;
  reason?: string | null;
}
