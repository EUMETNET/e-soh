ALTER TABLE geo_point DROP CONSTRAINT geo_point_point_camsl_key;
ALTER TABLE geo_point ADD CONSTRAINT geo_point_point_key UNIQUE (point);
ALTER TABLE geo_point DROP COLUMN camsl;
