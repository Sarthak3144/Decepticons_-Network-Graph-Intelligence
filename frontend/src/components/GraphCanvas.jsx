import { useEffect, useRef, useState } from "react";

const RISK_COLORS = {
  "RISK-LOW": "#3A4048",
  "RISK-MED": "#E8A33D",
  "RISK-HIGH": "#D14B4B",
  UNKNOWN: "#3A4048",
};

export default function GraphCanvas({ subgraph, centerAccount, loading }) {
  const svgRef = useRef(null);
  const [positions, setPositions] = useState({});

  useEffect(() => {
    if (!subgraph || !subgraph.nodes.length) return;

    const width = 900;
    const height = 520;
    const cx = width / 2;
    const cy = height / 2;

    const center = subgraph.nodes.find((n) => n.is_center);
    const others = subgraph.nodes.filter((n) => !n.is_center);

    const pos = {};
    if (center) pos[center.id] = { x: cx, y: cy };

    const radius = Math.min(width, height) / 2 - 80;
    others.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / Math.max(others.length, 1);
      pos[node.id] = {
        x: cx + radius * Math.cos(angle),
        y: cy + radius * Math.sin(angle),
      };
    });

    setPositions(pos);
  }, [subgraph]);

  if (loading) {
    return (
      <div className="graph-canvas graph-canvas--empty">
        <span className="mono dim">tracing flow…</span>
      </div>
    );
  }

  if (!subgraph || !subgraph.nodes.length) {
    return (
      <div className="graph-canvas graph-canvas--empty">
        <span className="mono dim">search an account to trace its network</span>
      </div>
    );
  }

  return (
    <div className="graph-canvas">
      <svg ref={svgRef} viewBox="0 0 900 520" className="graph-svg">
        <defs>
          <marker
            id="arrow"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#4A5058" />
          </marker>
        </defs>

        {subgraph.edges.map((edge, i) => {
          const a = positions[edge.source];
          const b = positions[edge.target];
          if (!a || !b) return null;
          const strokeWidth = Math.min(1 + Math.log10(edge.tx_count || 1) * 1.4, 6);
          return (
            <line
              key={i}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke="#3A4048"
              strokeWidth={strokeWidth}
              markerEnd="url(#arrow)"
              opacity="0.55"
            />
          );
        })}

        {subgraph.nodes.map((node) => {
          const p = positions[node.id];
          if (!p) return null;
          const color = RISK_COLORS[node.risk_grade] || RISK_COLORS.UNKNOWN;
          const isCenter = node.is_center;
          const flagged = node.pep_flag === 1 || node.sanctions_hit === 1;

          return (
            <g key={node.id} transform={`translate(${p.x}, ${p.y})`}>
              {flagged && (
                <circle r={isCenter ? 22 : 14} fill="none" stroke="#D14B4B" strokeWidth="1.5" opacity="0.7" />
              )}
              <circle
                r={isCenter ? 16 : 9}
                fill={isCenter ? "#E8A33D" : color}
                stroke="#0B0E11"
                strokeWidth="2"
              />
              <text
                y={isCenter ? 32 : 22}
                textAnchor="middle"
                className="mono node-label"
                fill={isCenter ? "#E8A33D" : "#8A9099"}
                fontSize={isCenter ? 12 : 10}
              >
                {node.id}
              </text>
            </g>
          );
        })}
      </svg>

      <div className="graph-legend mono">
        <span><i className="dot" style={{ background: "#E8A33D" }} /> center account</span>
        <span><i className="dot" style={{ background: "#D14B4B" }} /> high risk</span>
        <span><i className="dot" style={{ background: "#3A4048" }} /> standard</span>
        <span><i className="ring" /> PEP / sanctions flag</span>
      </div>
    </div>
  );
}