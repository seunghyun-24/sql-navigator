from rules.select_star import SelectStarRule
from tests.util import assert_explainable, run_rule

rule = SelectStarRule()


def test_detects_select_star():
    findings = run_rule(rule, "SELECT * FROM orders WHERE id = 1")
    assert len(findings) == 1
    assert findings[0].severity == "INFO"
    assert_explainable(findings)


def test_detects_qualified_star():
    findings = run_rule(rule, "SELECT o.* FROM orders o WHERE o.id = 1")
    assert len(findings) == 1


def test_no_finding_explicit_columns():
    assert run_rule(rule, "SELECT id, name FROM orders WHERE id = 1") == []


def test_no_finding_count_star():
    # count(*)의 *는 projection이 아니다
    assert run_rule(rule, "SELECT count(*) FROM orders WHERE id = 1") == []
