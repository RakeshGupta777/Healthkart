# Generated Data Quality Issues Report

## Dataset Profile

- Raw rows: 600
- Raw columns: 10
- Reference rows: 60
- Reference columns: 9
- Schema-level issue groups: 1
- Content-level issue groups: 14

## Issue Summary

- duplicate_keys: 1
- format_inconsistency: 3
- null_violation: 6
- out_of_domain: 3
- schema_mismatch: 1
- type_drift: 1

## Findings

### schema_mismatch - notes

- Scope: schema
- Severity: medium
- Count: 1
- Finding: Raw dataset has 1 column(s) not present in the reference schema.
- Examples: notes

```sql
-- Keep only reference columns in the final SELECT and ignore raw-only columns such as notes.
```

### type_drift - is_active

- Scope: content
- Severity: medium
- Count: 19
- Finding: `is_active` uses non-boolean encodings even though the reference is boolean-like.
- Examples: y, no, 1, 0, yes

```sql
-- Cast normalized values in the normalized CTE, for example signup_date::DATE and is_active::BOOLEAN.
```

### null_violation - email

- Scope: content
- Severity: high
- Count: 2
- Finding: Required column `email` contains null or blank values.
- Examples: none

```sql
-- Use NULLIF during standardization, then quarantine or filter rows where required columns remain NULL.
```

### null_violation - full_name

- Scope: content
- Severity: high
- Count: 4
- Finding: Required column `full_name` contains null or blank values.
- Examples: none

```sql
-- Use NULLIF during standardization, then quarantine or filter rows where required columns remain NULL.
```

### null_violation - phone

- Scope: content
- Severity: high
- Count: 4
- Finding: Required column `phone` contains null or blank values.
- Examples: none

```sql
-- Use NULLIF during standardization, then quarantine or filter rows where required columns remain NULL.
```

### null_violation - signup_date

- Scope: content
- Severity: high
- Count: 7
- Finding: Required column `signup_date` contains null or blank values.
- Examples: none

```sql
-- Use NULLIF during standardization, then quarantine or filter rows where required columns remain NULL.
```

### null_violation - city

- Scope: content
- Severity: high
- Count: 2
- Finding: Required column `city` contains null or blank values.
- Examples: none

```sql
-- Use NULLIF during standardization, then quarantine or filter rows where required columns remain NULL.
```

### null_violation - segment

- Scope: content
- Severity: high
- Count: 6
- Finding: Required column `segment` contains null or blank values.
- Examples: none

```sql
-- Use NULLIF during standardization, then quarantine or filter rows where required columns remain NULL.
```

### duplicate_keys - customer_id

- Scope: content
- Severity: high
- Count: 15
- Finding: Customer primary key appears in multiple raw rows.
- Examples: C200574, C200371, C200526, C200566, C200336

```sql
-- Use row_number() OVER (PARTITION BY customer_id ORDER BY signup_date DESC NULLS LAST) and keep duplicate_rank = 1.
```

### out_of_domain - country

- Scope: content
- Severity: medium
- Count: 40
- Finding: `country` contains values outside the reference domain: AE, IN, UK, US.
- Examples: U.K., United States, SG, india, USA

```sql
-- Map known synonyms to reference domains with CASE expressions, otherwise set the value to NULL for review.
```

### out_of_domain - segment

- Scope: content
- Severity: medium
- Count: 3
- Finding: `segment` contains values outside the reference domain: enterprise, premium, retail.
- Examples: enterprize, primium

```sql
-- Map known synonyms to reference domains with CASE expressions, otherwise set the value to NULL for review.
```

### out_of_domain - is_active

- Scope: content
- Severity: medium
- Count: 19
- Finding: `is_active` contains values outside the reference domain: false, true.
- Examples: Y, no, 1, 0, yes

```sql
-- Map known synonyms to reference domains with CASE expressions, otherwise set the value to NULL for review.
```

### format_inconsistency - email

- Scope: content
- Severity: medium
- Count: 16
- Finding: `email` does not consistently match the reference format.
- Examples: neha.mehta89@@yahoo.com, priya.iyer30.yahoo.com, arjun.bansal26.gmail.com, krishna.joshi24, neha.nair64.hotmail.com

