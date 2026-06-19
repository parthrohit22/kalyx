import { Component, OnInit } from '@angular/core';

import { KalyxApiService } from '../../core/api/kalyx-api.service';
import {
  AnchorStatusResponse,
  AnchorSubmissionResponse,
} from '../../core/models/anchor.model';
import {
  StatusResponse,
  VerificationResponse,
} from '../../core/models/verification.model';
import {
  BadgeTone,
  formatValue,
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
        <div class="panel-heading">
          <div>
            <p>GET /anchor/status / POST /anchor</p>
            <h3>Anchor Status</h3>
          </div>
          <div class="action-row">
            <button type="button" class="button secondary" (click)="checkAnchorStatus()" [disabled]="anchorLoading || loading">Check Anchor Status</button>
            <button type="button" class="button" (click)="anchorLatestCheckpoint()" [disabled]="anchorLoading || loading">Anchor Latest Checkpoint</button>
          </div>
        </div>

        <div class="fact-grid">
          <div>
            <dt>Current State</dt>
            <dd><app-status-badge [label]="anchorState" [tone]="toneForState(anchorState)" /></dd>
          </div>
          <div><dt>Submission</dt><dd>{{ anchorSubmission?.status || '--' }}</dd></div>
          <div><dt>Ledger ID</dt><dd>{{ anchorLedgerId }}</dd></div>
          <div><dt>Anchor URL</dt><dd>{{ anchorUrl }}</dd></div>
          <div><dt>Local Checkpoint</dt><dd>{{ localCheckpointSummary }}</dd></div>
          <div><dt>Pi Checkpoint</dt><dd>{{ piCheckpointSummary }}</dd></div>
          <div><dt>Pi Anchor</dt><dd>{{ piAnchorSummary }}</dd></div>
          <div><dt>Message</dt><dd>{{ anchorMessage }}</dd></div>
        </div>
      </section>

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
  anchorStatus: AnchorStatusResponse | null = null;
  anchorSubmission: AnchorSubmissionResponse | null = null;
  loading = false;
  anchorLoading = false;

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

  get anchorState(): string {
    return this.anchorStatus?.status || '--';
  }

  get anchorLedgerId(): string {
    return this.anchorStatus?.ledger_id || this.anchorSubmission?.ledger_id || '--';
  }

  get anchorUrl(): string {
    return this.anchorStatus?.anchor_url || this.anchorSubmission?.anchor_url || '--';
  }

  get localCheckpointSummary(): string {
    return this.checkpointSummary(
      this.anchorStatus?.local_index ?? this.anchorSubmission?.checkpoint_index,
      this.anchorStatus?.local_hash ?? this.anchorSubmission?.checkpoint_hash,
    );
  }

  get piCheckpointSummary(): string {
    return this.checkpointSummary(this.anchorStatus?.pi_index, this.anchorStatus?.pi_hash);
  }

  get piAnchorSummary(): string {
    return this.checkpointSummary(
      this.anchorSubmission?.pi_anchor_index ?? this.anchorSubmission?.anchor_index,
      this.anchorSubmission?.pi_anchor_hash,
    );
  }

  get anchorMessage(): string {
    return (
      this.anchorSubmission?.reason ||
      this.anchorStatus?.message ||
      this.anchorStatus?.reason ||
      '--'
    );
  }

  verify(): void {
    this.loading = true;
    this.api.verifyLedger().subscribe({
      next: (response) => {
        this.verification = response;
        this.state.verification.set(response);
        this.loading = false;
        const trustState = this.state.trustDisplayState(response);
        this.toast.show(`Verification ${trustState}`, toneForState(trustState) === 'danger' ? 'danger' : 'success');
        this.state.refreshSummary();
      },
      error: (error: Error) => {
        this.loading = false;
        this.toast.show(error.message, 'danger');
      }
    });
  }

  checkAnchorStatus(showToast = true): void {
    this.anchorLoading = true;
    this.api.getAnchorStatus().subscribe({
      next: (response) => {
        this.anchorStatus = response;
        this.anchorLoading = false;
        if (showToast) {
          this.toast.show(`Anchor ${response.status}`, this.toastToneForState(response.status));
        }
      },
      error: (error: Error) => {
        this.anchorLoading = false;
        this.toast.show(error.message, 'danger');
      }
    });
  }

  anchorLatestCheckpoint(): void {
    this.anchorLoading = true;
    this.api.anchorLatestCheckpoint().subscribe({
      next: (response) => {
        this.anchorSubmission = response;
        this.anchorLoading = false;
        this.toast.show(`Anchor ${response.status}`, this.toastToneForState(response.status));
        if (response.accepted) {
          this.checkAnchorStatus(false);
        }
      },
      error: (error: Error) => {
        this.anchorLoading = false;
        this.toast.show(error.message, 'danger');
      }
    });
  }

  shortHash(value: string | null | undefined, size = 12): string {
    return shortHash(value, size);
  }

  private checkpointSummary(
    index: number | null | undefined,
    hash: string | null | undefined,
  ): string {
    if ((index === null || index === undefined) && !hash) {
      return '--';
    }

    return `#${formatValue(index)} ${shortHash(hash, 18)}`;
  }

  private toastToneForState(value: string | null | undefined): 'success' | 'warning' | 'danger' | 'info' {
    const tone = toneForState(value);
    return tone === 'neutral' ? 'info' : tone;
  }

  toneForState(value: string | null | undefined): BadgeTone {
    return toneForState(value);
  }
}
