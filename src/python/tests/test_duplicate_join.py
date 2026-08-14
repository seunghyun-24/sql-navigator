from rules.duplicate_join import DuplicateJoinRule
from tests.util import assert_explainable, run_rule

rule = DuplicateJoinRule()


def test_detects_identical_join():
    sql = (
        "SELECT * FROM orders o "
        "JOIN customers c ON o.customer_id = c.id "
        "JOIN customers c ON o.customer_id = c.id"
    )
    findings = run_rule(rule, sql)
    assert len(findings) == 1
    assert_explainable(findings)


def test_detects_alias_only_difference():
    sql = (
        "SELECT * FROM orders o "
        "JOIN customers c ON o.customer_id = c.id "
        "JOIN customers c2 ON o.customer_id = c2.id"
    )
    findings = run_rule(rule, sql)
    assert len(findings) == 1


def test_no_finding_self_join_with_different_condition():
    # 조건이 다른 self-join은 정상
    sql = (
        "SELECT * FROM employees e "
        "JOIN employees m ON e.manager_id = m.id "
        "JOIN employees d ON e.deputy_id = d.id"
    )
    assert run_rule(rule, sql) == []


def test_no_finding_different_tables():
    sql = (
        "SELECT * FROM orders o "
        "JOIN customers c ON o.customer_id = c.id "
        "JOIN products p ON o.product_id = p.id"
    )
    assert run_rule(rule, sql) == []
