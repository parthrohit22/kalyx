import { DashboardStateService } from './dashboard-state.service';
import { KalyxApiService } from '../api/kalyx-api.service';
import { StatusResponse, VerificationResponse } from '../models/verification.model';

describe('DashboardStateService trustDisplayState', () => {
  let service: DashboardStateService;

  beforeEach(() => {
    service = new DashboardStateService({} as KalyxApiService);
  });

  function verification(source: Partial<VerificationResponse>): Partial<VerificationResponse> {
    return source;
  }

  function status(source: Partial<StatusResponse>): Partial<StatusResponse> {
    return source;
  }

  it('displays VERIFIED when backend trust_state is VERIFIED and verification is valid', () => {
    expect(
      service.trustDisplayState({
        trust_state: 'VERIFIED',
        verification_valid: true,
      } as Partial<StatusResponse>),
    ).toBe('VERIFIED');
  });

  it('does not upgrade UNTRUSTED trust_state when verification_valid is true', () => {
    expect(
      service.trustDisplayState(status({
        trust_state: 'UNTRUSTED',
        verification_valid: true,
      })),
    ).toBe('UNTRUSTED');
  });

  it('does not upgrade UNTRUSTED trust_state when status is VALID', () => {
    expect(
      service.trustDisplayState(verification({
        trust_state: 'UNTRUSTED',
        status: 'VALID',
        valid: true,
      })),
    ).toBe('UNTRUSTED');
  });

  it('displays UNTRUSTED when backend trust_state is UNTRUSTED and verification is invalid', () => {
    expect(
      service.trustDisplayState(verification({
        trust_state: 'UNTRUSTED',
        status: 'TAMPERED',
        valid: false,
      })),
    ).toBe('UNTRUSTED');
  });

  it('falls back to verification status when trust_state is missing', () => {
    expect(
      service.trustDisplayState(verification({
        status: 'VALID',
        valid: true,
      })),
    ).toBe('VERIFIED');
  });

  it('does not infer VERIFIED from valid flags when trust_state is unexpected', () => {
    expect(
      service.trustDisplayState(status({
        trust_state: 'MAYBE_TRUSTED',
        verification_status: 'VALID',
        verification_valid: true,
      })),
    ).toBe('UNKNOWN');
  });
});
