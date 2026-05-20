import { Component, OnInit } from '@angular/core';
import { forkJoin } from 'rxjs';

import { KalyxApiService } from '../../core/api/kalyx-api.service';
import { AlertResponse } from '../../core/models/alert.model';
import { DetectionResponse } from '../../core/models/detection.model';
import { LedgerResponse } from '../../core/models/ledger.model';
import { StatusResponse, VerificationResponse } from '../../core/models/verification.model';
import { DashboardStateService } from '../../core/state/dashboard-state.service';
import { JsonViewerComponent } from '../../shared/json-viewer/json-viewer.component';
import { ToastService } from '../../shared/toast/toast.service';

@Component({
  selector: 'app-evidence',
  standalone: true,
  imports: [JsonViewerComponent],
  template: `
    <section class="page">
      <div class="page-heading">
        <div>
          <p>Audit area</p>
          <h2>Raw Evidence</h2>
        </div>
        <button type="button" class="button secondary" (click)="loadEvidence()">Refresh Evidence</button>
      </div>

      <div class="evidence-stack">
        <app-json-viewer label="Status JSON" [value]="status" [open]="true" />
        <app-json-viewer label="Verification JSON" [value]="verification" />
        <app-json-viewer label="Ledger JSON" [value]="ledger" />
        <app-json-viewer label="Alerts JSON" [value]="alerts" />
        <app-json-viewer label="Detection JSON" [value]="detection" />
      </div>
    </section>
  `
})
export class EvidenceComponent implements OnInit {
  status: StatusResponse | null = null;
  verification: VerificationResponse | null = null;
  ledger: LedgerResponse | null = null;
  alerts: AlertResponse | null = null;
  detection: DetectionResponse | null = null;

  constructor(
    private readonly api: KalyxApiService,
    private readonly state: DashboardStateService,
    private readonly toast: ToastService
  ) {}

  ngOnInit(): void {
    this.loadEvidence();
  }

  loadEvidence(): void {
    forkJoin({
      status: this.api.getStatus(),
      ledger: this.api.getLedger(50),
      alerts: this.api.getAlerts()
    }).subscribe({
      next: ({ status, ledger, alerts }) => {
        this.status = status;
        this.verification = this.state.verification();
        this.ledger = ledger;
        this.alerts = alerts;
        this.detection = this.state.detection();
      },
      error: (error: Error) => this.toast.show(error.message, 'danger')
    });
  }
}
