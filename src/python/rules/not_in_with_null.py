"""not-in-with-null (docs/rules.md v0.6) — WARNING.

NOT IN (서브쿼리)는 서브쿼리 결과에 NULL이 하나라도 있으면 전체 결과가 빈다.
리터럴 목록 NOT IN ('A', 'B')는 안전하므로 탐지하지 않는다.
"""

from __future__ import annotations

from sqlglot import exp

from engine import Finding, Rule, RuleContext, snippet_of

_REASON = (
    "NOT IN은 내부적으로 모든 값과 != 비교를 AND로 묶습니다. 서브쿼리 결과에 "
    "NULL이 하나라도 있으면 전체 조건이 unknown이 되어 결과가 조용히 빕니다. "
    "NOT EXISTS는 NULL의 영향을 받지 않습니다."
)
_EXAMPLE = "SELECT * FROM users WHERE id NOT IN (SELECT user_id FROM banned)"
_FIX = (
    "SELECT * FROM users u "
    "WHERE NOT EXISTS (SELECT 1 FROM banned b WHERE b.user_id = u.id)"
)


class NotInWithNullRule(Rule):
    id = "not-in-with-null"
    severity = "WARNING"
    target_nodes = (exp.Not,)

    def check(self, node: exp.Expression, ctx: RuleContext) -> list[Finding]:
        inner = node.this
        if not isinstance(inner, exp.In):
            return []
        if not inner.args.get("query"):  # 리터럴 목록 NOT IN은 안전
            return []
        return [
            Finding(
                rule_id=self.id,
                severity=self.severity,
                message="NOT IN (서브쿼리)는 서브쿼리에 NULL이 있으면 결과가 통째로 빕니다.",
                reason=_REASON,
                example=_EXAMPLE,
                fix=_FIX,
                snippet=snippet_of(node, ctx.dialect),
            )
        ]
