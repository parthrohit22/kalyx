import { Component } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';

import { KalyxApiService } from '../../core/api/kalyx-api.service';
import { AlertRecord } from '../../core/models/alert.model';
import { DetectionResponse } from '../../core/models/detection.model';
import { BadgeTone, formatValue, toneForState } from '../../core/models/ui.model';
import { DashboardStateService } from '../../core/state/dashboard-state.service';
import { EmptyStateComponent } from '../../shared/empty-state/empty-state.component';
import { JsonViewerComponent } from '../../shared/json-viewer/json-viewer.component';
import { StatusBadgeComponent } from '../../shared/status-badge/status-badge.component';
import { ToastService } from '../../shared/toast/toast.service';

@Component({
  selector: 'app-detection',
  standalone: true,
  imports: [NgFor, NgIf, EmptyStateComponent, JsonViewerComponent, StatusBadgeComponent],
  template: `
    <section class="page">
      <div class="page-heading">
        <div>
          <p>POST /detect</p>
          <h2>Detection</h2>
        </div>
        <button type="button" class="button" (click)="runDetection()" [disabled]="loading">Run Detection</button>
      </div>

      <div class="result-panel" [class]="panelClass">
        <div>
          <app-status-badge [label]="stateLabel" [tone]="toneForState(stateLabel)" />
          <h3>{{ title }}</h3>
          <p>{{ copy }}</p>
        </div>
      </div>

      <section class="panel">
        <dl class="fact-grid">
          <div><dt>Skipped</dt><dd>{{ result ? (result.skipped ? 'Yes' : 'No') : '--' }}</dd></div>
          <div><dt>Reason</dt><dd>{{ result?.reason || '--' }}</dd></div>
          <div><dt>Verification</dt><dd>{{ result?.verification?.status || '--' }}</dd></div>
          <div><dt>Written Alerts</dt><dd>{{ result?.written ?? '--' }}</dd></div>
        </dl>
      </section>

      <section class="panel">
        <div class="panel-heading">
          <div>
            <p>Generated alerts</p>
            <h3>Detection Results</h3>
          </div>
        </div>

        <div class="card-grid" *ngIf="alerts.length; else emptyDetection">
          <article class="alert-card" *ngFor="let alert of alerts">
            <app-status-badge [label]="alert.severity || 'UNKNOWN'" [tone]="toneForState(alert.severity)" />
            <strong>{{ alert.type || 'Alert' }}</strong>
            <p>{{ alert.details || alert.target || 'No alert detail' }}</p>
            <small>{{ formatValue(alert.user) }} | {{ formatValue(alert.session) }} | {{ formatValue(alert.target) }}</small>
          </article>
        </div>

        <ng-template #emptyDetection>
          <app-empty-state
            [title]="result?.skipped ? 'Detection skipped' : 'No generated alerts'"
            [message]="result?.skipped ? 'The backend refused to run detection against untrusted evidence.' : 'Run detection to evaluate trusted ledger evidence.'" />
        </ng-template>
      </section>

      <app-json-viewer label="Raw detection response" [value]="result" />
    </section>
  `
})
export class DetectionComponent {
  result: DetectionResponse | null = null;
  loading = false;

  constructor(
    private readonly api: KalyxApiService,
    private readonly state: DashboardStateService,
    private readonly toast: ToastService
  ) {}

  get alerts(): AlertRecord[] {
    return this.result?.alerts ?? [];
  }

  get stateLabel(): string {
    if (!this.result) {
      return 'UNKNOWN';
    }

    return this.result.skipped ? 'SKIPPED' : this.state.trustDisplayState(this.result.verification);
  }

  get panelClass(): string {
    return `state-${toneForState(this.stateLabel)}`;
  }

  get title(): string {
    if (!this.result) {
      return 'Detection has not run';
    }

    return this.result.skipped ? 'Detection skipped by backend' : 'Detection completed';
  }

  get copy(): string {
    if (!this.result) {
      return 'Detection verifies backend trust first and does not run against untrusted evidence.';
    }

    return this.result.skipped
      ? 'The backend reported the ledger is not trusted, so detection was skipped.'
      : 'Detection ran against the current backend-verified ledger view.';
  }

  runDetection(): void {
    this.loading = true;
    this.api.runDetection().subscribe({
      next: (response) => {
        this.result = response;
        this.state.detection.set(response);
        this.loading = false;
        this.toast.show(response.skipped ? 'Detection skipped' : 'Detection completed', response.skipped ? 'warning' : 'success');
        this.state.refreshSummary();
      },
      error: (error: Error) => {
        this.loading = false;
        this.toast.show(error.message, 'danger');
      }
    });
  }

  toneForState(value: string | null | undefined): BadgeTone {
    return toneForState(value);
  }

  formatValue(value: unknown): string {
    return formatValue(value);
  }
}
