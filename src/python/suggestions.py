"""Refactoring Suggestion (docs/roadmap.md v0.5, docs/analyzer.md).

읽기 좋은 SQL 재작성 제안. 원본 AST는 불변 — 제안마다 ast.copy()에
변환을 적용해 **새 AST를 생성**한다 (docs/principles.md Immutable).

출력 계약 (AnalysisResult.suggestions, UI에서 Green=추천으로 표시):
  [{ id, title, description, sql }]
"""

from __future__ import annotations

from functools import reduce

from sqlglot import exp

from config import DIALECT
from rules.or_abuse import THRESHOLD
from scope import alias_table_map


def _split_eq(op: exp.Expression):
    """EQ -> (column, value) | None. or_abuse와 동일한 판별."""
    if not isinstance(op, exp.EQ):
        return None
    left, right = op.this, op.expression
    if isinstance(left, exp.Column) and not isinstance(right, exp.Column):
        return left, right
    if isinstance(right, exp.Column) and not isinstance(left, exp.Column):
        return right, left
    return None


def _rewrite_or_chains(root: exp.Expression, dialect: str) -> bool:
    """같은 컬럼 EQ가 THRESHOLD개 이상인 OR 체인을 IN으로 재작성. (copy 위에서만 호출)"""
    changed = False
    for node in list(root.find_all(exp.Or)):
        if isinstance(node.parent, exp.Or):
            continue  # 체인 루트에서만

        groups: dict[str, tuple[exp.Column, list[exp.Expression]]] = {}
        order: list[tuple[str, exp.Expression]] = []  # (그룹 key | "", 원본 operand)
        for op in node.flatten():
            pair = _split_eq(op)
            if pair is not None:
                col, val = pair
                key = col.sql(dialect=dialect).lower()
                groups.setdefault(key, (col, []))[1].append(val)
                order.append((key, op))
            else:
                order.append(("", op))

        big = {k for k, (_, vals) in groups.items() if len(vals) >= THRESHOLD}
        if not big:
            continue

        parts: list[exp.Expression] = []
        emitted: set[str] = set()
        for key, op in order:
            if key in big:
                if key not in emitted:  # 그룹 첫 등장 위치에 IN 삽입
                    col, vals = groups[key]
                    parts.append(exp.In(this=col.copy(), expressions=[v.copy() for v in vals]))
                    emitted.add(key)
            else:
                parts.append(op.copy())

        replacement = reduce(lambda a, b: exp.Or(this=a, expression=b), parts)
        node.replace(replacement)
        changed = True
    return changed


def _expand_select_star(root: exp.Expression, schema: dict) -> bool:
    """최상위 SELECT * 를 스키마 컬럼 목록으로 전개. 모든 relation을 알 때만."""
    if not isinstance(root, exp.Select):
        return False
    exprs = root.expressions
    if len(exprs) != 1 or not isinstance(exprs[0], exp.Star):
        return False

    mapping = alias_table_map(root)  # alias -> table (선언 순서 유지)
    if not mapping:
        return False
    tables_info = schema.get("tables") or {}

    columns: list[exp.Expression] = []
    qualify = len(mapping) > 1
    for alias, table in mapping.items():
        info = tables_info.get(table)
        if not info or not info.get("columns"):
            return False  # 하나라도 모르면 전개하지 않는다 (단정 금지)
        for col in info["columns"]:
            columns.append(exp.column(col, table=alias) if qualify else exp.column(col))

    root.set("expressions", columns)
    return True


def build_suggestions(ast: exp.Expression, schema: dict | None, dialect: str = DIALECT) -> list[dict]:
    """원본 AST를 수정하지 않는다. 제안마다 독립된 copy에 변환을 적용한다."""
    suggestions: list[dict] = []

    or_copy = ast.copy()
    if _rewrite_or_chains(or_copy, dialect):
        suggestions.append(
            {
                "id": "rewrite-or-to-in",
                "title": "OR 나열을 IN으로 재작성",
                "description": "같은 컬럼에 대한 OR 동등 비교를 IN 목록으로 바꾸면 "
                "가독성이 좋아지고 index 활용에 유리합니다.",
                "sql": or_copy.sql(dialect=dialect, pretty=True),
            }
        )

    if schema:
        star_copy = ast.copy()
        if _expand_select_star(star_copy, schema):
            suggestions.append(
                {
                    "id": "expand-select-star",
                    "title": "SELECT * 를 명시적 컬럼으로 전개",
                    "description": "스키마 기준으로 컬럼을 명시하면 불필요한 전송을 줄이고 "
                    "스키마 변경에 덜 취약해집니다.",
                    "sql": star_copy.sql(dialect=dialect, pretty=True),
                }
            )

    return suggestions
