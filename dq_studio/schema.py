from __future__ import annotations

import re

import pandas as pd

from dq_studio.models import ColumnSpec


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+91-\d{10}$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def infer_reference_schema(reference: pd.DataFrame) -> dict[str, ColumnSpec]:
    specs: dict[str, ColumnSpec] = {}
    for column in reference.columns:
        series = reference[column]
        normalized = series.dropna().astype(str).str.strip()
        logical_type = "string"
        format_name = None
        domain: tuple[str, ...] = ()

        if column == "is_active":
            logical_type = "boolean"
            domain = tuple(sorted(normalized.str.lower().unique()))
        elif column == "signup_date" or normalized.map(lambda x: bool(ISO_DATE_RE.match(x))).mean() >= 0.95:
            logical_type = "date"
            format_name = "yyyy-mm-dd"
        elif column == "email" or normalized.map(lambda x: bool(EMAIL_RE.match(x))).mean() >= 0.95:
            logical_type = "email"
            format_name = "local@domain.tld"
        elif column == "phone" or normalized.map(lambda x: bool(PHONE_RE.match(x))).mean() >= 0.95:
            logical_type = "phone"
            format_name = "+91-##########"
        elif column in {"country", "segment"}:
            logical_type = "category"
            domain = tuple(sorted(normalized.unique()))

        specs[column] = ColumnSpec(
            name=column,
            logical_type=logical_type,
            nullable=bool(series.isna().any()),
            domain=domain,
            format_name=format_name,
        )
    return specs
