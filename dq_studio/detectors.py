from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from dq_studio.models import ColumnSpec, Issue
from dq_studio.schema import EMAIL_RE, ISO_DATE_RE, PHONE_RE
from dq_studio.sql_generator import ISSUE_SQL

Detector = Callable[[pd.DataFrame, pd.DataFrame, dict[str, ColumnSpec]], list[Issue]]


def _examples(series: pd.Series, limit: int = 5) -> tuple[str, ...]:
    values = series.dropna().astype(str).drop_duplicates().head(limit).tolist()
    return tuple(values)


def detect_schema_mismatches(raw: pd.DataFrame, reference: pd.DataFrame, schema: dict[str, ColumnSpec]) -> list[Issue]:
    issues: list[Issue] = []
    raw_cols = set(raw.columns)
    ref_cols = set(reference.columns)
    extra = sorted(raw_cols - ref_cols)
    missing = sorted(ref_cols - raw_cols)
    if extra:
        issues.append(Issue(
            "schema_mismatch", "schema", "medium", ", ".join(extra),
            f"Raw dataset has {len(extra)} column(s) not present in the reference schema.",
            len(extra), tuple(extra), ISSUE_SQL["schema_mismatch"],
        ))
    if missing:
        issues.append(Issue(
            "schema_mismatch", "schema", "high", ", ".join(missing),
            f"Raw dataset is missing {len(missing)} required reference column(s).",
            len(missing), tuple(missing), ISSUE_SQL["schema_mismatch"],
        ))
    return issues


def detect_null_violations(raw: pd.DataFrame, reference: pd.DataFrame, schema: dict[str, ColumnSpec]) -> list[Issue]:
    issues: list[Issue] = []
    for column, spec in schema.items():
        if column not in raw or spec.nullable:
            continue
        mask = raw[column].isna() | raw[column].astype(str).str.strip().eq("")
        if mask.any():
            issues.append(Issue(
                "null_violation", "content", "high", column,
                f"Required column `{column}` contains null or blank values.",
                int(mask.sum()), _examples(raw.loc[mask, column]), ISSUE_SQL["null_violation"],
            ))
    return issues


def detect_duplicate_keys(raw: pd.DataFrame, reference: pd.DataFrame, schema: dict[str, ColumnSpec]) -> list[Issue]:
    if "customer_id" not in raw:
        return []
    mask = raw.duplicated("customer_id", keep=False)
    if not mask.any():
        return []
    duplicate_ids = raw.loc[mask, "customer_id"].astype(str)
    return [Issue(
        "duplicate_keys", "content", "high", "customer_id",
        "Customer primary key appears in multiple raw rows.",
        int(duplicate_ids.nunique()), _examples(duplicate_ids), ISSUE_SQL["duplicate_keys"],
    )]


def detect_out_of_domain(raw: pd.DataFrame, reference: pd.DataFrame, schema: dict[str, ColumnSpec]) -> list[Issue]:
    issues: list[Issue] = []
    for column, spec in schema.items():
        if column not in raw or not spec.domain:
            continue
        allowed = {v.strip().lower() for v in spec.domain}
        values = raw[column].dropna().astype(str).str.strip()
        mask = ~values.str.lower().isin(allowed)
        if mask.any():
            bad = values[mask]
            issues.append(Issue(
                "out_of_domain", "content", "medium", column,
                f"`{column}` contains values outside the reference domain: {', '.join(spec.domain)}.",
                int(mask.sum()), _examples(bad), ISSUE_SQL["out_of_domain"],
            ))
    return issues


def detect_format_inconsistencies(raw: pd.DataFrame, reference: pd.DataFrame, schema: dict[str, ColumnSpec]) -> list[Issue]:
    checks = {
        "email": lambda s: s.astype(str).str.strip().map(lambda x: bool(EMAIL_RE.match(x))),
        "phone": lambda s: s.astype(str).str.strip().map(lambda x: bool(PHONE_RE.match(x))),
        "signup_date": lambda s: s.astype(str).str.strip().map(lambda x: bool(ISO_DATE_RE.match(x))),
    }
    issues: list[Issue] = []
    for column, check in checks.items():
        if column not in raw:
            continue
        present = ~(raw[column].isna() | raw[column].astype(str).str.strip().eq(""))
        valid = check(raw.loc[present, column])
        invalid_index = valid[~valid].index
        if len(invalid_index):
            issues.append(Issue(
                "format_inconsistency", "content", "medium", column,
                f"`{column}` does not consistently match the reference format.",
                len(invalid_index), _examples(raw.loc[invalid_index, column]), ISSUE_SQL["format_inconsistency"],
            ))
    return issues


def detect_type_drift(raw: pd.DataFrame, reference: pd.DataFrame, schema: dict[str, ColumnSpec]) -> list[Issue]:
    issues: list[Issue] = []
    if "is_active" in raw:
        values = raw["is_active"].dropna().astype(str).str.strip().str.lower()
        boolean_like = {"true", "false"}
        drift = values[~values.isin(boolean_like)]
        if not drift.empty:
            issues.append(Issue(
                "type_drift", "content", "medium", "is_active",
                "`is_active` uses non-boolean encodings even though the reference is boolean-like.",
                int(drift.shape[0]), _examples(drift), ISSUE_SQL["type_drift"],
            ))
    if "signup_date" in raw:
        parsed = pd.to_datetime(raw["signup_date"], errors="coerce", format="mixed")
        present = ~(raw["signup_date"].isna() | raw["signup_date"].astype(str).str.strip().eq(""))
        drift = raw.loc[present & parsed.isna(), "signup_date"]
        if not drift.empty:
            issues.append(Issue(
                "type_drift", "content", "high", "signup_date",
                "`signup_date` has values that cannot be parsed as dates.",
                int(drift.shape[0]), _examples(drift), ISSUE_SQL["type_drift"],
            ))
    return issues


DETECTORS: list[Detector] = [
    detect_schema_mismatches,
    detect_type_drift,
    detect_null_violations,
    detect_duplicate_keys,
    detect_out_of_domain,
    detect_format_inconsistencies,
]


def run_detectors(raw: pd.DataFrame, reference: pd.DataFrame) -> list[Issue]:
    schema = __import__("dq_studio.schema", fromlist=["infer_reference_schema"]).infer_reference_schema(reference)
    issues: list[Issue] = []
    for detector in DETECTORS:
        issues.extend(detector(raw, reference, schema))
    return issues
