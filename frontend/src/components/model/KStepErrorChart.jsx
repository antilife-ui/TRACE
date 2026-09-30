import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';

/** data: [{ horizon, error }] */
export default function KStepErrorChart({ data }) {
  return (
    <div className="h-[160px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
          <CartesianGrid stroke="#1C232B" vertical={false} />
          <XAxis
            dataKey="horizon"
            tickFormatter={(h) => `+${h}`}
            stroke="#5A6570"
            tick={{ fontSize: 10, fill: '#8A97A0' }}
            axisLine={{ stroke: '#232B32' }}
            tickLine={false}
          />
          <YAxis
            stroke="#5A6570"
            tick={{ fontSize: 10, fill: '#8A97A0' }}
            axisLine={{ stroke: '#232B32' }}
            tickLine={false}
            width={30}
          />
          <Tooltip
            cursor={{ fill: 'rgba(53,184,217,0.06)' }}
            contentStyle={{
              background: '#161C22',
              border: '1px solid #2E3944',
              fontSize: 11,
              fontFamily: 'IBM Plex Mono',
            }}
            labelFormatter={(h) => `+${h} window`}
          />
          <Bar dataKey="error" fill="#35B8D9" radius={[1, 1, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
