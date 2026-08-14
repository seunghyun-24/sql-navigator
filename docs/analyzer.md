# Analyzer

## 역할

AST를 입력받아 AnalysisResult를 출력하는 순수 함수 계층.
Parsing하지 않고, AST를 수정하지 않고, 상태를 갖지 않는다. (principles.md)

```
Analyzer(ast, context?) → AnalysisResult
```

## AnalysisResult

```
AnalysisResult {
  warnings:    Warning[]        // Rule 실행 결과
  suggestions: Suggestion[]     // Refactoring 제안 (새 AST 기반)
  metrics:     Metrics          // complexity 등 수치
  joinGraph:   JoinGraph        // 테이블 관계 그래프
  dataFlow:    DataFlow         // 컬럼 lineage, 데이터 흐름
  formatted:   string           // Formatter 결과
}

Metrics {
  joinCount, subqueryDepth, cteCount,
  tableCount, whereConditionCount,
  complexityScore                // 가중합, 산식은 rules.md 참조
}
```

## Rule Interface

모든 Rule은 아래 인터페이스를 구현한다. **새 검사 = 새 Rule 구현체.**
Engine 수정 없이 등록만으로 확장한다.

```python
class Rule(Protocol):
    id: str                    # 예: "cartesian-product"
    severity: Severity         # INFO | WARNING | CRITICAL
    target_nodes: list[type]   # 방문할 AST 노드 타입 (예: [exp.Join])

    def check(self, node: Expression, ctx: RuleContext) -> list[Finding]:
        """node를 검사하고 Finding을 반환. AST를 수정하지 않는다."""
```

```
Finding {
  ruleId, severity,
  message,          # 한 줄 요약
  reason,           # 왜 위험한가          ← Explainability
  example,          # 문제 쿼리 예시 (before)
  fix,              # 수정 예시 (after)
  snippet,          # 해당 부분 SQL 조각 (UI 표시용, 분석에 사용 금지)
  fixSql,           # (v0.9) 자동 수정 SQL | null — 새 AST 생성으로 만든
                    # 문장 대체 텍스트. 있으면 UI에 Apply 버튼이 노출된다
  location          # AST 노드 위치 (line, col) | null — v0.2에서는 null +
                    # snippet 대체, v0.7부터 Position Mapper로 채운다
}

RuleContext {
  root,             # 전체 AST (read-only) — 노드 밖 문맥이 필요한 Rule용
  dialect,          # "postgres"
  schema?           # 선택: 사용자가 제공한 스키마 정보 (PK, index)
}
```

## Engine 동작

1. Rule Registry에서 활성 Rule 목록을 가져온다
2. AST를 한 번 순회하며 각 노드에서 `target_nodes`가 일치하는 Rule의 `check`를 호출한다 (Rule마다 재순회하지 않는다 — 단일 순회)
3. Finding을 모아 severity 순으로 정렬해 warnings로 반환한다

```python
engine = AnalysisEngine(rules=[
    CartesianProductRule(),
    DeleteWithoutWhereRule(),
    ...
])
result = engine.run(ast, context)
```

## Schema Context (선택 입력)

PK/index 기반 Rule(예: pk-not-used)은 스키마 정보가 있어야 정확하다.
사용자가 스키마(DDL 또는 JSON)를 제공하면 RuleContext.schema로 전달된다.

- 스키마 없음 → 해당 Rule은 "가능성" 수준의 INFO만 내거나 skip
- 스키마 있음 → 정확한 WARNING

DB에 연결해서 스키마를 가져오지 않는다. 항상 사용자 제공이다.

## Position Mapper (v0.7)

sqlglot AST는 노드 위치를 안정적으로 제공하지 않으므로,
tokenizer 토큰 스트림의 위치 정보로 AST 노드 → `(line, col)`을 매핑하는
보조 모듈을 둔다.

- 위치: Parser Layer의 보조 모듈 (분석 로직 아님 — Warning을 만들지 않는다)
- 입력: 원본 SQL + AST 노드, 출력: `{ line, col } | null`
- 매핑 실패 시 null을 반환하고 Finding은 snippet으로 폴백한다 (v0.2 동작 유지)
- Rule은 Position Mapper를 직접 호출하지 않는다 — Engine이 Finding 수집 후
  일괄로 location을 채운다 (Rule은 위치 관심사를 모른다)

## SQL Diff (v0.8)

두 SQL을 AST 수준에서 비교하는 별도 진입점. Regex/문자열 diff 금지.

```
diff(sqlA, sqlB, dialect) → DiffResult
```

```
DiffResult {
  equivalent,       # AST 수준 변경 없음 (formatting-only 차이는 동일 취급)
  changes[],        # AST 수준 변경 목록 (sqlglot diff 위임, Keep 제외)
                    # { op: insert|remove|move|update, kind, before, after }
  changeCount,
  metricsBefore, metricsAfter,      # Complexity 비교
  warningsBefore, warningsAfter,    # { total, bySeverity } (Engine 재사용)
  resolvedRules[],                  # before 대비 줄어든 ruleId (개선, Green)
  introducedRules[]                 # before 대비 늘어난 ruleId (악화, Red)
}
```

- 내부적으로 양쪽을 각각 parse → analyze 후 결과를 비교한다
- Analyzer 원칙 동일 적용: 순수 함수, AST 수정 금지, JSON만 Bridge 통과

## Fix Apply (v0.9)

Rule이 기계적으로 안전하게 고칠 수 있는 Finding에는 `fixSql`을 첨부한다.

- 생성 방법: 원본 AST를 **복사**해 새 AST를 만들고 SQL로 출력한다 (Immutable)
- `fixSql`은 문장 전체의 대체 텍스트다 — UI는 에디터 내용을 교체만 한다
  (UI에서 SQL 조작 금지, architecture.md Layer 책임)
- 모든 Rule이 fixSql을 제공할 필요는 없다 — 기계적 치환이 안전한 경우만
  (예: null-comparison의 `= NULL → IS NULL`, or-abuse의 `OR → IN`)
- 판단이 필요한 수정(예: cartesian-product의 JOIN 조건)은 fixSql 없이
  example/fix 텍스트로만 안내한다 — 틀린 자동 수정은 없는 것보다 나쁘다
- Apply 후 UI는 재분석을 트리거해 해당 Warning 해소를 확인한다

### 테스트 (fixSql 제공 Rule 추가 요건)

- fixSql을 parse했을 때 에러가 없어야 한다
- fixSql에 같은 Rule을 다시 적용했을 때 Finding이 없어야 한다

## 테스트

- 테스트는 **Rule 단위**로 작성한다
- 각 Rule은 최소한 다음을 커버한다:
  - 탐지해야 하는 SQL (true positive)
  - 탐지하면 안 되는 유사 SQL (false positive 방지)
  - Finding의 reason/example/fix 존재 여부
- 입력은 SQL 문자열 → parse → Rule 적용 순서로 하되,
  assertion은 Finding에 대해서만 한다
