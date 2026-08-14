# SQL Navigator

SQL을 실행하기 위한 도구가 아니라, **SQL을 구조적으로 이해하고 품질을 분석하기 위한 도구**입니다.

SQL을 붙여넣으면 브라우저 안에서 곧바로 AST로 파싱하고, 구조·위험·복잡도를 분석해 보여줍니다. 서버로 전송되지 않고, DB에 연결하지도 않습니다.

## 왜 만드는가

기존 SQL 도구는 대부분 Execution Plan 중심입니다. DB가 어떻게 실행할지는 보여주지만, 사람이 SQL의 구조와 위험을 이해하는 데는 도움이 크지 않습니다. sqlglot 같은 라이브러리는 Parser·Formatter·AST 조작 기능을 제공하지만, 그 자체로는 사람을 위한 분석·시각화 도구가 아닙니다.

SQL Navigator는 이 사이를 채웁니다.

| 구분 | 기존 도구 | SQL Navigator |
|---|---|---|
| 중심 | Execution Plan (DB 관점) | Query 구조 (사람 관점) |
| 시점 | 실행 후 | 실행 전 (리뷰/검토 단계) |
| 대상 | DBA, 튜닝 전문가 | SQL을 작성·리뷰하는 모든 개발자 |
| 역할 | 성능 진단 | 구조 이해 + 위험 사전 발견 |

SQL IDE도 아니고, DB에 연결하는 도구도 아닙니다. 코드 리뷰와 검토 단계에서 쓰는 보조 도구이며, Explain Plan을 대체하지 않고 그 이전 단계를 채우는 것을 목표로 합니다. 자세한 내용은 [docs/vision.md](docs/vision.md)에 있습니다.

## 무엇을 하는가 (현재 구현 범위)

로드맵 v0.1~v0.9까지 전 기능이 구현되어 있습니다.

- **SQL Editor + Parse Error 표시** — 파싱 실패 시 위치와 메시지를 구조화해 보여줍니다
- **Formatter** — sqlglot 위임
- **AST Explorer** — 구조 트리 시각화
- **Warnings (Rule 기반 위험 탐지, 16종)** — Cartesian Product, WHERE 없는 DELETE/UPDATE/SELECT, NULL 비교 오류, NOT IN + NULL, 선행 와일드카드 LIKE, OR 남용, 중복 JOIN, SELECT * 등. 각 Warning은 이유·예시·수정 방법을 함께 제공합니다 ([docs/rules.md](docs/rules.md))
- **Complexity Metrics** — JOIN 수, 서브쿼리 깊이, CTE 수, 복잡도 점수
- **Join Graph** — 테이블 관계 노드 그래프, Cartesian Product 강조
- **Query Flow / Data Flow** — 쿼리 실행 흐름의 논리적 재구성(FROM → JOIN → WHERE → … → LIMIT)과 컬럼 lineage
- **Schema Context** — DDL(CREATE TABLE/INDEX)을 붙여넣으면 PK·index·컬럼 타입 기반 정밀 분석(pk-not-used, implicit-conversion, join-type-mismatch)이 활성화됩니다. DDL도 브라우저를 떠나지 않습니다
- **Refactoring Suggestion** — OR 나열 → IN, SELECT * → 명시적 컬럼 등 재작성 제안 (원본 AST는 불변, 새 AST를 생성)
- **Warning 위치 하이라이트** — 토큰 위치 기반으로 에디터의 정확한 지점을 가리킵니다
- **SQL Diff** — 두 SQL을 AST 수준에서 비교해 동등성, 변경 목록, Complexity/Warning 변화, 개선/악화된 Rule을 보여줍니다
- **Fix Apply** — 기계적으로 안전한 Warning은 자동 수정 SQL을 제공하고, 적용 시 에디터 내용을 교체한 뒤 재분석합니다

전 과정이 Pyodide로 브라우저 안에서 실행됩니다. 앞으로의 계획(다른 dialect, CLI 모드 등)은 [docs/roadmap.md](docs/roadmap.md)에 있습니다.

## 아키텍처

```
SQL (text)
   │
   ▼
Parser ─────────────── sqlglot.parse_one(sql, dialect)      [Python / Pyodide]
   │
   ▼
AST (immutable)
   │
   ▼
Analysis Engine ────── 등록된 Rule을 AST에 단일 순회로 적용   [Python / Pyodide]
   │
   ▼
AnalysisResult (JSON, 직렬화 가능)
   │
   ▼
Bridge ──────────────── Pyodide ↔ JS, JSON만 통과            [src/bridge]
   │
   ▼
Renderer ─────────────── 화면 모델 변환 (그래프 레이아웃 등)   [src/renderer]
   │
   ▼
UI (React) ───────────── 렌더 전용, Business Logic 없음       [src/components]
```

