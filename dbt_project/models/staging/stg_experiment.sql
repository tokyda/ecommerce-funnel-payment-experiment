{{ config(materialized='view') }}

SELECT
    user_id::INTEGER          AS user_id,
    timestamp::TIMESTAMP      AS event_timestamp,
    "group"                   AS experiment_group,
    landing_page,
    converted::INTEGER        AS converted
FROM read_csv_auto('{{ var("raw_data_path") }}/ab_data.csv')
