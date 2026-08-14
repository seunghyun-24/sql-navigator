"""SQL Diff (docs/analyzer.md v0.8) — Analysis Layer의 별도 진입점.

두 SQL을 AST 수준에서 비교한다 (sqlglot.diff 위임). 문자열 diff 금지.
양쪽을 각각 parse -> analyze 하여 metrics / warnings 요약을 함께 반환한다.

원칙 (docs/principles.md):
- 순수 함수 — 같은 입력이면 같은 출력
- AST 수정 금지 — sqlglot.diff에는 복사본을 넘긴다
- 반환은 직렬화 가능한 JSON 모델뿐 (Bridge 계약)
"""

from __future__ import annotations

from typing import Optional

import sqlglot
from sqlglot import exp

from engine import AnalysisEngine, Finding, RuleContext, snippet_of
from metrics import compute_metrics
from parser import parse
from rules import ALL_RULES

_MAX_CHANGES = 100


def _snip(node) -> tuple[str, str]:
    if isinstance(node, exp.Expression):
        return snippet_of(node), type(node).__name__
    return "", ""


def _change(op) -> Optional[dict]:
    """sqlglot edit op -> 직렬화 가능한 변경 항목. Keep은 None."""
    name = type(op).__name__
    if name == "Keep":
        return None
    if name == "Update":
        before_sql, kind = _snip(getattr(op, "source", None))
        after_sql, _ = _snip(getattr(op, "target", None))
        return {"op": "update", "kind": kind, "before": before_sql, "after": after_sql}

    expr = getattr(op, "expression", None)
    if expr is None:
        expr = getattr(op, "source", None) or getattr(op, "target", None)
    sql, kind = _snip(expr)
    op_key = name.lower()
    return {
        "op": op_key,
        "kind": kind,
        "before": sql if op_key == "remove" else "",
        "after": sql if op_key in ("insert", "move") else "",
    }


def _warning_summary(findings: list[Finding]) -> tuple[dict, dict]:
    """(UI 요약, ruleId별 카운트). 카운트는 resolved/introduced 계산용."""
    by_severity = {"CRITICAL": 0, "WARNING": 0, "INFO": 0}
    by_rule: dict[str, int] = {}
    for f in findings:
        by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
        by_rule[f.rule_id] = by_rule.get(f.rule_id, 0) + 1
    return {"total": len(findings), "bySeverity": by_severity}, by_rule


def build_diff(
    sql_before: str,
    sql_after: str,
    schema: Optional[dict] = None,
    engine: Optional[AnalysisEngine] = None,
) -> dict:
    """DiffResult(JSON 모델)를 반환한다 (docs/architecture.md 데이터 계약)."""
    ast_before, err_before = parse(sql_before)
    ast_after, err_after = parse(sql_after)
    if err_before is not None or err_after is not None:
        return {"ok": False, "errorBefore": err_before, "errorAfter": err_after}
    assert ast_before is not None and ast_after is not None

    engine = engine or AnalysisEngine(ALL_RULES)
    findings_before = engine.run(ast_before, RuleContext(root=ast_before, schema=schema))
    findings_after = engine.run(ast_after, RuleContext(root=ast_after, schema=schema))

    # sqlglot.diff는 내부적으로 노드에 주석을 달 수 있다 — 복사본으로 원본 보존
    try:
        ops = sqlglot.diff(ast_before.copy(), ast_after.copy())
    except Exception:
        ops = None  # diff 실패는 비교 요약만이라도 반환한다
    changes = (
        [] if ops is None else [c for c in (_change(op) for op in ops) if c is not None]
    )

    summary_before, rules_before = _warning_summary(findings_before)
    summary_after, rules_after = _warning_summary(findings_after)
    resolved = sorted(
        r for r, n in rules_before.items() if rules_after.get(r, 0) < n
    )
    introduced = sorted(
        r for r, n in rules_after.items() if rules_before.get(r, 0) < n
    )

    return {
        "ok": True,
        "equivalent": ops is not None and len(changes) == 0,
        "changes": changes[:_MAX_CHANGES],
        "changeCount": len(changes),
        "metricsBefore": compute_metrics(ast_before),
        "metricsAfter": compute_metrics(ast_after),
        "warningsBefore": summary_before,
        "warningsAfter": summary_after,
        "resolvedRules": resolved,
        "introducedRules": introduced,
    }
