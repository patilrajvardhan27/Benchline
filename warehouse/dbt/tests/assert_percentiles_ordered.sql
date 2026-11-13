select *
from {{ ref('fct_group_benchmark_weekly') }}
where not (p10 <= p25 and p25 <= p50 and p50 <= p75 and p75 <= p90) or n_obs < 1
