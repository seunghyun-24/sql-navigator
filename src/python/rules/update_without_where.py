"""update-without-where (docs/rules.md) — CRITICAL."""

from __future__ import annotations

from sqlglot import exp

from engine import Finding, Rule, RuleContext, snippet_of


class UpdateWithoutWhereRule(Rule):
    id = "update-without-where"
    severity = "CRITICAL"
    target_nodes = (exp.Update,)

    def check(self, node: exp.Expression, ctx: RuleContext) -> list[Finding]:
        if node.args.get("where"):
            return []
        return [
            Finding(
                rule_id=self.id,
                severity=self.severity,
                message="WHERE 없는 UPDATE — 테이블 전체가 갱신됩니다.",
                reason="조건이 없는 UPDATE는 대상 테이블의 모든 행을 갱신합니다.",
                example="UPDATE users SET status = 'inactive'",
                fix="UPDATE users SET status = 'inactive' WHERE last_login < :cutoff",
                snippet=snippet_of(node, ctx.dialect),
            )
        ]
