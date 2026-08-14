// Layout (docs/ui.md): Sidebar | Center(Editor) | Right(Analysis 탭).
// Right 탭 (docs/ui.md): Warnings | Graph | Flow | Structure | Formatted. Component는 렌더만.

import { useRef, useState } from "react";
import { useAnalysis } from "./hooks/useAnalysis";
import { useDiff } from "./hooks/useDiff";
import DiffPanel from "./components/DiffPanel";
import Editor, { type LocateRequest } from "./components/Editor";
import AstTree from "./components/AstTree";
import FormattedSql from "./components/FormattedSql";
import ErrorPanel from "./components/ErrorPanel";
import WarningsPanel from "./components/WarningsPanel";
import MetricsBar from "./components/MetricsBar";
import JoinGraphView from "./components/JoinGraphView";
import QueryFlowView from "./components/QueryFlowView";
import SchemaPanel from "./components/SchemaPanel";
import SuggestionsPanel from "./components/SuggestionsPanel";

type Tab = "warnings" | "graph" | "flow" | "structure" | "formatted" | "diff";

export default function App() {
  const { sql, setSql, schemaDdl, setSchemaDdl, result, parsing, bridgeStatus, bridgeError } =
    useAnalysis();
  const [tab, setTab] = useState<Tab>("warnings");
  const [locate, setLocate] = useState<LocateRequest | null>(null);
  const locateSeq = useRef(0);

  const handleLocate = (loc: { line: number; col: number }) => {
    locateSeq.current += 1;
    setLocate({ ...loc, seq: locateSeq.current });
  };

  // (v0.9) Apply 버튼: SQL 교체 → 재분석 자동 트리거
  const handleApplyFix = (fixSql: string) => {
    setSql(fixSql);
  };

  // SQL Diff (v0.8): Diff 탭이 열려 있을 때만 비교한다
  const diff = useDiff(sql, schemaDdl, bridgeStatus, tab === "diff");

  const error = result && !result.ok ? result.error : null;
  const ok = result?.ok ? result : null;
  const criticalCount = ok?.warnings.filter((w) => w.severity === "CRITICAL").length ?? 0;

  const tabs: [Tab, string][] = [
    ["warnings", ok ? `Warnings (${ok.warnings.length})` : "Warnings"],
    ["graph", "Graph"],
    ["flow", "Flow"],
    ["structure", "Structure"],
    ["formatted", "Formatted"],
    ["diff", "Diff"],
  ];

  return (
    <div className="flex h-full flex-col bg-zinc-950 text-zinc-100">
      <header className="flex items-center gap-3 border-b border-zinc-800 px-4 py-2">
        <h1 className="text-sm font-semibold tracking-tight">SQL Navigator</h1>
        <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] text-zinc-400">
          v0.9 · PostgreSQL
        </span>
        {criticalCount > 0 && (
          <span className="rounded bg-red-950 px-1.5 py-0.5 text-[10px] font-medium text-red-300">
            위험 {criticalCount}
          </span>
        )}
        <span className="ml-auto text-xs text-zinc-500">
          {bridgeStatus === "loading" && "분석 엔진 로딩 중… (최초 1회, 수 초 소요)"}
          {bridgeStatus === "ready" &&
            (parsing ? "분석 중…" : "준비됨 · SQL은 브라우저를 떠나지 않습니다")}
          {bridgeStatus === "error" && (
            <span className="text-red-400">엔진 로딩 실패: {bridgeError}</span>
          )}
        </span>
      </header>

      <div className="flex min-h-0 flex-1">
        {/* Sidebar — Schema Context 입력 (v0.5). 쿼리 목록은 이후 버전 */}
        <aside className="hidden w-56 shrink-0 border-r border-zinc-800 p-3 md:block">
          <SchemaPanel
            ddl={schemaDdl}
            onChange={setSchemaDdl}
            info={result?.schemaInfo ?? null}
          />
        </aside>

        {/* Center — SQL Editor */}
        <main className="min-w-0 flex-1 border-r border-zinc-800">
          <Editor sql={sql} onChange={setSql} errorLine={error?.line ?? null} locate={locate} />
        </main>

        {/* Right — Analysis */}
        <section className="flex w-[42%] min-w-72 shrink-0 flex-col">
          <div className="flex gap-1 border-b border-zinc-800 px-2 py-1.5">
            {tabs.map(([key, name]) => (
              <button
                key={key}
                type="button"
                onClick={() => setTab(key)}
                className={`rounded px-2.5 py-1 text-xs ${
                  tab === key
                    ? "bg-zinc-800 text-zinc-100"
                    : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200"
                }`}
              >
                {name}
              </button>
            ))}
          </div>
          <div className="min-h-0 flex-1 overflow-auto">
            {error && <ErrorPanel error={error} />}
            {!error && tab === "warnings" && (
              <>
                <WarningsPanel
                  warnings={ok?.warnings ?? []}
                  onLocate={handleLocate}
                  onApplyFix={handleApplyFix}
                />
                <SuggestionsPanel suggestions={ok?.suggestions ?? []} />
              </>
            )}
            {!error && tab === "graph" && <JoinGraphView graph={ok?.joinGraph ?? null} />}
            {!error && tab === "flow" && <QueryFlowView flow={ok?.dataFlow ?? null} />}
            {!error && tab === "structure" && <AstTree root={ok?.tree ?? null} />}
            {!error && tab === "formatted" && <FormattedSql formatted={ok?.formatted ?? null} />}
            {!error && tab === "diff" && <DiffPanel diff={diff} />}
          </div>
          {ok && <MetricsBar metrics={ok.metrics} />}
        </section>
      </div>
    </div>
  );
}
