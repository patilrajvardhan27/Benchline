select *
from {{ ref('fct_savings_opportunity') }}
where savings_amount <= 0 or paid_unit_price <= benchmark_p25
