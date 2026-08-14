import sqlglot
from sqlglot import exp

from config import DIALECT
from engine import AnalysisEngine, RuleContext
from position import PositionMapper
from rules.null_comparison import NullComparisonRule


def _node(sql: str, cls: type) -> exp.Expression:
    ast = sqlglot.parse_one(sql, read=DIALECT)
    node = ast.find(cls)
    assert node is not None
    return node


def test_locates_eq_in_where():
    sql = "SELECT *\nFROM users\nWHERE deleted_at = NULL"
    loc = PositionMapper(sql).locate(_node(sql, exp.EQ))
    assert loc == {"line": 3, "col": 7}


def test_locates_single_line():
    sql = "SELECT * FROM users WHERE email LIKE '%x'"
    loc = PositionMapper(sql).locate(_node(sql, exp.Like))
    assert loc is not None
    assert loc["line"] == 1
    assert loc["col"] == 27  # 'email' 시작 위치 (1-based)


def test_absorbs_operator_notation_difference():
    # sqlglot은 !=를 <>로 렌더링할 수 있다 — 타입 비교로 흡수돼야 한다
    sql = "SELECT * FROM users WHERE deleted_at != NULL"
    loc = PositionMapper(sql).locate(_node(sql, exp.NEQ))
    assert loc is not None
    assert loc["col"] == 27


def test_ambiguous_returns_none():
    # 같은 식이 2회 등장 — 단정할 수 없으면 None (Static Only)
    sql = "SELECT * FROM t WHERE a = 1 OR a = 1"
    assert PositionMapper(sql).locate(_node(sql, exp.EQ)) is None


def test_engine_fills_location():
    sql = "SELECT *\nFROM users\nWHERE deleted_at = NULL"
    ast = sqlglot.parse_one(sql, read=DIALECT)
    mapper = PositionMapper(sql)
    findings = AnalysisEngine([NullComparisonRule()]).run(
        ast, RuleContext(root=ast), locate=mapper.locate
    )
    assert len(findings) == 1
    assert findings[0].location == {"line": 3, "col": 7}


def test_engine_without_locator_keeps_none():
    sql = "SELECT * FROM users WHERE deleted_at = NULL"
    ast = sqlglot.parse_one(sql, read=DIALECT)
    findings = AnalysisEngine([NullComparisonRule()]).run(ast, RuleContext(root=ast))
    assert findings[0].location is None


def test_locate_never_raises_on_garbage_mapper():
    mapper = PositionMapper("")
    node = _node("SELECT * FROM t WHERE a = 1", exp.EQ)
    assert mapper.locate(node) is None
