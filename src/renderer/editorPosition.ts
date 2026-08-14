// Renderer Layer (docs/architecture.md)
// 책임: Finding.location(line, col) -> 에디터 selection 범위(문자 오프셋).
// 순수 함수 — Component 밖 (docs/ui.md). SQL/AST 해석은 하지 않는다.

export interface SelectionRange {
  start: number;
  end: number;
}

/** 1-based (line, col) -> textarea selection 범위. 해당 위치부터 줄 끝까지. */
export function selectionForLocation(
  sql: string,
  line: number,
  col: number
): SelectionRange | null {
  const lines = sql.split("\n");
  if (line < 1 || line > lines.length) return null;

  let lineStart = 0;
  for (let i = 0; i < line - 1; i++) {
    lineStart += lines[i].length + 1; // +1 = 개행 문자
  }
  const lineText = lines[line - 1];
  const start = lineStart + Math.min(Math.max(col - 1, 0), lineText.length);
  const end = lineStart + lineText.length;
  return start < end ? { start, end } : null;
}
