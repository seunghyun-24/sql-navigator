"""Parser Layer.

책임: SQL -> AST, AST -> 직렬화 가능한 트리, Formatter 위임.
하지 않는 것: Warning 생성, Optimization, 분석. (docs/architecture.md)
"""

from __future__ import annotations

from typing import Optional

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from config import DIALECT

_MAX_LABEL = 60


def parse(sql: str) -> tuple[Optional[exp.Expression], Optional[dict]]:
    """SQL -> (ast, None) 또는 (None, error dict)."""
    sql = sql or ""
    if not sql.strip():
        return None, {"message": "SQL이 비어 있습니다.", "line": None, "col": None}

    try:
        ast = sqlglot.parse_one(sql, read=DIALECT)
    except ParseError as e:
        first = e.errors[0] if e.errors else {}
        return None, {
            "message": first.get("description") or str(e),
            "line": first.get("line"),
            "col": first.get("col"),
        }

    if ast is None:
        return None, {"message": "파싱 결과가 없습니다.", "line": None, "col": None}
    return ast, None


def format_sql(ast: exp.Expression) -> str:
    return ast.sql(dialect=DIALECT, pretty=True)


def _label(node: exp.Expression) -> str:
    """사람이 읽을 짧은 라벨. 잘려도 구조 파악엔 지장 없다."""
    try:
        text = node.sql(dialect=DIALECT)
    except Exception:
        text = ""
    text = " ".join(text.split())
    if len(text) > _MAX_LABEL:
        text = text[: _MAX_LABEL - 1] + "…"
    return text


def node_to_tree(node: exp.Expression, arg: str = "") -> dict:
    """AST -> 직렬화 가능한 트리. AST를 수정하지 않는다."""
    children = []
    for key, value in node.args.items():
        items = value if isinstance(value, list) else [value]
        for item in items:
            if isinstance(item, exp.Expression):
                children.append(node_to_tree(item, key))
            elif item is not None and item is not False and item != "":
                children.append(
                    {
                        "type": "value",
                        "arg": key,
                        "label": str(item),
                        "children": [],
                    }
                )
    return {
        "type": type(node).__name__,
        "arg": arg,
        "label": _label(node),
        "children": children,
    }

