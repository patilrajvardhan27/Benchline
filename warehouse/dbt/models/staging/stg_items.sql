select
    item_id,
    ndc11,
    description,
    group_id,
    group_name
from {{ source('raw', 'items') }}
