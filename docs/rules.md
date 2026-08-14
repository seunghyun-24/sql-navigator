# Rules

초기 Rule 카탈로그. 모든 Rule은 analyzer.md의 Rule Interface를 구현한다.
severity: INFO(파랑) < WARNING(노랑) < CRITICAL(빨강) — 색상 의미는 ui.md와 일치.

## v0.2 대상 Rule

### cartesian-product — CRITICAL

- 탐지: JOIN 조건이 없는 다중 테이블 (`FROM a, b` 또는 `CROSS JOIN`, ON 절 누락)
- 이유: 두 테이블 행 수의 곱만큼 결과가 폭발한다
- 예시: `SELECT * FROM orders, customers`
- 수정: `SELECT * FROM orders o JOIN customers c ON o.customer_id = c.id`
- 주의: 의도적 `CROSS JOIN` 명시는 WARNING으로 낮춘다

### delete-without-where — CRITICAL

- 탐지: WHERE 없는 DELETE 문
- 이유: 테이블 전체 삭제
- 예시: `DELETE FROM users`
- 수정: `DELETE FROM users WHERE id = :id`

### update-without-where — CRITICAL

- 탐지: WHERE 없는 UPDATE 문
- 이유: 테이블 전체 갱신
- 예시: `UPDATE users SET status = 'inactive'`
- 수정: `UPDATE users SET status = 'inactive' WHERE last_login < :cutoff`

### select-without-where — WARNING

- 탐지: WHERE 없는 SELECT (LIMIT도 없을 때)
- 이유: Full Scan 가능성, 대량 데이터 전송
- 주의: 집계 전용 쿼리(`SELECT count(*)`), 소형 코드 테이블 조회 등 정상 케이스가 많으므로 WARNING 이상으로 올리지 않는다

### pk-not-used — INFO / WARNING

- 탐지: WHERE/JOIN 조건에 PK·index 컬럼이 없는 경우
- 이유: index를 타지 못하면 Full Scan으로 느려질 수 있다
- 전제: schema context 필요 (analyzer.md). 스키마 없으면 skip
- 스키마 있으면 WARNING, 부분 정보만 있으면 INFO

### or-abuse — WARNING

- 탐지: 같은 컬럼에 대한 OR 조건 N개 이상 (기본 N=3)
- 이유: index 활용을 방해하고 가독성을 해친다
- 예시: `WHERE status = 'A' OR status = 'B' OR status = 'C'`
- 수정: `WHERE status IN ('A', 'B', 'C')`

### duplicate-join — WARNING

- 탐지: 같은 테이블을 같은 조건으로 2회 이상 JOIN (alias만 다르고 ON 절 동일)
- 이유: 불필요한 중복 작업, 대개 복붙 실수
- 주의: self-join(조건이 다른 동일 테이블 JOIN)은 정상 — 탐지 제외

### function-on-indexed-column — WARNING

- 탐지: WHERE 조건의 컬럼에 함수 적용 (`WHERE upper(name) = ...`, `WHERE date(created_at) = ...`)
- 이유: 일반 index를 무효화한다 (non-sargable)
- 수정: 리터럴 쪽을 변환하거나 expression index 고려

### implicit-conversion — INFO

- 탐지: 컬럼 타입과 비교 리터럴 타입 불일치 (schema context 필요)
- 이유: 암묵적 형변환은 index를 무효화할 수 있다
- 예시: `WHERE user_id = '123'` (user_id가 integer일 때)

### select-star — INFO

- 탐지: `SELECT *`
- 이유: 불필요한 컬럼 전송, 스키마 변경에 취약
- 주의: 개발 편의상 흔하므로 INFO 유지

## v0.6 대상 Rule

### null-comparison — CRITICAL

- 탐지: `= NULL`, `!= NULL`, `<> NULL` 비교
- 이유: NULL 비교는 항상 unknown — 조건이 조용히 항상 거짓이 되어 결과가 틀린다
- 예시: `SELECT * FROM users WHERE deleted_at = NULL`
- 수정: `SELECT * FROM users WHERE deleted_at IS NULL`
- fixSql 가능 (v0.9): `= NULL` → `IS NULL` 기계적 치환

### not-in-with-null — WARNING

