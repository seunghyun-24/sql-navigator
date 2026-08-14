"""Parser Layer + 진입점(analyze) 데이터 계약 테스트.

- ok=True: tree + formatted + warnings + metrics 존재
- ok=False: 구조화된 error (message, line, col)
- 반환값은 항상 JSON 직렬화 가능
"""

import json

from main import analyze


def run(sql: str) -> dict:
    return json.loads(analyze(sql))


def test_valid_select_contract():
    r = run("SELECT id, name FROM users WHERE id = 1")
    assert r["ok"] is True
    assert r["tree"]["type"] == "Select"
    assert "FROM users" in r["formatted"]
    assert isinstance(r["warnings"], list)
    assert r["metrics"]["tableCount"] == 1


def test_join_appears_in_tree():
    r = run("SELECT * FROM orders o JOIN customers c ON o.customer_id = c.id")
    types = set()

    def walk(n):
        types.add(n["type"])
        for c in n["children"]:
            walk(c)

    walk(r["tree"])
    assert "Join" in types


def test_parse_error_is_structured():
    r = run("SELEC id FROM users")
    assert r["ok"] is False
    assert r["error"]["message"]
    assert r["error"]["line"] is not None


def test_empty_sql():
    assert run("   ")["ok"] is False


def test_formatted_is_pretty():
    r = run("select a,b from t where a=1 and b=2")
    assert r["ok"] is True
    assert "\n" in r["formatted"]


def test_warnings_have_explainability_fields():
    r = run("DELETE FROM users")
    assert r["ok"] is True
    w = [x for x in r["warnings"] if x["ruleId"] == "delete-without-where"]
    assert len(w) == 1
    assert w[0]["severity"] == "CRITICAL"
    assert w[0]["reason"] and w[0]["example"] and w[0]["fix"]


def test_warnings_sorted_by_severity():
    r = run("SELECT * FROM a, b")  # select-star(INFO) + cartesian(CRITICAL) + no-where(WARNING)
    sev = [w["severity"] for w in r["warnings"]]
    order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
    assert sev == sorted(sev, key=lambda s: order[s])


def test_metrics():
    r = run(
        "WITH cte AS (SELECT id FROM a) "
        "SELECT c.id, (SELECT max(x) FROM b WHERE b.id = c.id) AS mx "
        "FROM cte c JOIN d ON c.id = d.id WHERE c.id > 0"
    )
    assert r["ok"] is True
    m = r["metrics"]
    assert m["cteCount"] == 1
    assert m["joinCount"] == 1
    assert m["subqueryDepth"] >= 1
    assert m["complexityScore"] > 0
    json.dumps(r)  # 전체 직렬화 가능
