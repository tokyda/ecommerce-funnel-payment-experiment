{{ config(materialized='table') }}

-- One row per user, ready for z-test and segment analysis in notebooks
SELECT
    user_id,
    experiment_group,
    landing_page,
    converted,
    COALESCE(country, 'Unknown') AS country
FROM {{ ref('int_experiment') }}
