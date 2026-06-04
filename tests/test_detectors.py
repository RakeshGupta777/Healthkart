from dq_studio.detectors import run_detectors
from dq_studio.report import load_data
from dq_studio.sql_generator import full_repair_sql


def test_required_issue_categories_are_detected():
    raw, reference = load_data()
    categories = {issue.category for issue in run_detectors(raw, reference)}
    assert {
        "schema_mismatch",
        "type_drift",
        "null_violation",
        "duplicate_keys",
        "out_of_domain",
        "format_inconsistency",
    }.issubset(categories)


def test_generated_sql_contains_duckdb_repair_steps():
    sql = full_repair_sql()
    assert "read_csv_auto" in sql
    assert "regexp_replace" in sql
    assert "try_strptime" in sql
    assert "duplicate_rank = 1" in sql
