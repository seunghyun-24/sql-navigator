"""cartesian-product (docs/rules.md) — CRITICAL / 명시적 CROSS JOIN은 WARNING."""

from __future__ import annotations

from sqlglot import exp

from engine import Finding, Rule, RuleContext, snippet_of

_REASON = "JOIN 조건이 없으면 두 테이블 행 수의 곱만큼 결과가 폭발합니다."
_EXAMPLE = "SELECT * FROM orders, customers"
_FIX = "SELECT * FROM orders o JOIN customers c ON o.customer_id = c.id"


class CartesianProductRule(Rule):
    id = "cartesian-product"
    severity = "CRITICAL"
    # From: 구버전 sqlglot의 comma join(expressions 복수) 대응
    target_nodes = (exp.Join, exp.From)

    def check(self, node: exp.Expression, ctx: RuleContext) -> list[Finding]:
        if isinstance(node, exp.From):
            return self._check_from(node, ctx)
        return self._check_join(node, ctx)

    def _check_from(self, node: exp.From, ctx: RuleContext) -> list[Finding]:
        exprs = node.args.get("expressions") or []
        if len(exprs) > 1:
            return [self._finding(node, ctx, explicit=False)]
        return []

    def _check_join(self, node: exp.Join, ctx: RuleContext) -> list[Finding]:
        if node.args.get("on") or node.args.get("using"):
            return []
        if node.args.get("method"):  # NATURAL JOIN — 암묵적 조건 존재
            return []
        kind = str(node.args.get("kind") or "").upper()
        if kind in ("SEMI", "ANTI"):
            return []
        return [self._finding(node, ctx, explicit=(kind == "CROSS"))]

    def _finding(self, node: exp.Expression, ctx: RuleContext, explicit: bool) -> Finding:
        if explicit:
            message = "명시적 CROSS JOIN입니다. 의도한 것인지 확인하세요."
            severity = "WARNING"
        else:
            message = "JOIN 조건이 없어 Cartesian Product가 발생합니다."
            severity = "CRITICAL"
        return Finding(
            rule_id=self.id,
            severity=severity,
            message=message,
            reason=_REASON,
            example=_EXAMPLE,
            fix=_FIX,
            snippet=snippet_of(node, ctx.dialect),
        )
