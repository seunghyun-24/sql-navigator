from rules.join_type_mismatch import JoinTypeMismatchRule
from tests.util import assert_explainable, run_rule

rule = JoinTypeMismatchRule()

SCHEMA = {
    "tables": {
        "users": {"columns": {"id": "number"}, "pk": ["id"], "indexes": []},
        "logs": {
            "columns": {"user_id": "text", "actor_id": "number"},
            "pk": [],
            "indexes": [],
        },
    }
}


def test_detects_type_mismatch():
    sql = "SELECT * FROM users u JOIN logs l ON l.user_id = u.id"
    findings = run_rule(rule, sql, schema=SCHEMA)
    assert len(findings) == 1
    assert findings[0].severity == "WARNING"
    assert_explainable(findings)


def test_no_finding_matching_types():
    sql = "SELECT * FROM users u JOIN logs l ON l.actor_id = u.id"
    assert run_rule(rule, sql, schema=SCHEMA) == []


def test_no_finding_without_schema():
    # 스키마 없으면 skip (docs/rules.md)
    sql = "SELECT * FROM users u JOIN logs l ON l.user_id = u.id"
    assert run_rule(rule, sql) == []


def test_no_finding_unknown_column():
    # 스키마에 없는 컬럼은 단정할 수 없다 — 침묵 (Static Only)
    sql = "SELECT * FROM users u JOIN logs l ON l.unknown_col = u.id"
    assert run_rule(rule, sql, schema=SCHEMA) == []
