ALTER TABLE observation ADD COLUMN quality_code BIGINT;
ALTER TABLE time_series ADD COLUMN quality_code_vocabulary TEXT;
