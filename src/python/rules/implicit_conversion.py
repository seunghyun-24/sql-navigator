"""implicit-conversion (docs/rules.md) — INFO. Schema Context 필요.

컬럼 타입과 비교 리터럴 타입이 다르면(숫자 컬럼 = 문자열 리터럴 등)
암묵적 형변환이 index를 무효화할 수 있다. 스키마 없으면 skip.
"""

from __future__ import annotations

from typing import Optional

from sqlglot import exp

from engine import Finding, Rule, RuleContext, snippet_of
from scope import alias_table_map, resolve_column

_REASON = (
    "타입이 다른 비교는 암묵적 형변환을 유발해 index를 무효화할 수 있습니다. "
    "리터럴 쪽을 컬럼 타입에 맞추는 것이 안전합니다."
)
_EXAMPLE = "SELECT * FROM users WHERE user_id = '123'  -- user_id는 integer"
_FIX = "SELECT * FROM users WHERE user_id = 123"

_COMPARISONS = (exp.EQ, exp.NEQ, exp.GT, exp.GTE, exp.LT, exp.LTE)


def _literal_category(node: exp.Expression) -> Optional[str]:
    if not isinstance(node, exp.Literal):
        return None
    if node.is_string:
        return "text"
    if node.is_number:
        return "number"
    return None


class ImplicitConversionRule(Rule):
    id = "implicit-conversion"
    severity = "INFO"
    target_nodes = _COMPARISONS

    def check(self, node: exp.Expression, ctx: RuleContext) -> list[Finding]:
        if not ctx.schema:
            return []  # 스키마 없으면 skip (docs/rules.md)

        left, right = node.this, node.args.get("expression")
        if isinstance(left, exp.Column):
            col, other = left, right
        elif isinstance(right, exp.Column):
            col, other = right, left
        else:
            return []
        lit_category = _literal_category(other) if other is not None else None
        if lit_category is None:
            return []

        stmt = col.find_ancestor(exp.Select, exp.Update, exp.Delete)
        resolved = resolve_column(col, alias_table_map(stmt))
        if resolved is None:
            return []
        table, column = resolved
        col_category = ((ctx.schema.get("tables") or {}).get(table) or {}).get(
            "columns", {}
        ).get(column)

        # 확실한 불일치만 말한다: number<->text 교차 (datetime 컬럼의 문자열 리터럴은 정상)
        mismatch = (col_category == "number" and lit_category == "text") or (
            col_category == "text" and lit_category == "number"
        )
        if not mismatch:
            return []

        literal_sql = other.sql(dialect=ctx.dialect)
        return [
            Finding(
                rule_id=self.id,
                severity=self.severity,
                message=(
                    f"{table}.{column}({col_category})를 {lit_category} 리터럴 "
                    f"{literal_sql}과(와) 비교합니다 — 암묵적 형변환 가능성."
                ),
                reason=_REASON,
                example=_EXAMPLE,
                fix=_FIX,
                snippet=snippet_of(node, ctx.dialect),
            )
        ]
