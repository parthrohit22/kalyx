import { Component, OnInit } from '@angular/core';
import { DashboardStateService } from '../../core/state/dashboard-state.service';
import { StatusBadgeComponent } from '../../shared/status-badge/status-badge.component';
import { BadgeTone, toneForState } from '../../core/models/ui.model';

@Component({
  selector: 'app-topbar',
  standalone: true,
  imports: [StatusBadgeComponent],
  template: `
    <header class="topbar">
      <div>
        <p>Operations Console</p>
        <h2>Ledger integrity workspace</h2>
      </div>

      <div class="topbar-status">
        <span class="api-health" [class.error]="state.apiError()">
          <i aria-hidden="true"></i>
          {{ state.apiError() ? 'API error' : 'API ready' }}
        </span>
        <span class="topbar-fact">Ledger <strong>{{ state.status()?.ledger_state || '--' }}</strong></span>
        <span class="topbar-fact">Verify <strong>{{ state.status()?.verification_status || '--' }}</strong></span>
        <span class="topbar-fact">Alerts <strong>{{ state.alerts().count }}</strong></span>
        <app-status-badge
          [label]="state.trustDisplayState(state.status())"
          [tone]="toneForState(state.trustDisplayState(state.status()))" />
        <button type="button" class="button secondary" (click)="refresh()" [disabled]="state.loading()">
          Refresh
        </button>
      </div>
    </header>
  `
})
export class TopbarComponent implements OnInit {
  constructor(readonly state: DashboardStateService) {}

  ngOnInit(): void {
    this.state.refreshSummary();
  }

  refresh(): void {
    this.state.refreshSummary();
  }

  toneForState(value: string): BadgeTone {
    return toneForState(value);
  }
}
