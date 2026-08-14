"""Analysis Engine (docs/analyzer.md).

책임: 등록된 Rule을 AST에 단일 순회로 적용해 Finding을 수집한다.
원칙 (docs/principles.md):
- AST를 수정하지 않는다 (Immutable)
- 순수 함수 (Stateless) — 외부 I/O, 전역 상태 없음
- Engine 안에 개별 검사 로직(if 나열)을 넣지 않는다 (Rule Driven)
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, replace
from typing import Callable, Iterator, Optional

from sqlglot import exp

from config import DIALECT

_SEVERITY_ORDER = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
_MAX_SNIPPET = 200


@dataclass(frozen=True)
class Finding:
    """Explainability (docs/principles.md): 이유/예시/수정은 필수다."""

    rule_id: str
    severity: str  # "INFO" | "WARNING" | "CRITICAL"
    message: str
    reason: str
    example: str
    fix: str
    snippet: str = ""
    location: Optional[dict] = None  # {"line": int, "col": int} | None
    fix_sql: Optional[str] = None  # (v0.9) 자동 수정 SQL 또는 None

    def to_dict(self) -> dict:
        return {
            "ruleId": self.rule_id,
            "severity": self.severity,
            "message": self.message,
            "reason": self.reason,
            "example": self.example,
            "fix": self.fix,
            "snippet": self.snippet,
            "location": self.location,
            "fixSql": self.fix_sql,
        }


@dataclass(frozen=True)
class RuleContext:
    root: exp.Expression  # 전체 AST (read-only)
    dialect: str = DIALECT
    schema: Optional[dict] = None  # 사용자 제공 스키마 (v0.5)


class Rule(abc.ABC):
    """모든 Rule이 구현해야 하는 Interface (docs/analyzer.md)."""

    id: str
    severity: str
    target_nodes: tuple  # 방문할 AST 노드 타입들

    @abc.abstractmethod
    def check(self, node: exp.Expression, ctx: RuleContext) -> list[Finding]:
        """node를 검사하고 Finding 목록을 반환. AST를 수정하지 않는다."""


def iter_nodes(root: exp.Expression) -> Iterator[exp.Expression]:
    """sqlglot 버전에 의존하지 않는 자체 순회 (읽기 전용)."""
    stack = [root]
    while stack:
        node = stack.pop()
        yield node
        for value in node.args.values():
            items = value if isinstance(value, list) else [value]
            for item in items:
                if isinstance(item, exp.Expression):
                    stack.append(item)


def clause(node: exp.Expression, cls: type) -> Optional[exp.Expression]:
    """직접 자식 절을 타입으로 찾는다. arg 키 이름에 의존하지 않는다.

    sqlglot 버전에 따라 키가 바뀔 수 있어서다 (예: 최신 버전에서
    Select의 'from' 키가 'from_'로 변경됨). 하위 서브쿼리는 탐색하지 않는다.
    """
    for value in node.args.values():
        items = value if isinstance(value, list) else [value]
        for item in items:
            if isinstance(item, cls):
                return item
    return None


def snippet_of(node: exp.Expression, dialect: str = DIALECT) -> str:
    """UI 표시용 SQL 조각. 분석에 사용하지 않는다."""
    try:
        text = " ".join(node.sql(dialect=dialect).split())
    except Exception:
        return ""
    return text[: _MAX_SNIPPET - 1] + "…" if len(text) > _MAX_SNIPPET else text


class AnalysisEngine:
    """Rule Registry를 받아 AST를 1회 순회하며 적용한다."""

    def __init__(self, rules: list[Rule]):
        self._rules = list(rules)

    def run(
        self,
        ast: exp.Expression,
        ctx: Optional[RuleContext] = None,
        locate: Optional[Callable[[exp.Expression], Optional[dict]]] = None,
    ) -> list[Finding]:
        """locate: Position Mapper 콜백 (v0.7, docs/analyzer.md).

        Rule은 위치 관심사를 모른다 — Engine이 Finding 수집 시점에
        해당 노드의 위치를 일괄로 채운다. 매핑 실패(None)면 그대로 둔다
        (snippet 폴백).
        """
        ctx = ctx or RuleContext(root=ast)
        findings: list[Finding] = []
        for node in iter_nodes(ast):
            for rule in self._rules:
                if isinstance(node, rule.target_nodes):
                    for finding in rule.check(node, ctx):
                        if locate is not None and finding.location is None:
                            loc = locate(node)
                            if loc is not None:
                                finding = replace(finding, location=loc)
                        findings.append(finding)
        findings.sort(key=lambda f: _SEVERITY_ORDER.get(f.severity, 9))
        return findings
