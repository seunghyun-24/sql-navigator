"""select-without-where (docs/rules.md) — WARNING.

false positive 방지:
- 최상위 SELECT만 검사 (서브쿼리는 외부 조건과 상관관계가 흔함)
- LIMIT, GROUP BY, 순수 집계 쿼리는 제외
"""

from __future__ import annotations

from sqlglot import exp

from engine import Finding, Rule, RuleContext, clause, snippet_of


def _is_pure_aggregate(select: exp.Select) -> bool:
    """SELECT count(*) FROM t 같은 집계 전용 쿼리인가."""
    projections = select.expressions
    if not projections:
        return False
    for e in projections:
        inner = e.this if isinstance(e, exp.Alias) else e
        if not isinstance(inner, exp.AggFunc):
            return False
    return True


class SelectWithoutWhereRule(Rule):
    id = "select-without-where"
    severity = "WARNING"
    target_nodes = (exp.Select,)

    def check(self, node: exp.Expression, ctx: RuleContext) -> list[Finding]:
        if node is not ctx.root:  # 최상위 SELECT만
            return []
        if clause(node, exp.From) is None:  # SELECT 1 등
            return []
        if clause(node, exp.Where) or clause(node, exp.Limit) or clause(node, exp.Group):
            return []
        if _is_pure_aggregate(node):
            return []
        return [
            Finding(
                rule_id=self.id,
                severity=self.severity,
                message="WHERE와 LIMIT이 모두 없는 SELECT입니다.",
                reason="조건 없는 SELECT는 Full Scan 가능성이 있고, 대량 데이터를 전송할 수 있습니다.",
                example="SELECT id, name FROM users",
                fix="SELECT id, name FROM users WHERE created_at >= :since LIMIT 100",
                snippet=snippet_of(node, ctx.dialect),
            )
        ]
