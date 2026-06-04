# Data Quality & SQL Repair Studio

A Streamlit web app for the BrightLife Care Data Engineering Intern assignment. It loads the provided raw and reference customer datasets, profiles them, separates schema-level and content-level data quality issues, and generates runnable DuckDB SQL to repair the raw import.

## What It Detects

- Schema mismatches: raw-only or missing reference columns.
- Type drift: values that no longer match reference logical types.
- Null violations: required reference fields that are blank in raw data.
- Duplicate keys: repeated `customer_id` values.
- Out-of-domain values: country, segment, and boolean values outside the reference domains.
- Format inconsistencies: email, Indian phone, and ISO date format drift.

## Run

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

The bundled datasets are already placed at:

- `data/raw/customers_raw.csv`
- `data/reference/customers_reference.csv`

## Generate The Report

```bash
python -m dq_studio.report
```

This writes:

- `reports/issues_report.md`
- `reports/repair_customers.sql`

## Project Structure

```text
app.py                         Streamlit UI
dq_studio/detectors.py         Pluggable issue detectors
dq_studio/schema.py            Reference schema inference
dq_studio/sql_generator.py     DuckDB repair SQL
dq_studio/report.py            Markdown report generator
data/raw/                      Raw import data
data/reference/                Clean reference data
tests/                         Focused regression tests
```

## Adding A New Issue Type

Add a detector function in `dq_studio/detectors.py` with this signature:

```python
def detect_new_issue(raw, reference, schema) -> list[Issue]:
    ...
```

Then append it to the `DETECTORS` list. The profiling engine calls every registered detector and the UI/report automatically render returned `Issue` objects, so no UI changes are required.

## SQL Notes

The generated SQL uses DuckDB functions such as `read_csv_auto`, `regexp_replace`, `regexp_matches`, and `try_strptime`. It creates CTEs for raw loading, normalization, and deduplication, then returns a reference-shaped customer table.

## License

This repository is prepared for release under an OSI-approved license. Add the license file requested by your submission process before publishing.
