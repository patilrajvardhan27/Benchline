-- Purchase lines priced above their group's latest p25: (paid - p25) * qty.
with latest_benchmark as (
    select *
    from {{ ref('fct_group_benchmark_weekly') }}
    qualify row_number() over (partition by group_id order by as_of_week desc) = 1
)

select
    pl.purchase_line_id,
    pl.facility_id,
    pl.item_id,
    i.group_id,
    pl.unit_price as paid_unit_price,
    b.p25 as benchmark_p25,
    b.p50 as benchmark_p50,
    b.as_of_week,
    pl.qty,
    cast((pl.unit_price - b.p25) * pl.qty as numeric(18, 5)) as savings_amount
from {{ ref('stg_purchase_lines') }} pl
join {{ ref('stg_items') }} i on i.item_id = pl.item_id
join latest_benchmark b on b.group_id = i.group_id
where pl.unit_price > b.p25
