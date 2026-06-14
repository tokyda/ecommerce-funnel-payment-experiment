{{ config(materialized='view') }}

SELECT
    user_id::INTEGER AS user_id,
    country
FROM read_csv_auto('{{ var("raw_data_path") }}/countries.csv')
