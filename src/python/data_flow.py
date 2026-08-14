"""Query Flow / Data Flow (docs/roadmap.md v0.4).

AST -> 쿼리 실행 흐름의 논리적 재구성(DAG) + 컬럼 lineage.
"사람이 이해하기 쉬운 Explain Plan" — DB 실행 계획이 아니라 논리 순서다:
FROM -> JOIN -> WHERE -> GROUP BY -> HAVING -> SELECT -> DISTINCT -> ORDER BY -> LIMIT

원칙 (docs/principles.md): 순수 함수, AST 수정 금지, Static Only.
lineage는 schema 없이 alias 해석만으로 판단 가능한 수준까지만 말한다
(sqlglot.lineage 모듈은 schema context가 필요해 v0.5에서 검토).

출력 계약:
  steps:   [{ id, kind, label, detail, scope, cartesian }]
           kind: "source" | "join" | "where" | "group" | "having"
               | "select" | "distinct" | "order" | "limit"
  edges:   [{ source, target }]
  lineage: [{ output, expression, sources: ["orders.customer_id", ...] }]
"""

from __future__ import annotations

from typing import Optional

from sqlglot import exp

from config import DIALECT
from engine import clause

_MAX_DETAIL = 100


def _short(node: exp.Expression, dialect: str) -> str:
    try:
        text = " ".join(node.sql(dialect=dialect).split())
    except Exception:
        return ""
    return text[: _MAX_DETAIL - 1] + "…" if len(text) > _MAX_DETAIL else text


def _join_type(join: exp.Join) -> str:
    parts = [
        str(join.args.get("method") or ""),
        str(join.args.get("side") or ""),
        str(join.args.get("kind") or ""),
    ]
    text = " ".join(p for p in parts if p).strip().upper()
    return text or "INNER"


