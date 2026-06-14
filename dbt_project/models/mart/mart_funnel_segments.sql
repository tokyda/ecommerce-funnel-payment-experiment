{{ config(materialized='table') }}

SELECT
    COALESCE(device, 'unknown')  AS device,
    COALESCE(gender, 'unknown')  AS gender,
    COUNT(*)                                                                    AS home_users,
    COUNT(*) FILTER (WHERE visited_search)                                      AS search_users,
    COUNT(*) FILTER (WHERE visited_payment)                                     AS payment_users,
    COUNT(*) FILTER (WHERE completed_purchase)                                  AS confirmation_users,
    ROUND(100.0 * COUNT(*) FILTER (WHERE visited_search)
        / NULLIF(COUNT(*), 0), 2)                                               AS search_rate_pct,
    ROUND(100.0 * COUNT(*) FILTER (WHERE visited_payment)
        / NULLIF(COUNT(*), 0), 2)                                               AS payment_rate_pct,
    ROUND(100.0 * COUNT(*) FILTER (WHERE completed_purchase)
        / NULLIF(COUNT(*), 0), 2)                                               AS purchase_rate_pct,
    ROUND(100.0
        * (COUNT(*) FILTER (WHERE visited_payment) - COUNT(*) FILTER (WHERE completed_purchase))
        / NULLIF(COUNT(*) FILTER (WHERE visited_payment), 0), 2)                AS payment_dropoff_pct
FROM {{ ref('int_user_journey') }}
GROUP BY device, gender
ORDER BY device, gender
