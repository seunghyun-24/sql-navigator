"""scalar-subquery-in-select (docs/rules.md v0.6) — WARNING.

SELECT 절의 상관(correlated) 스칼라 서브쿼리는 외부 쿼리 행마다 실행될 수
있다 (N+1 유사). 비상관 서브쿼리는 1회 실행이므로 탐지하지 않는다.
상관 여부를 단정할 수 없으면 침묵한다 (Static Only).
"""

from __future__ import annotations

from sqlglot import exp

from engine import Finding, Rule, RuleContext, snippet_of
from scope import alias_table_map

_REASON = (
    "SELECT 절의 상관 서브쿼리는 외부 쿼리의 행 수만큼 반복 실행될 수 "
    "있습니다. JOIN으로 재작성하면 한 번의 조인으로 같은 결과를 얻습니다."
)
_EXAMPLE = (
    "SELECT o.id, (SELECT c.name FROM customers c WHERE c.id = o.customer_id) "
    "FROM orders o"
)
_FIX = "SELECT o.id, c.name FROM orders o JOIN customers c ON c.id = o.customer_id"


class ScalarSubqueryInSelectRule(Rule):
    id = "scalar-subquery-in-select"
    severity = "WARNING"
    target_nodes = (exp.Select,)

    def check(self, node: exp.Expression, ctx: RuleContext) -> list[Finding]:
        outer = alias_table_map(node)
        if not outer:
            return []
        findings: list[Finding] = []
        for proj in node.args.get("expressions") or []:
            sub = proj.this if isinstance(proj, exp.Alias) else proj
            if not isinstance(sub, exp.Subquery):
                continue
            if self._is_correlated(sub, outer):
                findings.append(
                    Finding(
                        rule_id=self.id,
                        severity=self.severity,
                        message="SELECT 절의 상관 서브쿼리는 행마다 실행될 수 있습니다.",
                        reason=_REASON,
                        example=_EXAMPLE,
                        fix=_FIX,
                        snippet=snippet_of(sub, ctx.dialect),
                    )
                )
        return findings

    @staticmethod
    def _is_correlated(sub: exp.Subquery, outer: dict[str, str]) -> bool:
        """서브쿼리 내부 컬럼이 외부 relation을 참조하면 상관이다."""
        inner_names: set[str] = set()
        for table in sub.find_all(exp.Table):
            if table.name:
                inner_names.add(table.name.lower())
            if table.alias:
                inner_names.add(table.alias.lower())
        for col in sub.find_all(exp.Column):
            qualifier = col.table
            if not qualifier:
                continue  # 비한정 컬럼은 단정 불가 — 침묵 (Static Only)
            q = qualifier.lower()
            if q not in inner_names and q in outer:
                return True
        return False
