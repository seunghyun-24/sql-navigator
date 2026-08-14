# SQL Navigator — 아키텍처 & 폴더 구조

> GitHub용 프로젝트 전체 구조 가이드. 계층별 책임, 데이터 흐름, 폴더 구성을 한눈에 파악할 수 있습니다.

---

## 📐 전체 아키텍처 구조

```
사용자 입력 SQL
   ↓
┌──────────────────────────────────────┐
│         UI Layer (React/TS)          │  ← src/components/, src/hooks/
│  • Editor (SQL 입력)                 │
│  • WarningsPanel (분석 결과 표시)    │
│  • Visualizations (그래프, 플로우)   │
└──────────────────┬───────────────────┘
                   │ sql, schemaDdl
                   ↓
┌──────────────────────────────────────┐
│    Bridge Layer (Pyodide ↔ JS)       │  ← src/bridge/pyodide.ts
│  • Pyodide 로딩 & 초기화             │
│  • Python 함수 호출                  │
│  • JSON 직렬화/역직렬화              │
└──────────────────┬───────────────────┘
                   │ analyze(sql, schema)
                   ↓
┌──────────────────────────────────────┐
│    Analysis Layer (Python/Pyodide)   │  ← src/python/
│  ┌────────────────────────────────┐  │
│  │ Parser: SQL → AST              │  │  ← parser.py
│  │ (sqlglot 이용, 서버 없음)      │  │
│  └────────────────────────────────┘  │
│                 ↓                     │
│  ┌────────────────────────────────┐  │
│  │ Analysis Engine                │  │  ← engine.py
│  │ • Rule 적용 (단일 순회)        │  │
│  │ • Finding 생성 (fixSql 포함)   │  │
│  │ • Metrics 계산                 │  │
│  └────────────────────────────────┘  │
│                 ↓                     │
│  ┌────────────────────────────────┐  │
│  │ Post-Processing                │  │
│  │ • Join Graph 생성              │  │  ← join_graph.py
│  │ • Data Flow 추출               │  │  ← data_flow.py
│  │ • Suggestions 생성             │  │  ← suggestions.py
│  │ • SQL Diff 비교                │  │  ← sql_diff.py
│  └────────────────────────────────┘  │
│                 ↓                     │
│        AnalysisResult (JSON)          │
└──────────────────┬───────────────────┘
                   │ JSON
                   ↓
┌──────────────────────────────────────┐
│   Renderer Layer (TypeScript)        │  ← src/renderer/
│  • Layout 계산 (그래프, 플로우)      │
│  • Position 매핑 (에디터 하이라이트) │
└──────────────────┬───────────────────┘
                   ↓
┌──────────────────────────────────────┐
│         UI Layer (React)             │
│   분석 결과 렌더링 & 상호작용        │
│   • Warning 표시 & Apply 버튼        │
│   • Graph/Flow 시각화                │
│   • Metrics 표시                     │
└──────────────────────────────────────┘
```

---

## 📁 폴더 구조 & 역할

