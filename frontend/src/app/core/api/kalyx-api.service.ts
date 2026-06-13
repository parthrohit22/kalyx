import {
  HttpClient,
  HttpErrorResponse,
  HttpHeaders,
  HttpParams,
} from '@angular/common/http';
import { Inject, Injectable } from '@angular/core';
import { Observable, catchError, throwError } from 'rxjs';

import {
  KALYX_API_CONFIG,
  KALYX_API_KEY_HEADER,
  KalyxApiConfig,
} from './kalyx-api.config';
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

interface ApiRequestOptions {
  headers?: HttpHeaders;
  params?: HttpParams;
}

@Injectable({ providedIn: 'root' })
export class KalyxApiService {
  constructor(
    private readonly http: HttpClient,
    @Inject(KALYX_API_CONFIG) private readonly config: KalyxApiConfig,
  ) {}

  getStatus(): Observable<StatusResponse> {
    return this.http
      .get<StatusResponse>(this.apiUrl('/status'), this.requestOptions())
      .pipe(catchError((error) => this.handleError(error, 'GET /status')));
  }

  verifyLedger(): Observable<VerificationResponse> {
    return this.http
      .post<VerificationResponse>(
        this.apiUrl('/verify'),
        {},
        this.requestOptions(),
      )
      .pipe(catchError((error) => this.handleError(error, 'POST /verify')));
  }

  ingestStructuredEvent(
    payload: StructuredIngestRequest,
  ): Observable<IngestResponse> {
    return this.http
      .post<IngestResponse>(
        this.apiUrl('/ingest'),
        payload,
        this.requestOptions(),
      )
      .pipe(catchError((error) => this.handleError(error, 'POST /ingest')));
  }

  ingestRawLine(payload: RawLineIngestRequest): Observable<IngestResponse> {
    return this.http
      .post<IngestResponse>(
        this.apiUrl('/ingest'),
        payload,
        this.requestOptions(),
      )
      .pipe(catchError((error) => this.handleError(error, 'POST /ingest')));
  }

  runDetection(): Observable<DetectionResponse> {
    return this.http
      .post<DetectionResponse>(
        this.apiUrl('/detect'),
        {},
        this.requestOptions(),
      )
      .pipe(catchError((error) => this.handleError(error, 'POST /detect')));
  }

  getAlerts(): Observable<AlertResponse> {
    return this.http
      .get<AlertResponse>(this.apiUrl('/alerts'), this.requestOptions())
      .pipe(catchError((error) => this.handleError(error, 'GET /alerts')));
  }

  getLedger(limit = 50): Observable<LedgerResponse> {
    const clamped = Math.min(500, Math.max(1, Math.trunc(limit)));
    const params = new HttpParams().set('limit', String(clamped));

    return this.http
      .get<LedgerResponse>(
        this.apiUrl('/ledger'),
        this.requestOptions({ params }),
      )
      .pipe(catchError((error) => this.handleError(error, 'GET /ledger')));
  }

  private apiUrl(path: string): string {
    const baseUrl = this.config.apiBaseUrl.trim().replace(/\/+$/, '');
    return `${baseUrl}${path}`;
  }

  private requestOptions(extra: ApiRequestOptions = {}): ApiRequestOptions {
    const apiKey = this.config.apiKey?.trim();

    if (!apiKey) {
      return extra;
    }

    const headers = (extra.headers ?? new HttpHeaders()).set(
      KALYX_API_KEY_HEADER,
      apiKey,
    );

    return {
      ...extra,
      headers,
    };
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
    if (error.status === 401) {
      return 'Authentication failed. Check frontend API key configuration.';
    }

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
