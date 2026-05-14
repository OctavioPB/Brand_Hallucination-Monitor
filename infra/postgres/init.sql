-- init.sql — runs on first Postgres container start
-- Creates the airflow database alongside the main hallucin8 DB.

CREATE DATABASE airflow;
GRANT ALL PRIVILEGES ON DATABASE airflow TO hallucin8;
