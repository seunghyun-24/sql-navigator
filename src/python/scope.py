"""Scope 해석 유틸 (Analysis Layer 공용, 읽기 전용).

문(Select/Update/Delete) 하나의 FROM/JOIN/대상 테이블에서
alias -> 테이블 이름 매핑을 만들고, Column 노드를 (table, column)으로 해석한다.
스키마 기반 Rule(pk-not-used, implicit-conversion)이 공유한다.
AST를 수정하지 않는다.
"""

from __future__ import annotations

from typing import Optional

from sqlglot import exp

from engine import clause


def alias_table_map(stmt: Optional[exp.Expression]) -> dict[str, str]:
    """alias(또는 테이블명) 소문자 -> 실제 테이블명 소문자. 실제 테이블만 포함."""
    if stmt is None:
        return {}
    items: list[exp.Expression] = []

    from_clause = clause(stmt, exp.From)
    if from_clause is not None:
        if from_clause.args.get("this") is not None:
            items.append(from_clause.args["this"])
        items.extend(from_clause.args.get("expressions") or [])  # 구버전 comma join

    for join in stmt.args.get("joins") or []:
        if isinstance(join, exp.Join):
            items.append(join.this)

    # UPDATE t / DELETE FROM t — 대상 테이블
    if isinstance(stmt, (exp.Update, exp.Delete)) and isinstance(stmt.args.get("this"), exp.Table):
        items.append(stmt.args["this"])

    mapping: dict[str, str] = {}
    for item in items:
        if isinstance(item, exp.Table) and item.name:
            mapping[(item.alias or item.name).lower()] = item.name.lower()
    return mapping


def resolve_column(col: exp.Column, mapping: dict[str, str]) -> Optional[tuple[str, str]]:
    """Column -> (테이블명, 컬럼명). 단정할 수 없으면 None (Static Only)."""
    name = col.name.lower()
    if not name:
        return None
    qualifier = col.table
    if qualifier:
        table = mapping.get(qualifier.lower())
        return (table, name) if table else None
    if len(mapping) == 1:  # relation이 하나뿐이면 확정 가능
        return (next(iter(mapping.values())), name)
    return None
