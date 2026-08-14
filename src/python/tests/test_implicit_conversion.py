"""implicit-conversion Rule 테스트 (탐지/비탐지/Explainability)."""

from rules.implicit_conversion import ImplicitConversionRule
from tests.util import assert_explainable, run_rule

SCHEMA = {
    "tables": {
        "users": {
            "columns": {"id": "number", "name": "text", "created_at": "datetime"},
            "pk": ["id"],
            "indexes": [],
        }
    }
}


def test_detects_number_column_vs_string_literal():
    findings = run_rule(ImplicitConversionRule(), "SELECT * FROM users WHERE id = '123'", SCHEMA)
    assert len(findings) == 1
    assert findings[0].severity == "INFO"
    assert "users.id" in findings[0].message
    assert_explainable(findings)


def test_detects_text_column_vs_number_literal():
    findings = run_rule(ImplicitConversionRule(), "SELECT * FROM users WHERE name = 42", SCHEMA)
    assert len(findings) == 1


def test_detects_reversed_operands():
    findings = run_rule(ImplicitConversionRule(), "SELECT * FROM users WHERE '123' = id", SCHEMA)
    assert len(findings) == 1


def test_no_finding_when_types_match():
    assert run_rule(ImplicitConversionRule(), "SELECT * FROM users WHERE id = 123", SCHEMA) == []
    assert run_rule(ImplicitConversionRule(), "SELECT * FROM users WHERE name = 'kim'", SCHEMA) == []


def test_datetime_string_literal_is_normal():
    sql = "SELECT * FROM users WHERE created_at > '2026-01-01'"
    assert run_rule(ImplicitConversionRule(), sql, SCHEMA) == []


def test_skip_without_schema():
    assert run_rule(ImplicitConversionRule(), "SELECT * FROM users WHERE id = '123'") == []


def test_skip_unknown_column_or_table():
    assert run_rule(ImplicitConversionRule(), "SELECT * FROM users WHERE ghost = '1'", SCHEMA) == []
    assert run_rule(ImplicitConversionRule(), "SELECT * FROM other_t WHERE id = '1'", SCHEMA) == []


def test_alias_resolution():
    sql = "SELECT * FROM users u JOIN users v ON u.id = v.id WHERE u.id = '9'"
    findings = run_rule(ImplicitConversionRule(), sql, SCHEMA)
    assert len(findings) == 1


def test_update_where_covered():
    findings = run_rule(ImplicitConversionRule(), "UPDATE users SET name = 'x' WHERE id = '5'", SCHEMA)
    assert len(findings) == 1
