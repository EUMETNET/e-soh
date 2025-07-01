ALTER TABLE geo_point ADD COLUMN camsl INTEGER;

-- drop UNIQUE constraint of 'point' column
-- WARNING: we assume that the constraint name is the correct one (it was never explicitly set)
ALTER TABLE geo_point DROP CONSTRAINT geo_point_point_key;

-- and instead define a UNIQUE constraint on the combination of the 'point' and 'camsl' columns
-- (note how we name the new constraint explicitly this time!)
ALTER TABLE geo_point ADD CONSTRAINT geo_point_point_camsl_key UNIQUE NULLS NOT DISTINCT (point, camsl);
