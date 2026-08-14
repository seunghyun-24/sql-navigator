from rules.not_in_with_null import NotInWithNullRule
from tests.util import assert_explainable, run_rule

rule = NotInWithNullRule()


def test_detects_not_in_subquery():
    sql = "SELECT * FROM users WHERE id NOT IN (SELECT user_id FROM banned)"
    findings = run_rule(rule, sql)
    assert len(findings) == 1
    assert "NOT EXISTS" in findings[0].fix
    assert_explainable(findings)


def test_no_finding_literal_list():
    # 리터럴 목록은 안전 — 탐지 제외 (docs/rules.md)
    assert run_rule(rule, "SELECT * FROM users WHERE status NOT IN ('A', 'B')") == []


def test_no_finding_positive_in_subquery():
    sql = "SELECT * FROM users WHERE id IN (SELECT user_id FROM active)"
    assert run_rule(rule, sql) == []


def test_no_finding_other_not():
    assert run_rule(rule, "SELECT * FROM users WHERE NOT active") == []
