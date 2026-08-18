import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { RefundTrendPoint } from '../../../types';
import { formatCurrency } from '../../../utils/format';

/** Refund volume over the trailing window, rendered from the dense daily series. */
export function RefundTrendChart({ points }: { points: RefundTrendPoint[] }): JSX.Element {
  const data = points.map((point) => ({
    day: point.day.slice(5),
    amount: Number(point.amount),
    count: point.count,
  }));

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
          <defs>
            <linearGradient id="refundAmount" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#2563eb" stopOpacity={0.35} />
              <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
          <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#64748b' }} interval={4} />
          <YAxis
            tick={{ fontSize: 11, fill: '#64748b' }}
            tickFormatter={(value: number) => `$${Math.round(value / 100) / 10}k`}
            width={48}
          />
          <Tooltip
            formatter={(value: number, name) =>
              name === 'amount' ? formatCurrency(value) : `${value} refunds`
            }
            labelFormatter={(label: string) => `Day ${label}`}
          />
          <Area
            type="monotone"
            dataKey="amount"
            stroke="#2563eb"
            strokeWidth={2}
            fill="url(#refundAmount)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
