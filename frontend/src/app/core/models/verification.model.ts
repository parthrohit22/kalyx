export type TrustDisplayState =
  | 'VERIFIED'
  | 'TAMPERED'
  | 'CORRUPTED'
  | 'EMPTY'
  | 'NO_LEDGER'
  | 'UNTRUSTED'
  | 'UNKNOWN';

export interface VerificationResponse {
  valid: boolean;
  status: string;
  trust_state?: string | null;
  reason?: string | null;
  record_count: number;
  failure_index?: number | null;
  valid_until_index: number;
  last_valid_hash?: string | null;
  expected_prev_hash?: string | null;
  actual_prev_hash?: string | null;
  expected_hash?: string | null;
  actual_hash?: string | null;
  checkpoint?: Record<string, unknown> | null;
  checkpoint_file?: string | null;
  checkpoint_available?: boolean | null;
  checkpoint_state?: string | null;
  checkpoint_gap_detected?: boolean | null;
  checkpoint_reason?: string | null;
  checkpoint_index?: number | null;
  checkpoint_record_count?: number | null;
  checkpoint_last_hash?: string | null;
  checkpoint_hash?: string | null;
  checkpoint_created_at?: string | null;
  checkpoint_previous_hash?: string | null;
}

export interface StatusResponse {
  ledger_file: string;
  entries: number;
  last_hash?: string | null;
  verification_status?: string | null;
  verification_valid: boolean;
  verification_timestamp?: string | null;
  failure_index?: number | null;
  failure_reason?: string | null;
  valid_until_index: number;
  last_valid_hash?: string | null;
  ledger_state: string;
  trust_state: string;
  checkpoint_file: string;
  checkpoint_available: boolean;
  checkpoint_state: string;
  checkpoint_gap_detected: boolean;
  checkpoint_reason?: string | null;
  checkpoint_index?: number | null;
  checkpoint_record_count: number;
  checkpoint_last_hash?: string | null;
  checkpoint_hash?: string | null;
  checkpoint_created_at?: string | null;
  checkpoint_previous_hash?: string | null;
}
