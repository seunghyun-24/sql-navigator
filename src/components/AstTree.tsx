// AST Explorer. 렌더만 담당 — 접기/펼치기는 순수 UI 상태 (docs/ui.md).

import { useState } from "react";
import type { AstNode } from "../types";

const DEFAULT_OPEN_DEPTH = 3;

function TreeNode({ node, depth }: { node: AstNode; depth: number }) {
  const [open, setOpen] = useState(depth < DEFAULT_OPEN_DEPTH);
  const hasChildren = node.children.length > 0;
  const isValue = node.type === "value";

  return (
    <div>
      <button
        type="button"
        onClick={() => hasChildren && setOpen((v) => !v)}
        className="flex w-full items-baseline gap-2 rounded px-1 py-0.5 text-left hover:bg-zinc-800/60"
        style={{ paddingLeft: `${depth * 14 + 4}px` }}
      >
        <span className="w-3 shrink-0 text-zinc-500">
          {hasChildren ? (open ? "▾" : "▸") : "·"}
        </span>
        {node.arg && <span className="shrink-0 text-xs text-zinc-500">{node.arg}:</span>}
        <span className={isValue ? "text-xs text-emerald-300" : "text-xs font-semibold text-sky-300"}>
          {isValue ? node.label : node.type}
        </span>
        {!isValue && node.label && (
          <span className="truncate text-xs text-zinc-400">{node.label}</span>
        )}
      </button>
      {open &&
        node.children.map((child, i) => (
          <TreeNode key={`${child.type}-${i}`} node={child} depth={depth + 1} />
        ))}
    </div>
  );
}

export default function AstTree({ root }: { root: AstNode | null }) {
  if (!root) {
    return <p className="p-4 text-sm text-zinc-500">파싱된 AST가 없습니다.</p>;
  }
  return (
    <div className="overflow-auto p-2 font-mono">
      <TreeNode node={root} depth={0} />
    </div>
  );
}
