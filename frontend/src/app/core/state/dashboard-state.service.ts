import { Injectable, signal } from '@angular/core';
import { forkJoin } from 'rxjs';

import { KalyxApiService } from '../api/kalyx-api.service';
import { AlertResponse } from '../models/alert.model';
import {
  StatusResponse,
  TrustDisplayState,
  VerificationResponse,
} from '../models/verification.model';
import { LedgerResponse } from '../models/ledger.model';
import { DetectionResponse } from '../models/detection.model';

type TrustSource =
  | StatusResponse
  | VerificationResponse
  | Partial<StatusResponse>
  | Partial<VerificationResponse>
  | null
  | undefined;

@Injectable({ providedIn: 'root' })
export class DashboardStateService {
  readonly status = signal<StatusResponse | null>(null);
  readonly verification = signal<VerificationResponse | null>(null);
  readonly alerts = signal<AlertResponse>({ alerts: [], count: 0 });
  readonly ledger = signal<LedgerResponse>({ records: [], count: 0 });
  readonly detection = signal<DetectionResponse | null>(null);
  readonly loading = signal(false);
  readonly apiError = signal<string | null>(null);

  constructor(private readonly api: KalyxApiService) {}

  refreshSummary(limit = 8): void {
    this.loading.set(true);
    this.apiError.set(null);

    forkJoin({
      status: this.api.getStatus(),
      alerts: this.api.getAlerts(),
      ledger: this.api.getLedger(limit),
    }).subscribe({
      next: ({ status, alerts, ledger }) => {
        this.status.set(status);
        this.alerts.set(alerts);
        this.ledger.set(ledger);
        this.loading.set(false);
      },
      error: (error: Error) => {
        this.apiError.set(error.message);
        this.loading.set(false);
      },
    });
  }

  trustDisplayState(source: TrustSource): TrustDisplayState {
    if (!source) {
      return 'UNKNOWN';
    }

    const status = this.normalize(this.readString(source, 'status'));
    const verificationStatus = this.normalize(
      this.readString(source, 'verification_status'),
    );
    const trustState = this.normalize(this.readString(source, 'trust_state'));
    const reason = this.normalize(
      this.readString(source, 'reason') || this.readString(source, 'failure_reason'),
    );
    const valid = this.readBoolean(source, 'valid');
    const verificationValid = this.readBoolean(source, 'verification_valid');

    if (
      status === 'VALID' ||
      verificationStatus === 'VALID' ||
      trustState === 'VERIFIED' ||
      valid === true ||
      verificationValid === true
    ) {
      return 'VERIFIED';
    }

    if (status === 'NO_LEDGER' || verificationStatus === 'NO_LEDGER' || trustState === 'NO_LEDGER') {
      return 'NO_LEDGER';
    }

    if (status === 'EMPTY' || verificationStatus === 'EMPTY') {
      return 'EMPTY';
    }

    if (
      status === 'CORRUPTED' ||
      verificationStatus === 'CORRUPTED' ||
      reason === 'INVALID_JSON' ||
      reason === 'INVALID_RECORD_TYPE'
    ) {
      return 'CORRUPTED';
    }

    if (
      status === 'TAMPERED' ||
      verificationStatus === 'TAMPERED' ||
      trustState === 'PARTIALLY_TRUSTED'
    ) {
      return 'TAMPERED';
    }

    if (valid === false || verificationValid === false || trustState === 'UNTRUSTED') {
      return 'UNTRUSTED';
    }

    return 'UNKNOWN';
  }

  private readString(source: object, key: string): string | undefined {
    if (!Object.prototype.hasOwnProperty.call(source, key)) {
      return undefined;
    }

    const value = (source as Record<string, unknown>)[key];
    return typeof value === 'string' ? value : undefined;
  }

  private readBoolean(source: object, key: string): boolean | undefined {
    if (!Object.prototype.hasOwnProperty.call(source, key)) {
      return undefined;
    }

    const value = (source as Record<string, unknown>)[key];
    return typeof value === 'boolean' ? value : undefined;
  }

  private normalize(value: unknown): string {
    return String(value ?? '').trim().toUpperCase();
  }
}