```sql
-- Use regexp_matches, regexp_replace, and try_strptime to standardize email, phone, and date formats.
```

### format_inconsistency - phone

- Scope: content
- Severity: medium
- Count: 49
- Finding: `phone` does not consistently match the reference format.
- Examples: 7358718098, 91-9800667638, 7979273333, +91 85419 06299, +91 71638 89719

```sql
-- Use regexp_matches, regexp_replace, and try_strptime to standardize email, phone, and date formats.
```

### format_inconsistency - signup_date

- Scope: content
- Severity: medium
- Count: 38
- Finding: `signup_date` does not consistently match the reference format.
- Examples: 03/01/2025, 2024/07/09, 23.09.2024, 2025/02/13, 11.11.2025

```sql
-- Use regexp_matches, regexp_replace, and try_strptime to standardize email, phone, and date formats.
```

## Full Repair SQL

```sql
-- DuckDB repair SQL generated for the provided customer raw file.
-- It removes schema-only columns, standardizes formats/domains, and deduplicates keys.
WITH raw_customers AS (
    SELECT * FROM read_csv_auto('data/raw/customers_raw.csv', header = true)
),
numbered AS (
    SELECT
        *,
        row_number() OVER () AS source_row_number
    FROM raw_customers
),
normalized AS (
    SELECT
        NULLIF(trim(customer_id), '') AS customer_id,
        CASE
            WHEN regexp_matches(lower(trim(email)), '^[^@\s]+@[^@\s]+\.[^@\s]+$')
            THEN lower(trim(email))
            ELSE NULL
        END AS email,
        NULLIF(regexp_replace(trim(full_name), '\s+', ' ', 'g'), '') AS full_name,
        CASE
            WHEN regexp_matches(regexp_replace(COALESCE(phone, ''), '[^0-9]', '', 'g'), '^91[0-9]{10}$')
            THEN '+91-' || right(regexp_replace(COALESCE(phone, ''), '[^0-9]', '', 'g'), 10)
            WHEN regexp_matches(regexp_replace(COALESCE(phone, ''), '[^0-9]', '', 'g'), '^[0-9]{10}$')
            THEN '+91-' || regexp_replace(COALESCE(phone, ''), '[^0-9]', '', 'g')
            ELSE NULL
        END AS phone,
        COALESCE(
            try_strptime(trim(signup_date), '%Y-%m-%d'),
            try_strptime(trim(signup_date), '%d/%m/%Y'),
            try_strptime(trim(signup_date), '%m/%d/%Y'),
            try_strptime(trim(signup_date), '%d.%m.%Y')
        )::DATE AS signup_date,
        CASE
            WHEN lower(trim(country)) IN ('in', 'india') THEN 'IN'
            WHEN lower(trim(country)) IN ('us', 'usa', 'united states') THEN 'US'
            WHEN lower(trim(country)) IN ('uk', 'u.k.') THEN 'UK'
            WHEN upper(trim(country)) IN ('SG', 'AE') THEN upper(trim(country))
            ELSE NULL
        END AS country,
        NULLIF(regexp_replace(trim(city), '\s+', ' ', 'g'), '') AS city,
        CASE
            WHEN lower(trim(segment)) IN ('retail') THEN 'retail'
            WHEN lower(trim(segment)) IN ('premium', 'primium') THEN 'premium'
            WHEN lower(trim(segment)) IN ('enterprise', 'enterprize') THEN 'enterprise'
            ELSE NULL
        END AS segment,
        CASE
            WHEN lower(trim(CAST(is_active AS VARCHAR))) IN ('true', '1', 'y', 'yes') THEN TRUE
            WHEN lower(trim(CAST(is_active AS VARCHAR))) IN ('false', '0', 'n', 'no') THEN FALSE
            ELSE NULL
        END AS is_active,
        source_row_number
    FROM numbered
),
deduped AS (
    SELECT
        *,
        row_number() OVER (
            PARTITION BY customer_id
            ORDER BY signup_date DESC NULLS LAST, source_row_number DESC
        ) AS duplicate_rank
    FROM normalized
)
SELECT
    customer_id,
    email,
    full_name,
    phone,
    signup_date,
    country,
    city,
    segment,
    is_active
FROM deduped
WHERE duplicate_rank = 1;

```