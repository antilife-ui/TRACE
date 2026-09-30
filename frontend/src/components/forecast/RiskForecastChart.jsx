import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from 'recharts';

function formatTick(iso) {
  const d = new Date(iso);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function TooltipContent({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const point = payload[0];
  const kind = point.dataKey === 'observedValue' ? 'Observed' : 'Forecast';
  return (
    <div className="bg-elevated border border-border-strong px-3 py-2 text-xs">
      <div className="text-text-muted mb-1">{formatTick(label)}</div>
      <div className="text-text-primary tabular font-mono">
        {kind} risk: {Math.round(point.value * 100)}%
      </div>
    </div>
  );
}

/** timeline: [{ timestamp, value, kind: 'observed' | 'predicted' }] */
export default function RiskForecastChart({ timeline }) {
  const firstPredictedIdx = timeline.findIndex((p) => p.kind === 'predicted');
  const chartData = timeline.map((p, i) => ({
    timestamp: p.timestamp,
    observedValue: p.kind === 'observed' ? p.value : i === firstPredictedIdx ? p.value : undefined,
    predictedValue: p.kind === 'predicted' ? p.value : i === firstPredictedIdx - 1 ? p.value : undefined,
  }));
  const nowTimestamp = timeline[firstPredictedIdx - 1]?.timestamp;

  return (
    <div className="h-[200px]">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
          <CartesianGrid stroke="#1C232B" vertical={false} />
          <XAxis
            dataKey="timestamp"
            tickFormatter={formatTick}
            stroke="#5A6570"
            tick={{ fontSize: 10, fill: '#8A97A0' }}
            axisLine={{ stroke: '#232B32' }}
            tickLine={false}
          />
          <YAxis
            domain={[0, 1]}
            tickFormatter={(v) => `${Math.round(v * 100)}%`}
            stroke="#5A6570"
            tick={{ fontSize: 10, fill: '#8A97A0' }}
            axisLine={{ stroke: '#232B32' }}
            tickLine={false}
            width={36}
          />
          <Tooltip content={<TooltipContent />} />
          {nowTimestamp && (
            <ReferenceLine
              x={nowTimestamp}
              stroke="#5A6570"
              strokeDasharray="2 2"
              label={{ value: 'NOW', fill: '#5A6570', fontSize: 10, position: 'insideTopRight' }}
            />
          )}
          <Line
            type="monotone"
            dataKey="observedValue"
            stroke="#35B8D9"
            strokeWidth={2}
            dot={false}
            connectNulls
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="predictedValue"
            stroke="#8B7FE8"
            strokeWidth={2}
            strokeDasharray="5 4"
            dot={false}
            connectNulls
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
