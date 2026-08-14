# 기능별 테스트 예제 쿼리

로드맵 v0.3~v0.9 기능을 수동 검증하기 위한 길고 복잡한 예제 모음.
모든 SQL은 PostgreSQL dialect 기준으로 작성했다.
파싱 검증: `python examples/validate_examples.py` (sqlglot 필요).

---

## 1. 복잡한 쿼리 — Join Graph / Query Flow / Complexity Score (v0.3, v0.4)

CTE 3개, 윈도우 함수, 상관 스칼라 서브쿼리, EXISTS, JOIN 5개.
Join Graph 노드/간선, 컬럼 lineage, Complexity Score "복잡(16+)" 구간을 확인한다.

```sql
WITH monthly_sales AS (
    SELECT
        o.customer_id,
        date_trunc('month', o.ordered_at) AS sales_month,
        sum(oi.quantity * oi.unit_price) AS month_total,
        count(DISTINCT o.id) AS order_count
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.id
    WHERE o.status NOT IN ('cancelled', 'refunded')
      AND o.ordered_at >= DATE '2025-01-01'
    GROUP BY o.customer_id, date_trunc('month', o.ordered_at)
),
customer_rank AS (
    SELECT
        ms.customer_id,
        ms.sales_month,
        ms.month_total,
        rank() OVER (PARTITION BY ms.sales_month ORDER BY ms.month_total DESC) AS month_rank,
        lag(ms.month_total) OVER (PARTITION BY ms.customer_id ORDER BY ms.sales_month) AS prev_month_total
    FROM monthly_sales ms
),
vip_customers AS (
    SELECT customer_id
    FROM customer_rank
    WHERE month_rank <= 100
    GROUP BY customer_id
    HAVING count(*) >= 3
)
SELECT
    c.id,
    c.name,
    c.tier,
    r.name AS region_name,
    cr.sales_month,
    cr.month_total,
    cr.month_total - coalesce(cr.prev_month_total, 0) AS month_over_month,
    (
        SELECT max(o2.ordered_at)
        FROM orders o2
        WHERE o2.customer_id = c.id
    ) AS last_order_at,
    CASE
        WHEN cr.month_rank <= 10 THEN 'platinum'
        WHEN cr.month_rank <= 50 THEN 'gold'
        ELSE 'silver'
    END AS month_grade
FROM customers c
JOIN customer_rank cr ON cr.customer_id = c.id
JOIN vip_customers v ON v.customer_id = c.id
LEFT JOIN regions r ON r.id = c.region_id
LEFT JOIN customer_notes n ON n.customer_id = c.id AND n.pinned = TRUE
WHERE c.deleted_at IS NULL
  AND EXISTS (
      SELECT 1
      FROM payments p
      WHERE p.customer_id = c.id
        AND p.method = 'card'
  )
ORDER BY cr.sales_month DESC, cr.month_total DESC
LIMIT 500;
```

기대 결과:

- Join Graph: customers를 중심으로 CTE 2개 + regions + customer_notes 간선, Cartesian 강조 없음
- Data Flow: `month_total` lineage가 order_items.quantity/unit_price → monthly_sales → customer_rank → 최종 SELECT로 추적
- Warnings: `scalar-subquery-in-select` 1건(last_order_at)만 — 그 외 Rule은 비탐지여야 함
- Complexity Score: "복잡(16+)" 구간

---

## 2. Schema Context 기반 Rule (v0.5, v0.6 join-type-mismatch)

### 2-1. 스키마 입력용 DDL

```sql
CREATE TABLE users (
    id integer PRIMARY KEY,
    email varchar(255) NOT NULL,
    name varchar(100),
    status varchar(20) NOT NULL DEFAULT 'active',
    created_at timestamp NOT NULL,
    deleted_at timestamp
);

CREATE INDEX idx_users_email ON users (email);

CREATE TABLE orders (
    id bigint PRIMARY KEY,
    customer_id integer NOT NULL REFERENCES users (id),
    status varchar(20) NOT NULL,
    total_amount numeric(12, 2) NOT NULL,
    ordered_at timestamp NOT NULL
);

CREATE INDEX idx_orders_customer ON orders (customer_id);
CREATE INDEX idx_orders_ordered_at ON orders (ordered_at);

CREATE TABLE access_logs (
    id bigint PRIMARY KEY,
    user_id varchar(20) NOT NULL, -- 의도적 타입 불일치: users.id는 integer
    path text,
    logged_at timestamp NOT NULL
);

CREATE TABLE banned_users (
    id integer PRIMARY KEY,
    user_id integer, -- 의도적으로 nullable: not-in-with-null 검증용
    banned_at timestamp NOT NULL
);
```

