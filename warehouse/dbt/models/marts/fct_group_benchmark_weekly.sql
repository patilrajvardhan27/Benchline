-- p10 to p90 per product group and week, the same method as the benchmark worker: each product's latest
-- NADAC rate as of the week end (Monday + 6 days), within 52 weeks, exact linear percentiles, 5 places.
with prices as (
    select p.item_id, i.group_id, p.unit_price, p.effective_date, p.as_of_date
    from {{ ref('stg_price_points') }} p
    join {{ ref('stg_items') }} i on i.item_id = p.item_id
    where p.source = 'NADAC'
),

weeks as (
    select distinct group_id, cast(date_trunc('week', as_of_date) as date) as week_start
    from prices
),

latest as (
    select w.group_id, w.week_start, p.item_id, p.unit_price as price
    from weeks w
    join prices p
      on p.group_id = w.group_id
     and p.effective_date <= {{ dbt.dateadd('day', 6, 'w.week_start') }}
     and p.effective_date > {{ dbt.dateadd('day', -358, 'w.week_start') }}
    qualify row_number() over (partition by w.group_id, w.week_start, p.item_id order by p.effective_date desc) = 1
),

ranked as (
    select
        group_id,
        week_start,
        price,
        row_number() over (partition by group_id, week_start order by price) - 1 as idx,
        count(*) over (partition by group_id, week_start) as n
    from latest
)

select
    group_id,
    week_start as as_of_week,
    {{ linear_percentile('0.10') }} as p10,
    {{ linear_percentile('0.25') }} as p25,
    {{ linear_percentile('0.50') }} as p50,
    {{ linear_percentile('0.75') }} as p75,
    {{ linear_percentile('0.90') }} as p90,
    max(n) as n_obs
from ranked
group by group_id, week_start
