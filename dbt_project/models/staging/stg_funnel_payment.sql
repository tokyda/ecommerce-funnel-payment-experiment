{{ config(materialized='view') }}

SELECT user_id::INTEGER AS user_id
FROM read_csv_auto('{{ var("raw_data_path") }}/payment_page_table.csv')
