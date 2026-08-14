"""Join Graph 데이터 계약 테스트 (Rule이 아니므로 탐지/비탐지 대신 구조 검증)."""

import json

import sqlglot

from config import DIALECT
from join_graph import build_join_graph


def build(sql: str) -> dict:
    ast = sqlglot.parse_one(sql, read=DIALECT)
    graph = build_join_graph(ast)
    json.dumps(graph)  # 직렬화 가능
    return graph


def test_simple_join():
    g = build("SELECT * FROM orders o JOIN customers c ON o.customer_id = c.id")
    ids = {n["id"] for n in g["nodes"]}
    assert ids == {"o", "c"}
    assert len(g["edges"]) == 1
    e = g["edges"][0]
    assert {e["source"], e["target"]} == {"o", "c"}
    assert e["cartesian"] is False
    assert "customer_id" in e["condition"]


def test_alias_and_table_recorded():
    g = build("SELECT * FROM orders o JOIN customers c ON o.customer_id = c.id")
    by_id = {n["id"]: n for n in g["nodes"]}
    assert by_id["o"]["table"] == "orders"
    assert by_id["c"]["alias"] == "c"
    assert by_id["c"]["kind"] == "table"


def test_cartesian_edge_flagged():
    g = build("SELECT * FROM a JOIN b")
    assert len(g["edges"]) == 1
    assert g["edges"][0]["cartesian"] is True


def test_left_join_type():
    g = build("SELECT * FROM a LEFT JOIN b ON a.id = b.a_id")
    assert "LEFT" in g["edges"][0]["joinType"]


def test_three_table_chain():
    g = build(
        "SELECT * FROM orders o "
        "JOIN customers c ON o.customer_id = c.id "
        "JOIN products p ON o.product_id = p.id"
    )
    assert len(g["nodes"]) == 3
    assert len(g["edges"]) == 2
    # ON 조건 qualifier 기반으로 둘 다 o에 연결되어야 한다
    sources = {e["source"] for e in g["edges"]}
    assert sources == {"o"}


def test_using_join():
    g = build("SELECT * FROM orders JOIN customers USING (customer_id)")
    assert len(g["edges"]) == 1
    e = g["edges"][0]
    assert e["cartesian"] is False
    assert "USING" in e["condition"]


def test_cte_node_kind():
    g = build(
        "WITH recent AS (SELECT * FROM orders WHERE created_at > '2026-01-01') "
        "SELECT * FROM recent r JOIN customers c ON r.customer_id = c.id"
    )
    by_id = {n["id"]: n for n in g["nodes"]}
    assert by_id["r"]["kind"] == "cte"


def test_no_join_no_edges():
    g = build("SELECT * FROM orders WHERE id = 1")
    assert g["edges"] == []
    assert len(g["nodes"]) == 1


def test_explicit_cross_join_is_cartesian():
    g = build("SELECT * FROM a CROSS JOIN b")
    assert len(g["edges"]) == 1
    e = g["edges"][0]
    assert e["cartesian"] is True
    assert "CROSS" in e["joinType"]


def test_self_join_two_nodes_not_cartesian():
    """alias가 다른 self-join은 별도 노드 2개, cartesian 아님 (false positive 방지)."""
    g = build("SELECT * FROM emp e JOIN emp m ON e.manager_id = m.id")
    assert {n["id"] for n in g["nodes"]} == {"e", "m"}
    assert len(g["edges"]) == 1
    assert g["edges"][0]["cartesian"] is False


def test_subquery_node_kind():
    g = build(
        "SELECT * FROM (SELECT id FROM orders) sub "
        "JOIN customers c ON sub.id = c.order_id"
    )
    by_id = {n["id"]: n for n in g["nodes"]}
    assert by_id["sub"]["kind"] == "subquery"
    assert any({e["source"], e["target"]} == {"sub", "c"} for e in g["edges"])


def test_natural_join_not_cartesian():
    g = build("SELECT * FROM a NATURAL JOIN b")
    assert len(g["edges"]) == 1
    e = g["edges"][0]
    assert e["cartesian"] is False
    assert e["condition"] == "NATURAL"


def test_analyze_contract_includes_join_graph():
    """진입점 계약: AnalysisResult에 joinGraph 포함, 전체 JSON 직렬화 가능."""
    from main import analyze

    r = json.loads(analyze("SELECT * FROM a JOIN b ON a.id = b.a_id"))
    assert r["ok"] is True
    g = r["joinGraph"]
    assert {n["id"] for n in g["nodes"]} == {"a", "b"}
    assert len(g["edges"]) == 1


def test_builder_does_not_mutate_ast():
    """Immutable (docs/principles.md): 그래프 생성이 AST를 바꾸면 안 된다."""
    ast = sqlglot.parse_one("SELECT * FROM a JOIN b ON a.id = b.a_id", read=DIALECT)
    before = ast.sql(dialect=DIALECT)
    build_join_graph(ast)
    assert ast.sql(dialect=DIALECT) == before