의존 방향은 한쪽으로만 흐릅니다: `UI → Renderer → Bridge → Analysis → Parser` (역방향 금지). Layer별 책임과 데이터 계약은 [docs/architecture.md](docs/architecture.md)에 정리되어 있습니다.

### 불변 원칙

- **AST First** — Regex나 문자열 검색으로 SQL을 분석하지 않습니다. 항상 AST
- **Immutable** — Analyzer는 AST를 수정하지 않습니다. 변환이 필요하면 새 AST를 생성합니다
- **Stateless** — Analyzer는 순수 함수입니다. DB 연결, 외부 I/O 없음
- **Rule Driven** — 새 검사 = 새 Rule 구현체 추가. Engine은 건드리지 않습니다
- **Explainability** — 모든 Warning은 이유·예시·수정 방법을 포함합니다
- **Local First** — SQL은 사용자의 브라우저를 떠나지 않습니다

자세한 내용은 [docs/principles.md](docs/principles.md)를 참고하세요.

## 기술 스택

- **Parser/Analyzer**: Python (sqlglot), Pyodide로 브라우저 내 실행
- **우선 지원 Dialect**: PostgreSQL
- **UI**: React + TypeScript + Tailwind + shadcn/ui + React Aria
- **그래프 렌더링**: 노드 그래프 (Join Graph, Query Flow)

## 실행

```bash
npm install
npm run dev
```

첫 접속 시 Pyodide + sqlglot을 CDN(cdn.jsdelivr.net, pypi.org)에서 내려받아 초기화합니다(수 초 소요, 이후 브라우저 캐시). 사내망에서 해당 CDN이 차단된 경우 `src/bridge/pyodide.ts`의 `PYODIDE_BASE`를 로컬 서빙 경로로 변경하세요.

## 테스트

테스트는 Rule 단위로 작성합니다. 각 Rule은 탐지 케이스, 비탐지(false positive 방지) 케이스, Explainability(이유/예시/수정) 검증을 포함합니다.

```bash
pip install sqlglot pytest
cd src/python && pytest tests/
```

## 구조

```
src/
├── python/                # Parser/Analysis Layer (sqlglot, Pyodide로 실행)
│   ├── parser.py          # SQL -> AST, 트리 직렬화, Formatter
│   ├── engine.py          # Rule Interface, Finding, AnalysisEngine
│   ├── rules/              # Rule 구현체 (1 파일 = 1 Rule) + Registry
│   ├── metrics.py          # Complexity Score
│   ├── join_graph.py       # 테이블 관계 그래프
│   ├── data_flow.py        # Query Flow + 컬럼 lineage
│   ├── schema_context.py   # DDL -> 스키마 모델
│   ├── scope.py            # alias -> 테이블 해석
│   ├── suggestions.py      # Refactoring Suggestion — 새 AST 생성
│   ├── position.py         # 토큰 위치 -> (line, col) 매핑
│   ├── sql_diff.py         # SQL Diff
│   ├── main.py             # 진입점: analyze(sql, schema_ddl), diff(before, after)
│   └── tests/              # Rule 단위 테스트
├── bridge/pyodide.ts       # Bridge Layer (JSON only)
├── hooks/                  # Business Logic (Component 밖)
├── renderer/                # Renderer Layer — 그래프/위치 레이아웃 계산
├── components/              # 렌더 전용 Component
└── App.tsx                  # Layout (Sidebar | Editor | Analysis 탭)

docs/
├── vision.md           # 왜 만드는가
├── architecture.md     # 시스템 구조, Layer 책임, 데이터 계약
├── principles.md       # 불변 원칙
├── analyzer.md          # Rule Interface, Engine 동작
├── rules.md             # Rule 카탈로그, 추가 절차
├── ui.md                # UI 철학, 레이아웃, 색상 규칙
└── roadmap.md            # 버전별 개발 계획

CLAUDE.md                # 이 프로젝트에서 AI가 따르는 작업 규칙
```

## 기여

새 기능을 만들기 전에 [docs/architecture.md](docs/architecture.md)를 위반하지 않는지 먼저 확인하세요. 새 Rule을 추가하는 절차는 [docs/rules.md](docs/rules.md)의 "Rule 추가 절차"를 참고하세요 — Rule 파일 추가, 테스트 작성, Registry 등록, 문서 업데이트 순서입니다. UI는 Tailwind, shadcn/ui, React Aria만 사용하며 Business Logic은 Component 내부에 두지 않습니다.
# SQL Navigator

