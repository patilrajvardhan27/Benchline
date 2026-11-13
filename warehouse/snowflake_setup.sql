-- One-time setup in a Snowflake trial account. Run as ACCOUNTADMIN in a Snowsight worksheet.
-- An X-Small warehouse that suspends after 60 idle seconds keeps the trial credits for a long time.

create warehouse if not exists benchline_wh
  warehouse_size = xsmall
  auto_suspend = 60
  auto_resume = true
  initially_suspended = true;

create database if not exists benchline;
create schema if not exists benchline.raw;
create schema if not exists benchline.analytics;

create role if not exists benchline_dev;
grant usage on warehouse benchline_wh to role benchline_dev;
grant usage on database benchline to role benchline_dev;
grant all on schema benchline.raw to role benchline_dev;
grant all on schema benchline.analytics to role benchline_dev;
grant create schema on database benchline to role benchline_dev;

-- Replace with your own user name.
grant role benchline_dev to user my_user;
