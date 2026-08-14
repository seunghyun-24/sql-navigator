from rules.leading_wildcard_like import LeadingWildcardLikeRule
from tests.util import assert_explainable, run_rule

rule = LeadingWildcardLikeRule()


def test_detects_leading_percent():
    findings = run_rule(rule, "SELECT * FROM users WHERE email LIKE '%@gmail.com'")
    assert len(findings) == 1
    assert findings[0].severity == "WARNING"
    assert_explainable(findings)


def test_detects_leading_underscore():
    assert len(run_rule(rule, "SELECT * FROM users WHERE code LIKE '_X%'")) == 1


def test_detects_ilike():
    assert len(run_rule(rule, "SELECT * FROM users WHERE name ILIKE '%kim'")) == 1


def test_no_finding_trailing_wildcard():
    assert run_rule(rule, "SELECT * FROM users WHERE email LIKE 'kim%'") == []


def test_no_finding_non_literal_pattern():
    # 패턴이 컬럼/식이면 단정할 수 없다 — 침묵 (Static Only)
    assert run_rule(rule, "SELECT * FROM users WHERE email LIKE pattern_col") == []
