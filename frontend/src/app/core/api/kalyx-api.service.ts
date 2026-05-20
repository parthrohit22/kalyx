import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, catchError, throwError } from 'rxjs';

import { AlertResponse } from '../models/alert.model';
import { DetectionResponse } from '../models/detection.model';
import {
  IngestResponse,
  RawLineIngestRequest,
  StructuredIngestRequest,
} from '../models/ingest.model';
import { LedgerResponse } from '../models/ledger.model';
import {
  StatusResponse,
  VerificationResponse,
} from '../models/verification.model';

@Injectable({ providedIn: 'root' })
export class KalyxApiService {
  private readonly apiBaseUrl = 'http://127.0.0.1:8000';

  constructor(private readonly http: HttpClient) {}

  getStatus(): Observable<StatusResponse> {
    return this.http
      .get<StatusResponse>(`${this.apiBaseUrl}/status`)
      .pipe(catchError((error) => this.handleError(error, 'GET /status')));
  }

  verifyLedger(): Observable<VerificationResponse> {
    return this.http
      .post<VerificationResponse>(`${this.apiBaseUrl}/verify`, {})
      .pipe(catchError((error) => this.handleError(error, 'POST /verify')));
  }

  ingestStructuredEvent(
    payload: StructuredIngestRequest,
  ): Observable<IngestResponse> {
    return this.http
      .post<IngestResponse>(`${this.apiBaseUrl}/ingest`, payload)
      .pipe(catchError((error) => this.handleError(error, 'POST /ingest')));
  }

  ingestRawLine(payload: RawLineIngestRequest): Observable<IngestResponse> {
    return this.http
      .post<IngestResponse>(`${this.apiBaseUrl}/ingest`, payload)
      .pipe(catchError((error) => this.handleError(error, 'POST /ingest')));
  }

  runDetection(): Observable<DetectionResponse> {
    return this.http
      .post<DetectionResponse>(`${this.apiBaseUrl}/detect`, {})
      .pipe(catchError((error) => this.handleError(error, 'POST /detect')));
  }

  getAlerts(): Observable<AlertResponse> {
    return this.http
      .get<AlertResponse>(`${this.apiBaseUrl}/alerts`)
      .pipe(catchError((error) => this.handleError(error, 'GET /alerts')));
  }

  getLedger(limit = 50): Observable<LedgerResponse> {
    const clamped = Math.min(500, Math.max(1, Math.trunc(limit)));
    const params = new HttpParams().set('limit', String(clamped));

    return this.http
      .get<LedgerResponse>(`${this.apiBaseUrl}/ledger`, { params })
      .pipe(catchError((error) => this.handleError(error, 'GET /ledger')));
  }

  private handleError(
    error: HttpErrorResponse,
    operation: string,
  ): Observable<never> {
    return throwError(
      () => new Error(`${operation} failed: ${this.extractErrorMessage(error)}`),
    );
  }

  private extractErrorMessage(error: HttpErrorResponse): string {
    const body = error.error as unknown;

    if (typeof body === 'string' && body.trim()) {
      return body;
    }

    if (this.hasDetailString(body)) {
      return body.detail;
    }

    if (this.hasDetailList(body)) {
      return body.detail.map((item) => item.msg).join('; ');
    }

    return error.message || `HTTP ${error.status}`;
  }

  private hasDetailString(value: unknown): value is { detail: string } {
    return (
      typeof value === 'object' &&
      value !== null &&
      'detail' in value &&
      typeof (value as { detail: unknown }).detail === 'string'
    );
  }

  private hasDetailList(value: unknown): value is { detail: Array<{ msg: string }> } {
    return (
      typeof value === 'object' &&
      value !== null &&
      'detail' in value &&
      Array.isArray((value as { detail: unknown }).detail)
    );
  }
}