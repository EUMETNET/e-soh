-- Example generated SQL for upserting 2 points (constructed in getGeoPointIDs)
 WITH input_rows AS (
         SELECT * FROM (
                 (SELECT point FROM geo_point LIMIT 0)  -- only copies column names and types
                 UNION ALL
                 VALUES (ST_MakePoint($1, $2)::geography),(ST_MakePoint($3, $4)::geography)
         ) t ORDER BY point  -- ORDER BY for consistent order to avoid deadlocks
 )
                        , ins AS (
         INSERT INTO geo_point (point)
                 SELECT * FROM input_rows
                 ON CONFLICT (point) DO NOTHING
                 RETURNING id, point
 )
 SELECT id, point FROM ins
 UNION
 SELECT c.id, point FROM input_rows
 JOIN geo_point c USING (point);


-- Example generated SQL for upserting 2 timeseries (constructed in getUpsertStatement)
WITH input_rows AS (SELECT *
                    FROM (SELECT *
                          FROM (VALUES ((NULL::time_series).link_href, (NULL::time_series).link_rel,
                                        (NULL::time_series).link_type, (NULL::time_series).link_hreflang,
                                        (NULL::time_series).link_title, (NULL::time_series).level,
                                        (NULL::time_series).period, (NULL::time_series).version,
                                        (NULL::time_series).type, (NULL::time_series).title,
                                        (NULL::time_series).summary, (NULL::time_series).keywords,
                                        (NULL::time_series).keywords_vocabulary, (NULL::time_series).license,
                                        (NULL::time_series).conventions, (NULL::time_series).naming_authority,
                                        (NULL::time_series).creator_type, (NULL::time_series).creator_name,
                                        (NULL::time_series).creator_email, (NULL::time_series).creator_url,
                                        (NULL::time_series).institution, (NULL::time_series).project,
                                        (NULL::time_series).source, (NULL::time_series).platform,
                                        (NULL::time_series).platform_vocabulary, (NULL::time_series).platform_name,
                                        (NULL::time_series).standard_name, (NULL::time_series).unit,
                                        (NULL::time_series).function, (NULL::time_series).instrument,
                                        (NULL::time_series).instrument_vocabulary, (NULL::time_series).parameter_name,
                                        (NULL::time_series).timeseries_id,
                                        (NULL::time_series).quality_code_vocabulary), -- header column to get correct column types
                                       ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18,
                                        $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29, $30, $31, $32, $33, $34),
                                       ($35, $36, $37, $38, $39, $40, $41, $42, $43, $44, $45, $46, $47, $48, $49, $50,
                                        $51, $52, $53, $54, $55, $56, $57, $58, $59, $60, $61, $62, $63, $64, $65, $66,
                                        $67, $68) -- actual values
                               ) t (link_href, link_rel, link_type, link_hreflang, link_title, level, period, version,
                                    type, title, summary, keywords, keywords_vocabulary, license, conventions,
                                    naming_authority, creator_type, creator_name, creator_email, creator_url,
                                    institution, project, source, platform, platform_vocabulary, platform_name,
                                    standard_name, unit, function, instrument, instrument_vocabulary, parameter_name,
                                    timeseries_id, quality_code_vocabulary)
                          OFFSET 1) t
                    ORDER BY naming_authority, platform, standard_name, level, function, period,
                             instrument -- ORDER BY for consistent order to avoid deadlocks
)
   , ins AS (
    INSERT INTO time_series (link_href, link_rel, link_type, link_hreflang, link_title, level, period, version, type,
                             title, summary, keywords, keywords_vocabulary, license, conventions, naming_authority,
                             creator_type, creator_name, creator_email, creator_url, institution, project, source,
                             platform, platform_vocabulary, platform_name, standard_name, unit, function, instrument,
                             instrument_vocabulary, parameter_name, timeseries_id, quality_code_vocabulary)
        SELECT * FROM input_rows
        ON CONFLICT ON CONSTRAINT unique_main
            DO UPDATE SET link_rel = EXCLUDED.link_rel,keywords = EXCLUDED.keywords,conventions = EXCLUDED.conventions,platform_name = EXCLUDED.platform_name,quality_code_vocabulary = EXCLUDED.quality_code_vocabulary,summary = EXCLUDED.summary,project = EXCLUDED.project,source = EXCLUDED.source,title = EXCLUDED.title,platform_vocabulary = EXCLUDED.platform_vocabulary,license = EXCLUDED.license,creator_type = EXCLUDED.creator_type,version = EXCLUDED.version,instrument_vocabulary = EXCLUDED.instrument_vocabulary,link_type = EXCLUDED.link_type,link_hreflang = EXCLUDED.link_hreflang,type = EXCLUDED.type,keywords_vocabulary = EXCLUDED.keywords_vocabulary,timeseries_id = EXCLUDED.timeseries_id,link_href = EXCLUDED.link_href,link_title = EXCLUDED.link_title,creator_url = EXCLUDED.creator_url,parameter_name = EXCLUDED.parameter_name,creator_name = EXCLUDED.creator_name,creator_email = EXCLUDED.creator_email,institution = EXCLUDED.institution,unit = EXCLUDED.unit -- do update of fields not in unique constraint
                WHERE time_series.link_href IS DISTINCT FROM EXCLUDED.link_href OR
                      time_series.link_hreflang IS DISTINCT FROM EXCLUDED.link_hreflang OR
                      time_series.creator_email IS DISTINCT FROM EXCLUDED.creator_email OR
                      time_series.type IS DISTINCT FROM EXCLUDED.type OR
                      time_series.keywords IS DISTINCT FROM EXCLUDED.keywords OR
                      time_series.instrument_vocabulary IS DISTINCT FROM EXCLUDED.instrument_vocabulary OR
                      time_series.quality_code_vocabulary IS DISTINCT FROM EXCLUDED.quality_code_vocabulary OR
                      time_series.summary IS DISTINCT FROM EXCLUDED.summary OR
                      time_series.creator_name IS DISTINCT FROM EXCLUDED.creator_name OR
                      time_series.project IS DISTINCT FROM EXCLUDED.project OR
                      time_series.timeseries_id IS DISTINCT FROM EXCLUDED.timeseries_id OR
                      time_series.link_type IS DISTINCT FROM EXCLUDED.link_type OR
                      time_series.conventions IS DISTINCT FROM EXCLUDED.conventions OR
                      time_series.creator_url IS DISTINCT FROM EXCLUDED.creator_url OR
                      time_series.platform_vocabulary IS DISTINCT FROM EXCLUDED.platform_vocabulary OR
                      time_series.parameter_name IS DISTINCT FROM EXCLUDED.parameter_name OR
                      time_series.link_rel IS DISTINCT FROM EXCLUDED.link_rel OR
                      time_series.creator_type IS DISTINCT FROM EXCLUDED.creator_type OR
                      time_series.source IS DISTINCT FROM EXCLUDED.source OR
                      time_series.platform_name IS DISTINCT FROM EXCLUDED.platform_name OR
                      time_series.link_title IS DISTINCT FROM EXCLUDED.link_title OR
                      time_series.version IS DISTINCT FROM EXCLUDED.version OR
                      time_series.license IS DISTINCT FROM EXCLUDED.license OR
                      time_series.title IS DISTINCT FROM EXCLUDED.title OR
                      time_series.institution IS DISTINCT FROM EXCLUDED.institution OR
                      time_series.keywords_vocabulary IS DISTINCT FROM EXCLUDED.keywords_vocabulary OR
                      time_series.unit IS DISTINCT FROM EXCLUDED.unit -- only if at least one value is actually different, to avoid table churn
        RETURNING id, naming_authority,platform,standard_name,level,function,period,instrument -- RETURNING only gives back rows that were actually inserted or modified
)
SELECT id,
       naming_authority,
       platform,
       standard_name,
       level,
       function,
       period,
       instrument -- magic to get the id's for all rows'
