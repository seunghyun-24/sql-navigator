"""Refactoring Suggestion 테스트 (docs/roadmap.md v0.5).

핵심: 재작성 결과 검증 + 원본 AST 불변성 (docs/principles.md Immutable).
"""

import json

import sqlglot

from config import DIALECT
from suggestions import build_suggestions

SCHEMA = {
    "tables": {
        "users": {
            "columns": {"id": "number", "name": "text", "email": "text"},
            "pk": ["id"],
            "indexes": [],
        },
        "orders": {
            "columns": {"id": "number", "user_id": "number"},
            "pk": ["id"],
            "indexes": [],
        },
    }
}


def build(sql: str, schema=None):
    ast = sqlglot.parse_one(sql, read=DIALECT)
    before = ast.sql(dialect=DIALECT)
    suggestions = build_suggestions(ast, schema)
    assert ast.sql(dialect=DIALECT) == before  # 원본 AST 불변
    json.dumps(suggestions)  # 직렬화 가능
    return suggestions


def test_or_chain_rewritten_to_in():
    s = build("SELECT id FROM users WHERE status = 'A' OR status = 'B' OR status = 'C'")
    assert len(s) == 1
    assert s[0]["id"] == "rewrite-or-to-in"
    assert "IN ('A', 'B', 'C')" in s[0]["sql"]
    assert s[0]["title"] and s[0]["description"]


def test_or_chain_preserves_other_operands():
    s = build(
        "SELECT id FROM users WHERE status = 'A' OR status = 'B' OR status = 'C' OR deleted = TRUE"
    )
    assert len(s) == 1
    assert "IN ('A', 'B', 'C')" in s[0]["sql"]
    assert "deleted" in s[0]["sql"]


def test_short_or_chain_not_rewritten():
    assert build("SELECT id FROM users WHERE status = 'A' OR status = 'B'") == []


def test_different_columns_not_rewritten():
    assert build("SELECT id FROM users WHERE a = 1 OR b = 2 OR c = 3") == []


def test_select_star_expanded_with_schema():
    s = build("SELECT * FROM users WHERE id = 1", SCHEMA)
    assert len(s) == 1
    assert s[0]["id"] == "expand-select-star"
    sql = s[0]["sql"]
    assert "id" in sql and "name" in sql and "email" in sql
    assert "*" not in sql


def test_select_star_multi_table_qualified():
    s = build("SELECT * FROM users u JOIN orders o ON u.id = o.user_id", SCHEMA)
    star = [x for x in s if x["id"] == "expand-select-star"]
    assert len(star) == 1
    assert "u.name" in star[0]["sql"]
    assert "o.user_id" in star[0]["sql"]


def test_select_star_not_expanded_without_schema():
    assert build("SELECT * FROM users WHERE id = 1") == []


def test_select_star_not_expanded_for_unknown_table():
    assert build("SELECT * FROM ghost_table WHERE id = 1", SCHEMA) == []


def test_analyze_contract_includes_suggestions_and_schema_info():
    from main import analyze

    r = json.loads(analyze("SELECT * FROM users WHERE id = 1", "CREATE TABLE users (id int PRIMARY KEY, name varchar(10))"))
    assert r["ok"] is True
    assert r["schemaInfo"]["provided"] is True and r["schemaInfo"]["tableCount"] == 1
    ids = {s["id"] for s in r["suggestions"]}
    assert "expand-select-star" in ids


def test_analyze_without_schema_still_works():
    from main import analyze

    r = json.loads(analyze("SELECT id FROM users WHERE id = 1"))
    assert r["ok"] is True
    assert r["schemaInfo"]["provided"] is False
    assert r["suggestions"] == []
