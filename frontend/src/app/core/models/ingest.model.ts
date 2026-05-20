import { LedgerRecord } from './ledger.model';

export interface StructuredExecutionEvent {
  comm: string;
  pid: number;
  ppid: number;
  argv: string;
  ret?: number | null;
  uid?: number | null;
}

export interface StructuredIngestRequest {
  event: StructuredExecutionEvent;
  source: string;
}

export interface RawLineIngestRequest {
  raw_line: string;
  source: string;
}

export type IngestRequest = StructuredIngestRequest | RawLineIngestRequest;

export interface IngestResponse {
  ingested: boolean;
  record?: LedgerRecord | null;
  reason?: string | null;
}
