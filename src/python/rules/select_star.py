"""select-star (docs/rules.md) — INFO.

count(*) 같은 함수 내부의 *는 정상이므로 projection 위치의 *만 탐지한다.
"""

from __future__ import annotations

from sqlglot import exp

from engine import Finding, Rule, RuleContext, snippet_of


def _is_star(e: exp.Expression) -> bool:
    if isinstance(e, exp.Star):
        return True
    return isinstance(e, exp.Column) and isinstance(e.this, exp.Star)  # t.*


class SelectStarRule(Rule):
    id = "select-star"
    severity = "INFO"
    target_nodes = (exp.Select,)

    def check(self, node: exp.Expression, ctx: RuleContext) -> list[Finding]:
        if not any(_is_star(e) for e in node.expressions):
            return []
        return [
            Finding(
                rule_id=self.id,
                severity=self.severity,
                message="SELECT * 를 사용합니다.",
                reason="불필요한 컬럼까지 전송하고, 테이블 스키마 변경에 취약합니다.",
                example="SELECT * FROM orders",
                fix="SELECT id, amount, created_at FROM orders",
                snippet=snippet_of(node, ctx.dialect),
            )
        ]
