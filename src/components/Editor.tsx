// SQL Editor (Center). 렌더만 담당 — 로직 없음 (docs/ui.md).
// Warning 클릭 → 해당 위치 하이라이트 (v0.7): locate가 바뀌면
// selection 계산(Renderer Layer)에 따라 커서를 옮긴다.

import { useEffect, useRef } from "react";
import { selectionForLocation } from "../renderer/editorPosition";

export interface LocateRequest {
  line: number;
  col: number;
  /** 같은 Warning을 다시 클릭해도 재하이라이트되도록 하는 증가값 */
  seq: number;
}

interface EditorProps {
  sql: string;
  onChange: (sql: string) => void;
  errorLine: number | null;
  locate: LocateRequest | null;
}

export default function Editor({ sql, onChange, errorLine, locate }: EditorProps) {
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!locate || !ref.current) return;
    const range = selectionForLocation(ref.current.value, locate.line, locate.col);
    if (!range) return;
    ref.current.focus();
    ref.current.setSelectionRange(range.start, range.end);
  }, [locate]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-zinc-800 px-4 py-2">
        <span className="text-xs font-medium uppercase tracking-wider text-zinc-400">
          SQL Editor
        </span>
        <span className="flex items-center gap-2">
          {locate && (
            <span className="text-xs text-zinc-500">
              line {locate.line}:{locate.col}
            </span>
          )}
          {errorLine !== null && (
            <span className="text-xs text-red-400">line {errorLine} 근처 오류</span>
          )}
        </span>
      </div>
      <textarea
        ref={ref}
        value={sql}
        onChange={(e) => onChange(e.target.value)}
        spellCheck={false}
        aria-label="SQL 입력"
        className="min-h-0 flex-1 resize-none bg-transparent p-4 font-mono text-sm leading-6 text-zinc-100 outline-none placeholder:text-zinc-600"
        placeholder="SQL을 입력하세요…"
      />
    </div>
  );
}
