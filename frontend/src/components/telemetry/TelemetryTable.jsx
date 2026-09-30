import { formatBytes, formatRelativeTime, riskLevel } from '../../utils/formatters.js';
import StatusBadge from '../common/StatusBadge.jsx';

const HEAD_CLS = 'text-left px-3 py-2 font-medium text-text-muted uppercase tracking-wide text-[10px]';
const CELL_CLS = 'px-3 py-2 font-mono text-[12px] text-text-primary whitespace-nowrap';

export default function TelemetryTable({ records, onSelectRow, selectedId }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs border-collapse">
        <thead className="border-b border-border sticky top-0 bg-surface">
          <tr>
            <th className={HEAD_CLS}>Time</th>
            <th className={HEAD_CLS}>Source</th>
            <th className={HEAD_CLS}>Destination</th>
            <th className={HEAD_CLS}>Proto</th>
            <th className={HEAD_CLS}>Bytes</th>
            <th className={HEAD_CLS}>Stage</th>
            <th className={HEAD_CLS}>Risk</th>
          </tr>
        </thead>
        <tbody>
          {records.map((r) => (
            <tr
              key={r.id}
              onClick={() => onSelectRow(r)}
              className={`border-b border-border/60 cursor-pointer hover:bg-elevated/60 ${
                selectedId === r.id ? 'bg-elevated' : ''
              }`}
            >
              <td className={`${CELL_CLS} text-text-muted`}>{formatRelativeTime(r.timestamp)}</td>
              <td className={CELL_CLS}>
                {r.sourceIp}:{r.sourcePort}
              </td>
              <td className={CELL_CLS}>
                {r.destinationIp}:{r.destinationPort}
              </td>
              <td className={CELL_CLS}>{r.protocol}</td>
              <td className={CELL_CLS}>{formatBytes(r.bytes)}</td>
              <td className={`${CELL_CLS} font-sans`}>{r.stage}</td>
              <td className={CELL_CLS}>
                <StatusBadge level={riskLevel(r.riskScore)} label={`${Math.round(r.riskScore * 100)}%`} dense />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
