from rules.distinct_as_bandaid import DistinctAsBandaidRule
from tests.util import assert_explainable, run_rule

rule = DistinctAsBandaidRule()


def test_detects_distinct_with_join():
    sql = (
        "SELECT DISTINCT o.id FROM orders o "
        "JOIN order_items i ON i.order_id = o.id"
    )
    findings = run_rule(rule, sql)
    assert len(findings) == 1
    assert findings[0].severity == "INFO"
    assert "EXISTS" in findings[0].fix
    assert_explainable(findings)


def test_no_finding_distinct_single_table():
    assert run_rule(rule, "SELECT DISTINCT status FROM orders") == []


def test_no_finding_join_without_distinct():
    sql = "SELECT o.id FROM orders o JOIN order_items i ON i.order_id = o.id"
    assert run_rule(rule, sql) == []


def test_no_finding_distinct_on():
    # DISTINCT ON (...)은 의도적 사용 — 탐지 제외
    sql = (
        "SELECT DISTINCT ON (o.id) o.id, i.name FROM orders o "
        "JOIN order_items i ON i.order_id = o.id"
    )
    assert run_rule(rule, sql) == []
