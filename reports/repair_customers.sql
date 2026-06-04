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
