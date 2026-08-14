# CLAUDE.md

## 항상 먼저 읽을 것

- docs/vision.md — 무엇을 만드는가
- docs/architecture.md — Layer 구조와 데이터 계약
- docs/principles.md — 불변 원칙

기능 관련 작업 시 추가로:

- docs/analyzer.md — Rule Interface, Engine
- docs/rules.md — Rule 카탈로그, 추가 절차
- docs/ui.md — UI 규칙
- docs/roadmap.md — 버전별 범위

## 절대 규칙

- 새 기능을 만들기 전에 현재 Architecture를 위반하지 않는지 확인한다
- Regex(및 문자열 검색)로 SQL을 분석하지 않는다 — 항상 AST
- 새 Rule은 Analyzer Rule Interface(docs/analyzer.md)를 구현해야 한다
- Analyzer는 AST를 수정하면 안 된다 — 변환이 필요하면 새 AST를 생성한다
- Analyzer는 순수 함수 (stateless, DB 연결·외부 I/O 금지)
- SQL은 브라우저를 떠나지 않는다 — 서버 전송 금지

## 테스트

- 테스트는 Rule 단위로 작성한다
- 각 Rule: 탐지 케이스 + 비탐지(false positive 방지) 케이스 + Explainability(이유/예시/수정) 검증

## UI

- Tailwind, shadcn/ui, React Aria만 사용한다
- Business Logic은 React Component 내부에 작성하지 않는다
- 색상 의미: Blue=정보, Yellow=주의, Red=위험, Green=추천 (docs/ui.md)

## 스택

- Parser/Analyzer: Python (sqlglot), Pyodide로 브라우저 실행
- 우선 dialect: PostgreSQL
- Pyodide↔JS 경계는 직렬화 가능한 JSON만 통과