```
sql-navigator/
│
├── 📄 프로젝트 설정
│   ├── package.json                 # npm 의존성, 빌드 스크립트
│   ├── tsconfig.json                # TypeScript 설정
│   ├── vite.config.ts               # Vite 번들러 설정
│   ├── index.html                   # 진입점 HTML
│   └── tailwind.config.js           # Tailwind CSS 설정
│
├── 📚 문서 (docs/)
│   ├── vision.md                    # 프로젝트 비전 & 목표
│   ├── architecture.md              # 레이어 책임 & 데이터 계약
│   ├── principles.md                # 개발 원칙 (Immutable, AST First 등)
│   ├── analyzer.md                  # Rule 인터페이스 & Engine
│   ├── rules.md                     # Rule 카탈로그 & 구현 절차
│   ├── ui.md                        # UI 색상/컴포넌트 규칙
│   └── roadmap.md                   # 버전별 기능 로드맵
│
├── 📋 프로젝트 지침
│   └── CLAUDE.md                    # Claude 개발자용 지침
│
├── 📝 예제 & 테스트
│   └── examples/
│       ├── test-queries.md          # 테스트 쿼리 예제
│       └── validate_examples.py     # 예제 검증 스크립트
│
└── 📦 소스코드 (src/)
    ├── main.tsx                     # React 진입점
    ├── types.ts                     # 레이어 간 데이터 계약
    ├── App.tsx                      # 메인 App 컴포넌트
    │
    ├── 🔵 UI Layer (React Components)
    │   └── components/
    │       ├── Editor.tsx           # SQL 입력 에디터
    │       ├── WarningsPanel.tsx    # Warning 목록 & Apply 버튼 (v0.9)
    │       ├── AstTree.tsx          # AST 구조 트리 시각화
    │       ├── JoinGraphView.tsx    # 테이블 관계 그래프
    │       ├── QueryFlowView.tsx    # 쿼리 실행 흐름 시각화
    │       ├── FormattedSql.tsx     # 포맷팅된 SQL 표시
    │       ├── ErrorPanel.tsx       # Parse 에러 표시
    │       ├── MetricsBar.tsx       # 복잡도 메트릭 표시
    │       ├── SuggestionsPanel.tsx # 리팩토링 제안
    │       ├── SchemaPanel.tsx      # DDL 입력 (v0.5)
    │       └── DiffPanel.tsx        # SQL Diff 비교 (v0.8)
    │
    ├── 🎣 Business Logic Hooks
    │   └── hooks/
    │       ├── useAnalysis.ts       # SQL 분석 상태 관리
    │       │                        # • sql, setSql
    │       │                        # • result (AnalysisResult)
    │       │                        # • parsing, bridgeStatus
    │       └── useDiff.ts           # SQL Diff 상태 관리
    │
    ├── 🌉 Bridge Layer (Pyodide ↔ JavaScript)
    │   └── bridge/
    │       └── pyodide.ts           # Pyodide 통신 계층
    │                                # • loadPyodide()
    │                                # • callPythonAnalyze(sql, schema)
    │                                # • JSON 직렬화/역직렬화
    │
    ├── 📐 Renderer Layer
    │   └── renderer/
    │       ├── joinGraphLayout.ts   # Join Graph 레이아웃 계산
    │       ├── queryFlowLayout.ts   # Query Flow 레이아웃 계산
    │       └── editorPosition.ts    # 에디터 위치 ↔ AST 노드 매핑
    │
    └── 🐍 Analysis Layer (Python, Pyodide에서 실행)
        └── python/
            ├── main.py              # 진입점 (Bridge 호출 함수)
            │                        # • analyze(sql, schema_ddl) → JSON
            │                        # • diff(sql_before, sql_after) → JSON
            │
            ├── 📄 Parser
            │   └── parser.py        # SQL 파싱
            │                        # • parse(sql) → AST | error
            │                        # • format_sql(ast) → formatted
            │                        # • node_to_tree(ast) → AstNode[]
            │
            ├── 🔧 Core Analysis
            │   ├── engine.py        # Analysis Engine
            │   │                    # • class Rule (추상)
            │   │                    # • class Finding (fixSql 포함)
            │   │                    # • class AnalysisEngine
            │   │                    # • iter_nodes() 순회
            │   │
            │   ├── position.py      # Position Mapper (v0.7)
            │   │                    # • 토큰 기반 AST → (line, col) 매핑
            │   │
            │   ├── schema_context.py # 스키마 파싱 (v0.5)
            │   │                    # • parse_schema(ddl) → Schema
            │   │
            │   └── scope.py         # 스코프 해석
            │                        # • CTE, 서브쿼리 범위 해석
            │
            ├── 📊 Metrics & Analysis
            │   ├── metrics.py       # 복잡도 메트릭
            │   │                    # • joinCount, subqueryDepth
            │   │                    # • complexityScore 계산
            │   │
            │   ├── join_graph.py    # Join Graph 생성
            │   │                    # • 테이블 노드 & 관계 추출
            │   │
            │   ├── data_flow.py     # Data Flow 분석
            │   │                    # • 쿼리 흐름 단계 추출
            │   │                    # • 컬럼 lineage 계산
            │   │
            │   ├── suggestions.py   # 리팩토링 제안 (v0.5)
            │   │                    # • 새 AST 생성 기반 제안
            │   │
            │   └── sql_diff.py      # SQL Diff (v0.8)
            │                        # • AST 수준 비교
            │                        # • Warning/Metrics before-after
            │
            ├── ⚙️ Rules (Rule 카탈로그)
            │   ├── __init__.py      # Rule Registry (ALL_RULES)
            │   │
            │   ├── v0.2 Rules (기본)
            │   │   ├── cartesian_product.py       # Cartesian Product 탐지
            │   │   ├── delete_without_where.py   # DELETE 없는 WHERE
            │   │   ├── update_without_where.py   # UPDATE 없는 WHERE
            │   │   ├── select_without_where.py   # SELECT 없는 WHERE (SELECT *)
            │   │   ├── or_abuse.py               # OR → IN 제안 (v0.9: fixSql)
            │   │   ├── duplicate_join.py        # 중복 JOIN 탐지
            │   │   └── select_star.py           # SELECT * 탐지
            │   │
            │   ├── v0.5 Rules (스키마 기반)
            │   │   ├── pk_not_used.py           # PK 미사용 탐지
            │   │   └── implicit_conversion.py   # 암묵적 형변환 탐지
            │   │
            │   └── v0.6 Rules (안티패턴 확장)
            │       ├── null_comparison.py        # NULL 비교 (v0.9: fixSql)
            │       ├── not_in_with_null.py      # NOT IN NULL
            │       ├── leading_wildcard_like.py # LIKE '%...'
            │       ├── scalar_subquery_in_select.py # SELECT 스칼라 서브쿼리
            │       ├── union_vs_union_all.py    # UNION vs UNION ALL
            │       ├── offset_pagination.py     # OFFSET 페이지네이션
            │       ├── distinct_as_bandaid.py  # DISTINCT 남용
            │       └── join_type_mismatch.py   # JOIN 타입 불일치 (스키마 필요)
            │
            ├── 📋 Configuration
            │   └── config.py        # 전역 설정
            │                        # • DIALECT = "postgres"
            │
            └── 🧪 Tests
                └── tests/
                    ├── util.py              # 테스트 헬퍼
                    │                        # • run_rule() 유틸
                    │
                    ├── test_parser.py       # Parser 테스트
                    ├── test_position.py     # Position Mapper 테스트
                    │
                    └── test_<rule_name>.py  # 각 Rule별 테스트
                        # 예: test_null_comparison.py, test_or_abuse.py
                        # 각 테스트:
                        #   1. 탐지 케이스 (true positive)
                        #   2. 미탐지 케이스 (false positive 방지)
                        #   3. fixSql 검증 (v0.9+)
```

