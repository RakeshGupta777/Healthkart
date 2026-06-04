from __future__ import annotations

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


raw, reference = cached_data()
issues = run_detectors(raw, reference)
issue_df = pd.DataFrame([issue.__dict__ for issue in issues])
schema = infer_reference_schema(reference)

st.title("Data Quality & SQL Repair Studio")
st.caption("Raw customer import compared with the clean reference schema and dataset.")

metric_cols = st.columns(5)
metric_cols[0].metric("Raw rows", f"{len(raw):,}")
metric_cols[1].metric("Reference rows", f"{len(reference):,}")
metric_cols[2].metric("Issue groups", f"{len(issues):,}")
metric_cols[3].metric("Schema issues", f"{sum(i.scope == 'schema' for i in issues):,}")
metric_cols[4].metric("Content issues", f"{sum(i.scope == 'content' for i in issues):,}")

overview_tab, issues_tab, sql_tab, data_tab = st.tabs(["Overview", "Issues", "Generated SQL", "Data"])

with overview_tab:
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
    st.code(sql, language="sql")
    st.download_button("Download repair SQL", sql, file_name="repair_customers.sql")
    report = markdown_report(raw, reference)
    st.download_button("Download issues report", report, file_name="issues_report.md")

with data_tab:
    left, right = st.columns(2)
    with left:
        st.subheader(f"Raw: {RAW_PATH}")
        st.dataframe(raw.head(200), use_container_width=True)
    with right:
        st.subheader(f"Reference: {REFERENCE_PATH}")
        st.dataframe(reference.head(200), use_container_width=True)
