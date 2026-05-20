import { AlertRecord } from './alert.model';
import { VerificationResponse } from './verification.model';

export interface DetectionResponse {
  alerts: AlertRecord[];
  written: number;
  skipped: boolean;
  reason?: string | null;
  verification: Partial<VerificationResponse>;
}
