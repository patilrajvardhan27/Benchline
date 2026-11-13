{#- Linear-interpolation percentile in exact decimal arithmetic over a ranked set
    (columns idx from 0 and n). Built-in percentile_cont goes through floats. -#}
{% macro linear_percentile(q) -%}
{%- set position = q ~ ' * (max(n) - 1)' -%}
{%- set lower = 'max(case when idx = floor(' ~ q ~ ' * (n - 1)) then price end)' -%}
{%- set upper = 'max(case when idx = floor(' ~ q ~ ' * (n - 1)) + 1 then price end)' -%}
cast(round({{ lower }} + (coalesce({{ upper }}, {{ lower }}) - {{ lower }})
     * ({{ position }} - floor({{ position }})), 5) as numeric(14, 5))
{%- endmacro %}
