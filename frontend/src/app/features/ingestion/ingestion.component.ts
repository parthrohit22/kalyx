import { Component, inject } from '@angular/core';
import { NgIf } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { KalyxApiService } from '../../core/api/kalyx-api.service';
import { IngestResponse } from '../../core/models/ingest.model';
import { shortHash } from '../../core/models/ui.model';
import { DashboardStateService } from '../../core/state/dashboard-state.service';
import { JsonViewerComponent } from '../../shared/json-viewer/json-viewer.component';
import { ToastService } from '../../shared/toast/toast.service';

type IngestionTab = 'structured' | 'raw';
type StructuredField = 'comm' | 'pid' | 'ppid' | 'argv' | 'ret' | 'uid' | 'source';
type RawField = 'raw_line' | 'source';

@Component({
  selector: 'app-ingestion',
  standalone: true,
  imports: [NgIf, ReactiveFormsModule, JsonViewerComponent],
  template: `
    <section class="page">
      <div class="page-heading">
        <div>
          <p>POST /ingest</p>
          <h2>Ingestion</h2>
        </div>
      </div>

      <section class="panel">
        <div class="tabs">
          <button type="button" [class.active]="activeTab === 'structured'" (click)="activeTab = 'structured'">Structured Event</button>
          <button type="button" [class.active]="activeTab === 'raw'" (click)="activeTab = 'raw'">Raw Line</button>
        </div>

        <form *ngIf="activeTab === 'structured'" class="form-grid" [formGroup]="structuredForm" (ngSubmit)="submitStructured()">
          <label><span>Command</span><input formControlName="comm"><small>{{ fieldError('comm') }}</small></label>
          <label><span>PID</span><input type="number" formControlName="pid"><small>{{ fieldError('pid') }}</small></label>
          <label><span>PPID</span><input type="number" formControlName="ppid"><small>{{ fieldError('ppid') }}</small></label>
          <label><span>Return Code</span><input type="number" formControlName="ret"></label>
          <label><span>UID</span><input type="number" formControlName="uid"></label>
          <label><span>Source</span><input formControlName="source"><small>{{ fieldError('source') }}</small></label>
          <label class="wide"><span>Arguments</span><input formControlName="argv"></label>
          <div class="form-actions"><button type="submit" class="button" [disabled]="structuredForm.invalid || loading">Ingest Structured Event</button></div>
        </form>

        <form *ngIf="activeTab === 'raw'" class="raw-form" [formGroup]="rawForm" (ngSubmit)="submitRaw()">
          <label><span>Raw execsnoop-style line</span><textarea rows="8" formControlName="raw_line"></textarea><small>{{ rawFieldError('raw_line') }}</small></label>
          <label><span>Source</span><input formControlName="source"><small>{{ rawFieldError('source') }}</small></label>
          <div class="form-actions"><button type="submit" class="button" [disabled]="rawForm.invalid || loading">Ingest Raw Line</button></div>
        </form>
      </section>

      <section class="success-card" *ngIf="result?.record">
        <div>
          <p>Ingest result</p>
          <h3>Evidence appended</h3>
        </div>
        <dl class="fact-grid">
          <div><dt>Seq</dt><dd>{{ result?.record?.seq ?? '--' }}</dd></div>
          <div><dt>Command</dt><dd>{{ result?.record?.comm || '--' }}</dd></div>
          <div><dt>Previous Hash</dt><dd>{{ shortHash(result?.record?.prev_hash) }}</dd></div>
          <div><dt>Hash</dt><dd>{{ shortHash(result?.record?.hash) }}</dd></div>
        </dl>
      </section>

      <app-json-viewer label="Raw ingest response" [value]="result" />
    </section>
  `
})
export class IngestionComponent {
  private readonly fb = inject(FormBuilder);

  activeTab: IngestionTab = 'structured';
  loading = false;
  result: IngestResponse | null = null;

  readonly structuredForm = this.fb.nonNullable.group({
    comm: ['touch', [Validators.required]],
    pid: [5000, [Validators.required, Validators.min(1)]],
    ppid: [4000, [Validators.required, Validators.min(0)]],
    argv: ['touch /tmp/kalyx-angular-demo.txt'],
    ret: [0],
    uid: [1000, [Validators.min(0)]],
    source: ['angular_console', [Validators.required]]
  });

  readonly rawForm = this.fb.nonNullable.group({
    raw_line: ['1000 touch 5000 4000 0 touch /tmp/kalyx-raw-angular.txt', [Validators.required]],
    source: ['angular_console_raw', [Validators.required]]
  });

  constructor(
    private readonly api: KalyxApiService,
    private readonly state: DashboardStateService,
    private readonly toast: ToastService
  ) {}

  submitStructured(): void {
    if (this.structuredForm.invalid) {
      this.structuredForm.markAllAsTouched();
      return;
    }

    const value = this.structuredForm.getRawValue();
    this.loading = true;
    this.api.ingestStructuredEvent({
      event: {
        comm: value.comm,
        pid: value.pid,
        ppid: value.ppid,
        argv: value.argv,
        ret: value.ret,
        uid: value.uid
      },
      source: value.source
    }).subscribe(this.ingestObserver());
  }

  submitRaw(): void {
    if (this.rawForm.invalid) {
      this.rawForm.markAllAsTouched();
      return;
    }

    const value = this.rawForm.getRawValue();
    this.loading = true;
    this.api.ingestRawLine({
      raw_line: value.raw_line,
      source: value.source
    }).subscribe(this.ingestObserver());
  }

  fieldError(field: StructuredField): string {
    const control = this.structuredForm.controls[field];
    if (!control.touched || control.valid) {
      return '';
    }

    return 'Check this field before submitting.';
  }

  rawFieldError(field: RawField): string {
    const control = this.rawForm.controls[field];
    if (!control.touched || control.valid) {
      return '';
    }

    return 'This field is required.';
  }

  private ingestObserver() {
    return {
      next: (response: IngestResponse) => {
        this.result = response;
        this.loading = false;
        this.toast.show(`Evidence appended at seq ${response.record?.seq ?? '--'}`, 'success');
        this.state.refreshSummary();
      },
      error: (error: Error) => {
        this.loading = false;
        this.toast.show(error.message, 'danger');
      }
    };
  }

  shortHash(value: string | null | undefined): string {
    return shortHash(value);
  }
}