---

## 🔄 데이터 흐름 (Message Passing)

### 1. SQL 분석 흐름

```
User Input (SQL 입력)
   ↓
App.tsx: setSql(sql)
   ↓
useAnalysis Hook
   ├─ sql 상태 업데이트
   └─ bridge.callPythonAnalyze(sql, schemaDdl) 호출
   ↓
Bridge Layer (pyodide.ts)
   ├─ Pyodide Worker에서 main.analyze(sql, schema_ddl) 실행
   └─ AnalysisResult(JSON) 반환
   ↓
Python Analysis (main.py)
   1. parse(sql) → AST
   2. AnalysisEngine.run(ast) → Findings[] (각각 fixSql 포함)
   3. build_join_graph(ast) → JoinGraph
   4. build_data_flow(ast) → DataFlow
   5. compute_metrics(ast) → Metrics
   6. to_dict() → JSON
   ↓
TypeScript: AnalysisResult 수신
   ↓
App.tsx: setResult(result)
   ↓
Components 렌더링
   ├─ WarningsPanel: Warning[] 표시
   ├─ JoinGraphView: 그래프 렌더링
   ├─ MetricsBar: 메트릭 표시
   └─ ...
```

### 2. Apply Fix 흐름 (v0.9)

```
User Click: "✓ 자동 수정 적용" Button
   ↓
WarningCard.handleApply()
   └─ onApplyFix(warning.fixSql) 호출
   ↓
App.tsx: handleApplyFix(fixSql)
   └─ setSql(fixSql)
   ↓
useAnalysis Hook: sql 변경 감지
   └─ bridge.callPythonAnalyze(fixSql, ...) 호출 (자동 재분석)
   ↓
Python Analysis: 새 SQL 분석
   ├─ 같은 Rule 재적용 → Finding 없음 확인
   └─ AnalysisResult 반환
   ↓
UI 업데이트: 문제 해소됨 표시
```

