"""null-comparison (docs/rules.md v0.6) — CRITICAL.

= NULL / != NULL / <> NULL 비교는 항상 unknown이라 조건이 조용히 거짓이 된다.
UPDATE ... SET a = NULL은 대입(sqlglot이 EQ로 표현)이므로 제외한다.
"""

from __future__ import annotations

from sqlglot import exp, parse_one

from engine import Finding, Rule, RuleContext, snippet_of

_REASON = (
    "SQL에서 NULL과의 =/!= 비교는 참도 거짓도 아닌 unknown이 됩니다. "
    "조건이 조용히 항상 탈락해 결과가 틀립니다. IS [NOT] NULL을 사용해야 합니다."
)
_EXAMPLE = "SELECT * FROM users WHERE deleted_at = NULL"
_FIX = "SELECT * FROM users WHERE deleted_at IS NULL"


class NullComparisonRule(Rule):
    id = "null-comparison"
    severity = "CRITICAL"
    target_nodes = (exp.EQ, exp.NEQ)

    def check(self, node: exp.Expression, ctx: RuleContext) -> list[Finding]:
        # UPDATE SET / ON CONFLICT SET 대입은 비교가 아니다 (false positive 방지)
        parent = node.parent
        if isinstance(parent, exp.Update):
            return []
        if parent is not None and type(parent).__name__ in ("OnConflict", "Set"):
            return []

        left, right = node.this, node.args.get("expression")
        if not isinstance(left, exp.Null) and not isinstance(right, exp.Null):
            return []

        other = left if isinstance(right, exp.Null) else right
        other_sql = (
            other.sql(dialect=ctx.dialect) if isinstance(other, exp.Expression) else "expr"
        )
        is_neq = isinstance(node, exp.NEQ)
        op = "!=" if is_neq else "="
        fixed = f"{other_sql} IS NOT NULL" if is_neq else f"{other_sql} IS NULL"

        # (v0.9) fixSql: 원본 AST 복사 → 새 노드로 교체 → SQL 생성
        fix_sql = self._generate_fix_sql(ctx, node, is_neq)

        return [
            Finding(
                rule_id=self.id,
                severity=self.severity,
                message=f"NULL과 {op} 비교는 항상 unknown입니다 — 조건이 결코 참이 되지 않습니다.",
                reason=_REASON,
                example=_EXAMPLE,
                fix=fixed,
                snippet=snippet_of(node, ctx.dialect),
                fix_sql=fix_sql,
            )
        ]

    def _generate_fix_sql(
        self, ctx: RuleContext, node: exp.Expression, is_neq: bool
    ) -> str | None:
        """원본 AST 복사 후 NULL 비교를 IS [NOT] NULL로 변환.

        에러 발생 시 None 반환 (fixSql 없음).
        """
        try:
            # 원본 AST 복사 (Immutable 원칙)
            root_copy = ctx.root.copy()

            # 복사된 AST에서 같은 위치의 노드를 찾기 위해 순회
            for copied_node in root_copy.find_all(type(node)):
                left, right = copied_node.this, copied_node.args.get("expression")
                if not isinstance(left, exp.Null) and not isinstance(right, exp.Null):
                    continue

                other = left if isinstance(right, exp.Null) else right

                # NULL 비교를 IS [NOT] NULL로 변환
                if is_neq:
                    new_condition = exp.IsNot(this=other.copy(), expression=exp.Null())
                else:
                    new_condition = exp.Is(this=other.copy(), expression=exp.Null())

                # 부모 노드에서 이 노드를 새 노드로 교체
                copied_node.replace(new_condition)

                # 첫 번째 일치하는 노드만 수정 (가장 가까운 노드)
                result = root_copy.sql(dialect=ctx.dialect)
                return result

            return None
        except Exception:
            return None
