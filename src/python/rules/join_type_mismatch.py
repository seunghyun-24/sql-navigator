"""join-type-mismatch (docs/rules.md v0.6) — WARNING. Schema Context 필요.

JOIN 키 양쪽 컬럼의 타입 카테고리가 다르면 암묵적 형변환으로 index가
무효화될 수 있다. 스키마 없으면 skip (pk-not-used와 동일 정책).
확실한 것만 말한다: 양쪽 카테고리를 모두 알고, 둘 다 'other'가 아니며,
서로 다를 때만 경고한다 (Static Only).
"""

from __future__ import annotations

from typing import Optional

from sqlglot import exp

from engine import Finding, Rule, RuleContext, snippet_of
from scope import alias_table_map, resolve_column

_REASON = (
    "JOIN 키의 타입이 다르면 DB가 한쪽을 암묵적으로 형변환합니다. "
    "변환이 컬럼 쪽에 적용되면 그 컬럼의 index를 사용할 수 없습니다."
)
_EXAMPLE = "JOIN logs l ON l.user_id = u.id  -- l.user_id는 varchar, u.id는 integer"
_FIX = "컬럼 타입을 일치시키거나, 캐스팅을 index가 없는 쪽 컬럼에 적용하세요."


class JoinTypeMismatchRule(Rule):
    id = "join-type-mismatch"
    severity = "WARNING"
    target_nodes = (exp.Join,)

    def check(self, node: exp.Expression, ctx: RuleContext) -> list[Finding]:
        if not ctx.schema:
            return []  # 스키마 없으면 skip (docs/rules.md)
        on = node.args.get("on")
        if on is None:
            return []

        stmt = node.find_ancestor(exp.Select) or ctx.root
        mapping = alias_table_map(stmt)
        findings: list[Finding] = []
        for eq in on.find_all(exp.EQ):
            left, right = eq.this, eq.args.get("expression")
            if not (isinstance(left, exp.Column) and isinstance(right, exp.Column)):
                continue
            lcat = self._category(left, mapping, ctx.schema, ctx)
            rcat = self._category(right, mapping, ctx.schema, ctx)
            if lcat is None or rcat is None or "other" in (lcat, rcat):
                continue
            if lcat == rcat:
                continue
            findings.append(
                Finding(
                    rule_id=self.id,
                    severity=self.severity,
                    message=(
                        f"JOIN 키 타입 불일치: "
                        f"{left.sql(dialect=ctx.dialect)}({lcat}) = "
                        f"{right.sql(dialect=ctx.dialect)}({rcat})"
                    ),
                    reason=_REASON,
                    example=_EXAMPLE,
                    fix=_FIX,
                    snippet=snippet_of(eq, ctx.dialect),
                )
            )
        return findings

    @staticmethod
    def _category(
        col: exp.Column, mapping: dict[str, str], schema: dict, ctx: RuleContext
    ) -> Optional[str]:
        resolved = resolve_column(col, mapping)
        if resolved is None:
            return None
        table, column = resolved
        return (
            ((schema.get("tables") or {}).get(table) or {})
            .get("columns", {})
            .get(column)
        )
