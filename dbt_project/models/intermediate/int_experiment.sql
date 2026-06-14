{{ config(materialized='view') }}

-- Remove rows where group and page don't match, then deduplicate to one row per user
WITH valid_assignments AS (
    SELECT *
    FROM {{ ref('stg_experiment') }}
    WHERE (experiment_group = 'control'   AND landing_page = 'old_page')
       OR (experiment_group = 'treatment' AND landing_page = 'new_page')
),

-- Users with valid rows in BOTH groups are contaminated (e.g. cookie clearing, bot traffic).
-- Excluding them avoids arbitrary first-touch tie-breaking that could bias group sizes.
contaminated AS (
    SELECT user_id
    FROM valid_assignments
    GROUP BY user_id
    HAVING COUNT(DISTINCT experiment_group) > 1
),

deduped AS (
    SELECT DISTINCT ON (user_id)
        user_id,
        event_timestamp,
        experiment_group,
        landing_page,
        converted
    FROM valid_assignments
    WHERE user_id NOT IN (SELECT user_id FROM contaminated)
    ORDER BY user_id, event_timestamp ASC
)

SELECT
    d.user_id,
    d.experiment_group,
    d.landing_page,
    d.converted,
    c.country
FROM deduped d
LEFT JOIN {{ ref('stg_countries') }} c ON d.user_id = c.user_id
