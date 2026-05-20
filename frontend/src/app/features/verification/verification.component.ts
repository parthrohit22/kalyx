import { Component, OnInit } from '@angular/core';

import { KalyxApiService } from '../../core/api/kalyx-api.service';
import {
  StatusResponse,
  VerificationResponse,
} from '../../core/models/verification.model';
import {
  BadgeTone,
  shortHash,
  toneForState,
} from '../../core/models/ui.model';
import { DashboardStateService } from '../../core/state/dashboard-state.service';
import { JsonViewerComponent } from '../../shared/json-viewer/json-viewer.component';
import { StatusBadgeComponent } from '../../shared/status-badge/status-badge.component';
import { ToastService } from '../../shared/toast/toast.service';

@Component({
  selector: 'app-verification',
  standalone: true,
  imports: [JsonViewerComponent, StatusBadgeComponent],
  template: `
    <section class="page">
      <div class="page-heading">
        <div>
          <p>POST /verify</p>
          <h2>Verification</h2>
        </div>
        <button type="button" class="button" (click)="verify()" [disabled]="loading">Verify Ledger</button>
      </div>

      <div class="result-panel" [class]="panelClass">
        <div>
          <app-status-badge [label]="displayState" [tone]="toneForState(displayState)" />
          <h3>{{ title }}</h3>
          <p>{{ copy }}</p>
        </div>
      </div>

      <section class="panel">
        <div class="fact-grid">
          <div><dt>Status</dt><dd>{{ rawStatus }}</dd></div>
          <div><dt>Trust State</dt><dd>{{ rawTrustState }}</dd></div>
          <div><dt>Failure Reason</dt><dd>{{ reason }}</dd></div>
          <div><dt>Failure Index</dt><dd>{{ failureIndex }}</dd></div>
          <div><dt>Valid Until Index</dt><dd>{{ validUntil }}</dd></div>
          <div><dt>Last Valid Hash</dt><dd>{{ shortHash(lastValidHash, 18) }}</dd></div>
        </div>
      </section>

      <app-json-viewer label="Raw verification response" [value]="verification || status" />
    </section>
  `
})
export class VerificationComponent implements OnInit {
  status: StatusResponse | null = null;
  verification: VerificationResponse | null = null;
  loading = false;

  constructor(
    private readonly api: KalyxApiService,
    private readonly state: DashboardStateService,
    private readonly toast: ToastService
  ) {}

  ngOnInit(): void {
    this.api.getStatus().subscribe({
      next: (status) => {
        this.status = status;
        this.state.status.set(status);
      },
      error: (error: Error) => this.toast.show(error.message, 'danger')
    });
  }

  get source(): StatusResponse | VerificationResponse | null {
    return this.verification || this.status;
  }

  get displayState(): string {
    return this.state.trustDisplayState(this.source);
  }

  get panelClass(): string {
    return `state-${toneForState(this.displayState)}`;
  }

  get title(): string {
    if (this.displayState === 'VERIFIED') {
      return 'Backend verification succeeded';
    }
    if (this.displayState === 'NO_LEDGER') {
      return 'No ledger available';
    }
    if (this.displayState === 'EMPTY') {
      return 'Ledger is empty';
    }
    if (this.displayState === 'TAMPERED' || this.displayState === 'CORRUPTED' || this.displayState === 'UNTRUSTED') {
      return 'Integrity boundary is not trusted';
    }
    return 'Verification state unknown';
  }

  get copy(): string {
    return 'KALYX displays the backend verification result. Trust decisions remain in FastAPI services and ledger verification code.';
  }

  get rawStatus(): string {
    return this.verification?.status || this.status?.verification_status || '--';
  }

  get rawTrustState(): string {
    return this.verification?.trust_state || this.status?.trust_state || '--';
  }

  get reason(): string {
    return this.verification?.reason || this.status?.failure_reason || '--';
  }

  get failureIndex(): number | string {
    return this.source?.failure_index ?? '--';
  }

  get validUntil(): number | string {
    return this.source?.valid_until_index ?? '--';
  }

  get lastValidHash(): string | null | undefined {
    return this.source?.last_valid_hash;
  }

  verify(): void {
    this.loading = true;
    this.api.verifyLedger().subscribe({
      next: (response) => {
        this.verification = response;
        this.state.verification.set(response);
        this.loading = false;
        this.toast.show(`Verification ${response.status}`, toneForState(response.status) === 'danger' ? 'danger' : 'success');
        this.state.refreshSummary();
      },
      error: (error: Error) => {
        this.loading = false;
        this.toast.show(error.message, 'danger');
      }
    });
  }

  shortHash(value: string | null | undefined, size = 12): string {
    return shortHash(value, size);
  }

  toneForState(value: string | null | undefined): BadgeTone {
    return toneForState(value);
  }
}
