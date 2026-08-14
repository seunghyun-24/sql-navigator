from rules.delete_without_where import DeleteWithoutWhereRule
from rules.update_without_where import UpdateWithoutWhereRule
from tests.util import assert_explainable, run_rule

delete_rule = DeleteWithoutWhereRule()
update_rule = UpdateWithoutWhereRule()


def test_detects_delete_without_where():
    findings = run_rule(delete_rule, "DELETE FROM users")
    assert len(findings) == 1
    assert findings[0].severity == "CRITICAL"
    assert_explainable(findings)


def test_no_finding_delete_with_where():
    assert run_rule(delete_rule, "DELETE FROM users WHERE id = 1") == []


def test_detects_update_without_where():
    findings = run_rule(update_rule, "UPDATE users SET status = 'inactive'")
    assert len(findings) == 1
    assert findings[0].severity == "CRITICAL"
    assert_explainable(findings)


def test_no_finding_update_with_where():
    sql = "UPDATE users SET status = 'inactive' WHERE last_login < '2025-01-01'"
    assert run_rule(update_rule, sql) == []
