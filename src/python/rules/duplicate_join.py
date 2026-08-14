"""duplicate-join (docs/rules.md) — WARNING.

같은 테이블을 같은 ON 조건으로 2회 이상 JOIN하면 탐지한다.
alias만 다른 경우를 잡기 위해 ON 조건의 alias를 테이블명으로 치환한
사본(새 AST)으로 비교한다 — 원본 AST는 수정하지 않는다 (docs/principles.md).
self-join(조건이 다른 동일 테이블 JOIN)은 정상이므로 제외.
"""

from __future__ import annotations

from sqlglot import exp

from engine import Finding, Rule, RuleContext, snippet_of


def _canonical_on(join: exp.Join, table: exp.Table, dialect: str) -> str | None:
    on = join.args.get("on")
    if on is None:
        return None
    on_copy = on.copy()  # 원본 보존
    alias = table.alias
    if alias:
        for col in on_copy.find_all(exp.Column):
            if (col.table or "").lower() == alias.lower():
                col.set("table", exp.to_identifier(table.name))
    return on_copy.sql(dialect=dialect).lower()


class DuplicateJoinRule(Rule):
    id = "duplicate-join"
    severity = "WARNING"
    target_nodes = (exp.Select,)

    def check(self, node: exp.Expression, ctx: RuleContext) -> list[Finding]:
        seen: set[tuple[str, str]] = set()
        findings = []
        for join in node.args.get("joins") or []:
            table = join.this
            if not isinstance(table, exp.Table):
                continue
            on_key = _canonical_on(join, table, ctx.dialect)
            if on_key is None:  # ON 없는 JOIN은 cartesian-product 담당
                continue
            key = (table.name.lower(), on_key)
            if key in seen:
                findings.append(
                    Finding(
                        rule_id=self.id,
                        severity=self.severity,
                        message=f"테이블 {table.name}을(를) 같은 조건으로 중복 JOIN합니다.",
                        reason="같은 테이블·같은 조건의 JOIN은 불필요한 중복 작업이며, 대개 복사-붙여넣기 실수입니다.",
                        example="JOIN customers c ON o.customer_id = c.id JOIN customers c2 ON o.customer_id = c2.id",
                        fix="중복 JOIN을 제거하고 기존 alias(c)를 재사용하세요.",
                        snippet=snippet_of(join, ctx.dialect),
                    )
                )
            else:
                seen.add(key)
        return findings
