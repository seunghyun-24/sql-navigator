"""진입점. Bridge가 호출하는 함수: analyze(sql), diff(before, after) -> JSON 문자열.

Pipeline (docs/architecture.md): Parser -> Analysis Engine -> AnalysisResult(JSON).
SQL Diff (v0.8)는 별도 진입점 diff()로, DiffResult(JSON)를 반환한다.
"""

from __future__ import annotations

import json

from data_flow import build_data_flow
from engine import AnalysisEngine, RuleContext
from join_graph import build_join_graph
from metrics import compute_metrics
from parser import format_sql, node_to_tree, parse
from position import PositionMapper
from rules import ALL_RULES
from schema_context import parse_schema
from sql_diff import build_diff
from suggestions import build_suggestions

# Rule은 전부 stateless이므로 Engine 재사용은 안전하다 (docs/principles.md).
_engine = AnalysisEngine(ALL_RULES)


def analyze(sql: str, schema_ddl: str = "") -> str:
    """schema_ddl: 사용자가 붙여넣은 DDL (선택, docs/analyzer.md Schema Context)."""
    ast, error = parse(sql)
    schema, schema_info = parse_schema(schema_ddl)
    if error is not None:
        return json.dumps(
            {"ok": False, "error": error, "schemaInfo": schema_info}, ensure_ascii=False
        )
    assert ast is not None

    # Position Mapper (v0.7): Finding.location을 원본 SQL 기준으로 채운다
    mapper = PositionMapper(sql)
    findings = _engine.run(ast, RuleContext(root=ast, schema=schema), locate=mapper.locate)

    return json.dumps(
        {
            "ok": True,
            "tree": node_to_tree(ast),
            "formatted": format_sql(ast),
            "warnings": [f.to_dict() for f in findings],
            "suggestions": build_suggestions(ast, schema),
            "metrics": compute_metrics(ast),
            "joinGraph": build_join_graph(ast),
            "dataFlow": build_data_flow(ast),
            "schemaInfo": schema_info,
        },
        ensure_ascii=False,
    )


def diff(sql_before: str, sql_after: str, schema_ddl: str = "") -> str:
    """SQL Diff 진입점 (v0.8, docs/analyzer.md). DiffResult(JSON)를 반환한다."""
    schema, _info = parse_schema(schema_ddl)
    return json.dumps(
        build_diff(sql_before, sql_after, schema=schema, engine=_engine),
        ensure_ascii=False,
    )