### 2-2. 탐지 케이스 — 스키마 있을 때 세 Rule이 모두 발화

```sql
SELECT
    u.name,
    u.status,
    l.path,
    l.logged_at
FROM users u
JOIN access_logs l ON l.user_id = u.id
WHERE u.status = 'active'
  AND u.created_at > '2026-01-01'
  AND l.user_id = 123
ORDER BY l.logged_at DESC;
```

기대 결과:

- `join-type-mismatch` WARNING: `l.user_id`(varchar) = `u.id`(integer)
- `implicit-conversion` INFO: `l.user_id = 123` (varchar 컬럼 vs integer 리터럴)
- `pk-not-used` WARNING: WHERE에 users의 PK/index 컬럼 없음 (status·created_at 모두 비인덱스)
- 스키마 미입력 상태에서 같은 쿼리 실행 시: 세 Rule 모두 skip(또는 INFO)되는지도 확인

### 2-3. 비탐지 케이스 — 스키마가 있어도 조용해야 함

```sql
SELECT
    u.id,
    u.email,
    o.total_amount
FROM users u
JOIN orders o ON o.customer_id = u.id
WHERE u.email = 'a@b.com'
  AND o.ordered_at >= TIMESTAMP '2026-07-01 00:00:00'
LIMIT 100;
```

JOIN 키 양쪽 integer, WHERE는 index 컬럼(email, ordered_at), 타입 일치 — Finding 0건이어야 한다.

---

## 3. v0.6 Rule 종합 + Location Mapping (v0.6, v0.7)

### 3-1. 탐지 케이스 — 한 쿼리에서 8개 Rule 동시 발화

Warning이 여러 줄에 흩어져 있어 Warning 클릭 → 에디터 위치 하이라이트(v0.7) 검증에도 사용한다.

```sql
SELECT DISTINCT
    u.id,
    u.email,
    (
        SELECT count(*)
        FROM orders o
        WHERE o.customer_id = u.id
    ) AS lifetime_orders
FROM users u
JOIN orders recent ON recent.customer_id = u.id
WHERE u.deleted_at = NULL
  AND u.email LIKE '%@gmail.com'
  AND (u.status = 'active' OR u.status = 'trial' OR u.status = 'pending' OR u.status = 'invited')
  AND u.id NOT IN (
      SELECT user_id
      FROM banned_users
  )
UNION
SELECT
    u2.id,
    u2.email,
    0 AS lifetime_orders
FROM users u2
LEFT JOIN orders o3 ON o3.customer_id = u2.id
WHERE o3.id IS NULL
ORDER BY id
LIMIT 20 OFFSET 100000;
```

기대 Finding 8건:

- `null-comparison` CRITICAL — `u.deleted_at = NULL`
- `not-in-with-null` WARNING — `NOT IN (SELECT user_id FROM banned_users)` (user_id nullable)
- `leading-wildcard-like` WARNING — `LIKE '%@gmail.com'`
- `or-abuse` WARNING — status OR 4개
- `scalar-subquery-in-select` WARNING — lifetime_orders 상관 서브쿼리
- `distinct-as-bandaid` INFO — JOIN + SELECT DISTINCT
- `union-vs-union-all` INFO — UNION
- `offset-pagination` INFO — OFFSET 100000

각 Finding의 location이 정확한 (line, col)을 가리키는지, reason/example/fix가 채워졌는지 확인.

### 3-2. 비탐지 케이스 — 같은 구조의 안전한 쿼리 (false positive 방지)

```sql
SELECT
    u.id,
    u.email,
    count(o.id) AS lifetime_orders
FROM users u
LEFT JOIN orders o ON o.customer_id = u.id
WHERE u.deleted_at IS NULL
  AND u.email LIKE 'admin%'
  AND u.status IN ('active', 'trial', 'pending', 'invited')
  AND NOT EXISTS (
      SELECT 1
      FROM banned_users b
      WHERE b.user_id = u.id
  )
GROUP BY u.id, u.email
UNION ALL
SELECT
    u2.id,
    u2.email,
    0 AS lifetime_orders
FROM users u2
WHERE u2.id > 8400000
ORDER BY id
LIMIT 20;
```

`IS NULL`, 후행 와일드카드, `IN` 목록, `NOT EXISTS`, `UNION ALL`, keyset pagination, DISTINCT 없음 — Finding 0건이어야 한다.

---

## 4. SQL Diff (v0.8)

