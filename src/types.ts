// Layer 간 데이터 계약 (docs/architecture.md)
// Bridge 경계는 직렬화 가능한 JSON만 통과한다.

export interface AstNode {
  /** sqlglot Expression 클래스명 (예: "Select", "Join") 또는 "value" */
  type: string;
  /** 부모 노드에서의 arg 키 (예: "from", "where") */
  arg: string;
  /** 사람이 읽을 짧은 SQL 라벨 */
  label: string;
  children: AstNode[];
}

export type Severity = "INFO" | "WARNING" | "CRITICAL";

/** Explainability (docs/principles.md): reason/example/fix 필수 */
export interface Warning {
  ruleId: string;
  severity: Severity;
  message: string;
  reason: string;
  example: string;
  fix: string;
  snippet: string;
  location: { line: number; col: number } | null;
  fixSql?: string; // (v0.9) 자동 수정 SQL 또는 undefined
}

export interface Metrics {
  joinCount: number;
  subqueryDepth: number;
  cteCount: number;
  tableCount: number;
  wherePredicateCount: number;
  complexityScore: number;
  complexityGrade: "simple" | "moderate" | "complex";
}

export interface JoinGraphNode {
  id: string;
  table: string | null;
  alias: string | null;
  kind: "table" | "subquery" | "cte";
}

export interface JoinGraphEdge {
  source: string;
  target: string;
  joinType: string;
  condition: string;
  cartesian: boolean;
}

export interface JoinGraph {
  nodes: JoinGraphNode[];
  edges: JoinGraphEdge[];
}

/** Query Flow 논리 단계 (v0.4). scope: "main" | "cte:<name>" | "sub:<alias>" */
export type FlowStepKind =
  | "source"
  | "join"
  | "where"
  | "group"
  | "having"
  | "select"
  | "distinct"
  | "order"
  | "limit";

export interface FlowStep {
  id: string;
  kind: FlowStepKind;
  label: string;
  detail: string;
  scope: string;
  cartesian: boolean;
}

export interface FlowEdge {
  source: string;
  target: string;
}

/** 컬럼 lineage. 확정 불가한 source는 "?.col"로 표기 (Static Only) */
export interface LineageEntry {
  output: string;
  expression: string;
  sources: string[];
}

export interface DataFlow {
  steps: FlowStep[];
  edges: FlowEdge[];
  lineage: LineageEntry[];
}

/** Refactoring Suggestion (v0.5). Green=추천 (docs/ui.md) */
export interface Suggestion {
  id: string;
  title: string;
  description: string;
  /** 새 AST로 생성한 재작성 SQL (원본 불변) */
  sql: string;
}

/** 사용자 제공 스키마(DDL) 파싱 상태 (v0.5) */
export interface SchemaInfo {
  provided: boolean;
  tableCount: number;
  error: string | null;
}

export interface ParseErrorInfo {
  message: string;
  line: number | null;
  col: number | null;
}

export type AnalysisResult =
  | {
      ok: true;
      tree: AstNode;
      formatted: string;
      warnings: Warning[];
      suggestions: Suggestion[];
      metrics: Metrics;
      joinGraph: JoinGraph;
      dataFlow: DataFlow;
      schemaInfo: SchemaInfo;
    }
  | { ok: false; error: ParseErrorInfo; schemaInfo?: SchemaInfo };

/** SQL Diff (v0.8, docs/analyzer.md) — AST 수준 변경 항목 */
export interface DiffChange {
  op: "insert" | "remove" | "move" | "update";
  /** 변경된 AST 노드 타입 (예: "Where", "Join") */
  kind: string;
  before: string;
  after: string;
}

export interface WarningSummary {
  total: number;
  bySeverity: Record<Severity, number>;
}

export type DiffResult =
  | {
      ok: true;
      /** AST 수준 변경 없음 (구조적으로 동일) */
      equivalent: boolean;
      changes: DiffChange[];
      changeCount: number;
      metricsBefore: Metrics;
      metricsAfter: Metrics;
      warningsBefore: WarningSummary;
      warningsAfter: WarningSummary;
      /** before에는 있었지만 after에서 줄어든 ruleId (개선, Green) */
      resolvedRules: string[];
      /** after에서 늘어난 ruleId (악화, Red) */
      introducedRules: string[];
    }
  | { ok: false; errorBefore: ParseErrorInfo | null; errorAfter: ParseErrorInfo | null };

/** Bridge(Pyodide) 로딩 상태 */
export type BridgeStatus = "idle" | "loading" | "ready" | "error";
