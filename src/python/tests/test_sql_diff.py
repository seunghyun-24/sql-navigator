from sql_diff import build_diff


def test_identical_sql_is_equivalent():
    sql = "SELECT id FROM users WHERE id = 1"
    r = build_diff(sql, sql)
    assert r["ok"] is True
    assert r["equivalent"] is True
    assert r["changes"] == []


def test_formatting_only_change_is_equivalent():
    # 문자열은 다르지만 AST는 동일 — 문자열 diff가 아님을 보장
    r = build_diff(
        "SELECT id FROM users WHERE id = 1",
        "select id\nfrom users\nwhere id = 1",
    )
    assert r["ok"] is True
    assert r["equivalent"] is True


def test_detects_structural_change():
    r = build_diff(
        "SELECT id FROM users WHERE id = 1",
        "SELECT id, name FROM users WHERE id = 1",
    )
    assert r["ok"] is True
    assert r["equivalent"] is False
    assert r["changeCount"] >= 1


def test_resolved_rules_on_improvement():
    r = build_diff(
        "SELECT id FROM users WHERE deleted_at = NULL",
        "SELECT id FROM users WHERE deleted_at IS NULL",
    )
    assert r["ok"] is True
    assert "null-comparison" in r["resolvedRules"]
    assert r["warningsBefore"]["total"] > r["warningsAfter"]["total"]
    assert r["warningsBefore"]["bySeverity"]["CRITICAL"] == 1
    assert r["warningsAfter"]["bySeverity"]["CRITICAL"] == 0


def test_introduced_rules_on_regression():
    r = build_diff("DELETE FROM users WHERE id = 1", "DELETE FROM users")
    assert r["ok"] is True
    assert "delete-without-where" in r["introducedRules"]
    assert r["resolvedRules"] == []


def test_metrics_compare():
    r = build_diff(
        "SELECT * FROM a WHERE x = 1",
        "SELECT * FROM a JOIN b ON a.id = b.a_id WHERE x = 1",
    )
    assert r["ok"] is True
    assert r["metricsAfter"]["joinCount"] == r["metricsBefore"]["joinCount"] + 1
    assert r["metricsAfter"]["complexityScore"] > r["metricsBefore"]["complexityScore"]


def test_parse_error_reported_per_side():
    r = build_diff("SELECT * FROM (", "SELECT 1")
    assert r["ok"] is False
    assert r["errorBefore"] is not None
    assert r["errorAfter"] is None