SQL을 실행하기 위한 도구가 아니라, **SQL을 구조적으로 이해하고 품질을 분석하기 위한 도구**입니다.

SQL을 붙여넣으면 브라우저 안에서 곧바로 AST로 파싱하고, 구조·위험·복잡도를 분석해 보여줍니다. 서버로 전송되지 않고, DB에 연결하지도 않습니다.

## 왜 만드는가

기존 SQL 도구는 대부분 Execution Plan 중심입니다. DB가 어떻게 실행할지는 보여주지만, 사람이 SQL의 구조와 위험을 이해하는 데는 도움이 크지 않습니다. sqlglot 같은 라이브러리는 Parser·Formatter·AST 조작 기능을 제공하지만, 그 자체로는 사람을 위한 분석·시각화 도구가 아닙니다.

SQL Navigator는 이 사이를 채웁니다.

| 구분 | 기존 도구 | SQL Navigator |
|---|---|---|
| 중심 | Execution Plan (DB 관점) | Query 구조 (사람 관점) |
| 시점 | 실행 후 | 실행 전 (리뷰/검토 단계) |
| 대상 | DBA, 튜닝 전문가 | SQL을 작성·리뷰하는 모든 개발자 |
| 역할 | 성능 진단 | 구조 이해 + 위험 사전 발견 |

SQL IDE도 아니고, DB에 연결하는 도구도 아닙니다. 코드 리뷰와 검토 단계에서 쓰는 보조 도구이며, Explain Plan을 대체하지 않고 그 이전 단계를 채우는 것을 목표로 합니다. 자세한 내용은 [docs/vision.md](docs/vision.md)에 있습니다.

## 무엇을 하는가 (현재 구현 범위)

로드맵 v0.1~v0.9까지 전 기능이 구현되어 있습니다.

- **SQL Editor + Parse Error 표시** — 파싱 실패 시 위치와 메시지를 구조화해 보여줍니다
- **Formatter** — sqlglot 위임
- **AST Explorer** — 구조 트리 시각화
- **Warnings (Rule 기반 위험 탐지, 16종)** — Cartesian Product, WHERE 없는 DELETE/UPDATE/SELECT, NULL 비교 오류, NOT IN + NULL, 선행 와일드카드 LIKE, OR 남용, 중복 JOIN, SELECT * 등. 각 Warning은 이유·예시·수정 방법을 함께 제공합니다 ([docs/rules.md](docs/rules.md))
- **Complexity Metrics** — JOIN 수, 서브쿼리 깊이, CTE 수, 복잡도 점수
- **Join Graph** — 테이블 관계 노드 그래프, Cartesian Product 강조
- **Query Flow / Data Flow** — 쿼리 실행 흐름의 논리적 재구성(FROM → JOIN → WHERE → … → LIMIT)과 컬럼 lineage
- **Schema Context** — DDL(CREATE TABLE/INDEX)을 붙여넣으면 PK·index·컬럼 타입 기반 정밀 분석(pk-not-used, implicit-conversion, join-type-mismatch)이 활성화됩니다. DDL도 브라우저를 떠나지 않습니다
- **Refactoring Suggestion** — OR 나열 → IN, SELECT * → 명시적 컬럼 등 재작성 제안 (원본 AST는 불변, 새 AST를 생성)
- **Warning 위치 하이라이트** — 토큰 위치 기반으로 에디터의 정확한 지점을 가리킵니다
- **SQL Diff** — 두 SQL을 AST 수준에서 비교해 동등성, 변경 목록, Complexity/Warning 변화, 개선/악화된 Rule을 보여줍니다
- **Fix Apply** — 기계적으로 안전한 Warning은 자동 수정 SQL을 제공하고, 적용 시 에디터 내용을 교체한 뒤 재분석합니다

전 과정이 Pyodide로 브라우저 안에서 실행됩니다. 앞으로의 계획(다른 dialect, CLI 모드 등)은 [docs/roadmap.md](docs/roadmap.md)에 있습니다.

## 아키텍처

```
SQL (text)
   │
   ▼
Parser ─────────────── sqlglot.parse_one(sql, dialect)      [Python / Pyodide]
   │
   ▼
AST (immutable)
   │
   ▼
Analysis Engine ────── 등록된 Rule을 AST에 단일 순회로 적용   [Python / Pyodide]
   │
   ▼
AnalysisResult (JSON, 직렬화 가능)
   │
   ▼
Bridge ──────────────── Pyodide ↔ JS, JSON만 통과            [src/bridge]
   │
   ▼
Renderer ─────────────── 화면 모델 변환 (그래프 레이아웃 등)   [src/renderer]
   │
   ▼
UI (React) ───────────── 렌더 전용, Business Logic 없음       [src/components]
```

