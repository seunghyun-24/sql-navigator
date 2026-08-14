// Join Graph 시각화 (docs/roadmap.md v0.3). 렌더만 담당 — 좌표 계산은
// renderer/joinGraphLayout.ts (docs/ui.md: Business Logic은 Component 밖).
// 색상 의미 (docs/ui.md): Red=위험(Cartesian), Blue=정보.

import { useMemo } from "react";
import type { JoinGraph } from "../types";
import { layoutJoinGraph, nodeLabel } from "../renderer/joinGraphLayout";

const KIND_STYLE: Record<string, { fill: string; stroke: string }> = {
  table: { fill: "#18181b", stroke: "#3f3f46" },
  cte: { fill: "#0c1a2b", stroke: "#0ea5e9" },
  subquery: { fill: "#1a1030", stroke: "#8b5cf6" },
};

export default function JoinGraphView({ graph }: { graph: JoinGraph | null }) {
  const layout = useMemo(() => (graph ? layoutJoinGraph(graph) : null), [graph]);

  if (!graph || !layout || layout.nodes.length === 0) {
    return <p className="p-4 text-sm text-zinc-500">표시할 테이블이 없습니다.</p>;
  }

  const hasCartesian = graph.edges.some((e) => e.cartesian);

  return (
    <div className="h-full overflow-auto p-3">
      {hasCartesian && (
        <p className="mb-2 rounded border border-red-900 bg-red-950/50 px-3 py-1.5 text-xs text-red-300">
          빨간 엣지는 JOIN 조건이 없는 연결(Cartesian Product)입니다.
        </p>
      )}
      <svg
        viewBox={`0 0 ${layout.width} ${layout.height}`}
        className="w-full"
        role="img"
        aria-label="테이블 JOIN 관계 그래프"
      >
        {/* edges */}
        {layout.edges.map((e, i) => (
          <g key={`e-${i}`}>
            <line
              x1={e.x1}
              y1={e.y1}
              x2={e.x2}
              y2={e.y2}
              stroke={e.cartesian ? "#ef4444" : "#52525b"}
              strokeWidth={e.cartesian ? 2.5 : 1.5}
              strokeDasharray={e.cartesian ? "6 4" : undefined}
            />
            <g>
              <text
                x={e.labelX}
                y={e.labelY - 10}
                textAnchor="middle"
                className="select-none"
                fill={e.cartesian ? "#f87171" : "#a1a1aa"}
                fontSize="10"
                fontWeight="600"
              >
                {e.cartesian ? "CARTESIAN!" : e.joinType}
              </text>
              {e.condition && (
                <text
                  x={e.labelX}
                  y={e.labelY + 4}
                  textAnchor="middle"
                  className="select-none"
                  fill="#71717a"
                  fontSize="9"
                  fontFamily="monospace"
                >
                  {e.condition.length > 40 ? `${e.condition.slice(0, 39)}…` : e.condition}
                </text>
              )}
            </g>
          </g>
        ))}

        {/* nodes */}
        {layout.nodes.map((node) => {
          const style = KIND_STYLE[node.kind] ?? KIND_STYLE.table;
          return (
            <g key={node.id}>
              <rect
                x={node.x - node.width / 2}
                y={node.y - node.height / 2}
                width={node.width}
                height={node.height}
                rx={8}
                fill={style.fill}
                stroke={style.stroke}
                strokeWidth={1.5}
              />
              <text
                x={node.x}
                y={node.y + 1}
                textAnchor="middle"
                dominantBaseline="middle"
                fill="#e4e4e7"
                fontSize="12"
                fontFamily="monospace"
              >
                {nodeLabel(node)}
              </text>
              {node.kind !== "table" && (
                <text
                  x={node.x}
                  y={node.y - node.height / 2 - 5}
                  textAnchor="middle"
                  fill={style.stroke}
                  fontSize="9"
                >
                  {node.kind.toUpperCase()}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
