{{ config(materialized='view') }}

SELECT
    h.user_id,
    u.device,
    u.gender,
    TRUE                            AS visited_home,
    (s.user_id IS NOT NULL)         AS visited_search,
    (p.user_id IS NOT NULL)         AS visited_payment,
    (c.user_id IS NOT NULL)         AS completed_purchase
FROM {{ ref('stg_funnel_home') }} h
LEFT JOIN {{ ref('stg_funnel_search') }}       s ON h.user_id = s.user_id
LEFT JOIN {{ ref('stg_funnel_payment') }}      p ON h.user_id = p.user_id
LEFT JOIN {{ ref('stg_funnel_confirmation') }} c ON h.user_id = c.user_id
LEFT JOIN {{ ref('stg_users') }}               u ON h.user_id = u.user_id
