# Principles

## AST First

모든 기능은 AST 기반으로 구현한다.

절대로 Regex로 SQL을 분석하지 않는다.
문자열 검색(`sql.includes("WHERE")` 등)도 금지다. 같은 이유다.

## Immutable

Analyzer는 AST를 변경하지 않는다.

Refactoring Suggestion처럼 변환이 필요한 기능도
원본 AST를 복사해 **새 AST를 생성**한다. 원본은 항상 보존된다.

## Stateless

Analyzer는 순수 함수여야 한다.

같은 AST 입력 → 항상 같은 AnalysisResult 출력.
전역 상태, 캐시, 외부 I/O에 의존하지 않는다.

## Rule Driven

분석은 Rule 기반으로 수행한다.

Analyzer 내부에 if문을 나열하지 않는다.
Rule 객체를 등록하는 방식으로 확장한다.
새 검사를 추가한다 = 새 Rule 파일을 추가한다. Engine은 건드리지 않는다.

## Explainability

모든 Warning은 다음을 포함해야 한다:

- **이유** — 왜 위험한가
- **예시** — 어떤 쿼리가 문제인가 (before)
- **수정 방법** — 어떻게 고치는가 (after)

"위험합니다"로 끝나는 Warning은 금지다. 사람이 배울 수 있어야 한다.

## Static Only

DB에 연결하지 않는다. 실행하지 않는다.

통계 정보 없이 AST만으로 판단할 수 있는 것만 말하고,
확신할 수 없는 것은 "가능성"으로 표현한다.
(예: "Full Scan 가능성" — 단정이 아니라 주의 환기)

## Local First

SQL은 사용자의 브라우저를 떠나지 않는다.
서버 전송, 외부 API 호출 금지.
