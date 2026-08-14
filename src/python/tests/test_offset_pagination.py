from rules.offset_pagination import OffsetPaginationRule
from tests.util import assert_explainable, run_rule

rule = OffsetPaginationRule()


def test_detects_large_offset():
    sql = "SELECT * FROM orders ORDER BY id LIMIT 20 OFFSET 100000"
    findings = run_rule(rule, sql)
    assert len(findings) == 1
    assert "keyset" in findings[0].message
    assert_explainable(findings)


def test_detects_at_threshold():
    sql = "SELECT * FROM orders ORDER BY id LIMIT 20 OFFSET 1000"
    assert len(run_rule(rule, sql)) == 1


def test_no_finding_small_offset():
    assert run_rule(rule, "SELECT * FROM orders ORDER BY id LIMIT 20 OFFSET 40") == []


def test_no_finding_without_offset():
    assert run_rule(rule, "SELECT * FROM orders ORDER BY id LIMIT 20") == []
