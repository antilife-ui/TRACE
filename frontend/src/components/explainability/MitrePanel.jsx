import StatusBadge from '../common/StatusBadge.jsx';
import { riskLevel } from '../../utils/formatters.js';
import { DEMO_MODE } from '../../api/client.js';

// Static ATT&CK tactic/technique reference table. There is no backend
// endpoint that derives this mapping (or its confidence) from the live
// model -- it is illustrative domain reference content, not model output.
// The confidence numbers below are demo-only sample values; production
// must not present them as calibrated model confidence (see README,
// "What's real vs. placeholder in this integration").
const MAPPING = [
  { tactic: 'Reconnaissance', technique: 'Active Scanning (T1595)', status: 'observed', confidence: 0.95 },
  { tactic: 'Initial Access', technique: 'Exploit Public-Facing Application (T1190)', status: 'observed', confidence: 0.88 },
  { tactic: 'Lateral Movement', technique: 'Remote Services: SMB/Windows Admin Shares (T1021.002)', status: 'inferred', confidence: 0.81 },
  { tactic: 'Command and Control', technique: 'Application Layer Protocol (T1071)', status: 'predicted', confidence: 0.58 },
  { tactic: 'Exfiltration', technique: 'Exfiltration Over C2 Channel (T1041)', status: 'predicted', confidence: 0.37 },
];

export default function MitrePanel() {
  return (
    <div>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-left text-text-muted uppercase tracking-wide text-[10px] border-b border-border">
            <th className="py-2 pr-3">Tactic</th>
            <th className="py-2 pr-3">Technique</th>
            <th className="py-2 pr-3">Status</th>
            {DEMO_MODE && <th className="py-2">Confidence</th>}
          </tr>
        </thead>
        <tbody>
          {MAPPING.map((m) => (
            <tr key={m.technique} className="border-b border-border/60">
              <td className="py-2 pr-3 text-text-primary">{m.tactic}</td>
              <td className="py-2 pr-3 font-mono text-text-secondary">{m.technique}</td>
              <td className="py-2 pr-3">
                <StatusBadge
                  level={m.status === 'predicted' ? 'predicted' : m.status === 'observed' ? 'observed' : riskLevel(DEMO_MODE ? m.confidence : null)}
                  label={m.status}
                  dense
                />
              </td>
              {/* Confidence is demo-only sample data (see note above the MAPPING
                  const) -- never rendered outside demo mode rather than shown
                  as if it were real model confidence. */}
              {DEMO_MODE && <td className="py-2 font-mono">{Math.round(m.confidence * 100)}%</td>}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-xs text-text-muted mt-3 leading-relaxed">
        {DEMO_MODE
          ? 'Mappings are a static reference table, shown here with illustrative sample confidence values — a single network feature does not confirm a specific technique.'
          : 'Static ATT&CK reference mapping for context only — not derived from live model output, and no calibrated confidence is available for it.'}
      </p>
    </div>
  );
}