FROM ins
UNION
SELECT ts.id,
       naming_authority,
       platform,
       standard_name,
       level,
       function,
       period,
       instrument
FROM input_rows
         JOIN time_series ts USING (naming_authority, platform, standard_name, level, function, period, instrument);


-- Example generated SQL for upserting 2 observations (constructed in upsertObs)
INSERT INTO observation (ts_id,
                         obstime_instant,
                         id,
                         geo_point_id,
                         pubtime,
                         data_id,
                         history,
                         processing_level,
                         quality_code,
                         value)
VALUES ($1,
        to_timestamp($2),
        $3,
        $4,
        to_timestamp($5),
        $6,
        $7,
        $8,
        $9,
        $10),
       ($12,
        to_timestamp($13),
        $14,
        $15,
        to_timestamp($16),
        $17,
        $18,
        $19,
        $20,
        $21)
ON CONFLICT ON CONSTRAINT observation_pkey DO UPDATE
    SET id               = EXCLUDED.id,
        geo_point_id     = EXCLUDED.geo_point_id,
        pubtime          = EXCLUDED.pubtime,
        data_id          = EXCLUDED.data_id,
        history          = EXCLUDED.history,
        processing_level = EXCLUDED.processing_level,
        quality_code     = EXCLUDED.quality_code,
        value            = EXCLUDED.value
WHERE observation.id IS DISTINCT FROM EXCLUDED.id
   OR observation.geo_point_id IS DISTINCT FROM EXCLUDED.geo_point_id
   OR observation.pubtime IS DISTINCT FROM EXCLUDED.pubtime
   OR observation.data_id IS DISTINCT FROM EXCLUDED.data_id
   OR observation.history IS DISTINCT FROM EXCLUDED.history
   OR observation.processing_level IS DISTINCT FROM EXCLUDED.processing_level
   OR observation.quality_code IS DISTINCT FROM EXCLUDED.quality_code
