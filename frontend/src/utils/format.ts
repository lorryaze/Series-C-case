/** Display helpers shared across the tools. */

export const DEFAULT_CURRENCY = 'USD';

const CURRENCY_CODE = /^[A-Za-z]{3}$/;
const formatters = new Map<string, Intl.NumberFormat>();

function formatterFor(currency: string, compact: boolean): Intl.NumberFormat {
  const code = CURRENCY_CODE.test(currency) ? currency.toUpperCase() : DEFAULT_CURRENCY;
  const cacheKey = compact ? `${code}:compact` : code;
  const cached = formatters.get(cacheKey);
  if (cached) return cached;

  const formatter = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: code,
    ...(compact
      ? { notation: 'compact', maximumFractionDigits: 1 }
      : { maximumFractionDigits: 2 }),
  });
  formatters.set(cacheKey, formatter);
  return formatter;
}

export function formatCurrency(
  amount: string | number,
  currency: string = DEFAULT_CURRENCY,
): string {
  return formatterFor(currency, false).format(Number(amount));
}

/** Short form for chart axes, e.g. `$1.2K`. */
export function formatCurrencyCompact(
  amount: string | number,
  currency: string = DEFAULT_CURRENCY,
): string {
  return formatterFor(currency, true).format(Number(amount));
}

export function formatDate(value: string | null): string {
  if (!value) return '—';
  return new Date(value).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
  });
}

export function formatDateTime(value: string | null): string {
  if (!value) return '—';
  return new Date(value).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatHours(hours: number | null): string {
  if (hours === null) return '—';
  if (hours < 24) return `${hours.toFixed(1)}h`;
  return `${(hours / 24).toFixed(1)}d`;
}

/** Turn a snake_case enum value into a human label. */
export function humanize(value: string | null | undefined): string {
  if (!value) return '—';
  return value
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}