### 4-1. 리팩토링 전후 — Warning/Complexity 개선 확인

Before (Warning 6건 예상):

```sql
SELECT DISTINCT
    o.id,
    o.total_amount,
    c.name,
    r.name AS region_name
FROM orders o, customers c, regions r
WHERE o.customer_id = c.id
  AND c.deleted_at = NULL
  AND (o.status = 'paid' OR o.status = 'shipped' OR o.status = 'delivered')
  AND o.customer_id NOT IN (
      SELECT customer_id
      FROM blacklist
  )
ORDER BY o.id
LIMIT 20 OFFSET 50000;
```

After:

```sql
SELECT
    o.id,
    o.total_amount,
    c.name,
    r.name AS region_name
FROM orders o
JOIN customers c ON c.id = o.customer_id
LEFT JOIN regions r ON r.id = c.region_id
WHERE c.deleted_at IS NULL
  AND o.status IN ('paid', 'shipped', 'delivered')
  AND NOT EXISTS (
      SELECT 1
      FROM blacklist b
      WHERE b.customer_id = o.customer_id
  )
  AND o.id > 8400000
ORDER BY o.id
LIMIT 20;
```

기대 결과:

- `equivalent = false`, changes에 join/where/distinct 변경이 잡힘
- warningsBefore 6건(`cartesian-product`(regions 조건 없음), `null-comparison`, `or-abuse`, `not-in-with-null`, `distinct-as-bandaid`, `offset-pagination`) → warningsAfter 0건
- `resolvedRules` 6개, `introducedRules` 0개 (Green)
- metricsBefore 대비 metricsAfter의 complexityScore 감소

### 4-2. Formatting-only 차이 — equivalent = true 확인

아래 두 쿼리는 AST가 동일해야 한다 (`equivalent = true`, changeCount 0):

```sql
select id,name from users where status='active' and deleted_at is null order by id limit 10;
```

```sql
SELECT
    id,
    name
FROM users
WHERE status = 'active'
  AND deleted_at IS NULL
ORDER BY id
LIMIT 10;
```

### 4-3. 의미가 바뀐 diff — 미세한 변경 탐지 확인

4-1 After에서 딱 두 곳만 바뀐 쿼리. `equivalent = false`와 changes 2건(JOIN 타입, 비교 연산자)이 잡혀야 한다.

```sql
SELECT
    o.id,
    o.total_amount,
    c.name,
    r.name AS region_name
FROM orders o
LEFT JOIN customers c ON c.id = o.customer_id
LEFT JOIN regions r ON r.id = c.region_id
WHERE c.deleted_at IS NULL
  AND o.status IN ('paid', 'shipped', 'delivered')
  AND NOT EXISTS (
      SELECT 1
      FROM blacklist b
      WHERE b.customer_id = o.customer_id
  )
  AND o.id >= 8400000
ORDER BY o.id
LIMIT 20;
```

---

## 5. Fix Apply (v0.9)

기계적 치환이 안전한 Rule만 fixSql을 제공한다. Apply 후 재분석 시 해당 Warning이 사라지는지 확인.

### 5-1. null-comparison 다발 — Finding별 개별 Apply

```sql
UPDATE subscriptions
SET status = 'expired',
    updated_at = now()
WHERE cancelled_at != NULL
  AND expired_at = NULL
  AND trial_ends_at <> NULL
  AND plan_id IS NOT NULL;
```

기대: `null-comparison` CRITICAL 3건, 각각 fixSql 첨부 (`IS NOT NULL` / `IS NULL` / `IS NOT NULL`).
마지막 조건(`IS NOT NULL`)은 비탐지. 하나씩 Apply할 때마다 해당 Finding만 해소되는지 확인.

### 5-2. or-abuse — OR → IN 치환

```sql
SELECT id, email, status
FROM users
WHERE (status = 'active' OR status = 'trial' OR status = 'pending' OR status = 'invited' OR status = 'migrated')
  AND created_at >= DATE '2026-01-01';
```

기대: fixSql이 `status IN ('active', 'trial', 'pending', 'invited', 'migrated')` 형태로 생성되고,
Apply 후 `or-abuse` 해소 + 다른 조건(created_at)은 보존.

### 5-3. fixSql이 없어야 하는 케이스

```sql
SELECT *
FROM orders, customers;
```

`cartesian-product` CRITICAL이지만 JOIN 조건은 판단이 필요하므로 fixSql = null,
Apply 버튼 없이 example/fix 텍스트만 노출되는지 확인. (`select-star` INFO도 함께 발화)
