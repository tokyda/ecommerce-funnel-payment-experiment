{{ config(materialized='table') }}

WITH base AS (
    SELECT
        COUNT(*)                                        AS home_users,
        COUNT(*) FILTER (WHERE visited_search)          AS search_users,
        COUNT(*) FILTER (WHERE visited_payment)         AS payment_users,
        COUNT(*) FILTER (WHERE completed_purchase)      AS confirmation_users
    FROM {{ ref('int_user_journey') }}
)

SELECT 'Home Page'         AS step, 1 AS step_order,
    home_users             AS users,
    0                      AS drop_off_count,
    0.0                    AS drop_off_pct,
    100.0                  AS conversion_from_home_pct
FROM base

UNION ALL

SELECT 'Search Page', 2,
    search_users,
    home_users - search_users,
    ROUND(100.0 * (home_users - search_users) / NULLIF(home_users, 0), 2),
    ROUND(100.0 * search_users / NULLIF(home_users, 0), 2)
FROM base

UNION ALL

SELECT 'Payment Page', 3,
    payment_users,
    search_users - payment_users,
    ROUND(100.0 * (search_users - payment_users) / NULLIF(search_users, 0), 2),
    ROUND(100.0 * payment_users / NULLIF(home_users, 0), 2)
FROM base

UNION ALL

SELECT 'Confirmation Page', 4,
    confirmation_users,
    payment_users - confirmation_users,
    ROUND(100.0 * (payment_users - confirmation_users) / NULLIF(payment_users, 0), 2),
    ROUND(100.0 * confirmation_users / NULLIF(home_users, 0), 2)
FROM base

ORDER BY step_order
