export type BadgeTone = 'success' | 'warning' | 'danger' | 'neutral';

export function toneForState(value: string | null | undefined): BadgeTone {
  const normalized = String(value ?? '').trim().toUpperCase().replace(/\s+/g, '_');

  if (
    [
      'VALID',
      'VERIFIED',
      'READY',
      'MATCHED',
      'MATCH',
      'TRUST_VERIFIED',
      'ACCEPTED',
      'ALREADY_ANCHORED',
    ].includes(normalized)
  ) {
    return 'success';
  }

  if (
    [
      'TAMPERED',
      'CORRUPTED',
      'ERROR',
      'FAILED',
      'UNTRUSTED',
      'DIVERGENCE',
      'UNREACHABLE',
      'REJECTED_INVALID',
      'REJECTED_STALE',
      'LEDGER_NOT_TRUSTED',
      'CHECKPOINT_NOT_ANCHORABLE',
      'INVALID_RESPONSE',
    ].includes(normalized)
  ) {
    return 'danger';
  }

  if (
    [
      'EMPTY',
      'NO_LEDGER',
      'NO_CHECKPOINT',
      'NO_ANCHOR',
      'AHEAD',
      'BEHIND',
      'PARTIALLY_TRUSTED',
      'SKIPPED',
      'WARNING',
    ].includes(normalized)
  ) {
    return 'warning';
  }

  return 'neutral';
}

export function shortHash(value: string | null | undefined, size = 12): string {
  if (!value) {
    return '--';
  }

  return value.length > size + 8 ? `${value.slice(0, size)}...${value.slice(-6)}` : value;
}

export function formatValue(value: unknown): string {
  return value === null || value === undefined || value === '' ? '--' : String(value);
}
