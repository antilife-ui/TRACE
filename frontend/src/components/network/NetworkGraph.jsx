import { useMemo, useState } from 'react';
import { layeredLayout } from './graphLayout.js';

const NODE_COLOR = {
  attacker: '#E5484D',
  gateway: '#8A97A0',
  server: '#35B8D9',
  host: '#8A97A0',
};

function NodeShape({ type, cx, cy, r, fill, stroke }) {
  if (type === 'attacker') {
    // Diamond
    const pts = [
      [cx, cy - r],
      [cx + r, cy],
      [cx, cy + r],
      [cx - r, cy],
    ]
      .map((p) => p.join(','))
      .join(' ');
    return <polygon points={pts} fill={fill} stroke={stroke} strokeWidth="1.5" />;
  }
  if (type === 'gateway') {
    return (
      <rect
        x={cx - r}
        y={cy - r}
        width={r * 2}
        height={r * 2}
        fill={fill}
        stroke={stroke}
        strokeWidth="1.5"
      />
    );
  }
  if (type === 'server') {
    return (
      <rect
        x={cx - r * 1.1}
        y={cy - r * 0.85}
        width={r * 2.2}
        height={r * 1.7}
        rx="2"
        fill={fill}
        stroke={stroke}
        strokeWidth="1.5"
      />
    );
  }
  return <circle cx={cx} cy={cy} r={r} fill={fill} stroke={stroke} strokeWidth="1.5" />;
}

/**
 * Renders an attack-path graph.
 * nodes: [{ id, type, label, ip }]
 * edges: [{ source, target, kind: 'observed' | 'predicted', riskScore, protocol, port }]
 */
export default function NetworkGraph({
  nodes,
  edges,
  height = 260,
  onNodeClick,
  onEdgeClick,
  selectedNodeId,
}) {
  const width = 760;
  const positions = useMemo(() => layeredLayout(nodes, edges, { width, height }), [nodes, edges, height]);
  const [hoverEdge, setHoverEdge] = useState(null);

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full" role="img" aria-label="Network attack path graph">
      <defs>
        <marker id="arrow-observed" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
          <path d="M0,0 L8,4 L0,8 Z" fill="#8A97A0" />
        </marker>
        <marker id="arrow-predicted" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
          <path d="M0,0 L8,4 L0,8 Z" fill="#8B7FE8" />
        </marker>
      </defs>

      {edges.map((e, i) => {
        const s = positions.get(e.source);
        const t = positions.get(e.target);
        if (!s || !t) return null;
        const isPredicted = e.kind === 'predicted';
        const key = `${e.source}-${e.target}-${i}`;
        return (
          <g key={key}>
            <line
              x1={s.x}
              y1={s.y}
              x2={t.x}
              y2={t.y}
              stroke={isPredicted ? '#8B7FE8' : '#8A97A0'}
              strokeWidth={hoverEdge === key ? 2.5 : 1.5}
              strokeDasharray={isPredicted ? '6 5' : undefined}
              className={isPredicted ? 'animate-dashFlow' : ''}
              markerEnd={`url(#arrow-${isPredicted ? 'predicted' : 'observed'})`}
              style={{ cursor: onEdgeClick ? 'pointer' : 'default' }}
              onMouseEnter={() => setHoverEdge(key)}
              onMouseLeave={() => setHoverEdge(null)}
              onClick={() => onEdgeClick?.(e)}
            />
            {!isPredicted && (
              <circle r="2.5" fill="#35B8D9">
                <animateMotion
                  dur="2.2s"
                  repeatCount="indefinite"
                  path={`M${s.x},${s.y} L${t.x},${t.y}`}
                />
              </circle>
            )}
          </g>
        );
      })}

      {nodes.map((n) => {
        const p = positions.get(n.id);
        if (!p) return null;
        const isSelected = selectedNodeId === n.id;
        const color = NODE_COLOR[n.type] || '#8A97A0';
        return (
          <g
            key={n.id}
            style={{ cursor: onNodeClick ? 'pointer' : 'default' }}
            onClick={() => onNodeClick?.(n)}
          >
            <NodeShape
              type={n.type}
              cx={p.x}
              cy={p.y}
              r={isSelected ? 15 : 13}
              fill="#10151A"
              stroke={color}
            />
            <text
              x={p.x}
              y={p.y + 28}
              textAnchor="middle"
              className="fill-text-secondary"
              fontSize="10"
              fontFamily="IBM Plex Sans"
            >
              {n.label}
            </text>
            {n.ip && (
              <text
                x={p.x}
                y={p.y + 40}
                textAnchor="middle"
                className="fill-text-muted"
                fontSize="9"
                fontFamily="IBM Plex Mono"
              >
                {n.ip}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}
