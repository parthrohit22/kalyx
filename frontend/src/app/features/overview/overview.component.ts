import { Component, OnInit } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';
import { RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';

import { KalyxApiService } from '../../core/api/kalyx-api.service';
import { AlertRecord } from '../../core/models/alert.model';
import { LedgerRecord } from '../../core/models/ledger.model';
import { StatusResponse } from '../../core/models/verification.model';
import { DashboardStateService } from '../../core/state/dashboard-state.service';
import { BadgeTone, formatValue, shortHash, toneForState } from '../../core/models/ui.model';
import { EmptyStateComponent } from '../../shared/empty-state/empty-state.component';
import { LoadingStateComponent } from '../../shared/loading-state/loading-state.component';
import { MetricCardComponent } from '../../shared/metric-card/metric-card.component';
import { StatusBadgeComponent } from '../../shared/status-badge/status-badge.component';
import { ToastService } from '../../shared/toast/toast.service';

@Component({
  selector: 'app-overview',
  standalone: true,
  imports: [NgFor, NgIf, RouterLink, EmptyStateComponent, LoadingStateComponent, MetricCardComponent, StatusBadgeComponent],
  template: `
    <section class="page">
      <div class="trust-hero" [class]="heroClass">
        <div>
          <app-status-badge [label]="trustState" [tone]="toneForState(trustState)" />
          <h2>{{ heroTitle }}</h2>
          <p>{{ heroCopy }}</p>
          <div class="action-row">
            <button type="button" class="button" (click)="verifyLedger()" [disabled]="loading">Verify Ledger</button>
            <button type="button" class="button secondary" (click)="runDetection()" [disabled]="loading">Run Detection</button>
            <button type="button" class="button ghost" (click)="refresh()" [disabled]="loading">Refresh</button>
          </div>
        </div>
        <dl>
          <div>
            <dt>Entries</dt>
            <dd>{{ status?.entries ?? '--' }}</dd>
          </div>
          <div>
            <dt>Valid Until</dt>
            <dd>{{ status?.valid_until_index ?? '--' }}</dd>
          </div>
          <div>
            <dt>Checkpoint</dt>
            <dd>{{ status?.checkpoint_state || '--' }}</dd>
          </div>
          <div>
            <dt>Last Valid Hash</dt>
            <dd>{{ shortHash(status?.last_valid_hash || status?.last_hash) }}</dd>
          </div>
        </dl>
      </div>

      <app-loading-state *ngIf="loading" />

      <div class="metric-grid">
        <app-metric-card label="Ledger Entries" [value]="status?.entries ?? '--'" [detail]="status?.ledger_file || 'Ledger file not loaded'" />
        <app-metric-card label="Ledger State" [value]="status?.ledger_state || '--'" [detail]="checkpointDetail" />
        <app-metric-card label="Verification" [value]="status?.verification_status || '--'" [detail]="verificationDetail" />
        <app-metric-card label="Alerts" [value]="alerts.length" [detail]="alertDetail" />
      </div>

      <div class="content-grid">
        <section class="panel">
          <div class="panel-heading">
            <div>
              <p>Recent activity</p>
              <h3>Ledger Records</h3>
            </div>
            <a routerLink="/ledger">Open ledger</a>
          </div>
          <div class="table-wrap" *ngIf="ledger.length; else noLedger">
            <table>
              <thead>
                <tr>
                  <th>Seq</th>
                  <th>Time</th>
                  <th>Command</th>
                  <th>Action</th>
                  <th>Target</th>
                  <th>User</th>
                  <th>Hash</th>
                </tr>
              </thead>
              <tbody>
                <tr *ngFor="let record of ledger">
                  <td class="mono">{{ record.seq }}</td>
                  <td>{{ record.ts || '--' }}</td>
                  <td>
                    <strong>{{ record.comm || '--' }}</strong>
                    <small>{{ record.argv || '' }}</small>
                  </td>
                  <td><app-status-badge [label]="record.action || 'EXEC'" tone="neutral" /></td>
                  <td>{{ record.target || '--' }}</td>
                  <td>{{ record.user || '--' }}</td>
                  <td class="mono">{{ shortHash(record.hash) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <ng-template #noLedger>
            <app-empty-state title="No ledger records" message="Ingest evidence to populate the ledger." />
          </ng-template>
        </section>

        <section class="panel">
          <div class="panel-heading">
            <div>
              <p>Alert summary</p>
              <h3>Recent Alerts</h3>
            </div>
            <a routerLink="/alerts">Open alerts</a>
          </div>
          <div class="summary-list" *ngIf="alerts.length; else noAlerts">
            <article *ngFor="let alert of alerts" class="summary-card">
              <app-status-badge [label]="alert.severity || 'UNKNOWN'" [tone]="toneForState(alert.severity)" />
              <strong>{{ alert.type || 'Alert' }}</strong>
              <p>{{ alert.details || alert.target || 'No details provided' }}</p>
            </article>
          </div>
          <ng-template #noAlerts>
            <app-empty-state title="No alerts" message="No persisted alerts are available." />
          </ng-template>
        </section>
      </div>
    </section>
  `
})
export class OverviewComponent implements OnInit {
  status: StatusResponse | null = null;
  ledger: LedgerRecord[] = [];
  alerts: AlertRecord[] = [];
  loading = false;

  constructor(
    private readonly api: KalyxApiService,
    readonly state: DashboardStateService,
    private readonly toast: ToastService
  ) {}

  ngOnInit(): void {
    this.refresh();
  }

  get trustState(): string {
    return this.state.trustDisplayState(this.status);
  }

  get heroClass(): string {
    return `state-${toneForState(this.trustState)}`;
  }

  get heroTitle(): string {
    if (this.trustState === 'VERIFIED') {
      return 'Ledger integrity is verified';
    }
    if (this.trustState === 'NO_LEDGER') {
      return 'No ledger has been created yet';
    }
    if (this.trustState === 'TAMPERED' || this.trustState === 'CORRUPTED' || this.trustState === 'UNTRUSTED') {
      return 'Ledger evidence requires investigation';
    }
    return 'Integrity posture unavailable';
  }

  get heroCopy(): string {
    if (this.trustState === 'VERIFIED') {
      return 'The backend verified the current ledger chain and checkpoint state. The frontend is displaying that result only.';
    }
    if (this.trustState === 'NO_LEDGER') {
      return 'Ingest evidence to create the ledger, then run verification before detection.';
    }
    return 'Run verification to establish the current backend trust state before using evidence operationally.';
  }

  get checkpointDetail(): string {
    return `checkpoint: ${formatValue(this.status?.checkpoint_state)} | gap: ${formatValue(this.status?.checkpoint_gap_detected)}`;
  }

  get verificationDetail(): string {
    return `failure: ${formatValue(this.status?.failure_index)} | valid until: ${formatValue(this.status?.valid_until_index)}`;
  }

  get alertDetail(): string {
    return this.alerts.length ? 'Persisted backend alert records' : 'No persisted alerts';
  }

  refresh(): void {
    this.loading = true;
    forkJoin({
      status: this.api.getStatus(),
      ledger: this.api.getLedger(8),
      alerts: this.api.getAlerts()
    }).subscribe({
      next: ({ status, ledger, alerts }) => {
        this.status = status;
        this.ledger = ledger.records.slice().reverse();
        this.alerts = alerts.alerts.slice().reverse().slice(0, 5);
        this.state.status.set(status);
        this.state.ledger.set(ledger);
        this.state.alerts.set(alerts);
        this.loading = false;
      },
      error: (error: Error) => {
        this.toast.show(error.message, 'danger');
        this.loading = false;
      }
    });
  }

  verifyLedger(): void {
    this.loading = true;
    this.api.verifyLedger().subscribe({
      next: (response) => {
        this.state.verification.set(response);
        const trustState = this.state.trustDisplayState(response);
        this.toast.show(`Verification ${trustState}`, toneForState(trustState) === 'danger' ? 'danger' : 'success');
        this.refresh();
      },
      error: (error: Error) => {
        this.toast.show(error.message, 'danger');
        this.loading = false;
      }
    });
  }

  runDetection(): void {
    this.loading = true;
    this.api.runDetection().subscribe({
      next: (response) => {
        this.state.detection.set(response);
        this.toast.show(response.skipped ? 'Detection skipped because evidence is not trusted' : 'Detection completed', response.skipped ? 'warning' : 'success');
        this.refresh();
      },
      error: (error: Error) => {
        this.toast.show(error.message, 'danger');
        this.loading = false;
      }
    });
  }

  shortHash(value: string | null | undefined): string {
    return shortHash(value);
  }

  toneForState(value: string | null | undefined): BadgeTone {
    return toneForState(value);
  }
}
