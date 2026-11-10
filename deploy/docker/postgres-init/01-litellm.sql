-- LiteLLM keeps virtual keys and spend in its own database, apart from Benchline's.
-- Runs only when the data volume is first created. For an existing volume run:
--   docker compose exec postgres createdb -U benchline litellm
CREATE DATABASE litellm;
