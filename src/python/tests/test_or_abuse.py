import sqlglot

from config import DIALECT
from rules.or_abuse import OrAbuseRule
from tests.util import assert_explainable, run_rule

rule = OrAbuseRule()


def test_detects_or_chain_on_same_column():
    sql = "SELECT * FROM t WHERE status = 'A' OR status = 'B' OR status = 'C'"
    findings = run_rule(rule, sql)
    assert len(findings) == 1
    assert "IN (" in findings[0].fix
    assert_explainable(findings)


def test_detection_reported_once_per_chain():
    sql = "SELECT * FROM t WHERE a = 1 OR a = 2 OR a = 3 OR a = 4"
    assert len(run_rule(rule, sql)) == 1


def test_no_finding_below_threshold():
    sql = "SELECT * FROM t WHERE status = 'A' OR status = 'B'"
    assert run_rule(rule, sql) == []


def test_no_finding_different_columns():
    sql = "SELECT * FROM t WHERE a = 1 OR b = 2 OR c = 3"
    assert run_rule(rule, sql) == []


def test_no_finding_non_equality():
    sql = "SELECT * FROM t WHERE a > 1 OR a > 2 OR a > 3"
    assert run_rule(rule, sql) == []


# (v0.9) fixSql 검증 테스트
def test_fix_sql_parses_without_error():
    """fixSql은 parse 가능해야 한다."""
    sql = "SELECT * FROM t WHERE status = 'A' OR status = 'B' OR status = 'C'"
    findings = run_rule(rule, sql)
    assert len(findings) == 1
    f = findings[0]
    assert f.fix_sql is not None, "fixSql이 없다"
    # fixSql을 parse할 수 있어야 한다
    try:
        ast = sqlglot.parse_one(f.fix_sql, read=DIALECT)
        assert ast is not None, "fixSql parse 실패"
    except Exception as e:
        raise AssertionError(f"fixSql parse 실패: {f.fix_sql}\n{e}")


def test_fix_sql_resolves_finding():
    """fixSql을 다시 분석하면 같은 Finding이 없어야 한다."""
    sql = "SELECT * FROM t WHERE status = 'A' OR status = 'B' OR status = 'C'"
    findings = run_rule(rule, sql)
    assert len(findings) == 1
    f = findings[0]
    assert f.fix_sql is not None

    # fixSql을 다시 분석
    refound = run_rule(rule, f.fix_sql)
    assert len(refound) == 0, f"fixSql 재적용 후에도 Finding이 남았다: {refound}"
