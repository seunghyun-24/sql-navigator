# Vision

SQL은 문자열이 아니다.

이 프로젝트는 SQL을 실행하기 위한 도구가 아니라,
**SQL을 이해하기 위한 도구**를 만든다.

## 문제 인식

기존 SQL 도구들은 Execution Plan 중심이다.
Explain Plan은 DB가 어떻게 실행할지를 보여주지만,
사람이 SQL의 **구조와 위험**을 이해하기에는 어렵다.

sqlglot 같은 라이브러리는 Parser, Formatter, Optimizer, AST 조작을 제공하지만
라이브러리일 뿐, 사람을 위한 분석·시각화 도구가 아니다.

## 우리가 만드는 것

**"SQL을 구조적으로 이해하고 품질을 분석하는 도구"**

사용자가 SQL을 입력하면:

- 구조를 이해할 수 있어야 한다 — AST Explorer, Join Graph, Data Flow
- 위험 요소를 발견할 수 있어야 한다 — WHERE 누락, Cartesian Product, Full Scan 가능성
- 사람이 설명받는 것처럼 시각화되어야 한다 — 노드 그래프 기반 Query Flow

## 포지셔닝

| 구분 | 기존 도구 | SQL Navigator |
|------|----------|---------------|
| 중심 | Execution Plan (DB 관점) | Query 구조 (사람 관점) |
| 시점 | 실행 후 | 실행 전 (리뷰/검토 단계) |
| 대상 | DBA, 튜닝 전문가 | SQL을 작성·리뷰하는 모든 개발자 |
| 역할 | 성능 진단 | 구조 이해 + 위험 사전 발견 |

우리는 SQL IDE를 만드는 것이 아니다.
우리는 DB에 연결하는 도구를 만드는 것이 아니다.

**우리는 SQL Analyzer를 만든다.**

코드 리뷰와 실제 검토 단계에서 쓰이는 **보조 도구**다.
Explain Plan을 대체하지 않고, 그 이전 단계를 채운다.
