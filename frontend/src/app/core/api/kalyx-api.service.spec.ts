import { HttpClient, HttpErrorResponse, HttpHeaders } from '@angular/common/http';
import { Observable, of, throwError } from 'rxjs';

import {
  KALYX_API_KEY_HEADER,
  KalyxApiConfig,
} from './kalyx-api.config';
import { KalyxApiService } from './kalyx-api.service';

interface CapturedRequest {
  method: 'GET' | 'POST';
  url: string;
  body?: unknown;
  options?: { headers?: HttpHeaders };
}

class FakeHttpClient {
  lastRequest: CapturedRequest | null = null;
  error: HttpErrorResponse | null = null;

  get<T>(url: string, options?: { headers?: HttpHeaders }): Observable<T> {
    this.lastRequest = {
      method: 'GET',
      url,
      options,
    };

    return this.response<T>();
  }

  post<T>(
    url: string,
    body: unknown,
    options?: { headers?: HttpHeaders },
  ): Observable<T> {
    this.lastRequest = {
      method: 'POST',
      url,
      body,
      options,
    };

    return this.response<T>();
  }

  private response<T>(): Observable<T> {
    if (this.error) {
      return throwError(() => this.error);
    }

    return of({} as T);
  }
}

describe('KalyxApiService API key support', () => {
  function createService(
    config: KalyxApiConfig,
  ): { service: KalyxApiService; http: FakeHttpClient } {
    const http = new FakeHttpClient();
    const service = new KalyxApiService(http as unknown as HttpClient, config);

    return {
      service,
      http,
    };
  }

  function headerValue(http: FakeHttpClient): string | null {
    return http.lastRequest?.options?.headers?.get(KALYX_API_KEY_HEADER) ?? null;
  }

  it('attaches the configured API key header to protected requests', () => {
    const { service, http } = createService({
      apiBaseUrl: 'http://backend.test',
      apiKey: 'demo-key',
    });

    service.verifyLedger().subscribe();
    expect(headerValue(http)).toBe('demo-key');

    service.ingestRawLine({
      raw_line: '1000 touch 5000 4000 0 touch /tmp/kalyx.txt',
      source: 'spec',
    }).subscribe();
    expect(headerValue(http)).toBe('demo-key');

    service.runDetection().subscribe();
    expect(headerValue(http)).toBe('demo-key');

    service.anchorLatestCheckpoint().subscribe();
    expect(headerValue(http)).toBe('demo-key');
  });

  it('does not send the API key header when no key is configured', () => {
    const { service, http } = createService({
      apiBaseUrl: 'http://backend.test',
      apiKey: '',
    });

    service.verifyLedger().subscribe();

    expect(headerValue(http)).toBeNull();
  });

  it('returns a clear message for 401 authentication failures', () => {
    const { service, http } = createService({
      apiBaseUrl: 'http://backend.test',
      apiKey: 'wrong-key',
    });
    let message = '';

    http.error = new HttpErrorResponse({
      status: 401,
      statusText: 'Unauthorized',
      error: { detail: 'Missing or invalid API key' },
    });

    service.verifyLedger().subscribe({
      error: (error: Error) => {
        message = error.message;
      },
    });

    expect(message).toBe(
      'POST /verify failed: Authentication failed. Check frontend API key configuration.',
    );
  });

  it('calls the host anchor endpoints', () => {
    const { service, http } = createService({
      apiBaseUrl: 'http://backend.test/',
      apiKey: '',
    });

    service.getAnchorStatus().subscribe();
    expect(http.lastRequest?.method).toBe('GET');
    expect(http.lastRequest?.url).toBe('http://backend.test/anchor/status');

    service.anchorLatestCheckpoint().subscribe();
    expect(http.lastRequest?.method).toBe('POST');
    expect(http.lastRequest?.url).toBe('http://backend.test/anchor');
    expect(http.lastRequest?.body).toEqual({});
  });
});
