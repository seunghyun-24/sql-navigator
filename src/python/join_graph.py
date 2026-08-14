"""Join Graph (docs/roadmap.md v0.3).

AST -> 테이블 관계 그래프 JSON. Rule이 아니라 시각화용 분석 모듈이다.
AST를 수정하지 않는다. 순수 함수. (docs/principles.md)

출력 계약:
  nodes: [{ id, table, alias, kind }]        kind: "table" | "subquery" | "cte"
  edges: [{ source, target, joinType, condition, cartesian }]
"""

from __future__ import annotations

from typing import Optional

from sqlglot import exp

from config import DIALECT
from engine import clause


def _join_type(join: exp.Join) -> str:
    parts = [
        str(join.args.get("method") or ""),
        str(join.args.get("side") or ""),
        str(join.args.get("kind") or ""),
    ]
    text = " ".join(p for p in parts if p).strip().upper()
    return text or "INNER"


class _GraphBuilder:
    def __init__(self, root: exp.Expression, dialect: str = DIALECT):
        self.root = root
        self.dialect = dialect
        self.nodes: dict[str, dict] = {}
        self.edges: list[dict] = []
        self.cte_names = {c.alias.lower() for c in root.find_all(exp.CTE) if c.alias}

    def build(self) -> dict:
        for select in self.root.find_all(exp.Select):
            self._process_select(select)
        return {"nodes": list(self.nodes.values()), "edges": self.edges}

    # -- nodes ---------------------------------------------------------------

    def _add_table(self, table: exp.Table) -> str:
        alias = table.alias or None
        name = table.name
        node_id = alias or name
        kind = "cte" if name.lower() in self.cte_names else "table"
        self.nodes.setdefault(
            node_id, {"id": node_id, "table": name, "alias": alias, "kind": kind}
        )
        return node_id

    def _add_relation(self, item: exp.Expression) -> Optional[str]:
        """FROM/JOIN 대상 -> 노드 id. 테이블/서브쿼리 외에는 무시."""
        if isinstance(item, exp.Table):
            return self._add_table(item)
        if isinstance(item, exp.Subquery):
            node_id = item.alias or "(subquery)"
            self.nodes.setdefault(
                node_id, {"id": node_id, "table": None, "alias": item.alias or None, "kind": "subquery"}
            )
            return node_id
        return None

    # -- edges ---------------------------------------------------------------

    def _process_select(self, select: exp.Select) -> None:
        base_id = self._base_relation(select)
        prev_id = base_id
        for join in select.args.get("joins") or []:
            if not isinstance(join, exp.Join):
                continue
            target_id = self._add_relation(join.this)
            if target_id is None:
                continue
            self._add_edge(select, join, target_id, prev_id)
            prev_id = target_id

    def _base_relation(self, select: exp.Select) -> Optional[str]:
        from_clause = clause(select, exp.From)
        if from_clause is None:
            return None
        items = []
        if from_clause.args.get("this") is not None:
            items.append(from_clause.args["this"])
        items.extend(from_clause.args.get("expressions") or [])  # 구버전 comma join
        base_id = None
        for item in items:
            node_id = self._add_relation(item)
            if base_id is None:
                base_id = node_id
        return base_id

    def _add_edge(
        self,
        select: exp.Select,
        join: exp.Join,
        target_id: str,
        prev_id: Optional[str],
    ) -> None:
        on = join.args.get("on")
        using = join.args.get("using")
        natural = bool(join.args.get("method"))

        if on is not None:
            source_id = self._source_from_on(on, target_id) or prev_id
            condition = on.sql(dialect=self.dialect)
            cartesian = False
        elif using:
            source_id = prev_id
            cols = ", ".join(u.sql(dialect=self.dialect) for u in using)
            condition = f"USING ({cols})"
            cartesian = False
        elif natural:
            source_id = prev_id
            condition = "NATURAL"
            cartesian = False
        else:
            source_id = prev_id
            condition = ""
            cartesian = True  # 조건 없는 JOIN — Cartesian Product

        if source_id is None or source_id == target_id:
            return
        self.edges.append(
            {
                "source": source_id,
                "target": target_id,
                "joinType": _join_type(join),
                "condition": condition,
                "cartesian": cartesian,
            }
        )

    def _source_from_on(self, on: exp.Expression, target_id: str) -> Optional[str]:
        """ON 조건의 컬럼 qualifier로 반대편 노드를 찾는다."""
        qualifiers = []
        for col in on.find_all(exp.Column):
            q = col.table
            if q and q not in qualifiers:
                qualifiers.append(q)
        others = [q for q in qualifiers if q != target_id and q in self.nodes]
        return others[0] if others else None


def build_join_graph(root: exp.Expression, dialect: str = DIALECT) -> dict:
    return _GraphBuilder(root, dialect).build()
