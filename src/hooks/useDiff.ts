// Business Logic은 Component 밖에 둔다 (docs/ui.md).
// Diff 탭(v0.8): before SQL 상태 관리 + Bridge diff 호출 + 디바운스.
// DiffPanel은 반환값을 그리기만 한다.

import { useEffect, useRef, useState } from "react";
import { diffSql } from "../bridge/pyodide";
import type { BridgeStatus, DiffResult } from "../types";

const DEBOUNCE_MS = 400;

export interface DiffState {
  beforeSql: string;
  setBeforeSql: (sql: string) => void;
  result: DiffResult | null;
  comparing: boolean;
}

/** sqlAfter: 현재 에디터 SQL. enabled: Diff 탭이 열려 있을 때만 계산한다. */
export function useDiff(
  sqlAfter: string,
  schemaDdl: string,
  bridgeStatus: BridgeStatus,
  enabled: boolean
): DiffState {
  const [beforeSql, setBeforeSql] = useState("");
  const [result, setResult] = useState<DiffResult | null>(null);
  const [comparing, setComparing] = useState(false);
  const requestId = useRef(0);

  useEffect(() => {
    if (!enabled || bridgeStatus !== "ready") return;
    if (!beforeSql.trim()) {
      setResult(null);
      return;
    }
    const timer = setTimeout(() => {
      const id = ++requestId.current;
      setComparing(true);
      diffSql(beforeSql, sqlAfter, schemaDdl)
        .then((r) => {
          if (id === requestId.current) setResult(r);
        })
        .catch(() => {
          if (id === requestId.current) setResult(null);
        })
        .finally(() => {
          if (id === requestId.current) setComparing(false);
        });
    }, DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [beforeSql, sqlAfter, schemaDdl, bridgeStatus, enabled]);

  return { beforeSql, setBeforeSql, result, comparing };
}
