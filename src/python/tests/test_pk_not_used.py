"""pk-not-used Rule 테스트 (탐지/비탐지/Explainability — docs/analyzer.md)."""

from rules.pk_not_used import PkNotUsedRule
from tests.util import assert_explainable, run_rule

SCHEMA = {
    "tables": {
        "users": {
            "columns": {"id": "number", "name": "text", "nickname": "text"},
            "pk": ["id"],
            "indexes": [["name"]],
        },
        "orders": {
            "columns": {"id": "number", "user_id": "number", "memo": "text"},
            "pk": ["id"],
            "indexes": [],
        },
    }
}


def test_detects_where_without_indexed_column():
    findings = run_rule(PkNotUsedRule(), "SELECT * FROM users WHERE nickname = 'kim'", SCHEMA)
    assert len(findings) == 1
    assert findings[0].rule_id == "pk-not-used"
    assert findings[0].severity == "WARNING"
    assert_explainable(findings)


def test_no_finding_when_pk_used():
    assert run_rule(PkNotUsedRule(), "SELECT * FROM users WHERE id = 1", SCHEMA) == []


def test_no_finding_when_index_used():
    assert run_rule(PkNotUsedRule(), "SELECT * FROM users WHERE name = 'kim'", SCHEMA) == []


def test_join_on_pk_counts():
    sql = "SELECT * FROM orders o JOIN users u ON o.user_id = u.id WHERE o.id = 1"
    assert run_rule(PkNotUsedRule(), sql, SCHEMA) == []


def test_detects_per_table_in_join():
    # users는 u.id로 커버되지만 orders는 memo만 사용 -> orders만 경고
    sql = "SELECT * FROM orders o JOIN users u ON u.id = 1 WHERE o.memo = 'x'"
    findings = run_rule(PkNotUsedRule(), sql, SCHEMA)
    assert len(findings) == 1
    assert "orders" in findings[0].message


def test_skip_without_schema():
    assert run_rule(PkNotUsedRule(), "SELECT * FROM users WHERE nickname = 'kim'") == []


def test_skip_unknown_table():
    assert run_rule(PkNotUsedRule(), "SELECT * FROM unknown_t WHERE x = 1", SCHEMA) == []


def test_skip_when_no_conditions():
    # WHERE/JOIN 없음 — select-without-where 영역, 중복 경고 방지
    assert run_rule(PkNotUsedRule(), "SELECT * FROM users", SCHEMA) == []
