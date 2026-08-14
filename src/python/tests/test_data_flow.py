"""Data Flow 데이터 계약 테스트 (docs/roadmap.md v0.4).

- 논리 순서 재구성 (FROM -> JOIN -> WHERE -> GROUP BY -> SELECT -> ...)
- 컬럼 lineage (alias 해석)
- 만들면 안 되는 것 (false positive 방지) + 직렬화 + AST 불변성
"""

import json

import sqlglot

from config import DIALECT
from data_flow import build_data_flow


def build(sql: str) -> dict:
    ast = sqlglot.parse_one(sql, read=DIALECT)
    flow = build_data_flow(ast)
    json.dumps(flow)  # 직렬화 가능
    return flow


def kinds_in_scope(flow: dict, scope: str = "main") -> list:
    return [s["kind"] for s in flow["steps"] if s["scope"] == scope]


def step_by_kind(flow: dict, kind: str, scope: str = "main") -> dict:
    matches = [s for s in flow["steps"] if s["kind"] == kind and s["scope"] == scope]
    assert matches, f"{scope}에 {kind} step 없음: {flow['steps']}"
    return matches[0]


def test_logical_order_full_pipeline():
    flow = build(
        "SELECT o.id, count(*) AS cnt FROM orders o "
        "JOIN customers c ON o.customer_id = c.id "
        "WHERE o.amount > 0 GROUP BY o.id HAVING count(*) > 1 "
        "ORDER BY cnt DESC LIMIT 10"
    )
    ks = kinds_in_scope(flow)
    # source 2개(orders, customers) + 논리 순서 파이프라인
    assert ks.count("source") == 2
    pipeline = [k for k in ks if k != "source"]
    assert pipeline == ["join", "where", "group", "having", "select", "order", "limit"]


def test_no_optional_clauses_no_steps():
    flow = build("SELECT id FROM users")
    ks = kinds_in_scope(flow)
    assert ks == ["source", "select"]  # where/group/order/limit 없음


def test_join_step_has_condition_detail():
    flow = build("SELECT * FROM a JOIN b ON a.id = b.a_id")
    j = step_by_kind(flow, "join")
    assert "a.id = b.a_id" in j["detail"]
    assert j["cartesian"] is False


def test_cartesian_join_flagged():
    flow = build("SELECT * FROM a CROSS JOIN b")
    assert step_by_kind(flow, "join")["cartesian"] is True


def test_join_step_receives_two_inputs():
    flow = build("SELECT * FROM a JOIN b ON a.id = b.a_id")
    j = step_by_kind(flow, "join")
    incoming = [e for e in flow["edges"] if e["target"] == j["id"]]
    assert len(incoming) == 2  # 이전 체인 + 조인 대상 relation


def test_cte_flow_feeds_main_source():
    flow = build(
        "WITH recent AS (SELECT id FROM orders WHERE created_at > '2026-01-01') "
        "SELECT * FROM recent r"
    )
    cte_kinds = kinds_in_scope(flow, "cte:recent")
    assert cte_kinds == ["source", "where", "select"]
    # CTE의 마지막 step -> main의 FROM recent source로 엣지
    cte_final = [s for s in flow["steps"] if s["scope"] == "cte:recent"][-1]
    main_src = step_by_kind(flow, "source")
    assert main_src["detail"] == "CTE"
    assert {"source": cte_final["id"], "target": main_src["id"]} in flow["edges"]


def test_subquery_flow_feeds_derived_source():
    flow = build("SELECT * FROM (SELECT id FROM orders) sub")
    sub_kinds = kinds_in_scope(flow, "sub:sub")
    assert sub_kinds == ["source", "select"]
    sub_final = [s for s in flow["steps"] if s["scope"] == "sub:sub"][-1]
    main_src = step_by_kind(flow, "source")
    assert {"source": sub_final["id"], "target": main_src["id"]} in flow["edges"]


def test_lineage_alias_resolution():
    flow = build(
        "SELECT o.id, c.name AS customer_name FROM orders o "
        "JOIN customers c ON o.customer_id = c.id"
    )
    by_output = {l["output"]: l for l in flow["lineage"]}
    assert by_output["id"]["sources"] == ["orders.id"]
    assert by_output["customer_name"]["sources"] == ["customers.name"]


def test_lineage_unqualified_single_table_resolved():
    flow = build("SELECT id, name FROM users")
    by_output = {l["output"]: l for l in flow["lineage"]}
    assert by_output["id"]["sources"] == ["users.id"]


def test_lineage_unqualified_multi_table_not_asserted():
    """relation이 여럿이고 qualifier가 없으면 단정하지 않는다 (Static Only)."""
    flow = build("SELECT id FROM a JOIN b ON a.x = b.y")
    assert flow["lineage"][0]["sources"] == ["?.id"]


def test_lineage_star_and_literal():
    flow = build("SELECT *, 1 AS one FROM orders o")
    by_output = {l["output"]: l for l in flow["lineage"]}
    assert by_output["*"]["sources"] == ["orders.*"]
    assert by_output["one"]["sources"] == []


def test_lineage_expression_collects_all_columns():
    flow = build("SELECT o.amount * c.rate AS total FROM orders o JOIN currencies c ON o.cur = c.id")
    total = {l["output"]: l for l in flow["lineage"]}["total"]
    assert set(total["sources"]) == {"orders.amount", "currencies.rate"}


def test_non_select_root_returns_empty_flow():
    flow = build("DELETE FROM users WHERE id = 1")
    assert flow == {"steps": [], "edges": [], "lineage": []}


def test_analyze_contract_includes_data_flow():
    from main import analyze

    r = json.loads(analyze("SELECT id FROM users WHERE id = 1"))
    assert r["ok"] is True
    assert kinds_in_scope(r["dataFlow"]) == ["source", "where", "select"]


def test_builder_does_not_mutate_ast():
    ast = sqlglot.parse_one(
        "WITH x AS (SELECT 1 AS a) SELECT a FROM x ORDER BY a LIMIT 1", read=DIALECT
    )
    before = ast.sql(dialect=DIALECT)
    build_data_flow(ast)
    assert ast.sql(dialect=DIALECT) == before
