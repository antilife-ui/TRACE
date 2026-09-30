// Mock data generators.
//
// These shapes mirror the API contracts defined in the TRACE frontend
// spec (NetworkState, Forecast, RiskTimeline, AttackStage, AttackPath,
// TelemetryFlow, Explanation, Incident, ModelStatus) so that swapping mock
// functions for real fetch calls in src/api/*.js requires no component
// changes — only the api layer changes.

const STAGES = [
  'Reconnaissance',
  'Initial Access',
  'Lateral Movement',
  'Command & Control',
  'Exfiltration',
];

function seedRandom(seed) {
  let s = seed;
  return () => {
    s = (s * 9301 + 49297) % 233280;
    return s / 233280;
  };
}

const rand = seedRandom(42);

export function generateNetworkState() {
  return {
    timestamp: new Date().toISOString(),
    windowId: 'window-482',
    riskScore: 0.72,
    stage: {
      name: 'Lateral Movement',
      status: 'current',
      confidence: 0.81,
    },
    metrics: {
      flowCount: 1284,
      packetCount: 84210,
      byteCount: 2_340_000,
    },
    features: {
      flowRate: 12.4,
      iatMean: 0.21,
    },
  };
}

export function generateForecast(horizon = 5) {
  const startRisk = 0.72;
  const states = Array.from({ length: horizon }, (_, i) => {
    const step = i + 1;
    const risk = Math.min(0.97, startRisk + step * 0.035 + rand() * 0.02);
    return {
      step,
      windowId: `forecast-${step}`,
      riskScore: Number(risk.toFixed(2)),
      stage: STAGES[Math.min(STAGES.length - 1, 2 + Math.floor(step / 3))],
    };
  });
  const scores = states.map((s) => s.riskScore);
  return {
    generatedAt: new Date().toISOString(),
    currentWindowId: 'window-482',
    horizon,
    // Matches the real contract: a horizon-weighted average, not just the last step.
    riskScore: Number((scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(2)),
    peakRisk: Math.max(...scores, startRisk),
    modelStable: true,
    states: states.map((s) => ({ ...s, modelStable: true })),
  };
}

export function generateRiskTimeline() {
  const observed = Array.from({ length: 12 }, (_, i) => ({
    timestamp: new Date(Date.now() - (12 - i) * 60000).toISOString(),
    value: Number((0.3 + i * 0.035 + rand() * 0.03).toFixed(2)),
    kind: 'observed',
  }));
  const forecast = Array.from({ length: 5 }, (_, i) => ({
    timestamp: new Date(Date.now() + (i + 1) * 60000).toISOString(),
    value: Number((0.72 + (i + 1) * 0.045 + rand() * 0.02).toFixed(2)),
    kind: 'predicted',
  }));
  return [...observed, ...forecast];
}

// Demo-mode only (gated by DEMO_MODE in src/api/forecastApi.js) -- these
// confidence numbers are illustrative sample data, never sent by the real
// backend. dashboard_routes.py's /forecast/attack-stages returns
// confidence: null / confidenceType: "not_calibrated" for the same reason
// no fabricated confidence is used anywhere else in production.
export function generateAttackStages() {
  return [
    { name: 'Reconnaissance', status: 'observed', score: 1.0, confidence: 0.95, windowId: 'w-470' },
    { name: 'Initial Access', status: 'observed', score: 0.91, confidence: 0.88, windowId: 'w-475' },
    { name: 'Lateral Movement', status: 'current', score: 0.81, confidence: 0.81, windowId: 'w-482' },
    { name: 'Command & Control', status: 'predicted', score: 0.63, confidence: 0.58, windowId: 'forecast-2' },
    { name: 'Exfiltration', status: 'predicted', score: 0.41, confidence: 0.37, windowId: 'forecast-4' },
  ];
}

export function generateAttackPath() {
  return {
    nodes: [
      { id: 'attacker', type: 'attacker', label: 'External Host', ip: '203.0.113.44' },
      { id: 'gateway', type: 'gateway', label: 'Edge Gateway', ip: '10.0.0.1' },
      { id: 'server-a', type: 'server', label: 'Server A', ip: '10.0.2.14' },
      { id: 'host-a', type: 'host', label: 'Host A', ip: '10.0.3.22' },
      { id: 'host-b', type: 'host', label: 'Host B', ip: '10.0.3.41' },
      { id: 'server-b', type: 'server', label: 'Server B (predicted target)', ip: '10.0.2.19' },
    ],
    edges: [
      { source: 'attacker', target: 'gateway', kind: 'observed', riskScore: 0.88, protocol: 'TCP', port: 443 },
      { source: 'gateway', target: 'server-a', kind: 'observed', riskScore: 0.74, protocol: 'TCP', port: 22 },
      { source: 'server-a', target: 'host-a', kind: 'observed', riskScore: 0.69, protocol: 'SMB', port: 445 },
      { source: 'host-a', target: 'host-b', kind: 'observed', riskScore: 0.62, protocol: 'SMB', port: 445 },
      { source: 'host-b', target: 'server-b', kind: 'predicted', riskScore: 0.58, protocol: 'TCP', port: 3389 },
    ],
  };
}

const PROTOCOLS = ['TCP', 'UDP', 'TCP', 'TCP', 'ICMP'];

export function generateTelemetry(count = 240) {
  return Array.from({ length: count }, (_, i) => {
    const risk = Number((rand()).toFixed(2));
    return {
      id: `flow-${1000 + i}`,
      timestamp: new Date(Date.now() - i * 4000).toISOString(),
      sourceIp: `10.0.${Math.floor(rand() * 4)}.${10 + (i % 240)}`,
      destinationIp: `10.0.${Math.floor(rand() * 4)}.${20 + (i % 200)}`,
      sourcePort: 1024 + Math.floor(rand() * 60000),
      destinationPort: [22, 443, 445, 3389, 80][i % 5],
      protocol: PROTOCOLS[i % PROTOCOLS.length],
      flowDuration: Math.floor(rand() * 4000) + 20,
      packets: Math.floor(rand() * 200) + 1,
      bytes: Math.floor(rand() * 500000) + 512,
      riskScore: risk,
      stage: STAGES[Math.min(STAGES.length - 1, Math.floor(risk * STAGES.length))],
    };
  });
}

export function generateExplanation() {
  return {
    forecastId: 'forecast-123',
    method: 'perturbation',
    features: [
      { name: 'SYN Flag Count', value: 8, contribution: 0.31, direction: 'positive' },
      { name: 'Flow Rate', value: 12.4, contribution: 0.21, direction: 'positive' },
      { name: 'IAT Variance', value: 0.44, contribution: 0.14, direction: 'positive' },
      { name: 'Fwd/Bwd Packet Ratio', value: 2.1, contribution: 0.1, direction: 'positive' },
      { name: 'Packet Size Std. Dev.', value: 340, contribution: 0.07, direction: 'negative' },
    ],
  };
}

export function generateIncidents() {
  return [
    {
      id: 'INC-2026-0091',
      firstObserved: new Date(Date.now() - 40 * 60000).toISOString(),
      lastUpdated: new Date(Date.now() - 2 * 60000).toISOString(),
      riskScore: 0.81,
      currentStage: 'Lateral Movement',
      forecastStage: 'Command & Control',
      affectedHosts: ['10.0.3.22', '10.0.3.41'],
      status: 'INVESTIGATING',
    },
    {
      id: 'INC-2026-0088',
      firstObserved: new Date(Date.now() - 5 * 3600000).toISOString(),
      lastUpdated: new Date(Date.now() - 3 * 3600000).toISOString(),
      riskScore: 0.44,
      currentStage: 'Reconnaissance',
      forecastStage: 'Initial Access',
      affectedHosts: ['10.0.1.9'],
      status: 'CONTAINED',
    },
    {
      id: 'INC-2026-0081',
      firstObserved: new Date(Date.now() - 2 * 86400000).toISOString(),
      lastUpdated: new Date(Date.now() - 1.5 * 86400000).toISOString(),
      riskScore: 0.93,
      currentStage: 'Exfiltration',
      forecastStage: 'Exfiltration',
      affectedHosts: ['10.0.2.14', '10.0.2.19', '10.0.3.41'],
      status: 'RESOLVED',
    },
  ];
}

export function generateModelStatus() {
  return {
    name: 'TRACE World Model',
    type: 'GRU',
    status: 'ready',
    version: '0.4.2-dev',
    stateFeatures: 40,
    sequenceLength: 20,
    windowDurationSec: 5,
    forecastHorizon: 5,
    device: 'cuda',
    inferenceLatencyMs: 42,
    lastTrained: new Date(Date.now() - 3 * 86400000).toISOString(),
    trainingCorpus: {
      name: 'CIC-IDS2017 (cleaned)',
      recordCount: 2_574_264,
    },
    memory: {
      gpuVramUsedMb: 1840,
      gpuVramTotalMb: 4096,
      ramUsedMb: 4920,
      ramTotalMb: 8192,
    },
    performance: {
      f1: 0.91,
      precision: 0.89,
      recall: 0.93,
      rocAuc: 0.96,
      leadTimeSec: 18,
      kStepError: [
        { horizon: 1, error: 0.27 },
        { horizon: 2, error: 0.31 },
        { horizon: 3, error: 0.34 },
        { horizon: 4, error: 0.38 },
        { horizon: 5, error: 0.43 },
      ],
    },
  };
}
