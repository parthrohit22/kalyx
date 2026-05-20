export interface AlertRecord {
  severity?: string | null;
  type?: string | null;
  target?: string | null;
  user?: string | null;
  session?: string | null;
  details?: string | null;
  seq_start?: number | null;
  seq_end?: number | null;
  ts_start?: string | null;
  ts_end?: string | null;
  delta_seconds?: number | null;
  [key: string]: unknown;
}

export interface AlertResponse {
  alerts: AlertRecord[];
  count: number;
}
