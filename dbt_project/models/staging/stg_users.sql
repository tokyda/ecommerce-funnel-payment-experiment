{{ config(materialized='view') }}

SELECT
    user_id::INTEGER          AS user_id,
    date::DATE                AS signup_date,
    LOWER(device)             AS device,
    LOWER(sex)                AS gender
FROM read_csv_auto('{{ var("raw_data_path") }}/user_table.csv')
