"""Complexity Metrics (docs/rules.md).

score = joinCount*2 + subqueryDepth*3 + cteCount*1 + tableCount*1
"""

from __future__ import annotations

from sqlglot import exp


def _subquery_depth(root: exp.Expression) -> int:
    """SELECT 노드가 가진 조상 SELECT 수의 최댓값. 루트 SELECT = 0."""
    depth = 0
    for sel in root.find_all(exp.Select):
        d = 0
        parent = sel.parent
        while parent is not None:
            if isinstance(parent, exp.Select):
                d += 1
            parent = parent.parent
        depth = max(depth, d)
    return depth


def compute_metrics(root: exp.Expression) -> dict:
    join_count = sum(1 for _ in root.find_all(exp.Join))
    cte_count = sum(1 for _ in root.find_all(exp.CTE))
    tables = {t.name.lower() for t in root.find_all(exp.Table) if t.name}
    depth = _subquery_depth(root)
    where_predicates = sum(
        1 for w in root.find_all(exp.Where) for _ in w.find_all(exp.Predicate)
    )

    score = join_count * 2 + depth * 3 + cte_count * 1 + len(tables) * 1
    grade = "simple" if score <= 5 else ("moderate" if score <= 15 else "complex")

    return {
        "joinCount": join_count,
        "subqueryDepth": depth,
        "cteCount": cte_count,
        "tableCount": len(tables),
        "wherePredicateCount": where_predicates,
        "complexityScore": score,
        "complexityGrade": grade,
    }