class _FlowBuilder:
    """빌드 1회용. build_data_flow 호출마다 새로 생성 — 전역 상태 없음."""

    def __init__(self, root: exp.Expression, dialect: str = DIALECT):
        self.root = root
        self.dialect = dialect
        self.steps: list[dict] = []
        self.edges: list[dict] = []
        self._cte_final: dict[str, str] = {}  # cte 이름 -> 해당 flow의 마지막 step id

    # -- 공통 ------------------------------------------------------------------

    def _step(
        self,
        kind: str,
        label: str,
        detail: str = "",
        scope: str = "main",
        cartesian: bool = False,
    ) -> str:
        sid = f"n{len(self.steps)}"
        self.steps.append(
            {
                "id": sid,
                "kind": kind,
                "label": label,
                "detail": detail,
                "scope": scope,
                "cartesian": cartesian,
            }
        )
        return sid

    def _edge(self, source: Optional[str], target: str) -> None:
        if source is not None and source != target:
            self.edges.append({"source": source, "target": target})

    # -- relation (FROM/JOIN 대상) ---------------------------------------------

    def _relation_step(self, item: exp.Expression, scope: str) -> Optional[str]:
        if isinstance(item, exp.Table):
            name = item.name
            if not name:
                return None
            alias = item.alias
            label = f"FROM {name}" + (f" {alias}" if alias and alias != name else "")
            if name.lower() in self._cte_final:
                sid = self._step("source", label, detail="CTE", scope=scope)
                self._edge(self._cte_final[name.lower()], sid)
            else:
                sid = self._step("source", label, scope=scope)
            return sid
        if isinstance(item, exp.Subquery) and isinstance(item.this, exp.Select):
            alias = item.alias or "(subquery)"
            inner_final = self._select_flow(item.this, scope=f"sub:{alias}")
            sid = self._step("source", f"FROM ({alias})", detail="서브쿼리", scope=scope)
            self._edge(inner_final, sid)
            return sid
        return None

    # -- SELECT 1개 scope의 논리 파이프라인 --------------------------------------

    def _select_flow(self, select: exp.Select, scope: str) -> Optional[str]:
        chain: Optional[str] = None

        # FROM — 첫 relation이 파이프라인의 시작
        from_clause = clause(select, exp.From)
        relations: list[exp.Expression] = []
        if from_clause is not None:
            if from_clause.args.get("this") is not None:
                relations.append(from_clause.args["this"])
            relations.extend(from_clause.args.get("expressions") or [])  # 구버전 comma join

        for i, item in enumerate(relations):
            sid = self._relation_step(item, scope)
            if sid is None:
                continue
            if i == 0:
                chain = sid
            else:  # FROM a, b — 조건 없는 곱
                jid = self._step("join", "CROSS JOIN", scope=scope, cartesian=True)
                self._edge(chain, jid)
                self._edge(sid, jid)
                chain = jid

        # JOIN — 선언 순서 = 논리 순서
        for join in select.args.get("joins") or []:
            if not isinstance(join, exp.Join):
                continue
            rel_id = self._relation_step(join.this, scope)
            if rel_id is None:
                continue
            on = join.args.get("on")
            using = join.args.get("using")
            natural = bool(join.args.get("method"))
            if on is not None:
                detail, cartesian = _short(on, self.dialect), False
            elif using:
                cols = ", ".join(_short(u, self.dialect) for u in using)
                detail, cartesian = f"USING ({cols})", False
            elif natural:
                detail, cartesian = "NATURAL", False
            else:
                detail, cartesian = "", True
            jid = self._step(
                "join", f"{_join_type(join)} JOIN".replace("INNER JOIN", "JOIN"),
                detail=detail, scope=scope, cartesian=cartesian,
            )
            self._edge(chain, jid)
            self._edge(rel_id, jid)
            chain = jid

        # WHERE -> GROUP BY -> HAVING
        where = clause(select, exp.Where)
        if where is not None:
            sid = self._step("where", "WHERE", detail=_short(where.this, self.dialect), scope=scope)
            self._edge(chain, sid)
            chain = sid
        group = clause(select, exp.Group)
        if group is not None:
            cols = ", ".join(_short(e, self.dialect) for e in group.expressions)
            sid = self._step("group", "GROUP BY", detail=cols, scope=scope)
            self._edge(chain, sid)
            chain = sid
        having = clause(select, exp.Having)
        if having is not None:
            sid = self._step("having", "HAVING", detail=_short(having.this, self.dialect), scope=scope)
            self._edge(chain, sid)
            chain = sid

        # SELECT (projection) -> DISTINCT -> ORDER BY -> LIMIT
        projections = ", ".join(_short(e, self.dialect) for e in select.expressions)
        sid = self._step("select", "SELECT", detail=projections, scope=scope)
        self._edge(chain, sid)
        chain = sid
        if select.args.get("distinct"):
            sid = self._step("distinct", "DISTINCT", scope=scope)
            self._edge(chain, sid)
            chain = sid
        order = clause(select, exp.Order)
        if order is not None:
            cols = ", ".join(_short(e, self.dialect) for e in order.expressions)
            sid = self._step("order", "ORDER BY", detail=cols, scope=scope)
            self._edge(chain, sid)
            chain = sid
        limit = clause(select, exp.Limit)
        if limit is not None:
            sid = self._step(
                "limit", "LIMIT",
                detail=_short(limit.expression, self.dialect) if limit.expression is not None else "",
                scope=scope,
            )
            self._edge(chain, sid)
            chain = sid
        return chain

    # -- lineage (최상위 SELECT만, alias 해석 수준) -------------------------------

    def _lineage(self, select: exp.Select) -> list[dict]:
        # scope의 alias -> 표시용 relation 이름
        rel_names: dict[str, str] = {}
        from_clause = clause(select, exp.From)
        items: list[exp.Expression] = []
        if from_clause is not None:
            if from_clause.args.get("this") is not None:
                items.append(from_clause.args["this"])
            items.extend(from_clause.args.get("expressions") or [])
        for join in select.args.get("joins") or []:
            if isinstance(join, exp.Join):
                items.append(join.this)
        for item in items:
            if isinstance(item, exp.Table) and item.name:
                rel_names[(item.alias or item.name).lower()] = item.name
            elif isinstance(item, exp.Subquery) and item.alias:
                rel_names[item.alias.lower()] = item.alias

        def resolve(col: exp.Column) -> str:
            q = col.table
            if q:
                return f"{rel_names.get(q.lower(), q)}.{col.name}"
            if len(rel_names) == 1:  # relation이 하나뿐이면 확정 가능
                return f"{next(iter(rel_names.values()))}.{col.name}"
            return f"?.{col.name}"  # schema 없이는 단정하지 않는다 (Static Only)

        lineage: list[dict] = []
        for e in select.expressions:
            if isinstance(e, exp.Star):
                lineage.append(
                    {
                        "output": "*",
                        "expression": "*",
                        "sources": [f"{name}.*" for name in dict.fromkeys(rel_names.values())],
                    }
                )
                continue
            expr = e.this if isinstance(e, exp.Alias) else e
            output = e.alias_or_name or _short(e, self.dialect)
            sources: list[str] = []
            for col in expr.find_all(exp.Column):
                s = resolve(col)
                if s not in sources:
                    sources.append(s)
            lineage.append(
                {"output": output, "expression": _short(expr, self.dialect), "sources": sources}
            )
        return lineage

    # -- entry ------------------------------------------------------------------

    def build(self) -> dict:
        if not isinstance(self.root, exp.Select):
            # UNION/DML 등은 v0.4 범위 밖 — 빈 flow (UI는 "표시할 흐름 없음"으로 처리)
            return {"steps": [], "edges": [], "lineage": []}

        # arg 키 이름("with")은 sqlglot 버전에 따라 바뀔 수 있다 — 타입으로 찾는다
        with_clause = clause(self.root, exp.With)
        if isinstance(with_clause, exp.With):
            for cte in with_clause.expressions:
                if isinstance(cte, exp.CTE) and isinstance(cte.this, exp.Select) and cte.alias:
                    final = self._select_flow(cte.this, scope=f"cte:{cte.alias}")
                    if final is not None:
                        self._cte_final[cte.alias.lower()] = final

        self._select_flow(self.root, scope="main")
        return {"steps": self.steps, "edges": self.edges, "lineage": self._lineage(self.root)}


def build_data_flow(root: exp.Expression, dialect: str = DIALECT) -> dict:
    """AST -> DataFlow(JSON 직렬화 가능 dict). AST를 수정하지 않는다."""
    return _FlowBuilder(root, dialect).build()
