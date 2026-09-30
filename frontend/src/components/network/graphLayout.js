// Simple layered (BFS-depth) layout for the small attack-path graphs
// TRACE deals with. This is intentionally not a general force-directed
// layout — attack-path graphs here are shallow chains/trees (attacker ->
// gateway -> hosts -> target), so depth-based columns read clearly and
// stay stable across re-renders (no physics jitter).
export function layeredLayout(nodes, edges, { width = 720, height = 260, padding = 60 } = {}) {
  const adjacency = new Map(nodes.map((n) => [n.id, []]));
  edges.forEach((e) => {
    if (adjacency.has(e.source)) adjacency.get(e.source).push(e.target);
  });

  const root = nodes.find((n) => n.type === 'attacker') || nodes[0];
  const depth = new Map([[root.id, 0]]);
  const queue = [root.id];
  while (queue.length) {
    const current = queue.shift();
    const currentDepth = depth.get(current);
    (adjacency.get(current) || []).forEach((next) => {
      if (!depth.has(next)) {
        depth.set(next, currentDepth + 1);
        queue.push(next);
      }
    });
  }
  // Any unreached nodes get placed at the end.
  const maxKnownDepth = Math.max(0, ...depth.values());
  nodes.forEach((n) => {
    if (!depth.has(n.id)) depth.set(n.id, maxKnownDepth + 1);
  });

  const maxDepth = Math.max(...depth.values());
  const layers = new Map();
  nodes.forEach((n) => {
    const d = depth.get(n.id);
    if (!layers.has(d)) layers.set(d, []);
    layers.get(d).push(n.id);
  });

  const positions = new Map();
  const colStep = maxDepth > 0 ? (width - padding * 2) / maxDepth : 0;
  layers.forEach((ids, d) => {
    const rowStep = (height - padding * 2) / Math.max(1, ids.length - 1 || 1);
    ids.forEach((id, i) => {
      const x = padding + colStep * d;
      const y = ids.length === 1 ? height / 2 : padding + rowStep * i;
      positions.set(id, { x, y });
    });
  });

  return positions;
}
