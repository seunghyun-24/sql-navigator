"""Schema Context 파서 테스트 (docs/roadmap.md v0.5)."""

import json

from schema_context import parse_schema

DDL = """
CREATE TABLE users (
  id int PRIMARY KEY,
  email varchar(100) UNIQUE,
  name varchar(50),
  created_at timestamp
);
CREATE TABLE orders (
  id bigint,
  user_id int,
  amount numeric(10, 2),
  PRIMARY KEY (id)
);
CREATE INDEX idx_orders_user ON orders (user_id);
"""


def test_tables_and_columns():
    schema, info = parse_schema(DDL)
    assert info == {"provided": True, "tableCount": 2, "error": None}
    users = schema["tables"]["users"]
    assert users["columns"]["id"] == "number"
    assert users["columns"]["email"] == "text"
    assert users["columns"]["created_at"] == "datetime"


def test_inline_and_table_level_pk():
    schema, _ = parse_schema(DDL)
    assert schema["tables"]["users"]["pk"] == ["id"]
    assert schema["tables"]["orders"]["pk"] == ["id"]


def test_unique_and_create_index_as_indexes():
    schema, _ = parse_schema(DDL)
    assert ["email"] in schema["tables"]["users"]["indexes"]
    assert ["user_id"] in schema["tables"]["orders"]["indexes"]
    # 인덱스/테이블 이름 식별자가 컬럼으로 오인되면 안 된다
    for idx in schema["tables"]["orders"]["indexes"]:
        assert "idx_orders_user" not in idx
        assert "orders" not in idx


def test_empty_ddl_not_provided():
    schema, info = parse_schema("   ")
    assert schema is None
    assert info["provided"] is False


def test_invalid_ddl_structured_error():
    schema, info = parse_schema("CREATE TABLE (")
    assert schema is None
    assert info["provided"] is True
    assert info["error"]


def test_non_ddl_statements_ignored():
    schema, info = parse_schema("SELECT 1")
    assert schema is None
    assert info["error"]  # CREATE TABLE 없음 안내


def test_serializable():
    schema, info = parse_schema(DDL)
    json.dumps(schema)
    json.dumps(info)