- 탐지: `NOT IN (서브쿼리)` 패턴
- 이유: 서브쿼리 결과에 NULL이 하나라도 있으면 전체 결과가 빈다
- 예시: `SELECT * FROM users WHERE id NOT IN (SELECT user_id FROM banned)`
- 수정: `SELECT * FROM users u WHERE NOT EXISTS (SELECT 1 FROM banned b WHERE b.user_id = u.id)`
- 주의: 리터럴 목록 `NOT IN ('A','B')`는 안전 — 탐지 제외

### leading-wildcard-like — WARNING

- 탐지: `LIKE '%...'` / `ILIKE '%...'` (선행 와일드카드)
- 이유: 일반 B-tree index를 사용할 수 없어 Full Scan 가능성
- 예시: `SELECT * FROM users WHERE email LIKE '%@gmail.com'`
- 수정: 후행 와일드카드로 재구성하거나 pg_trgm 등 전용 index 고려
- 주의: `LIKE 'foo%'`(후행만)는 정상 — 탐지 제외

### scalar-subquery-in-select — WARNING

- 탐지: SELECT 절의 상관 스칼라 서브쿼리
- 이유: 외부 쿼리 행마다 서브쿼리가 실행될 수 있다 (N+1 유사)
- 예시: `SELECT o.id, (SELECT name FROM customers c WHERE c.id = o.customer_id) FROM orders o`
- 수정: `SELECT o.id, c.name FROM orders o JOIN customers c ON c.id = o.customer_id`

### union-vs-union-all — INFO

- 탐지: `UNION` 사용 (UNION ALL 아님)
- 이유: UNION은 중복 제거를 위해 정렬/해시 비용이 든다. 중복이 없거나 무관하면 낭비
- 예시: `SELECT id FROM a UNION SELECT id FROM b`
- 수정: 중복 제거가 불필요하면 `UNION ALL`
- 주의: 의도적 중복 제거일 수 있으므로 INFO 유지

### offset-pagination — INFO

- 탐지: 큰 OFFSET 값 (기본 임계값 1000 이상)
- 이유: OFFSET 앞의 행을 모두 읽고 버린다 — 페이지가 깊을수록 느려진다
- 예시: `SELECT * FROM orders ORDER BY id LIMIT 20 OFFSET 100000`
- 수정: keyset pagination — `WHERE id > :last_id ORDER BY id LIMIT 20`

### distinct-as-bandaid — INFO

- 탐지: JOIN이 있는 쿼리의 `SELECT DISTINCT`
- 이유: JOIN으로 늘어난 중복 행을 DISTINCT로 덮는 패턴일 수 있다 — 원인(JOIN 조건)을 숨긴다
- 예시: `SELECT DISTINCT o.id FROM orders o JOIN order_items i ON i.order_id = o.id`
- 수정: JOIN 조건을 점검하거나 `EXISTS`로 재작성
- 주의: 단일 테이블 DISTINCT는 정상 — 탐지 제외

### join-type-mismatch — WARNING

- 탐지: JOIN 키 양쪽 컬럼의 타입 불일치 (schema context 필요)
- 이유: 암묵적 형변환으로 index가 무효화될 수 있다
- 예시: `JOIN logs l ON l.user_id = u.id` (l.user_id가 varchar, u.id가 integer)
- 수정: 컬럼 타입을 맞추거나 명시적 캐스팅 위치를 index 쪽 반대로 이동
- 전제: 스키마 없으면 skip (pk-not-used와 동일 정책)

## Complexity Score (Rule 아님, Metrics)

```
score = joinCount * 2
      + subqueryDepth * 3
      + cteCount * 1
      + tableCount * 1
```

- 0–5: 단순 / 6–15: 보통 / 16+: 복잡 (리뷰 권장)
- 산식은 초기값이며 사용 데이터에 따라 조정한다

## Rule 추가 절차

1. `rules/` 에 Rule 구현체 파일 추가 (Rule Interface 구현)
2. Rule 단위 테스트 작성 (탐지/비탐지/Explainability 3종 — analyzer.md)
3. Registry에 등록
4. 이 문서에 항목 추가 (탐지·이유·예시·수정 필수)

Engine, Parser, 다른 Rule은 건드리지 않는다.
