-- This can not run in a transaction, so it needs to be in a separate migration file, see:
-- https://github.com/golang-migrate/migrate/tree/master/database/postgres#multi-statement-mode
CREATE INDEX CONCURRENTLY IF NOT EXISTS time_series_api_idx ON time_series USING gist (platform gist_trgm_ops, parameter_name gist_trgm_ops, standard_name gist_trgm_ops, level, function gist_trgm_ops, period);
