// Diff 탭 (v0.8, docs/ui.md). 렌더만 담당 — 비교는 Analysis Layer에서 끝났다.
// 색상 의미: 개선=Green, 악화=Red (docs/ui.md 색상 의미 유지).

import type { DiffChange, Metrics, WarningSummary } from "../types";
import type { DiffState } from "../hooks/useDiff";

const OP_STYLE: Record<DiffChange["op"], { badge: string; label: string }> = {
  insert: { badge: "bg-emerald-950 text-emerald-300", label: "추가" },
  remove: { badge: "bg-red-950 text-red-300", label: "삭제" },
  update: { badge: "bg-yellow-950 text-yellow-300", label: "변경" },
  move: { badge: "bg-sky-950 text-sky-300", label: "이동" },
};

/** 낮을수록 좋은 지표의 before-after 한 줄. 개선 Green / 악화 Red. */
function CompareRow({ name, before, after }: { name: string; before: number; after: number }) {
  const delta = after - before;
  const color = delta < 0 ? "text-emerald-400" : delta > 0 ? "text-red-400" : "text-zinc-500";
  return (
    <div className="flex items-center justify-between py-1 text-xs">
      <span className="text-zinc-400">{name}</span>
      <span className="font-mono">
        <span className="text-zinc-300">{before}</span>
        <span className="mx-1 text-zinc-600">→</span>
        <span className="text-zinc-100">{after}</span>
        <span className={`ml-2 ${color}`}>
          {delta === 0 ? "±0" : delta > 0 ? `+${delta}` : `${delta}`}
        </span>
      </span>
    </div>
  );
}

function WarningCompare({ before, after }: { before: WarningSummary; after: WarningSummary }) {
  return (
    <div>
      <CompareRow name="Warnings 전체" before={before.total} after={after.total} />
      <CompareRow name="위험 (CRITICAL)" before={before.bySeverity.CRITICAL} after={after.bySeverity.CRITICAL} />
      <CompareRow name="주의 (WARNING)" before={before.bySeverity.WARNING} after={after.bySeverity.WARNING} />
      <CompareRow name="정보 (INFO)" before={before.bySeverity.INFO} after={after.bySeverity.INFO} />
    </div>
  );
}

function MetricsCompare({ before, after }: { before: Metrics; after: Metrics }) {
  return (
    <div>
      <CompareRow name="Complexity Score" before={before.complexityScore} after={after.complexityScore} />
      <CompareRow name="JOIN 수" before={before.joinCount} after={after.joinCount} />
      <CompareRow name="서브쿼리 깊이" before={before.subqueryDepth} after={after.subqueryDepth} />
      <CompareRow name="테이블 수" before={before.tableCount} after={after.tableCount} />
    </div>
  );
}

function RuleChips({ title, rules, tone }: { title: string; rules: string[]; tone: "good" | "bad" }) {
  if (rules.length === 0) return null;
  const chip =
    tone === "good"
      ? "bg-emerald-950 text-emerald-300 border-emerald-900"
      : "bg-red-950 text-red-300 border-red-900";
  return (
    <div>
      <span className="text-[11px] font-medium text-zinc-500">{title}</span>
      <div className="mt-1 flex flex-wrap gap-1">
        {rules.map((r) => (
          <span key={r} className={`rounded border px-1.5 py-0.5 font-mono text-[10px] ${chip}`}>
            {r}
          </span>
        ))}
      </div>
    </div>
  );
}

function ChangeList({ changes, total }: { changes: DiffChange[]; total: number }) {
  if (changes.length === 0) return null;
  return (
    <div>
      <span className="text-[11px] font-medium text-zinc-500">
        AST 변경 {total}건{total > changes.length ? ` (상위 ${changes.length}건 표시)` : ""}
      </span>
      <div className="mt-1 space-y-1">
        {changes.map((c, i) => {
          const style = OP_STYLE[c.op];
          return (
            <div key={i} className="flex items-start gap-2 rounded bg-zinc-900 px-2 py-1.5">
              <span className={`mt-0.5 shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium ${style.badge}`}>
                {style.label}
              </span>
              <span className="shrink-0 pt-0.5 font-mono text-[10px] text-zinc-500">{c.kind}</span>
              <span className="min-w-0 flex-1 break-all font-mono text-xs leading-5 text-zinc-300">
                {c.op === "update" ? (
                  <>
                    <span className="text-red-400 line-through">{c.before}</span>
                    <span className="mx-1 text-zinc-600">→</span>
                    <span className="text-emerald-400">{c.after}</span>
                  </>
                ) : (
                  c.before || c.after
                )}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function DiffPanel({ diff }: { diff: DiffState }) {
  const { beforeSql, setBeforeSql, result, comparing } = diff;

  return (
    <div className="space-y-4 p-3">
      <div>
        <div className="mb-1 flex items-center justify-between">
          <span className="text-[11px] font-medium text-zinc-500">
            비교 대상 SQL (before) — 현재 에디터 SQL이 after입니다
          </span>
          {comparing && <span className="text-[11px] text-zinc-500">비교 중…</span>}
        </div>
        <textarea
          value={beforeSql}
          onChange={(e) => setBeforeSql(e.target.value)}
          spellCheck={false}
          aria-label="비교 대상 SQL (before)"
          placeholder="리팩토링 전 SQL을 붙여넣으세요…"
          className="h-32 w-full resize-y rounded border border-zinc-800 bg-zinc-900 p-2 font-mono text-xs leading-5 text-zinc-200 outline-none placeholder:text-zinc-600"
        />
      </div>

      {result && !result.ok && (
        <div className="rounded border border-red-900 bg-red-950/40 p-2 text-xs text-red-300">
          {result.errorBefore && <p>before 파싱 오류: {result.errorBefore.message}</p>}
          {result.errorAfter && <p>after 파싱 오류: {result.errorAfter.message}</p>}
        </div>
      )}

      {result?.ok && (
        <>
          {result.equivalent ? (
            <p className="rounded border border-emerald-900 bg-emerald-950/40 p-2 text-xs text-emerald-300">
              두 SQL은 AST 수준에서 동일합니다.
            </p>
          ) : (
            <p className="text-xs text-zinc-400">
              AST 수준에서 {result.changeCount}건의 변경이 있습니다.
            </p>
          )}

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div className="rounded border border-zinc-800 p-2">
              <span className="text-[11px] font-medium text-zinc-500">Warnings</span>
              <WarningCompare before={result.warningsBefore} after={result.warningsAfter} />
            </div>
            <div className="rounded border border-zinc-800 p-2">
              <span className="text-[11px] font-medium text-zinc-500">Complexity</span>
              <MetricsCompare before={result.metricsBefore} after={result.metricsAfter} />
            </div>
          </div>

          <RuleChips title="해소된 Rule (개선)" rules={result.resolvedRules} tone="good" />
          <RuleChips title="새로 생긴 Rule (악화)" rules={result.introducedRules} tone="bad" />
          <ChangeList changes={result.changes} total={result.changeCount} />
        </>
      )}
    </div>
  );
}
