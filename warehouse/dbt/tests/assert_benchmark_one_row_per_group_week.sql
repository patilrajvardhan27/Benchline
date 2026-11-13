select group_id, as_of_week
from {{ ref('fct_group_benchmark_weekly') }}
group by group_id, as_of_week
having count(*) > 1
