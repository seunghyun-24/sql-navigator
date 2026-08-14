"""leading-wildcard-like (docs/rules.md v0.6) — WARNING.

LIKE/ILIKE 패턴이 % 또는 _로 시작하면 B-tree index를 사용할 수 없다.
후행 와일드카드(LIKE 'foo%')는 정상 — 탐지 제외.
"""

from __future__ import annotations

from sqlglot import exp

from engine import Finding, Rule, RuleContext, snippet_of

_REASON = (
    "선행 와일드카드 패턴은 문자열의 시작을 알 수 없어 일반 B-tree index를 "
    "사용할 수 없습니다 — Full Scan 가능성이 있습니다."
)
_EXAMPLE = "SELECT * FROM users WHERE email LIKE '%@gmail.com'"
_FIX = (
    "후행 와일드카드로 재구성하거나(LIKE 'foo%'), "
    "pg_trgm 등 전용 index를 고려하세요."
)


class LeadingWildcardLikeRule(Rule):
    id = "leading-wildcard-like"
    severity = "WARNING"
    target_nodes = (exp.Like, exp.ILike)

    def check(self, node: exp.Expression, ctx: RuleContext) -> list[Finding]:
        pattern = node.args.get("expression")
        if not isinstance(pattern, exp.Literal) or not pattern.is_string:
            return []  # 패턴이 리터럴이 아니면 단정할 수 없다 (Static Only)
        text = str(pattern.this)
        if not text.startswith("%") and not text.startswith("_"):
            return []
        return [
            Finding(
                rule_id=self.id,
                severity=self.severity,
                message=f"선행 와일드카드 패턴({text!r})은 index를 사용할 수 없습니다.",
                reason=_REASON,
                example=_EXAMPLE,
                fix=_FIX,
                snippet=snippet_of(node, ctx.dialect),
            )
        ]
