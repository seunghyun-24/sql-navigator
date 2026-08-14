from rules.select_without_where import SelectWithoutWhereRule
from tests.util import assert_explainable, run_rule

rule = SelectWithoutWhereRule()


def test_detects_select_without_where_or_limit():
    findings = run_rule(rule, "SELECT id, name FROM users")
    assert len(findings) == 1
    assert findings[0].severity == "WARNING"
    assert_explainable(findings)


def test_no_finding_with_where():
    assert run_rule(rule, "SELECT id FROM users WHERE id = 1") == []


def test_no_finding_with_limit():
    assert run_rule(rule, "SELECT id FROM users LIMIT 10") == []


def test_no_finding_pure_aggregate():
    assert run_rule(rule, "SELECT count(*) FROM users") == []
    assert run_rule(rule, "SELECT max(id) AS m, count(*) AS c FROM users") == []


def test_no_finding_group_by():
    assert run_rule(rule, "SELECT status, count(*) FROM users GROUP BY status") == []


def test_no_finding_subquery():
    # 서브쿼리는 검사하지 않는다 (false positive 방지)
    sql = "SELECT * FROM (SELECT id FROM users) u WHERE u.id = 1"
    assert run_rule(rule, sql) == []


def test_no_finding_without_from():
    assert run_rule(rule, "SELECT 1") == []
