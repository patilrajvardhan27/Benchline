-- Synthetic demo purchases, generated with a fixed seed.
select
    purchase_line_id,
    facility_id,
    item_id,
    cast(unit_price as numeric(14, 5)) as unit_price,
    qty,
    cast(purchased_on as date) as purchased_on
from {{ source('raw', 'purchase_lines') }}
