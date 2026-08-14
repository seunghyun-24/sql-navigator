"""Position Mapper (docs/analyzer.md v0.7) — Parser Layer 보조 모듈.

tokenizer 토큰 위치로 AST 노드 -> (line, col)을 매핑한다.
분석 로직이 아니다 — Warning을 만들지 않는다.

원리: 노드를 SQL로 렌더링해 토큰화한 뒤, 원본 SQL의 토큰 스트림에서
같은 토큰 시그니처 시퀀스를 찾는다. 키워드/연산자는 타입만 비교해
표기 차이(`!=` vs `<>`, 대소문자)를 흡수하고, 식별자/리터럴은 텍스트까지
비교한다.

단정할 수 없으면(일치 0개 또는 2개 이상) None을 반환하고 Finding은
snippet으로 폴백한다 (docs/principles.md Static Only).
"""

from __future__ import annotations

from typing import Optional

import sqlglot
from sqlglot import exp
from sqlglot.tokens import TokenType

from config import DIALECT

# 텍스트까지 비교하는 토큰 — 식별자/리터럴 (키워드·연산자는 타입만)
_TEXT_SENSITIVE = {
    TokenType.VAR,
    TokenType.IDENTIFIER,
    TokenType.STRING,
    TokenType.NUMBER,
}


def _signature(token) -> tuple:
    if token.token_type in _TEXT_SENSITIVE:
        return (token.token_type, token.text.lower())
    return (token.token_type, None)


def _line_col(sql: str, offset: int) -> dict:
    """문자 오프셋 -> 1-based {line, col}. 위치 계산용 문자열 처리 (분석 아님)."""
    line = sql.count("\n", 0, offset) + 1
    last_nl = sql.rfind("\n", 0, offset)
    return {"line": line, "col": offset - last_nl}


class PositionMapper:
    """원본 SQL 하나에 대해 생성하고 재사용한다. 읽기 전용 — 상태 변경 없음."""

    def __init__(self, sql: str, dialect: str = DIALECT):
        self._sql = sql or ""
        self._dialect = dialect
        try:
            self._tokens = sqlglot.tokenize(self._sql, read=dialect)
        except Exception:
            self._tokens = []
        self._signatures = [_signature(t) for t in self._tokens]

    def locate(self, node: exp.Expression) -> Optional[dict]:
        """AST 노드 -> {line, col} | None. 실패해도 예외를 내지 않는다."""
        try:
            rendered = node.sql(dialect=self._dialect)
            needle = [
                _signature(t) for t in sqlglot.tokenize(rendered, read=self._dialect)
            ]
        except Exception:
            return None
        if not needle or len(needle) > len(self._signatures):
            return None

        matches = [
            i
            for i in range(len(self._signatures) - len(needle) + 1)
            if self._signatures[i : i + len(needle)] == needle
        ]
        if len(matches) != 1:
            return None  # 0개(렌더링 표기 차이) 또는 2개 이상(모호) — 단정하지 않는다

        start = getattr(self._tokens[matches[0]], "start", None)
        if not isinstance(start, int):
            return None
        return _line_col(self._sql, start)
