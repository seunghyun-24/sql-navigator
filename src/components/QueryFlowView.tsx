// Query Flow 시각화 (docs/roadmap.md v0.4). 렌더만 담당 — 좌표 계산은
// renderer/queryFlowLayout.ts (docs/ui.md: Business Logic은 Component 밖).
// 색상 의미 (docs/ui.md): Red=위험(Cartesian), Blue=정보(CTE/서브쿼리 유입).

import { useMemo } from "react";
import type { DataFlow, FlowStepKind } from "../types";
import { layoutQueryFlow } from "../renderer/queryFlowLayout";

const KIND_STYLE: Record<FlowStepKind, { stroke: string; badge: string }> = {
  source: { stroke: "#3f3f46", badge: "" },
  join: { stroke: "#0ea5e9", badge: "JOIN" },
  where: { stroke: "#3f3f46", badge: "σ" },
  group: { stroke: "#3f3f46", badge: "γ" },
  having: { stroke: "#3f3f46", badge: "σ" },
  select: { stroke: "#3f3f46", badge: "π" },
  distinct: { stroke: "#3f3f46", badge: "δ" },
  order: { stroke: "#3f3f46", badge: "↕" },
  limit: { stroke: "#3f3f46", badge: "▤" },
};

function truncate(text: string, max: number): string {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

export default function QueryFlowView({ flow }: { flow: DataFlow | null }) {
  const layout = useMemo(() => (flow ? layoutQueryFlow(flow) : null), [flow]);

  if (!flow || !layout || layout.steps.length === 0) {
    return (
      <p className="p-4 text-sm text-zinc-500">
        표시할 실행 흐름이 없습니다. (SELECT 문에서 제공됩니다)
      </p>
    );
  }

  return (
    <div className="h-full overflow-auto p-3">
      <svg
        viewBox={`0 0 ${layout.width} ${layout.height}`}
        className="w-full"
        role="img"
        aria-label="쿼리 실행 흐름 그래프"
      >
        <defs>
          <marker id="flow-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
            <path d="M 0 1 L 7 4 L 0 7 z" fill="#52525b" />
          </marker>
        </defs>

        {/* lane 라벨 (main 제외 = CTE/서브쿼리) */}
        {layout.lanes
          .filter((l) => l.scope !== "main")
          .map((l) => (
            <text key={l.scope} x={l.x} y={14} textAnchor="middle" fill="#0ea5e9" fontSize="10">
              {l.scope.replace("cte:", "CTE ").replace("sub:", "서브쿼리 ")}
            </text>
          ))}

        {/* edges */}
        {layout.edges.map((e, i) => (
          <path
            key={`e-${i}`}
            d={
              e.sameLane
                ? `M ${e.x1} ${e.y1} L ${e.x2} ${e.y2}`
                : `M ${e.x1} ${e.y1} C ${e.x1 + 30} ${e.y1}, ${e.x2 - 30} ${e.y2}, ${e.x2} ${e.y2}`
            }
            fill="none"
            stroke={e.sameLane ? "#52525b" : "#0ea5e9"}
            strokeWidth={1.5}
            strokeDasharray={e.sameLane ? undefined : "5 4"}
            markerEnd="url(#flow-arrow)"
          />
        ))}

        {/* steps */}
        {layout.steps.map((s) => {
          const style = KIND_STYLE[s.kind];
          const stroke = s.cartesian ? "#ef4444" : style.stroke;
          return (
            <g key={s.id}>
              <rect
                x={s.x - s.width / 2}
                y={s.y - s.height / 2}
                width={s.width}
                height={s.height}
                rx={8}
                fill="#18181b"
                stroke={stroke}
                strokeWidth={s.cartesian ? 2 : 1.5}
              />
              <text
                x={s.x}
                y={s.detail ? s.y - 5 : s.y + 1}
                textAnchor="middle"
                dominantBaseline="middle"
                fill={s.cartesian ? "#f87171" : "#e4e4e7"}
                fontSize="11"
                fontWeight="600"
              >
                {s.cartesian ? `${s.label} — CARTESIAN!` : s.label}
              </text>
              {s.detail && (
                <text
                  x={s.x}
                  y={s.y + 11}
                  textAnchor="middle"
                  fill="#71717a"
                  fontSize="9"
                  fontFamily="monospace"
                >
                  {truncate(s.detail, 34)}
                </text>
              )}
            </g>
          );
        })}
      </svg>

      {/* 컬럼 lineage */}
      {flow.lineage.length > 0 && (
        <div className="mt-4 border-t border-zinc-800 pt-3">
          <p className="mb-2 text-xs font-medium uppercase tracking-wider text-zinc-500">
            컬럼 Lineage
          </p>
          <ul className="space-y-1">
            {flow.lineage.map((l, i) => (
              <li key={i} className="flex items-baseline gap-2 font-mono text-xs">
                <span className="text-zinc-200">{l.output}</span>
                <span className="text-zinc-600">←</span>
                {l.sources.length === 0 ? (
                  <span className="text-zinc-600">(상수/식)</span>
                ) : (
                  <span className="min-w-0 truncate">
                    {l.sources.map((src, j) => (
                      <span key={j} className={src.startsWith("?.") ? "text-zinc-600" : "text-sky-400"}>
                        {j > 0 && <span className="text-zinc-600">, </span>}
                        {src}
                      </span>
                    ))}
                  </span>
                )}
              </li>
            ))}
          </ul>
          <p className="mt-2 text-[10px] text-zinc-600">
            ?.col — 스키마 없이 출처를 단정할 수 없는 컬럼 (v0.5 Schema Context에서 해소)
          </p>
        </div>
      )}
    </div>
  );
}
