// Complexity Metrics 표시. 렌더만 담당 (docs/ui.md).

import type { Metrics } from "../types";

const GRADE_STYLE: Record<Metrics["complexityGrade"], { text: string; label: string }> = {
  simple: { text: "text-emerald-400", label: "단순" },
  moderate: { text: "text-yellow-400", label: "보통" },
  complex: { text: "text-red-400", label: "복잡 · 리뷰 권장" },
};

export default function MetricsBar({ metrics }: { metrics: Metrics }) {
  const grade = GRADE_STYLE[metrics.complexityGrade];
  const items: [string, number][] = [
    ["JOIN", metrics.joinCount],
    ["서브쿼리 깊이", metrics.subqueryDepth],
    ["CTE", metrics.cteCount],
    ["테이블", metrics.tableCount],
  ];
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-zinc-800 px-3 py-2">
      <span className="text-xs text-zinc-500">
        복잡도 <span className={`font-semibold ${grade.text}`}>{metrics.complexityScore}</span>{" "}
        <span className={grade.text}>({grade.label})</span>
      </span>
      {items.map(([name, value]) => (
        <span key={name} className="text-xs text-zinc-500">
          {name} <span className="text-zinc-300">{value}</span>
        </span>
      ))}
    </div>
  );
}
