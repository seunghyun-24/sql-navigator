"""offset-pagination (docs/rules.md v0.6) — INFO.

큰 OFFSET은 그 앞의 행을 모두 읽고 버린다 — 페이지가 깊을수록 느려진다.
임계값(기본 1000) 이상의 리터럴 OFFSET만 탐지한다.
"""

from __future__ import annotations

from sqlglot import exp

from engine import Finding, Rule, RuleContext, snippet_of

THRESHOLD = 1000

_REASON = (
    "OFFSET N은 앞의 N행을 전부 읽은 뒤 버립니다. 페이지가 깊어질수록 "
    "선형으로 느려집니다. 마지막 키 기준의 keyset pagination은 깊이와 "
    "무관하게 일정한 비용을 유지합니다."
)
_EXAMPLE = "SELECT * FROM orders ORDER BY id LIMIT 20 OFFSET 100000"
_FIX = "SELECT * FROM orders WHERE id > :last_id ORDER BY id LIMIT 20"


class OffsetPaginationRule(Rule):
    id = "offset-pagination"
    severity = "INFO"
    target_nodes = (exp.Offset,)

    def check(self, node: exp.Expression, ctx: RuleContext) -> list[Finding]:
        expr = node.args.get("expression")
        if not isinstance(expr, exp.Literal) or not expr.is_number:
            return []  # 파라미터/식 OFFSET은 단정할 수 없다 (Static Only)
        try:
            value = int(float(str(expr.this)))
        except (TypeError, ValueError):
            return []
        if value < THRESHOLD:
            return []
        return [
            Finding(
                rule_id=self.id,
                severity=self.severity,
                message=f"OFFSET {value} — 앞의 {value}행을 읽고 버립니다. keyset pagination을 고려하세요.",
                reason=_REASON,
                example=_EXAMPLE,
                fix=_FIX,
                snippet=snippet_of(node, ctx.dialect),
            )
        ]
