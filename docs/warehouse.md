# Warehouse: Snowflake and dbt

Benchline's gold tables, loaded into a warehouse and modelled with dbt. Two models rebuild the service's
own SQL: the weekly percentile benchmark and the savings opportunity. The same project runs on DuckDB (local,
free) and Snowflake with no SQL changes.

```
data/silver/nadac.parquet ──► load_gold.py ──► raw.items, raw.price_points, raw.purchase_lines
                                                  │
                         staging views ◄──────────┘   stg_items, stg_price_points, stg_purchase_lines
                                │
                         marts (tables)               fct_group_benchmark_weekly, fct_savings_opportunity
```

## Models

| Model | What it is |
|---|---|
| `fct_group_benchmark_weekly` | p10 to p90 per product group and week: each product's latest NADAC rate as of the week end, within 52 weeks |
| `fct_savings_opportunity` | Synthetic purchase lines above their group's latest p25, with `(paid - p25) * qty` |

Percentiles are linear interpolation in exact decimal arithmetic (macro `linear_percentile`). The built-in
`percentile_cont` goes through floating point in DuckDB, and in PostgreSQL it only accepts floats, which
rounds a value that lands exactly halfway (0.050285) the wrong way.

## Tests

- **Unit tests** (dbt 1.8+): hand-computed percentiles for 0.1 to 0.5, the 52-week window, an exact half rounding
  up, and savings counting only lines above p25.
- **Data tests:** keys not null and unique, prices tied to known items, one row per group and week, percentiles in
  order, savings always positive.
- **Cross-check:** on the 12-drug data, all 681 weekly snapshots match the separate Python implementation behind the
  demo site, value for value.

## Run it locally (free)

```bash
cd warehouse
uv sync
uv run python load_gold.py
uv run dbt build --project-dir dbt --profiles-dir dbt
```

Data comes from `data/silver/nadac.parquet` (see the README for the pipeline). Use `--silver` for another file and
`--group-map data/silver/item_groups.parquet` to group by the normalized product instead of the description.

## Run it on Snowflake

1. Start a Snowflake trial and run [`warehouse/snowflake_setup.sql`](../warehouse/snowflake_setup.sql) in a worksheet
   (change `my_user` to your user name).
2. Set the connection, then load and build:

```bash
export SNOWFLAKE_ACCOUNT=<org-account> SNOWFLAKE_USER=<user> SNOWFLAKE_ROLE=benchline_dev
export SNOWFLAKE_WAREHOUSE=benchline_wh SNOWFLAKE_DATABASE=benchline
read -s "SNOWFLAKE_PASSWORD?Snowflake password: "; export SNOWFLAKE_PASSWORD
cd warehouse
uv run python load_gold.py --target snowflake
DBT_TARGET=snowflake uv run dbt build --project-dir dbt --profiles-dir dbt
```

The warehouse is X-Small and suspends after 60 idle seconds, so a full load and build uses very little of the
trial credit. Models land in `BENCHLINE.ANALYTICS`.
