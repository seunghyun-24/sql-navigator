// Parse Error 표시. Red = 위험/오류 (docs/ui.md 색상 의미).

import type { ParseErrorInfo } from "../types";

export default function ErrorPanel({ error }: { error: ParseErrorInfo }) {
  return (
    <div className="m-3 rounded-md border border-red-900 bg-red-950/50 p-3">
      <p className="text-sm font-medium text-red-300">Parse Error</p>
      <p className="mt-1 text-sm text-red-200">{error.message}</p>
      {error.line !== null && (
        <p className="mt-1 text-xs text-red-400">
          위치: line {error.line}
          {error.col !== null ? `, col ${error.col}` : ""}
        </p>
      )}
    </div>
  );
}
