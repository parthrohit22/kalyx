import { Component, OnInit } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { combineLatest, startWith } from 'rxjs';

import { KalyxApiService } from '../../core/api/kalyx-api.service';
import { AlertRecord } from '../../core/models/alert.model';
import { BadgeTone, formatValue, toneForState } from '../../core/models/ui.model';
import { DashboardStateService } from '../../core/state/dashboard-state.service';
import { EmptyStateComponent } from '../../shared/empty-state/empty-state.component';
import { JsonViewerComponent } from '../../shared/json-viewer/json-viewer.component';
import { StatusBadgeComponent } from '../../shared/status-badge/status-badge.component';
import { ToastService } from '../../shared/toast/toast.service';

@Component({
  selector: 'app-alerts',
  standalone: true,
  imports: [NgFor, NgIf, ReactiveFormsModule, EmptyStateComponent, JsonViewerComponent, StatusBadgeComponent],
  template: `
    <section class="page">
      <div class="page-heading">
        <div>
          <p>GET /alerts</p>
          <h2>Alerts</h2>
        </div>
        <button type="button" class="button secondary" (click)="loadAlerts()">Refresh Alerts</button>
      </div>

      <section class="panel">
        <div class="toolbar">
          <label>
            <span>Severity</span>
            <select [formControl]="severityControl">
              <option value="">All severities</option>
              <option *ngFor="let severity of severityOptions" [value]="severity">{{ severity }}</option>
            </select>
          </label>
          <label>
            <span>Type</span>
            <select [formControl]="typeControl">
              <option value="">All types</option>
              <option *ngFor="let type of typeOptions" [value]="type">{{ type }}</option>
            </select>
          </label>
          <label>
            <span>Search</span>
            <input type="search" [formControl]="searchControl" placeholder="Target, user, session">
          </label>
        </div>

        <div class="table-wrap" *ngIf="filteredAlerts.length; else emptyAlerts">
          <table>
            <thead>
              <tr>
                <th>Severity</th>
                <th>Type</th>
                <th>Target</th>
                <th>User</th>
                <th>Session</th>
                <th>Window</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let alert of filteredAlerts" class="clickable-row" (click)="openAlert(alert)" tabindex="0">
                <td><app-status-badge [label]="alert.severity || 'UNKNOWN'" [tone]="toneForState(alert.severity)" /></td>
                <td>{{ alert.type || '--' }}</td>
                <td>{{ alert.target || '--' }}</td>
                <td>{{ alert.user || '--' }}</td>
                <td>{{ alert.session || '--' }}</td>
                <td>{{ windowFor(alert) }}</td>
                <td>{{ alert.details || '--' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <ng-template #emptyAlerts>
          <app-empty-state title="No alerts" message="No persisted alerts match the current filters." />
        </ng-template>
      </section>

      <aside class="drawer-backdrop" *ngIf="selectedAlert" (click)="closeDrawer()">
        <section class="drawer" (click)="$event.stopPropagation()">
          <button type="button" class="drawer-close" (click)="closeDrawer()">Close</button>
          <p>Alert detail</p>
          <h3>{{ selectedAlert.type || 'Alert' }}</h3>
          <dl class="drawer-facts">
            <div><dt>Severity</dt><dd>{{ selectedAlert.severity || '--' }}</dd></div>
            <div><dt>User</dt><dd>{{ selectedAlert.user || '--' }}</dd></div>
            <div><dt>Session</dt><dd>{{ selectedAlert.session || '--' }}</dd></div>
            <div><dt>Target</dt><dd>{{ selectedAlert.target || '--' }}</dd></div>
          </dl>
          <p class="drawer-copy">{{ selectedAlert.details || 'No details provided.' }}</p>
          <app-json-viewer label="Full alert JSON" [value]="selectedAlert" />
        </section>
      </aside>
    </section>
  `
})
export class AlertsComponent implements OnInit {
  readonly severityControl = new FormControl<string>('', { nonNullable: true });
  readonly typeControl = new FormControl<string>('', { nonNullable: true });
  readonly searchControl = new FormControl<string>('', { nonNullable: true });

  alerts: AlertRecord[] = [];
  filteredAlerts: AlertRecord[] = [];
  severityOptions: string[] = [];
  typeOptions: string[] = [];
  selectedAlert: AlertRecord | null = null;

  constructor(
    private readonly api: KalyxApiService,
    private readonly state: DashboardStateService,
    private readonly toast: ToastService
  ) {}

  ngOnInit(): void {
    combineLatest([
      this.severityControl.valueChanges.pipe(startWith(this.severityControl.value)),
      this.typeControl.valueChanges.pipe(startWith(this.typeControl.value)),
      this.searchControl.valueChanges.pipe(startWith(this.searchControl.value))
    ]).subscribe(() => this.applyFilters());

    this.loadAlerts();
  }

  loadAlerts(): void {
    this.api.getAlerts().subscribe({
      next: (response) => {
        this.alerts = response.alerts.slice().reverse();
        this.severityOptions = Array.from(new Set(this.alerts.map((alert) => formatValue(alert.severity)).filter((value) => value !== '--'))).sort();
        this.typeOptions = Array.from(new Set(this.alerts.map((alert) => formatValue(alert.type)).filter((value) => value !== '--'))).sort();
        this.state.alerts.set(response);
        this.applyFilters();
      },
      error: (error: Error) => this.toast.show(error.message, 'danger')
    });
  }

  applyFilters(): void {
    const severity = this.severityControl.value;
    const type = this.typeControl.value;
    const search = this.searchControl.value.trim().toLowerCase();

    this.filteredAlerts = this.alerts.filter((alert) => {
      const matchesSeverity = !severity || alert.severity === severity;
      const matchesType = !type || alert.type === type;
      const haystack = [alert.target, alert.user, alert.session, alert.details].map(formatValue).join(' ').toLowerCase();
      return matchesSeverity && matchesType && (!search || haystack.includes(search));
    });
  }

  openAlert(alert: AlertRecord): void {
    this.selectedAlert = alert;
  }

  closeDrawer(): void {
    this.selectedAlert = null;
  }

  windowFor(alert: AlertRecord): string {
    const start = alert.ts_start || alert.seq_start;
    const end = alert.ts_end || alert.seq_end;
    return start || end ? `${formatValue(start)} -> ${formatValue(end)}` : '--';
  }

  toneForState(value: string | null | undefined): BadgeTone {
    return toneForState(value);
  }
}
