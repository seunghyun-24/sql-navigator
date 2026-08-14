"""delete-without-where (docs/rules.md) — CRITICAL."""

from __future__ import annotations

from sqlglot import exp

from engine import Finding, Rule, RuleContext, snippet_of


class DeleteWithoutWhereRule(Rule):
    id = "delete-without-where"
    severity = "CRITICAL"
    target_nodes = (exp.Delete,)

    def check(self, node: exp.Expression, ctx: RuleContext) -> list[Finding]:
        if node.args.get("where"):
            return []
        return [
            Finding(
                rule_id=self.id,
                severity=self.severity,
                message="WHERE 없는 DELETE — 테이블 전체가 삭제됩니다.",
                reason="조건이 없는 DELETE는 대상 테이블의 모든 행을 삭제합니다.",
                example="DELETE FROM users",
                fix="DELETE FROM users WHERE id = :id",
                snippet=snippet_of(node, ctx.dialect),
            )
        ]
