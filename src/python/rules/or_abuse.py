"""or-abuse (docs/rules.md) — WARNING.

같은 컬럼에 대한 동등 비교 OR 체인이 THRESHOLD개 이상이면 IN으로 제안한다.
"""

from __future__ import annotations

from sqlglot import exp

from engine import Finding, Rule, RuleContext, snippet_of

THRESHOLD = 3


class OrAbuseRule(Rule):
    id = "or-abuse"
    severity = "WARNING"
    target_nodes = (exp.Or,)

    def check(self, node: exp.Expression, ctx: RuleContext) -> list[Finding]:
        # OR 체인의 루트에서만 검사 (중복 Finding 방지)
        if isinstance(node.parent, exp.Or):
            return []

        by_column: dict[str, list[exp.Expression]] = {}
        for operand in node.flatten():
            if not isinstance(operand, exp.EQ):
                continue
            left, right = operand.this, operand.expression
            if isinstance(left, exp.Column) and not isinstance(right, exp.Column):
                col, value = left, right
            elif isinstance(right, exp.Column) and not isinstance(left, exp.Column):
                col, value = right, left
            else:
                continue
            key = col.sql(dialect=ctx.dialect).lower()
            by_column.setdefault(key, []).append(value)

        findings = []
        for column, values in by_column.items():
            if len(values) < THRESHOLD:
                continue
            in_list = ", ".join(v.sql(dialect=ctx.dialect) for v in values)
            fix_sql = self._generate_fix_sql(ctx, node, by_column)
            findings.append(
                Finding(
                    rule_id=self.id,
                    severity=self.severity,
                    message=f"같은 컬럼({column})에 OR 동등 비교가 {len(values)}개 있습니다.",
                    reason="같은 컬럼에 대한 OR 나열은 index 활용을 방해하고 가독성을 해칩니다.",
                    example=f"WHERE {column} = … OR {column} = … OR {column} = …",
                    fix=f"WHERE {column} IN ({in_list})",
                    snippet=snippet_of(node, ctx.dialect),
                    fix_sql=fix_sql,
                )
            )
        return findings

    def _generate_fix_sql(
        self, ctx: RuleContext, node: exp.Expression, by_column: dict[str, list[exp.Expression]]
    ) -> str | None:
        """원본 AST 복사 후 OR 체인을 IN 조건으로 변환.

        THRESHOLD개 이상의 같은 컬럼 비교를 IN으로 변환한다.
        에러 발생 시 None 반환 (fixSql 없음).
        """
        try:
            root_copy = ctx.root.copy()

            # 복사된 AST에서 같은 위치의 OR 노드 찾기
            for copied_or in root_copy.find_all(exp.Or):
                if isinstance(copied_or.parent, exp.Or):
                    continue

                # 이 OR 노드에서 컬럼별 값을 수집
                local_by_column: dict[str, list[exp.Expression]] = {}
                for operand in copied_or.flatten():
                    if not isinstance(operand, exp.EQ):
                        continue
                    left, right = operand.this, operand.args.get("expression")
                    if isinstance(left, exp.Column) and not isinstance(right, exp.Column):
                        col, value = left, right
                    elif isinstance(right, exp.Column) and not isinstance(left, exp.Column):
                        col, value = right, left
                    else:
                        continue
                    key = col.sql(dialect=ctx.dialect).lower()
                    local_by_column.setdefault(key, []).append((col.copy(), value.copy()))

                # THRESHOLD 이상인 컬럼이 있는지 확인
                has_threshold = any(len(v) >= THRESHOLD for v in local_by_column.values())
                if not has_threshold:
                    continue

                # 모든 OR 조건을 IN으로 변환
                and_conditions = []
                for col_sql, col_value_pairs in local_by_column.items():
                    if len(col_value_pairs) < THRESHOLD:
                        # THRESHOLD 미만인 컬럼은 원래 OR 유지
                        col, _ = col_value_pairs[0]
                        original_eqs = [
                            exp.EQ(this=col.copy(), expression=val.copy())
                            for col, val in col_value_pairs
                        ]
                        for i, eq in enumerate(original_eqs):
                            if i == 0:
                                cond = eq
                            else:
                                cond = exp.Or(this=cond, expression=eq)
                        and_conditions.append(cond)
                    else:
                        # THRESHOLD 이상인 컬럼은 IN으로 변환
                        col, _ = col_value_pairs[0]
                        values = [val.copy() for _, val in col_value_pairs]
                        in_cond = exp.In(this=col.copy(), expressions=values)
                        and_conditions.append(in_cond)

                # 여러 IN 조건을 AND로 연결
                if len(and_conditions) == 1:
                    new_condition = and_conditions[0]
                else:
                    new_condition = and_conditions[0]
                    for cond in and_conditions[1:]:
                        new_condition = exp.And(this=new_condition, expression=cond)

                copied_or.replace(new_condition)
                result = root_copy.sql(dialect=ctx.dialect)
                return result

            return None
        except Exception:
            return None
