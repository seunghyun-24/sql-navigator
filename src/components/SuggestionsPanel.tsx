// Refactoring Suggestion 패널 (v0.5). 렌더만 담당 (docs/ui.md).
// 색상 의미 (docs/ui.md): Green=추천 (Suggestion).

import { useState } from "react";
import type { Suggestion } from "../types";

function SuggestionCard({ suggestion }: { suggestion: Suggestion }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const copy = () => {
    void navigator.clipboard.writeText(suggestion.sql).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  return (
    <div className="rounded-md border border-emerald-900 bg-zinc-900/40">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left"
      >
        <span className="shrink-0 rounded bg-emerald-950 px-1.5 py-0.5 text-[10px] font-medium text-emerald-300">
          추천
        </span>
        <span className="min-w-0 flex-1 truncate text-sm text-zinc-200">{suggestion.title}</span>
        <span className="shrink-0 text-zinc-500">{open ? "▾" : "▸"}</span>
      </button>

      {open && (
        <div className="space-y-3 border-t border-zinc-800 px-3 py-3">
          <p className="text-sm text-zinc-300">{suggestion.description}</p>
          <div>
            <div className="mb-1 flex items-center justify-between">
              <span className="text-[11px] font-medium text-zinc-500">재작성 SQL</span>
              <button
                type="button"
                onClick={copy}
                className="rounded border border-zinc-700 px-1.5 text-[10px] text-zinc-400 hover:bg-zinc-800"
              >
                {copied ? "복사됨" : "복사"}
              </button>
            </div>
            <pre className="overflow-x-auto rounded bg-zinc-900 p-2 font-mono text-xs leading-5 text-emerald-200">
              {suggestion.sql}
            </pre>
          </div>
          <p className="text-[10px] text-zinc-600">suggestion: {suggestion.id}</p>
        </div>
      )}
    </div>
  );
}

export default function SuggestionsPanel({ suggestions }: { suggestions: Suggestion[] }) {
  if (suggestions.length === 0) return null;
  return (
    <div className="space-y-2 border-t border-zinc-800 p-3">
      <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">
        Refactoring 제안
      </p>
      {suggestions.map((s, i) => (
        <SuggestionCard key={`${s.id}-${i}`} suggestion={s} />
      ))}
    </div>
  );
}
