"""Schema Context (docs/analyzer.md, docs/roadmap.md v0.5).

사용자가 붙여넣은 DDL(CREATE TABLE / CREATE INDEX) -> 스키마 모델.
DB에 연결하지 않는다 — 항상 사용자 제공이다 (docs/principles.md Static Only).
파싱은 sqlglot AST로만 한다 — Regex/문자열 검색 금지.

스키마 모델 (RuleContext.schema로 전달, JSON 직렬화 가능):
  {
    "tables": {
      "<table>": {
        "columns": { "<col>": "<type category>" },   # number|text|datetime|boolean|other
        "pk": ["<col>", ...],
        "indexes": [["<col>", ...], ...],             # PK 제외한 index들
      }
    }
  }

parse_schema는 (schema, info)를 반환한다. info는 UI 표시용:
  { "provided": bool, "tableCount": int, "error": str | None }
"""

from __future__ import annotations

from typing import Optional

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from config import DIALECT

# sqlglot DataType.this 이름 -> 카테고리 (implicit-conversion 비교용)
_NUMBER = {
    "TINYINT", "SMALLINT", "INT", "INTEGER", "BIGINT", "DECIMAL", "NUMERIC",
    "FLOAT", "DOUBLE", "REAL", "MONEY", "SMALLMONEY", "SERIAL", "BIGSERIAL",
    "SMALLSERIAL", "UTINYINT", "USMALLINT", "UINT", "UBIGINT",
}
_TEXT = {"CHAR", "NCHAR", "VARCHAR", "NVARCHAR", "TEXT", "MEDIUMTEXT", "LONGTEXT", "UUID"}
_DATETIME = {"DATE", "DATETIME", "DATETIME64", "TIMESTAMP", "TIMESTAMPTZ", "TIMESTAMPLTZ", "TIME", "TIMETZ"}
_BOOLEAN = {"BOOLEAN", "BIT"}


def _type_category(dtype: Optional[exp.DataType]) -> str:
    if dtype is None:
        return "other"
    name = dtype.this.name if isinstance(dtype.this, exp.DataType.Type) else str(dtype.this)
    name = name.upper()
    if name in _NUMBER:
        return "number"
    if name in _TEXT:
        return "text"
    if name in _DATETIME:
        return "datetime"
    if name in _BOOLEAN:
        return "boolean"
    return "other"


def _column_names(node: exp.Expression) -> list[str]:
    """제약/인덱스 정의 안의 컬럼 이름들 (선언 순서 유지, 중복 제거)."""
    names: list[str] = []
    for col in node.find_all(exp.Column):
        n = col.name.lower()
        if n and n not in names:
            names.append(n)
    for ident in node.find_all(exp.Identifier):
        n = ident.name.lower()
        if n and n not in names and ident.find_ancestor(exp.Column) is None:
            names.append(n)
    return names


def _parse_create_table(create: exp.Create, tables: dict) -> None:
    target = create.this
    schema_def = None
    if isinstance(target, exp.Schema):  # CREATE TABLE t (...) 는 Schema(this=Table)
        schema_def = target
        target = target.this
    if not isinstance(target, exp.Table) or not target.name:
        return

    table: dict = {"columns": {}, "pk": [], "indexes": []}
    tables[target.name.lower()] = table
    if schema_def is None:
        return

    for item in schema_def.expressions:
        if isinstance(item, exp.ColumnDef):
            col_name = item.name.lower()
            table["columns"][col_name] = _type_category(item.args.get("kind"))
            # 인라인 PRIMARY KEY / UNIQUE 제약
            for constraint in item.args.get("constraints") or []:
                kind = constraint.kind if isinstance(constraint, exp.ColumnConstraint) else constraint
                if isinstance(kind, exp.PrimaryKeyColumnConstraint):
                    table["pk"].append(col_name)
                elif isinstance(kind, exp.UniqueColumnConstraint):
                    table["indexes"].append([col_name])
        elif isinstance(item, exp.PrimaryKey):  # 테이블 레벨 PRIMARY KEY (a, b)
            table["pk"].extend(c for c in _column_names(item) if c not in table["pk"])
        elif isinstance(item, exp.UniqueColumnConstraint):  # 테이블 레벨 UNIQUE (a, b)
            cols = _column_names(item)
            if cols:
                table["indexes"].append(cols)
        elif isinstance(item, exp.Constraint):  # CONSTRAINT <name> PRIMARY KEY/UNIQUE (...)
            # 제약 이름 식별자가 섞이지 않도록 내부 제약 노드에서만 컬럼을 읽는다
            pk = item.find(exp.PrimaryKey)
            if pk is not None:
                table["pk"].extend(c for c in _column_names(pk) if c not in table["pk"])
            else:
                uniq = item.find(exp.UniqueColumnConstraint)
                if uniq is not None:
                    cols = _column_names(uniq)
                    if cols:
                        table["indexes"].append(cols)


def _parse_create_index(create: exp.Create, tables: dict) -> None:
    table_node = create.find(exp.Table)
    if table_node is None or not table_node.name:
        return
    name = table_node.name.lower()
    table = tables.setdefault(name, {"columns": {}, "pk": [], "indexes": []})

    # 인덱스 컬럼은 exp.Ordered로 감싸인다 — 인덱스/테이블 이름 식별자와 구분됨
    cols: list[str] = []
    for ordered in create.find_all(exp.Ordered):
        for c in _column_names(ordered):
            if c not in cols:
                cols.append(c)
    if not cols:  # 버전별 fallback: Column 노드만 (테이블 이름 제외)
        for col in create.find_all(exp.Column):
            n = col.name.lower()
            if n and n != name and n not in cols:
                cols.append(n)
    if cols:
        table["indexes"].append(cols)


def parse_schema(ddl: str) -> tuple[Optional[dict], dict]:
    """DDL -> (schema | None, info). 비어 있으면 (None, provided=False)."""
    ddl = (ddl or "").strip()
    if not ddl:
        return None, {"provided": False, "tableCount": 0, "error": None}

    try:
        statements = sqlglot.parse(ddl, read=DIALECT)
    except ParseError as e:
        first = e.errors[0] if e.errors else {}
        message = first.get("description") or str(e)
        return None, {"provided": True, "tableCount": 0, "error": message}

    tables: dict = {}
    for stmt in statements:
        if not isinstance(stmt, exp.Create):
            continue  # DDL 외 문장은 무시 (스키마 입력란이므로)
        kind = str(stmt.args.get("kind") or "").upper()
        if kind == "TABLE":
            _parse_create_table(stmt, tables)
        elif kind == "INDEX":
            _parse_create_index(stmt, tables)

    if not tables:
        return None, {
            "provided": True,
            "tableCount": 0,
            "error": "CREATE TABLE 문을 찾지 못했습니다.",
        }
    return {"tables": tables}, {"provided": True, "tableCount": len(tables), "error": None}
