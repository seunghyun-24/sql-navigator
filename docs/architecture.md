# Architecture

## 기술 스택

- **Parser**: sqlglot (Pyodide로 브라우저 내 실행, 서버 없음)
- **우선 지원 Dialect**: PostgreSQL (sqlglot dialect 옵션으로 확장 가능하게 설계)
- **UI**: React + TypeScript + Tailwind + shadcn/ui + React Aria
- **그래프 렌더링**: 노드 그래프 (Join Graph, Data Flow, Query Flow)

브라우저 단독 실행이 원칙이다. SQL은 사용자의 브라우저를 떠나지 않는다.

## Pipeline

```
SQL (text)
   │
   ▼
Parser  ──────────── sqlglot.parse_one(sql, dialect)
   │
   ▼
AST (immutable)
   │
   ▼
Analysis Engine ──── 등록된 Rule들을 AST에 순차 적용
   │
   ├── Formatter                 (sqlglot 위임)
   ├── Linter / Risk Rules       (안티패턴, 위험 쿼리 → Warning)
   ├── AST Explorer              (구조 트리)
   ├── Join Graph                (테이블 관계 그래프)
   ├── Data Flow                 (컬럼/데이터 흐름, lineage)
   ├── Complexity Score          (JOIN 수, 서브쿼리 깊이, CTE 수)
   └── Refactoring Suggestion    (읽기 좋은 SQL 제안 — 원본 AST는 불변,
                                  새 AST를 생성하여 제안)
   │
   ▼
AnalysisResult (JSON, 직렬화 가능)
   │
   ▼
Renderer ─────────── AnalysisResult → 시각 컴포넌트 모델
   │
   ▼
UI (React)
```

## Layer 책임

### Parser Layer (Python / Pyodide)

책임:
- SQL → AST 변환 (sqlglot 위임)
- Parse Error를 구조화된 형태로 반환 (위치, 메시지)

절대 하지 않는 것:
- Warning 생성
- Optimization
- 분석 로직

### Analysis Layer (Python / Pyodide)

책임:
- AST 분석 → AnalysisResult 생성
- Rule 등록/실행 (자세한 것은 analyzer.md)

절대 하지 않는 것:
- SQL Parsing (문자열을 직접 다루지 않는다)
- AST 수정 (Refactoring도 새 AST 생성으로 처리)
- UI 관심사 (색상, 레이아웃 등)

### Bridge Layer (Pyodide ↔ JS)

책임:
- SQL 문자열을 Python으로 전달
- AnalysisResult(JSON)를 JS로 반환
- Pyodide 로딩/에러 상태 관리

원칙:
- 경계를 넘는 데이터는 **직렬화 가능한 JSON만** 허용
- AST 객체 자체를 JS로 넘기지 않는다

### Renderer Layer (TypeScript)

책임:
- AnalysisResult → 화면 모델 변환 (그래프 레이아웃 계산 등)

절대 하지 않는 것:
- SQL/AST 해석 (분석은 Analysis Layer에서 끝난다)

### UI Layer (React)

책임:
- 화면 표시, 사용자 상호작용

절대 하지 않는 것:
- Business Logic (Component 내부에 분석/변환 로직 금지)

## 데이터 계약

Layer 간 통신은 아래 타입으로만 한다.

```
ParseResult      = { ast | error: { message, line, col } }
AnalysisResult   = { warnings[], suggestions[], metrics, joinGraph, dataFlow,
                     formatted, schemaInfo }
Warning          = { ruleId, severity, message, reason, example, fix,
                     fixSql?, location }                // fixSql: v0.9 자동 수정
Suggestion       = { id, title, description, sql }      // 새 AST 기반 재작성
SchemaInfo       = { provided, tableCount, error }      // 사용자 DDL 파싱 상태
DiffResult       = { equivalent, changes[], changeCount,
                     metricsBefore, metricsAfter,
                     warningsBefore, warningsAfter,     // { total, bySeverity }
                     resolvedRules[], introducedRules[] }  // v0.8 SQL Diff
```

SQL Diff(v0.8)는 Analysis Layer의 별도 진입점(`diff(sqlA, sqlB)`)으로,
같은 Bridge를 통해 DiffResult(JSON)만 반환한다 (analyzer.md).

Fix Apply(v0.9): `fixSql`은 Analysis Layer가 새 AST에서 생성한 완성된
문자열이다. UI는 에디터 내용을 이 문자열로 교체만 하고, 교체 후 재분석을
요청한다. UI에서 SQL을 조작하지 않는다.

Schema Context(v0.5): 사용자가 붙여넣은 DDL은 SQL과 함께 Bridge를 건너
Analysis Layer에서 파싱된다 (`analyze(sql, schemaDdl)`). DDL도 브라우저를
떠나지 않는다.

의존 방향은 한쪽으로만 흐른다: `UI → Renderer → Bridge → Analysis → Parser`.
역방향 의존 금지.
