"""Rule 테스트 공통 헬퍼 (docs/analyzer.md 테스트 절)."""

import sqlglot

from config import DIALECT
from engine import AnalysisEngine, Finding, Rule, RuleContext


def run_rule(rule: Rule, sql: str, schema: dict | None = None) -> list[Finding]:
    ast = sqlglot.parse_one(sql, read=DIALECT)
    assert ast is not None
    return AnalysisEngine([rule]).run(ast, RuleContext(root=ast, schema=schema))


def assert_explainable(findings: list[Finding]) -> None:
    """모든 Finding은 이유/예시/수정을 포함해야 한다 (docs/principles.md)."""
    for f in findings:
        assert f.reason, f"{f.rule_id}: reason 누락"
        assert f.example, f"{f.rule_id}: example 누락"
        assert f.fix, f"{f.rule_id}: fix 누락"
        assert f.message, f"{f.rule_id}: message 누락"