의존 방향은 한쪽으로만 흐릅니다: `UI → Renderer → Bridge → Analysis → Parser` (역방향 금지). Layer별 책임과 데이터 계약은 [docs/architecture.md](docs/architecture.md)에 정리되어 있습니다.

### 불변 원칙

- **AST First** — Regex나 문자열 검색으로 SQL을 분석하지 않습니다. 항상 AST
- **Immutable** — Analyzer는 AST를 수정하지 않습니다. 변환이 필요하면 새 AST를 생성합니다
- **Stateless** — Analyzer는 순수 함수입니다. DB 연결, 외부 I/O 없음
- **Rule Driven** — 새 검사 = 새 Rule 구현체 추가. Engine은 건드리지 않습니다
- **Explainability** — 모든 Warning은 이유·예시·수정 방법을 포함합니다
- **Local First** — SQL은 사용자의 브라우저를 떠나지 않습니다

자세한 내용은 [docs/principles.md](docs/principles.md)를 참고하세요.

## 기술 스택

- **Parser/Analyzer**: Python (sqlglot), Pyodide로 브라우저 내 실행
- **우선 지원 Dialect**: PostgreSQL
- **UI**: React + TypeScript + Tailwind + shadcn/ui + React Aria
- **그래프 렌더링**: 노드 그래프 (Join Graph, Query Flow)

## 실행

```bash
npm install
npm run dev
```

첫 접속 시 Pyodide + sqlglot을 CDN(cdn.jsdelivr.net, pypi.org)에서 내려받아 초기화합니다(수 초 소요, 이후 브라우저 캐시). 사내망에서 해당 CDN이 차단된 경우 `src/bridge/pyodide.ts`의 `PYODIDE_BASE`를 로컬 서빙 경로로 변경하세요.

## 테스트

테스트는 Rule 단위로 작성합니다. 각 Rule은 탐지 케이스, 비탐지(false positive 방지) 케이스, Explainability(이유/예시/수정) 검증을 포함합니다.

```bash
pip install sqlglot pytest
cd src/python && pytest tests/
```

## 구조

```
src/
├── python/                # Parser/Analysis Layer (sqlglot, Pyodide로 실행)
│   ├── parser.py          # SQL -> AST, 트리 직렬화, Formatter
│   ├── engine.py          # Rule Interface, Finding, AnalysisEngine
│   ├── rules/              # Rule 구현체 (1 파일 = 1 Rule) + Registry
│   ├── metrics.py          # Complexity Score
│   ├── join_graph.py       # 테이블 관계 그래프
│   ├── data_flow.py        # Query Flow + 컬럼 lineage
│   ├── schema_context.py   # DDL -> 스키마 모델
│   ├── scope.py            # alias -> 테이블 해석
│   ├── suggestions.py      # Refactoring Suggestion — 새 AST 생성
│   ├── position.py         # 토큰 위치 -> (line, col) 매핑
│   ├── sql_diff.py         # SQL Diff
│   ├── main.py             # 진입점: analyze(sql, schema_ddl), diff(before, after)
│   └── tests/              # Rule 단위 테스트
├── bridge/pyodide.ts       # Bridge Layer (JSON only)
├── hooks/                  # Business Logic (Component 밖)
├── renderer/                # Renderer Layer — 그래프/위치 레이아웃 계산
├── components/              # 렌더 전용 Component
└── App.tsx                  # Layout (Sidebar | Editor | Analysis 탭)

docs/
├── vision.md           # 왜 만드는가
├── architecture.md     # 시스템 구조, Layer 책임, 데이터 계약
├── principles.md       # 불변 원칙
├── analyzer.md          # Rule Interface, Engine 동작
├── rules.md             # Rule 카탈로그, 추가 절차
├── ui.md                # UI 철학, 레이아웃, 색상 규칙
└── roadmap.md            # 버전별 개발 계획

CLAUDE.md                # 이 프로젝트에서 AI가 따르는 작업 규칙
```

## 기여

새 기능을 만들기 전에 [docs/architecture.md](docs/architecture.md)를 위반하지 않는지 먼저 확인하세요. 새 Rule을 추가하는 절차는 [docs/rules.md](docs/rules.md)의 "Rule 추가 절차"를 참고하세요 — Rule 파일 추가, 테스트 작성, Registry 등록, 문서 업데이트 순서입니다. UI는 Tailwind, shadcn/ui, React Aria만 사용하며 Business Logic은 Component 내부에 두지 않습니다.
