"""distinct-as-bandaid (docs/rules.md v0.6) — INFO.

JOIN이 있는 쿼리의 SELECT DISTINCT는 JOIN으로 늘어난 중복 행을 덮는
패턴일 수 있다 — 원인(JOIN 조건)을 숨긴다.
단일 테이블 DISTINCT는 정상. DISTINCT ON (...)은 의도적 — 탐지 제외.
"""

from __future__ import annotations

from sqlglot import exp

from engine import Finding, Rule, RuleContext, snippet_of

_REASON = (
    "JOIN 결과의 중복을 DISTINCT로 제거하는 것은 증상 치료일 수 있습니다. "
    "중복의 원인이 1:N JOIN이라면 JOIN 조건을 점검하거나 EXISTS로 "
    "재작성하는 편이 의도가 명확하고 비용도 적습니다."
)
_EXAMPLE = (
    "SELECT DISTINCT o.id FROM orders o "
    "JOIN order_items i ON i.order_id = o.id"
)
_FIX = (
    "SELECT o.id FROM orders o "
    "WHERE EXISTS (SELECT 1 FROM order_items i WHERE i.order_id = o.id)"
)


class DistinctAsBandaidRule(Rule):
    id = "distinct-as-bandaid"
    severity = "INFO"
    target_nodes = (exp.Select,)

    def check(self, node: exp.Expression, ctx: RuleContext) -> list[Finding]:
        distinct = node.args.get("distinct")
        if not isinstance(distinct, exp.Distinct):
            return []
        if distinct.args.get("on"):  # DISTINCT ON (...)은 의도적 사용
            return []
        if not node.args.get("joins"):
            return []
        return [
            Finding(
                rule_id=self.id,
                severity=self.severity,
                message="JOIN 결과에 DISTINCT — JOIN으로 생긴 중복을 덮는 패턴일 수 있습니다.",
                reason=_REASON,
                example=_EXAMPLE,
                fix=_FIX,
                snippet=snippet_of(node, ctx.dialect),
            )
        ]
