from __future__ import annotations

from io import StringIO

import pandas as pd
import streamlit as st

from dq_studio.detectors import run_detectors
from dq_studio.report import REFERENCE_PATH, RAW_PATH, load_data, markdown_report
from dq_studio.schema import infer_reference_schema
from dq_studio.sql_generator import full_repair_sql


st.set_page_config(page_title="Data Quality & SQL Repair Studio", layout="wide")


@st.cache_data
def cached_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    return load_data()


def read_uploaded_csv(uploaded_file) -> pd.DataFrame | None:
    if uploaded_file is None:
        return None
    return pd.read_csv(uploaded_file)


def read_pasted_csv(csv_text: str) -> pd.DataFrame | None:
    if not csv_text.strip():
        return None
    return pd.read_csv(StringIO(csv_text))


default_raw, default_reference = cached_data()

st.sidebar.header("Upload Data")
input_mode = st.sidebar.radio("Input mode", ["Upload CSV files", "Paste CSV data", "Use bundled sample data"])
uploaded_raw = None
uploaded_reference = None
raw_text = ""
reference_text = ""

if input_mode == "Upload CSV files":
    uploaded_raw = st.sidebar.file_uploader("Raw dataset CSV", type=["csv"])
    uploaded_reference = st.sidebar.file_uploader("Reference dataset CSV", type=["csv"])
elif input_mode == "Paste CSV data":
    raw_text = st.sidebar.text_area("Raw CSV data", height=180, placeholder="customer_id,email,full_name,...")
    reference_text = st.sidebar.text_area("Reference CSV data", height=180, placeholder="customer_id,email,full_name,...")

try:
    if input_mode == "Upload CSV files":
        raw = read_uploaded_csv(uploaded_raw)
        reference = read_uploaded_csv(uploaded_reference)
    elif input_mode == "Paste CSV data":
        raw = read_pasted_csv(raw_text)
        reference = read_pasted_csv(reference_text)
    else:
        raw = default_raw
        reference = default_reference
except Exception as exc:
    st.error(f"Could not read CSV input: {exc}")
    st.stop()

if input_mode == "Upload CSV files" and (uploaded_raw is None or uploaded_reference is None):
    st.sidebar.warning("Upload both raw and reference CSV files to compare a custom dataset.")
if input_mode == "Paste CSV data" and (not raw_text.strip() or not reference_text.strip()):
    st.sidebar.warning("Paste both raw and reference CSV data to compare a custom dataset.")

has_data = raw is not None and reference is not None
raw_label = uploaded_raw.name if uploaded_raw is not None else ("pasted raw CSV" if raw_text.strip() else str(RAW_PATH))
reference_label = (
    uploaded_reference.name
    if uploaded_reference is not None
    else ("pasted reference CSV" if reference_text.strip() else str(REFERENCE_PATH))
)
issues = run_detectors(raw, reference) if has_data else []
issue_df = pd.DataFrame([issue.__dict__ for issue in issues]) if has_data else pd.DataFrame()
schema = infer_reference_schema(reference) if has_data else {}

st.title("Data Quality & SQL Repair Studio")
st.caption("Raw customer import compared with a clean reference schema and dataset.")

metric_cols = st.columns(5)
metric_cols[0].metric("Raw rows", f"{len(raw):,}" if has_data else "---")
metric_cols[1].metric("Reference rows", f"{len(reference):,}" if has_data else "---")
metric_cols[2].metric("Issue groups", f"{len(issues):,}" if has_data else "---")
metric_cols[3].metric("Schema issues", f"{sum(i.scope == 'schema' for i in issues):,}" if has_data else "---")
metric_cols[4].metric("Content issues", f"{sum(i.scope == 'content' for i in issues):,}" if has_data else "---")

overview_tab, issues_tab, sql_tab, data_tab = st.tabs(["Overview", "Issues", "Generated SQL", "Data"])

with overview_tab:
    if not has_data:
        st.info("Upload or paste both raw and reference CSV files to generate the issue report.")
        st.stop()
    left, right = st.columns(2)
    with left:
        st.subheader("Reference Schema")
        st.dataframe(pd.DataFrame([spec.__dict__ for spec in schema.values()]), use_container_width=True)
    with right:
        st.subheader("Issue Categories")
        if issue_df.empty:
            st.success("No issues detected.")
        else:
            st.dataframe(
                issue_df.groupby(["scope", "category"], as_index=False)["count"].sum(),
                use_container_width=True,
            )
    st.subheader("Analysis Output")
    if issue_df.empty:
        st.success("No issues detected.")
    else:
        output_df = issue_df[["scope", "severity", "category", "column", "count", "message", "examples"]].copy()
        output_df["examples"] = output_df["examples"].map(lambda values: ", ".join(values) if values else "")
        st.dataframe(output_df, use_container_width=True)

with issues_tab:
    st.subheader("Side-by-side Issues Report")
    if issue_df.empty:
        st.success("No issues detected.")
    else:
        scope_filter = st.segmented_control("Scope", ["all", "schema", "content"], default="all")
        visible = issue_df if scope_filter == "all" else issue_df[issue_df["scope"] == scope_filter]
        for issue in visible.itertuples(index=False):
            with st.expander(f"{issue.severity.upper()} | {issue.scope} | {issue.category} | {issue.column}", expanded=True):
                st.write(issue.message)
                c1, c2 = st.columns([1, 2])
                c1.metric("Affected count", issue.count)
                c2.write("Examples: " + (", ".join(issue.examples) if issue.examples else "none"))
                st.code(issue.sql, language="sql")

with sql_tab:
    st.subheader("Runnable DuckDB Repair SQL")
    sql = full_repair_sql(RAW_PATH)
    if input_mode != "Use bundled sample data":
        st.info(
            "The generated SQL is shown for the bundled assignment file path. "
            "For custom data, save the raw CSV and replace the path in `read_csv_auto(...)`."
        )
    st.code(sql, language="sql")
    st.download_button("Download repair SQL", sql, file_name="repair_customers.sql")
    report = markdown_report(raw, reference)
    st.download_button("Download issues report", report, file_name="issues_report.md")

with data_tab:
    left, right = st.columns(2)
    with left:
        st.subheader(f"Raw: {raw_label}")
        st.dataframe(raw.head(200), use_container_width=True)
    with right:
        st.subheader(f"Reference: {reference_label}")
        st.dataframe(reference.head(200), use_container_width=True)