### 3. SQL Diff 흐름 (v0.8)

```
User: Diff 탭 활성화
   ↓
useDiff Hook: diff(sqlBefore, sqlAfter, schema) 호출
   ↓
Bridge: main.diff(before, after, schema) 실행
   ↓
Python: sql_diff.build_diff()
   1. 양쪽 모두 analyze()
   2. Warning/Metrics before-after 비교
   3. resolvedRules (개선), introducedRules (악화) 추출
   └─ DiffResult(JSON)
   ↓
DiffPanel: before-after 비교 시각화
```

---

## 💾 데이터 계약 (Types)

### Warning (WarningsPanel에서 표시)
```typescript
interface Warning {
  ruleId: string;              // "null-comparison"
  severity: "CRITICAL" | "WARNING" | "INFO";
  message: string;             // 한 줄 요약
  reason: string;              // 왜 위험한가
  example: string;             // 문제 쿼리 예시
  fix: string;                 // 수정 방법 설명
  snippet: string;             // 해당 부분 SQL 조각
  location?: { line, col };    // v0.7: 에디터 위치
  fixSql?: string;             // v0.9: 자동 수정 SQL (있으면 Apply 버튼 표시)
}
```

### AnalysisResult (Python → TypeScript)
```typescript
interface AnalysisResult {
  ok: boolean;
  tree: AstNode;               // AST 트리
  formatted: string;           // 포맷팅된 SQL
  warnings: Warning[];         // 분석 결과
  suggestions: Suggestion[];   // 리팩토링 제안
  metrics: Metrics;            // 복잡도 메트릭
  joinGraph: JoinGraph;        // 테이블 관계
  dataFlow: DataFlow;          // 데이터 흐름
  schemaInfo: SchemaInfo;      // DDL 파싱 상태
}
```

---

## 🏗️ 레이어별 책임

### 1️⃣ UI Layer (React/TypeScript)
- **책임**: 화면 표시 & 사용자 상호작용
- **금지**: Business Logic, SQL 조작
- **파일**: `components/`, `App.tsx`

### 2️⃣ Renderer Layer (TypeScript)
- **책임**: AnalysisResult → 화면 모델 변환
  - 그래프 레이아웃 계산 (D3.js 같은 것 없이 논리적 계산만)
  - 에디터 위치 매핑
- **금지**: SQL 파싱, AST 해석
- **파일**: `renderer/`

### 3️⃣ Bridge Layer (TypeScript/Python 경계)
- **책임**: Pyodide ↔ JavaScript 통신
  - Python 함수 호출
  - JSON 직렬화/역직렬화
- **금지**: 분석 로직, UI 관심사
- **파일**: `bridge/pyodide.ts`

### 4️⃣ Analysis Layer (Python)
- **책임**: SQL 분석, Finding 생성
  - AST 기반 규칙 적용
  - fixSql 생성
  - 메트릭 계산
- **금지**: UI, 상태 관리, DB 연결
- **원칙**:
  - **Immutable**: AST 수정 X, 새 AST 생성
  - **Stateless**: 같은 입력 → 항상 같은 결과
  - **Rule Driven**: Engine 수정 X, Rule만 추가
- **파일**: `python/`

### 5️⃣ Parser Layer (Python)
- **책임**: SQL 문자열 → AST 변환
- **도구**: sqlglot
- **금지**: 분석, 최적화, 경고 생성
- **파일**: `parser.py`

---

## 📌 v0.9 주요 변경 (Fix Apply)

