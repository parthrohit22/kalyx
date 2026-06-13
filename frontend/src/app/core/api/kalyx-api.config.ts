import { InjectionToken } from '@angular/core';

import { environment } from '../../../environments/environment';

export interface KalyxApiConfig {
  apiBaseUrl: string;
  apiKey?: string;
}

export const KALYX_API_KEY_HEADER = 'X-KALYX-API-Key';

export const KALYX_API_CONFIG = new InjectionToken<KalyxApiConfig>(
  'KALYX_API_CONFIG',
  {
    providedIn: 'root',
    factory: () => ({
      apiBaseUrl: environment.kalyxApi.apiBaseUrl,
      apiKey: environment.kalyxApi.apiKey,
    }),
  },
);
