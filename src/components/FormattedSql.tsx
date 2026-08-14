// Formatter 결과 표시. 렌더만 담당 (docs/ui.md).

import { useState } from "react";

export default function FormattedSql({ formatted }: { formatted: string | null }) {
  const [copied, setCopied] = useState(false);

  if (!formatted) {
    return <p className="p-4 text-sm text-zinc-500">포맷팅 결과가 없습니다.</p>;
  }

  const copy = () => {
    void navigator.clipboard.writeText(formatted).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  return (
    <div className="relative h-full overflow-auto">
      <button
        type="button"
        onClick={copy}
        className="absolute right-3 top-2 rounded border border-zinc-700 bg-zinc-900 px-2 py-0.5 text-xs text-zinc-300 hover:bg-zinc-800"
      >
        {copied ? "복사됨" : "복사"}
      </button>
      <pre className="p-4 font-mono text-sm leading-6 text-zinc-100">{formatted}</pre>
    </div>
  );
}
