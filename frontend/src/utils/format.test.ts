import { describe, expect, it } from 'vitest';
import {
  DEFAULT_CURRENCY,
  formatCurrency,
  formatCurrencyCompact,
  formatDateTime,
  humanize,
} from './format';

describe('formatCurrency', () => {
  it('formats in the currency the record was booked in', () => {
    expect(formatCurrency('125.50', 'USD')).toBe('$125.50');
    expect(formatCurrency(125.5, 'EUR')).toBe('€125.50');
    expect(formatCurrency('1000', 'JPY')).toContain('¥');
  });

  it('accepts lowercase currency codes', () => {
    expect(formatCurrency('10', 'gbp')).toBe(formatCurrency('10', 'GBP'));
  });

  it('falls back to the platform default for missing or bogus codes', () => {
    expect(formatCurrency('10')).toBe(formatCurrency('10', DEFAULT_CURRENCY));
    expect(formatCurrency('10', 'not-a-code')).toBe(formatCurrency('10', DEFAULT_CURRENCY));
  });

  it('compacts chart axis values without losing the currency', () => {
    expect(formatCurrencyCompact(1200, 'USD')).toBe('$1.2K');
    expect(formatCurrencyCompact(1200, 'EUR')).toBe('€1.2K');
  });
});

describe('humanize', () => {
  it('turns backend enum values into labels', () => {
    expect(humanize('info_requested')).toBe('Info Requested');
    expect(humanize(null)).toBe('—');
  });
});

describe('formatDateTime', () => {
  it('renders an ISO timestamp', () => {
    expect(formatDateTime('2026-08-18T13:18:00Z')).toMatch(/2026/);
  });
});
