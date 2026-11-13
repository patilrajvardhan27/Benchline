-- Prices arrive as decimal strings so no float ever touches money.
select
    item_id,
    source,
    cast(unit_price as numeric(14, 5)) as unit_price,
    pricing_unit,
    cast(effective_date as date) as effective_date,
    cast(as_of_date as date) as as_of_date
from {{ source('raw', 'price_points') }}
