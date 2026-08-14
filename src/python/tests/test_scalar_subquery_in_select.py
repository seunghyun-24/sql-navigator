from rules.scalar_subquery_in_select import ScalarSubqueryInSelectRule
from tests.util import assert_explainable, run_rule

rule = ScalarSubqueryInSelectRule()


def test_detects_correlated_scalar_subquery():
    sql = (
        "SELECT o.id, "
        "(SELECT c.name FROM customers c WHERE c.id = o.customer_id) "
        "FROM orders o"
    )
    findings = run_rule(rule, sql)
    assert len(findings) == 1
    assert "JOIN" in findings[0].fix
    assert_explainable(findings)


def test_detects_aliased_correlated_subquery():
    sql = (
        "SELECT o.id, "
        "(SELECT c.name FROM customers c WHERE c.id = o.customer_id) AS customer_name "
        "FROM orders o"
    )
    assert len(run_rule(rule, sql)) == 1


def test_no_finding_uncorrelated_subquery():
    # 비상관 서브쿼리는 1회 실행 — 탐지하지 않는다
    sql = "SELECT o.id, (SELECT MAX(id) FROM customers) FROM orders o"
    assert run_rule(rule, sql) == []


def test_no_finding_subquery_in_where():
    # SELECT 절이 아닌 곳의 서브쿼리는 이 Rule의 대상이 아니다
    sql = (
        "SELECT o.id FROM orders o "
        "WHERE o.total > (SELECT AVG(p.total) FROM payments p WHERE p.order_id = o.id)"
    )
    assert run_rule(rule, sql) == []