### Python Layer
- **engine.py**: `Finding.fix_sql` 필드 추가
- **rules/** (selected):
  - `null_comparison.py`: `= NULL → IS NULL` 자동 변환
  - `or_abuse.py`: `OR → IN` 변환
  - 각 Rule: `_generate_fix_sql()` 메서드 구현

### TypeScript Layer
- **types.ts**: `Warning.fixSql?: string` 추가
- **WarningsPanel.tsx**:
  - fixSql 있으면 Green "✓ 자동 수정 적용" 버튼 표시
  - Apply 클릭 → `onApplyFix(fixSql)` 콜백
- **App.tsx**:
  - `handleApplyFix()`: `setSql(fixSql)` → 자동 재분석

### 테스트
- **test_*.py**: fixSql 검증 추가
  1. fixSql parse 성공
  2. 재적용 시 Finding 없음

---

## 🚀 개발 흐름

### 새 Rule 추가하기

1. **Rule 파일 작성** (`src/python/rules/my_rule.py`)
   ```python
   class MyRule(Rule):
       id = "my-rule"
       severity = "WARNING"
       target_nodes = (exp.Select,)  # 확인할 AST 노드
       
       def check(self, node, ctx):
           # AST 검사
           if 문제:
               return [Finding(..., fix_sql=None or "...")]
           return []
   ```

2. **Registry 등록** (`src/python/rules/__init__.py`)
   ```python
   from my_rule import MyRule
   ALL_RULES = [MyRule(), ...]
   ```

3. **테스트 작성** (`src/python/tests/test_my_rule.py`)
   ```python
   def test_detects_issue():
       findings = run_rule(rule, "SELECT ...")
       assert len(findings) == 1
   
   def test_fix_sql():  # v0.9+
       f = findings[0]
       assert f.fix_sql is not None
       # fixSql parse 검증
       # 재적용 시 Finding 없음 검증
   ```

### 새 Component 추가하기

1. **Component 파일 작성** (`src/components/MyComponent.tsx`)
   - Props: Analysis 결과만 (state 관리 X)
   - Render only

2. **App.tsx에서 조건부 렌더링**
   ```tsx
   {!error && tab === "myTab" && (
     <MyComponent data={ok?.myData ?? null} />
   )}
   ```

---

## 📚 주요 개념

### AST First
- 모든 분석은 AST 기반 (Regex X, 문자열 검색 X)
- Rule은 AST 노드 타입 기반

### Immutable
- 원본 AST 수정 금지
- 변환 필요 시 복사 → 새 AST 생성

### Local First
- 모든 처리 브라우저 내에서 (Pyodide)
- SQL은 서버로 전송되지 않음

### Rule Driven
- Engine 로직 변경 X
- 새 검사 = 새 Rule 파일 추가만

---

## 🔗 참고 문서

- **vision.md**: 프로젝트 목표 및 포지셔닝
- **architecture.md**: 레이어 설계 & 데이터 계약
- **principles.md**: 개발 원칙 (5가지)
- **analyzer.md**: Rule 인터페이스 & Engine 동작
- **rules.md**: Rule 카탈로그 & 각 Rule의 목적
- **ui.md**: UI 색상/컴포넌트 규칙
- **roadmap.md**: 버전별 기능 계획 (v0.1~v0.9+)

---

## 📦 빌드 & 실행

```bash
# 의존성 설치
npm install

# 개발 서버 실행
npm run dev

# 프로덕션 빌드
npm run build

# Python 테스트 (pytest 설치 필요)
cd src/python
pytest tests/ -v
```

---

## 🎯 핵심 통찰

**SQL Navigator는 SQL을 "실행하는" 도구가 아니라, "이해하는" 도구다.**

| 구분 | 기존 도구 | SQL Navigator |
|------|----------|---------------|
| 중심 | Execution Plan (DB 관점) | Query 구조 (사람 관점) |
| 시점 | 실행 후 | 실행 전 (리뷰 단계) |
| 대상 | DBA, 튜닝 전문가 | 모든 개발자 |
| 역할 | 성능 진단 | 구조 이해 + 위험 사전 발견 |

따라서:
- **AST First**: 구문 구조를 깊이 있게 이해
- **Local First**: 개인 브라우저에서만 처리 (개인정보 보호)
- **Explainability**: 모든 Warning은 이유 + 예시 + 수정 방법 제시
