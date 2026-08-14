from rules.union_vs_union_all import UnionVsUnionAllRule
from tests.util import assert_explainable, run_rule

rule = UnionVsUnionAllRule()


def test_detects_union():
    findings = run_rule(rule, "SELECT id FROM a UNION SELECT id FROM b")
    assert len(findings) == 1
    assert findings[0].severity == "INFO"
    assert "UNION ALL" in findings[0].fix
    assert_explainable(findings)


def test_chain_reported_once():
    sql = "SELECT id FROM a UNION SELECT id FROM b UNION SELECT id FROM c"
    assert len(run_rule(rule, sql)) == 1


def test_no_finding_union_all():
    assert run_rule(rule, "SELECT id FROM a UNION ALL SELECT id FROM b") == []


def test_no_finding_except():
    assert run_rule(rule, "SELECT id FROM a EXCEPT SELECT id FROM b") == []


def test_no_finding_intersect():
    assert run_rule(rule, "SELECT id FROM a INTERSECT SELECT id FROM b") == []
