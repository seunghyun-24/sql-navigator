// Sidebar 스키마 입력 (v0.5, docs/ui.md Layout의 Explorer 자리).
// 렌더만 담당 — DDL 파싱은 Analysis Layer(schema_context.py)에서.
// DDL도 SQL처럼 브라우저를 떠나지 않는다.

import type { SchemaInfo } from "../types";

interface Props {
  ddl: string;
  onChange: (ddl: string) => void;
  info: SchemaInfo | null;
}

export default function SchemaPanel({ ddl, onChange, info }: Props) {
  return (
    <div className="flex h-full flex-col gap-2">
      <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">Schema</p>
      <p className="text-[11px] leading-4 text-zinc-600">
        CREATE TABLE / CREATE INDEX DDL을 붙여넣으면 PK·index 기반 분석이 활성화됩니다.
      </p>
      <textarea
        value={ddl}
        onChange={(e) => onChange(e.target.value)}
        spellCheck={false}
        placeholder={"CREATE TABLE users (\n  id int PRIMARY KEY,\n  name varchar(50)\n);"}
        className="min-h-40 flex-1 resize-none rounded border border-zinc-800 bg-zinc-900/60 p-2 font-mono text-[11px] leading-4 text-zinc-200 placeholder:text-zinc-700 focus:border-zinc-600 focus:outline-none"
        aria-label="스키마 DDL 입력"
      />
      {info?.provided && (
        <p className={`text-[11px] ${info.error ? "text-yellow-400" : "text-emerald-400"}`}>
          {info.error ? `스키마 파싱 실패: ${info.error}` : `테이블 ${info.tableCount}개 인식됨`}
        </p>
      )}
    </div>
  );
}
