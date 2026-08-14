# Roadmap

## v0.1 — 기반

- Pyodide + sqlglot 로딩 파이프라인 (Bridge Layer)
- SQL Editor (입력) + Parse Error 표시
- Formatter (sqlglot 위임)
- AST Explorer (구조 트리 시각화)
- 목표: SQL 입력 → 포맷팅 + 구조 트리가 보인다

## v0.2 — Warnings

- Analysis Engine + Rule Registry (analyzer.md)
- 초기 Rule 셋 (rules.md): cartesian-product, delete/update-without-where,
  select-without-where, or-abuse, duplicate-join, select-star
- Warning 패널 (Explainability: 이유/예시/수정)
- Warning ↔ 에디터 위치 하이라이트 연동
- 목표: 위험 쿼리가 리뷰 가능한 수준으로 잡힌다

## v0.3 — Join Graph

- 테이블 관계 노드 그래프
- JOIN 조건 표시, Cartesian Product 시각적 강조
- Complexity Score 표시
- 목표: 테이블 관계가 한눈에 보인다

## v0.4 — Query Flow / Data Flow

- 쿼리 실행 흐름의 논리적 재구성 (FROM → JOIN → WHERE → GROUP BY → SELECT)
- 노드 그래프 형태 — "사람이 이해하기 쉬운 Explain Plan"
- 컬럼 lineage (어떤 컬럼이 어디서 와서 어디로 가는가)
- 목표: Explain Plan 없이 쿼리 동작을 설명할 수 있다

## v0.5 — Schema Context & 고급 분석

- 스키마 입력 (DDL 붙여넣기 → PK/index 정보 추출)
- pk-not-used, implicit-conversion 등 스키마 기반 Rule 활성화
- Refactoring Suggestion (읽기 좋은 SQL 재작성 — 새 AST 생성)
- 목표: "가능성" 경고가 "근거 있는" 경고가 된다

## v0.6 — Rule 확장

- 신규 Rule 추가 (rules.md v0.6 섹션): null-comparison, not-in-with-null,
  leading-wildcard-like, scalar-subquery-in-select, union-vs-union-all,
  offset-pagination, distinct-as-bandaid, join-type-mismatch(schema 필요)
- Engine/Parser 수정 없음 — Rule 파일 추가 + Registry 등록만 (analyzer.md 절차)
- 목표: 실무 안티패턴 커버리지가 2배가 된다

## v0.7 — Location Mapping

- Position Mapper 도입: tokenizer 토큰 위치 기반 AST 노드 → (line, col) 매핑
  (analyzer.md "Position Mapper")
- Finding.location 채움 — v0.2의 `null + snippet` 임시 방식 졸업
- Warning 클릭 → 에디터 해당 위치 하이라이트 완성 (ui.md)
- 목표: 모든 Warning이 에디터의 정확한 위치를 가리킨다

## v0.8 — SQL Diff

- 두 SQL의 AST 수준 비교 (sqlglot diff 활용, 문자열 diff 금지)
- Warning 수 / Complexity Score의 before-after 비교
- Right 패널에 Diff 탭 추가 (ui.md)
- 목표: 리팩토링 전후가 "같은 의미인지 + 얼마나 나아졌는지" 보인다

## v0.9 — Fix Apply

- Rule이 Finding에 fixSql 첨부 — 원본 AST 복사 → 새 AST 생성 → SQL 출력
  (Immutable 원칙 유지, analyzer.md "Fix Apply")
- Warning 패널에서 Finding 단위 개별 Apply 버튼 (Green) — 에디터 내용 교체
- Apply 후 자동 재분석 → 해당 Warning 해소 확인
- 목표: 툴이 "지적"에서 "수정"까지 완결한다

## 이후 (미확정)

- Cost 추정 (정적 휴리스틱, DB 미연결 원칙 유지)
- 다른 dialect (Oracle, MySQL) — sqlglot dialect 옵션 확장
- 리뷰 코멘트 export (Warning → Markdown)
- Rule 설정 공유 (Rule on/off, severity 조정, 임계값 — 팀 컨벤션 JSON)
- CI/CLI 모드 (Analyzer는 순수 Python이므로 브라우저 밖 실행 가능)
