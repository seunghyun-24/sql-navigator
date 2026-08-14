// Business Logic은 Component 밖에 둔다 (docs/ui.md).
// 이 hook이 Bridge 호출, 디바운스, 상태 관리를 담당하고
// Component는 반환값을 그리기만 한다.

import { useCallback, useEffect, useRef, useState } from "react";
import { analyzeSql, ensureBridge } from "../bridge/pyodide";
import type { AnalysisResult, BridgeStatus } from "../types";

const DEBOUNCE_MS = 400;

const INITIAL_SQL = `SELECT o.id, o.amount, c.name
FROM orders o
JOIN customers c ON o.customer_id = c.id
WHERE o.created_at >= '2026-01-01'
ORDER BY o.amount DESC
LIMIT 20`;

export interface AnalysisState {
  sql: string;
  setSql: (sql: string) => void;
  schemaDdl: string;
  setSchemaDdl: (ddl: string) => void;
  result: AnalysisResult | null;
  parsing: boolean;
  bridgeStatus: BridgeStatus;
  bridgeError: string | null;
}

export function useAnalysis(): AnalysisState {
  const [sql, setSql] = useState(INITIAL_SQL);
  const [schemaDdl, setSchemaDdl] = useState("");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [parsing, setParsing] = useState(false);
  const [bridgeStatus, setBridgeStatus] = useState<BridgeStatus>("idle");
  const [bridgeError, setBridgeError] = useState<string | null>(null);
  const requestId = useRef(0);

  // Pyodide는 앱 시작 시 미리 로딩한다 (수 초 소요).
  useEffect(() => {
    let cancelled = false;
    setBridgeStatus("loading");
    ensureBridge()
      .then(() => !cancelled && setBridgeStatus("ready"))
      .catch((e) => {
        if (!cancelled) {
          setBridgeStatus("error");
          setBridgeError(e instanceof Error ? e.message : String(e));
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const runParse = useCallback((value: string, ddl: string) => {
    const id = ++requestId.current;
    setParsing(true);
    analyzeSql(value, ddl)
      .then((r) => {
        if (id === requestId.current) setResult(r);
      })
      .catch((e) => {
        if (id === requestId.current) {
          setResult({
            ok: false,
            error: { message: e instanceof Error ? e.message : String(e), line: null, col: null },
          });
        }
      })
      .finally(() => {
        if (id === requestId.current) setParsing(false);
      });
  }, []);

  // 입력(SQL/DDL) 디바운스 후 파싱. bridge가 준비된 뒤에만.
  useEffect(() => {
    if (bridgeStatus !== "ready") return;
    const timer = setTimeout(() => runParse(sql, schemaDdl), DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [sql, schemaDdl, bridgeStatus, runParse]);

  return { sql, setSql, schemaDdl, setSchemaDdl, result, parsing, bridgeStatus, bridgeError };
}
