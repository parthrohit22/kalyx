import { Component, OnInit } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { combineLatest, startWith } from 'rxjs';

import { KalyxApiService } from '../../core/api/kalyx-api.service';
import { LedgerRecord } from '../../core/models/ledger.model';
import { formatValue, shortHash } from '../../core/models/ui.model';
import { DashboardStateService } from '../../core/state/dashboard-state.service';
import { EmptyStateComponent } from '../../shared/empty-state/empty-state.component';
import { JsonViewerComponent } from '../../shared/json-viewer/json-viewer.component';
import { StatusBadgeComponent } from '../../shared/status-badge/status-badge.component';
import { ToastService } from '../../shared/toast/toast.service';

@Component({
  selector: 'app-ledger',
  standalone: true,
  imports: [NgFor, NgIf, ReactiveFormsModule, EmptyStateComponent, JsonViewerComponent, StatusBadgeComponent],
  template: `
    <section class="page">
      <div class="page-heading">
        <div>
          <p>GET /ledger</p>
          <h2>Ledger Inspection</h2>
        </div>
        <button type="button" class="button secondary" (click)="loadLedger()">Refresh Ledger</button>
      </div>

      <section class="panel">
        <div class="toolbar">
          <label>
            <span>Search</span>
            <input type="search" [formControl]="searchControl" placeholder="Command, target, user, session, hash">
          </label>
          <label>
            <span>Action</span>
            <select [formControl]="actionControl">
              <option value="">All actions</option>
              <option *ngFor="let action of actionOptions" [value]="action">{{ action }}</option>
            </select>
          </label>
          <label class="limit-field">
            <span>Limit</span>
            <input type="number" min="1" max="500" [formControl]="limitControl">
          </label>
        </div>

        <div class="table-wrap" *ngIf="filteredRecords.length; else emptyLedger">
          <table>
            <thead>
              <tr>
                <th>Seq</th>
                <th>Timestamp</th>
                <th>Command</th>
                <th>Action</th>
                <th>Target</th>
                <th>User</th>
                <th>Session</th>
                <th>Hash</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let record of filteredRecords" class="clickable-row" (click)="openRecord(record)" tabindex="0">
                <td class="mono">{{ record.seq }}</td>
                <td>{{ record.ts || '--' }}</td>
                <td>
                  <strong>{{ record.comm || '--' }}</strong>
                  <small>{{ record.argv || '' }}</small>
                </td>
                <td><app-status-badge [label]="record.action || 'EXEC'" tone="neutral" /></td>
                <td>{{ record.target || '--' }}</td>
                <td>{{ record.user || '--' }}</td>
                <td>{{ record.session || '--' }}</td>
                <td class="mono">{{ shortHash(record.hash) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <ng-template #emptyLedger>
          <app-empty-state title="No ledger records" message="No records match the current filters." />
        </ng-template>
      </section>

      <aside class="drawer-backdrop" *ngIf="selectedRecord" (click)="closeDrawer()">
        <section class="drawer" (click)="$event.stopPropagation()">
          <button type="button" class="drawer-close" (click)="closeDrawer()">Close</button>
          <p>Ledger record</p>
          <h3>Seq {{ selectedRecord.seq }}</h3>
          <dl class="drawer-facts">
            <div><dt>Command</dt><dd>{{ selectedRecord.comm || '--' }}</dd></div>
            <div><dt>Action</dt><dd>{{ selectedRecord.action || '--' }}</dd></div>
            <div><dt>Target</dt><dd>{{ selectedRecord.target || '--' }}</dd></div>
            <div><dt>User</dt><dd>{{ selectedRecord.user || '--' }}</dd></div>
            <div><dt>Session</dt><dd>{{ selectedRecord.session || '--' }}</dd></div>
            <div><dt>Hash</dt><dd>{{ shortHash(selectedRecord.hash, 18) }}</dd></div>
          </dl>
          <app-json-viewer label="Full ledger record JSON" [value]="selectedRecord" [open]="false" />
        </section>
      </aside>
    </section>
  `
})
export class LedgerComponent implements OnInit {
  readonly searchControl = new FormControl<string>('', { nonNullable: true });
  readonly actionControl = new FormControl<string>('', { nonNullable: true });
  readonly limitControl = new FormControl<number>(50, { nonNullable: true });

  records: LedgerRecord[] = [];
  filteredRecords: LedgerRecord[] = [];
  actionOptions: string[] = [];
  selectedRecord: LedgerRecord | null = null;

  constructor(
    private readonly api: KalyxApiService,
    private readonly state: DashboardStateService,
    private readonly toast: ToastService
  ) {}

  ngOnInit(): void {
    combineLatest([
      this.searchControl.valueChanges.pipe(startWith(this.searchControl.value)),
      this.actionControl.valueChanges.pipe(startWith(this.actionControl.value))
    ]).subscribe(() => this.applyFilters());

    this.loadLedger();
  }

  loadLedger(): void {
    this.api.getLedger(this.limitControl.value).subscribe({
      next: (response) => {
        this.records = response.records.slice().reverse();
        this.actionOptions = Array.from(new Set(this.records.map((record) => formatValue(record.action)).filter((value) => value !== '--'))).sort();
        this.state.ledger.set(response);
        this.applyFilters();
      },
      error: (error: Error) => this.toast.show(error.message, 'danger')
    });
  }

  applyFilters(): void {
    const search = this.searchControl.value.trim().toLowerCase();
    const action = this.actionControl.value;
    this.filteredRecords = this.records.filter((record) => {
      const matchesAction = !action || record.action === action;
      const haystack = [
        record.seq,
        record.ts,
        record.comm,
        record.argv,
        record.action,
        record.target,
        record.user,
        record.session,
        record.hash
      ].map(formatValue).join(' ').toLowerCase();
      return matchesAction && (!search || haystack.includes(search));
    });
  }

  openRecord(record: LedgerRecord): void {
    this.selectedRecord = record;
  }

  closeDrawer(): void {
    this.selectedRecord = null;
  }

  shortHash(value: string | null | undefined, size = 12): string {
    return shortHash(value, size);
  }
}
