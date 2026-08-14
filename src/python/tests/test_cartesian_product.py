from rules.cartesian_product import CartesianProductRule
from tests.util import assert_explainable, run_rule

rule = CartesianProductRule()


def test_detects_comma_join():
    findings = run_rule(rule, "SELECT * FROM orders, customers")
    assert any(f.rule_id == "cartesian-product" for f in findings)
    assert findings[0].severity == "CRITICAL"
    assert_explainable(findings)


def test_detects_join_without_on():
    findings = run_rule(rule, "SELECT * FROM orders o JOIN customers c")
    assert len(findings) == 1
    assert findings[0].severity == "CRITICAL"


def test_explicit_cross_join_is_warning():
    findings = run_rule(rule, "SELECT * FROM sizes CROSS JOIN colors")
    assert len(findings) == 1
    assert findings[0].severity == "WARNING"
    assert_explainable(findings)


def test_no_finding_with_on():
    sql = "SELECT * FROM orders o JOIN customers c ON o.customer_id = c.id"
    assert run_rule(rule, sql) == []


def test_no_finding_with_using():
    sql = "SELECT * FROM orders JOIN customers USING (customer_id)"
    assert run_rule(rule, sql) == []


def test_no_finding_natural_join():
    sql = "SELECT * FROM orders NATURAL JOIN customers"
    assert run_rule(rule, sql) == []
