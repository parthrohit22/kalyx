export interface LedgerRecord {
  seq: number;
  ts?: string | null;
  comm?: string | null;
  argv?: string | null;
  action?: string | null;
  target?: string | null;
  user?: string | null;
  session?: string | null;
  hash?: string | null;
  prev_hash?: string | null;
  source?: string | null;
  pid?: number | null;
  ppid?: number | null;
  ret?: number | null;
  uid?: number | null;
  [key: string]: unknown;
}

export interface LedgerResponse {
  records: LedgerRecord[];
  count: number;
}
