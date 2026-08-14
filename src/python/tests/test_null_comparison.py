import sqlglot

from config import DIALECT
from rules.null_comparison import NullComparisonRule
from tests.util import assert_explainable, run_rule

rule = NullComparisonRule()


def test_detects_eq_null():
    findings = run_rule(rule, "SELECT * FROM users WHERE deleted_at = NULL")
    assert len(findings) == 1
    assert findings[0].severity == "CRITICAL"
    assert "IS NULL" in findings[0].fix
    assert_explainable(findings)


def test_detects_neq_null():
    findings = run_rule(rule, "SELECT * FROM users WHERE deleted_at != NULL")
    assert len(findings) == 1
    assert "IS NOT NULL" in findings[0].fix


def test_detects_null_on_left_side():
    findings = run_rule(rule, "SELECT * FROM users WHERE NULL = deleted_at")
    assert len(findings) == 1


def test_no_finding_is_null():
    assert run_rule(rule, "SELECT * FROM users WHERE deleted_at IS NULL") == []
    assert run_rule(rule, "SELECT * FROM users WHERE deleted_at IS NOT NULL") == []


def test_no_finding_update_set_null_assignment():
    # SET a = NULL은 대입이다 — 비교가 아니므로 탐지하면 안 된다
    assert run_rule(rule, "UPDATE users SET deleted_at = NULL WHERE id = 1") == []


def test_detects_null_comparison_in_update_where():
    findings = run_rule(rule, "UPDATE users SET a = 1 WHERE deleted_at = NULL")
    assert len(findings) == 1


# (v0.9) fixSql 검증 테스트
def test_fix_sql_parses_without_error():
    """fixSql은 parse 가능해야 한다."""
    findings = run_rule(rule, "SELECT * FROM users WHERE deleted_at = NULL")
    assert len(findings) == 1
    f = findings[0]
    assert f.fix_sql is not None, "fixSql이 없다"
    # fixSql을 parse할 수 있어야 한다
    try:
        ast = sqlglot.parse_one(f.fix_sql, read=DIALECT)
        assert ast is not None, "fixSql parse 실패"
    except Exception as e:
        raise AssertionError(f"fixSql parse 실패: {f.fix_sql}\n{e}")


def test_fix_sql_neq_parses_without_error():
    """NEQ 경우 fixSql도 parse 가능해야 한다."""
    findings = run_rule(rule, "SELECT * FROM users WHERE deleted_at != NULL")
    assert len(findings) == 1
    f = findings[0]
    assert f.fix_sql is not None
    ast = sqlglot.parse_one(f.fix_sql, read=DIALECT)
    assert ast is not None


def test_fix_sql_resolves_finding():
    """fixSql을 다시 분석하면 같은 Finding이 없어야 한다."""
    findings = run_rule(rule, "SELECT * FROM users WHERE deleted_at = NULL")
    assert len(findings) == 1
    f = findings[0]
    assert f.fix_sql is not None

    # fixSql을 다시 분석
    refound = run_rule(rule, f.fix_sql)
    assert len(refound) == 0, f"fixSql 재적용 후에도 Finding이 남았다: {refound}"
