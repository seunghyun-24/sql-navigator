// Warnings 패널. 렌더만 담당 (docs/ui.md).
// Explainability 강제: 펼치면 이유 / 예시(before) / 수정(after) 3단 구성.
// 색상 의미 (docs/ui.md): Blue=정보(INFO), Yellow=주의(WARNING), Red=위험(CRITICAL).
// Warning 클릭 → 에디터 위치 하이라이트 (v0.7): location 있으면 onLocate 호출.

import { useState } from "react";
import type { Severity, Warning } from "../types";

type OnLocate = (loc: { line: number; col: number }) => void;
type OnApplyFix = (fixSql: string) => void;

const SEVERITY_STYLE: Record<Severity, { border: string; badge: string; label: string }> = {
  CRITICAL: { border: "border-red-900", badge: "bg-red-950 text-red-300", label: "위험" },
  WARNING: { border: "border-yellow-900", badge: "bg-yellow-950 text-yellow-300", label: "주의" },
  INFO: { border: "border-sky-900", badge: "bg-sky-950 text-sky-300", label: "정보" },
};

function CodeBlock({ title, code }: { title: string; code: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    void navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };
  return (
    <div>
      <div className="mb-1 flex items-center justify-between">
        <span className="text-[11px] font-medium text-zinc-500">{title}</span>
        <button
          type="button"
          onClick={copy}
          className="rounded border border-zinc-700 px-1.5 text-[10px] text-zinc-400 hover:bg-zinc-800"
        >
          {copied ? "복사됨" : "복사"}
        </button>
      </div>
      <pre className="overflow-x-auto rounded bg-zinc-900 p-2 font-mono text-xs leading-5 text-zinc-200">
        {code}
      </pre>
    </div>
  );
}

function WarningCard({
  warning,
  onLocate,
  onApplyFix,
}: {
  warning: Warning;
  onLocate?: OnLocate;
  onApplyFix?: OnApplyFix;
}) {
  const [open, setOpen] = useState(false);
  const style = SEVERITY_STYLE[warning.severity];

  const handleClick = () => {
    setOpen((v) => !v);
    if (warning.location && onLocate) onLocate(warning.location);
  };

  const handleApply = () => {
    if (warning.fixSql && onApplyFix) {
      onApplyFix(warning.fixSql);
    }
  };

  return (
    <div className={`rounded-md border ${style.border} bg-zinc-900/40`}>
      <button
        type="button"
        onClick={handleClick}
        className="flex w-full items-center gap-2 px-3 py-2 text-left"
      >
        <span className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium ${style.badge}`}>
          {style.label}
        </span>
        <span className="min-w-0 flex-1 truncate text-sm text-zinc-200">{warning.message}</span>
        {warning.location && (
          <span className="shrink-0 rounded bg-zinc-800 px-1.5 py-0.5 font-mono text-[10px] text-zinc-400">
            L{warning.location.line}
          </span>
        )}
        <span className="shrink-0 text-zinc-500">{open ? "▾" : "▸"}</span>
      </button>

      {open && (
        <div className="space-y-3 border-t border-zinc-800 px-3 py-3">
          <div>
            <span className="text-[11px] font-medium text-zinc-500">이유</span>
            <p className="mt-1 text-sm text-zinc-300">{warning.reason}</p>
          </div>
          {warning.snippet && (
            <div>
              <span className="text-[11px] font-medium text-zinc-500">해당 부분</span>
              <pre className="mt-1 overflow-x-auto rounded bg-zinc-900 p-2 font-mono text-xs leading-5 text-zinc-400">
                {warning.snippet}
              </pre>
            </div>
          )}
          <CodeBlock title="예시 (before)" code={warning.example} />
          <CodeBlock title="수정 (after)" code={warning.fix} />
          {warning.fixSql && (
            <button
              type="button"
              onClick={handleApply}
              className="w-full rounded bg-emerald-950 px-3 py-2 text-sm font-medium text-emerald-300 hover:bg-emerald-900"
            >
              ✓ 자동 수정 적용
            </button>
          )}
          <p className="text-[10px] text-zinc-600">rule: {warning.ruleId}</p>
        </div>
      )}
    </div>
  );
}

export default function WarningsPanel({
  warnings,
  onLocate,
  onApplyFix,
}: {
  warnings: Warning[];
  onLocate?: OnLocate;
  onApplyFix?: OnApplyFix;
}) {
  if (warnings.length === 0) {
    return (
      <p className="p-4 text-sm text-emerald-400">
        발견된 문제가 없습니다.
      </p>
    );
  }
  return (
    <div className="space-y-2 p-3">
      {warnings.map((w, i) => (
        <WarningCard
          key={`${w.ruleId}-${i}`}
          warning={w}
          onLocate={onLocate}
          onApplyFix={onApplyFix}
        />
      ))}
    </div>
  );
}
