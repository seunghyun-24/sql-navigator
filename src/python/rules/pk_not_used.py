"""pk-not-used (docs/rules.md) — WARNING. Schema Context 필요 (docs/analyzer.md).

WHERE/JOIN 조건이 해당 테이블의 PK·index 컬럼을 하나도 사용하지 않으면 경고.
스키마가 없거나, 스키마에 그 테이블의 PK/index 정보가 없으면 skip —
근거 없이 단정하지 않는다 (docs/principles.md Static Only).
"""

from __future__ import annotations

from sqlglot import exp

from engine import Finding, Rule, RuleContext, clause, snippet_of
from scope import alias_table_map, resolve_column

_REASON = (
    "조건절이 PK나 index 컬럼을 타지 못하면 Full Scan 가능성이 있습니다. "
    "제공된 스키마 기준의 판단이며, 실제 실행 계획은 DB 통계에 따라 다를 수 있습니다."
)
_EXAMPLE = "SELECT * FROM users WHERE nickname = 'kim'  -- nickname에 index 없음"
_FIX = "SELECT * FROM users WHERE id = :id  -- PK 사용, 또는 해당 컬럼에 index 생성 검토"


class PkNotUsedRule(Rule):
    id = "pk-not-used"
    severity = "WARNING"
    target_nodes = (exp.Select,)

    def check(self, node: exp.Expression, ctx: RuleContext) -> list[Finding]:
        if not ctx.schema:
            return []  # 스키마 없으면 skip (docs/rules.md)
        schema_tables = ctx.schema.get("tables") or {}
        mapping = alias_table_map(node)
        if not mapping:
            return []

        # 조건 노드: 이 SELECT의 WHERE + 각 JOIN의 ON
        conditions: list[exp.Expression] = []
        where = clause(node, exp.Where)
        if where is not None:
            conditions.append(where)
        for join in node.args.get("joins") or []:
            if isinstance(join, exp.Join) and join.args.get("on") is not None:
                conditions.append(join.args["on"])
        if not conditions:
            return []  # 조건 자체가 없으면 select-without-where 영역 — 중복 경고 방지

        # 서브쿼리 내부 컬럼은 제외 — 그 서브쿼리 Select가 자체적으로 검사한다
        referenced: dict[str, set[str]] = {}
        for cond in conditions:
            for col in cond.find_all(exp.Column):
                nearest = col.find_ancestor(exp.Select)
                if nearest is not None and nearest is not node:
                    continue
                resolved = resolve_column(col, mapping)
                if resolved and resolved[0]:
                    referenced.setdefault(resolved[0], set()).add(resolved[1])

        findings: list[Finding] = []
        for table in dict.fromkeys(mapping.values()):  # 테이블 단위 1회 (self-join 중복 방지)
            info = schema_tables.get(table)
            if not info:
                continue  # 스키마에 없는 테이블 — 단정 불가
            indexed = set(info.get("pk") or [])
            for idx_cols in info.get("indexes") or []:
                indexed.update(idx_cols)
            if not indexed:
                continue  # PK/index 정보 자체가 없음 — 단정 불가
            if referenced.get(table, set()) & indexed:
                continue  # index 컬럼 사용 중 — 정상
            keys = ", ".join(sorted(indexed))
            findings.append(
                Finding(
                    rule_id=self.id,
                    severity=self.severity,
                    message=(
                        f"{table}: WHERE/JOIN 조건이 PK·index 컬럼({keys})을 사용하지 않습니다."
                    ),
                    reason=_REASON,
                    example=_EXAMPLE,
                    fix=_FIX,
                    snippet=snippet_of(node, ctx.dialect),
                )
            )
        return findings
