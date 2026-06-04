from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd

from dq_studio.detectors import run_detectors
from dq_studio.sql_generator import full_repair_sql


RAW_PATH = Path("data/raw/customers_raw.csv")
REFERENCE_PATH = Path("data/reference/customers_reference.csv")


def load_data(raw_path: Path = RAW_PATH, reference_path: Path = REFERENCE_PATH) -> tuple[pd.DataFrame, pd.DataFrame]:
    return pd.read_csv(raw_path), pd.read_csv(reference_path)


def issue_frame(raw: pd.DataFrame, reference: pd.DataFrame) -> pd.DataFrame:
    issues = run_detectors(raw, reference)
    return pd.DataFrame([issue.__dict__ for issue in issues])


def markdown_report(raw: pd.DataFrame, reference: pd.DataFrame) -> str:
    issues = run_detectors(raw, reference)
    by_category = Counter(issue.category for issue in issues)
    by_scope = Counter(issue.scope for issue in issues)
    lines = [
        "# Generated Data Quality Issues Report",
        "",
        "## Dataset Profile",
        "",
        f"- Raw rows: {len(raw):,}",
        f"- Raw columns: {len(raw.columns):,}",
        f"- Reference rows: {len(reference):,}",
        f"- Reference columns: {len(reference.columns):,}",
        f"- Schema-level issue groups: {by_scope.get('schema', 0)}",
        f"- Content-level issue groups: {by_scope.get('content', 0)}",
        "",
        "## Issue Summary",
        "",
    ]
    for category, count in sorted(by_category.items()):
        lines.append(f"- {category}: {count}")
    lines.extend(["", "## Findings", ""])
    for issue in issues:
        examples = ", ".join(issue.examples) if issue.examples else "none"
        lines.extend([
            f"### {issue.category} - {issue.column}",
            "",
            f"- Scope: {issue.scope}",
            f"- Severity: {issue.severity}",
            f"- Count: {issue.count}",
            f"- Finding: {issue.message}",
            f"- Examples: {examples}",
            "",
            "```sql",
            issue.sql,
            "```",
            "",
        ])
    lines.extend([
        "## Full Repair SQL",
        "",
        "```sql",
        full_repair_sql(),
        "```",
    ])
    return "\n".join(lines)


def main() -> None:
    raw, reference = load_data()
    Path("reports").mkdir(exist_ok=True)
    Path("reports/issues_report.md").write_text(markdown_report(raw, reference), encoding="utf-8")
    Path("reports/repair_customers.sql").write_text(full_repair_sql(), encoding="utf-8")
    print("Wrote reports/issues_report.md and reports/repair_customers.sql")


if __name__ == "__main__":
    main()
