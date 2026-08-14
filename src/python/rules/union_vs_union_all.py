"""union-vs-union-all (docs/rules.md v0.6) — INFO.

UNION은 중복 제거를 위해 정렬/해시 비용이 든다. 중복이 없거나 무관하면
UNION ALL이 낫다. 의도적 중복 제거일 수 있으므로 INFO 유지.
EXCEPT / INTERSECT는 대상이 아니다.
"""

from __future__ import annotations

from sqlglot import exp

from engine import Finding, Rule, RuleContext, snippet_of

_REASON = (
    "UNION은 결과 전체에서 중복을 제거하기 위해 정렬 또는 해시 비용이 "
    "듭니다. 두 집합에 중복이 없거나 중복이 무관하다면 UNION ALL이 "
    "불필요한 작업을 줄입니다."
)
_EXAMPLE = "SELECT id FROM archived UNION SELECT id FROM active"
_FIX = "SELECT id FROM archived UNION ALL SELECT id FROM active"


def _is_plain_union(node: exp.Expression) -> bool:
    return isinstance(node, exp.Union) and not isinstance(
        node, (exp.Except, exp.Intersect)
    )


class UnionVsUnionAllRule(Rule):
    id = "union-vs-union-all"
    severity = "INFO"
    target_nodes = (exp.Union,)

    def check(self, node: exp.Expression, ctx: RuleContext) -> list[Finding]:
        if not _is_plain_union(node):
            return []
        if _is_plain_union(node.parent):
            return []  # 체인 루트에서만 검사 (중복 Finding 방지)

        # 체인을 따라 내려가며 DISTINCT UNION 개수를 센다
        count = 0
        cur: exp.Expression | None = node
        while _is_plain_union(cur):
            if cur.args.get("distinct"):
                count += 1
            cur = cur.args.get("this")
        if count == 0:
            return []

        return [
            Finding(
                rule_id=self.id,
                severity=self.severity,
                message=f"UNION이 {count}회 사용되었습니다 — 중복 제거가 필요 없다면 UNION ALL을 고려하세요.",
                reason=_REASON,
                example=_EXAMPLE,
                fix=_FIX,
                snippet=snippet_of(node, ctx.dialect),
            )
        ]
