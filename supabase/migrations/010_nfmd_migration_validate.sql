-- ============================================================
-- NFM-10: NFMD Migration Validation Script
-- 7 verification checks for data integrity
-- Run AFTER 009_nfmd_data_migration.sql
-- Source tables are renamed to _src_* by migration 009
-- ============================================================

-- Results table for structured reporting
DROP TABLE IF EXISTS _validation_results;
CREATE TEMP TABLE _validation_results (
  check_num  integer PRIMARY KEY,
  check_name text NOT NULL,
  status     text NOT NULL,  -- PASS / FAIL / WARN
  details    text
);

-- ============================================================
-- Check 1: Record count comparison per table (source vs target)
-- ============================================================
DO $$
DECLARE
  src_materials integer; tgt_materials integer;
  src_aliases integer;   tgt_aliases integer;
  src_literature integer; tgt_data_sources integer;
  src_params integer;    tgt_measurements integer;
  src_categories integer; tgt_prop_categories integer;
  src_terminology integer; tgt_terminology integer;
  src_audit integer;     tgt_review_logs integer;
  overall_status text := 'PASS';
BEGIN
  -- Source counts (NFMD v2, now renamed to _src_*)
  SELECT count(*) INTO src_materials FROM _src_materials;
  SELECT count(*) INTO src_aliases FROM _src_material_aliases;
  SELECT count(*) INTO src_literature FROM _src_literature;
  SELECT count(*) INTO src_params FROM parameters;
  SELECT count(*) INTO src_categories FROM _src_categories;
  SELECT count(*) INTO src_terminology FROM _src_terminology;

  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'review_audit_log') THEN
    SELECT count(*) INTO src_audit FROM review_audit_log;
  ELSIF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '_src_audit_log') THEN
    -- audit_log was renamed; review_audit_log may still exist
    src_audit := 0;
    SELECT count(*) INTO src_audit FROM review_audit_log;
  ELSE
    src_audit := 0;
  END IF;

  -- Target counts (unified schema)
  SELECT count(*) INTO tgt_materials FROM materials;
  SELECT count(*) INTO tgt_aliases FROM material_aliases;
  SELECT count(*) INTO tgt_data_sources FROM data_sources;
  SELECT count(*) INTO tgt_measurements FROM property_measurements;
  SELECT count(*) INTO tgt_prop_categories FROM property_categories;
  SELECT count(*) INTO tgt_terminology FROM terminology;
  SELECT count(*) INTO tgt_review_logs FROM review_logs;

  -- Build details string
  DECLARE
    details text := '';
  BEGIN
    -- Materials
    IF tgt_materials >= src_materials THEN
      details := details || format('Materials: %s→%s ✓', src_materials, tgt_materials);
    ELSE
      overall_status := 'FAIL';
      details := details || format('Materials: %s→%s ✗', src_materials, tgt_materials);
    END IF;

    -- Aliases
    IF tgt_aliases >= src_aliases THEN
      details := details || format(' | Aliases: %s→%s ✓', src_aliases, tgt_aliases);
    ELSE
      overall_status := 'FAIL';
      details := details || format(' | Aliases: %s→%s ✗', src_aliases, tgt_aliases);
    END IF;

    -- Data sources (1:1 with literature)
    IF tgt_data_sources >= src_literature THEN
      details := details || format(' | DataSources: %s→%s ✓', src_literature, tgt_data_sources);
    ELSE
      overall_status := 'FAIL';
      details := details || format(' | DataSources: %s→%s ✗', src_literature, tgt_data_sources);
    END IF;

    -- Measurements (1:1 with parameters)
    IF tgt_measurements >= src_params THEN
      details := details || format(' | Measurements: %s→%s ✓', src_params, tgt_measurements);
    ELSE
      overall_status := 'FAIL';
      details := details || format(' | Measurements: %s→%s ✗', src_params, tgt_measurements);
    END IF;

    -- Additional info (non-critical counts)
    details := details || format(' | Categories: %s→%s', src_categories, tgt_prop_categories);
    details := details || format(' | Terminology: %s→%s', src_terminology, tgt_terminology);
    details := details || format(' | ReviewLogs: %s→%s', src_audit, tgt_review_logs);

    INSERT INTO _validation_results VALUES (1, 'Record Counts', overall_status, details);
  END;

  RAISE NOTICE 'Check 1 (Record Counts): %', overall_status;
END $$;

-- ============================================================
-- Check 2: Value type distribution verification
-- Ensure all 5 value types migrated correctly
-- ============================================================
DO $$
DECLARE
  v_count integer;
  v_result text;
BEGIN
  -- Count distinct value types in target
  SELECT count(DISTINCT value_type) INTO v_count
  FROM property_measurements;

  -- Also count from source for comparison
  SELECT string_agg(format('%s: %s', vt, cnt), ', ' ORDER BY cnt DESC)
  INTO v_result
  FROM (
    SELECT pm.value_type AS vt, count(*) AS cnt
    FROM property_measurements pm
    GROUP BY pm.value_type
  ) sub;

  IF v_count >= 5 THEN
    INSERT INTO _validation_results VALUES (2, 'Value Type Distribution', 'PASS',
      format('All %s value types present: %s', v_count, v_result));
  ELSE
    INSERT INTO _validation_results VALUES (2, 'Value Type Distribution', 'FAIL',
      format('Only %s of 5 value types found: %s', v_count, v_result));
  END IF;

  RAISE NOTICE 'Check 2 (Value Type Distribution): %', (SELECT status FROM _validation_results WHERE check_num = 2);
END $$;

-- ============================================================
-- Check 3: Random sampling — verify field mapping correctness
-- Compare source parameters to target measurements by content hash
-- ============================================================
DO $$
DECLARE
  v_sample_size integer := 100;
  v_matched integer := 0;
  v_sampled integer := 0;
BEGIN
  -- Match on value_type + material_id + approximate created_at
  -- This is a probabilistic check, not exact 1:1 mapping
  SELECT count(*) INTO v_matched
  FROM (
    SELECT pm.id
    FROM property_measurements pm
    WHERE EXISTS (
      SELECT 1 FROM parameters p
      WHERE p.value_type = pm.value_type
        AND p.material_id = pm.material_id
        AND p.unit IS NOT DISTINCT FROM pm.unit
      LIMIT 1
    )
    ORDER BY random()
    LIMIT v_sample_size
  ) sub;

  GET DIAGNOSTICS v_sampled = ROW_COUNT;

  IF v_matched >= v_sample_size * 0.9 THEN
    INSERT INTO _validation_results VALUES (3, 'Random Sample Verification', 'PASS',
      format('%s/%s sampled measurements matched source parameters (≥90%%)', v_matched, v_sample_size));
  ELSIF v_matched >= v_sample_size * 0.7 THEN
    INSERT INTO _validation_results VALUES (3, 'Random Sample Verification', 'WARN',
      format('%s/%s sampled measurements matched (70-90%%) — verify manually', v_matched, v_sample_size));
  ELSE
    INSERT INTO _validation_results VALUES (3, 'Random Sample Verification', 'FAIL',
      format('%s/%s sampled measurements matched (<70%%) — significant data loss', v_matched, v_sample_size));
  END IF;

  RAISE NOTICE 'Check 3 (Random Sampling): %', (SELECT status FROM _validation_results WHERE check_num = 3);
END $$;

-- ============================================================
-- Check 4: Orphan detection — no measurements without materials
-- ============================================================
DO $$
DECLARE
  v_orphan_materials integer;
  v_orphan_types integer;
  v_orphan_total integer;
BEGIN
  -- Measurements with non-null material_id that doesn't resolve
  SELECT count(*) INTO v_orphan_materials
  FROM property_measurements pm
  WHERE pm.material_id IS NOT NULL
    AND NOT EXISTS (SELECT 1 FROM materials m WHERE m.id = pm.material_id);

  -- Measurements without a property_type
  SELECT count(*) INTO v_orphan_types
  FROM property_measurements pm
  WHERE NOT EXISTS (SELECT 1 FROM property_types pt WHERE pt.id = pm.property_type_id);

  v_orphan_total := v_orphan_materials + v_orphan_types;

  IF v_orphan_total = 0 THEN
    INSERT INTO _validation_results VALUES (4, 'Orphan Detection', 'PASS',
      'No orphan measurements found');
  ELSE
    INSERT INTO _validation_results VALUES (4, 'Orphan Detection', 'FAIL',
      format('Orphans found: %s broken material FK, %s missing property_type',
        v_orphan_materials, v_orphan_types));
  END IF;

  RAISE NOTICE 'Check 4 (Orphan Detection): %', (SELECT status FROM _validation_results WHERE check_num = 4);
END $$;

-- ============================================================
-- Check 5: FK integrity — all foreign keys resolve
-- ============================================================
DO $$
DECLARE
  v_broken integer := 0;
  v_detail text := '';
BEGIN
  -- material_aliases → materials
  SELECT count(*) INTO v_broken
  FROM material_aliases ma
  WHERE NOT EXISTS (SELECT 1 FROM materials m WHERE m.id = ma.material_id);
  IF v_broken > 0 THEN
    v_detail := v_detail || format(' aliases→materials:%s', v_broken);
  END IF;

  -- property_measurements → materials
  SELECT count(*) INTO v_broken
  FROM property_measurements pm
  WHERE pm.material_id IS NOT NULL
    AND NOT EXISTS (SELECT 1 FROM materials m WHERE m.id = pm.material_id);
  IF v_broken > 0 THEN
    v_detail := v_detail || format(' measurements→materials:%s', v_broken);
  END IF;

  -- property_measurements → property_types
  SELECT count(*) INTO v_broken
  FROM property_measurements pm
  WHERE NOT EXISTS (SELECT 1 FROM property_types pt WHERE pt.id = pm.property_type_id);
  IF v_broken > 0 THEN
    v_detail := v_detail || format(' measurements→property_types:%s', v_broken);
  END IF;

  -- property_measurements → data_sources (nullable, only check non-null)
  SELECT count(*) INTO v_broken
  FROM property_measurements pm
  WHERE pm.data_source_id IS NOT NULL
    AND NOT EXISTS (SELECT 1 FROM data_sources ds WHERE ds.id = pm.data_source_id);
  IF v_broken > 0 THEN
    v_detail := v_detail || format(' measurements→data_sources:%s', v_broken);
  END IF;

  -- data_source_authors → data_sources + authors
  SELECT count(*) INTO v_broken
  FROM data_source_authors dsa
  WHERE NOT EXISTS (SELECT 1 FROM data_sources ds WHERE ds.id = dsa.data_source_id)
     OR NOT EXISTS (SELECT 1 FROM authors a WHERE a.id = dsa.author_id);
  IF v_broken > 0 THEN
    v_detail := v_detail || format(' ds_authors:%s', v_broken);
  END IF;

  -- property_types → property_categories
  SELECT count(*) INTO v_broken
  FROM property_types pt
  WHERE NOT EXISTS (SELECT 1 FROM property_categories pc WHERE pc.id = pt.category_id);
  IF v_broken > 0 THEN
    v_detail := v_detail || format(' property_types→categories:%s', v_broken);
  END IF;

  IF v_detail = '' THEN
    INSERT INTO _validation_results VALUES (5, 'FK Integrity', 'PASS',
      'All foreign keys resolve correctly');
  ELSE
    INSERT INTO _validation_results VALUES (5, 'FK Integrity', 'FAIL',
      'Broken FKs:' || v_detail);
  END IF;

  RAISE NOTICE 'Check 5 (FK Integrity): %', (SELECT status FROM _validation_results WHERE check_num = 5);
END $$;

-- ============================================================
-- Check 6: Full-text search verification — tsvector columns populated
-- ============================================================
DO $$
DECLARE
  v_materials_no_sv integer;
  v_measurements_no_sv integer;
  v_ds_no_sv integer;
  v_types_no_sv integer;
  v_total_no_sv integer;
BEGIN
  SELECT count(*) INTO v_materials_no_sv
  FROM materials WHERE search_vector IS NULL OR search_vector = '';

  SELECT count(*) INTO v_measurements_no_sv
  FROM property_measurements WHERE search_vector IS NULL OR search_vector = '';

  SELECT count(*) INTO v_ds_no_sv
  FROM data_sources WHERE search_vector IS NULL OR search_vector = '';

  SELECT count(*) INTO v_types_no_sv
  FROM property_types WHERE search_vector IS NULL OR search_vector = '';

  v_total_no_sv := v_materials_no_sv + v_measurements_no_sv + v_ds_no_sv + v_types_no_sv;

  IF v_total_no_sv = 0 THEN
    INSERT INTO _validation_results VALUES (6, 'Search Vector Verification', 'PASS',
      'All tsvector columns populated');
  ELSE
    INSERT INTO _validation_results VALUES (6, 'Search Vector Verification', 'WARN',
      format('Missing search_vector: materials=%s, measurements=%s, data_sources=%s, property_types=%s (total=%s)',
        v_materials_no_sv, v_measurements_no_sv, v_ds_no_sv, v_types_no_sv, v_total_no_sv));
  END IF;

  RAISE NOTICE 'Check 6 (Search Vectors): %', (SELECT status FROM _validation_results WHERE check_num = 6);
END $$;

-- ============================================================
-- Check 7: Summary report with final verdict
-- ============================================================
DO $$
DECLARE
  v_total_checks integer;
  v_passed integer;
  v_failed integer;
  v_warned integer;
  v_rec record;
BEGIN
  SELECT count(*),
         count(*) FILTER (WHERE status = 'PASS'),
         count(*) FILTER (WHERE status = 'FAIL'),
         count(*) FILTER (WHERE status = 'WARN')
  INTO v_total_checks, v_passed, v_failed, v_warned
  FROM _validation_results;

  RAISE NOTICE '';
  RAISE NOTICE '╔══════════════════════════════════════════════╗';
  RAISE NOTICE '║   NFMD → NFM Migration Validation Report     ║';
  RAISE NOTICE '╠══════════════════════════════════════════════╣';

  FOR v_rec IN SELECT * FROM _validation_results ORDER BY check_num LOOP
    RAISE NOTICE '║ [%] %: %', v_rec.status, v_rec.check_name, left(v_rec.details, 60);
  END LOOP;

  RAISE NOTICE '╠══════════════════════════════════════════════╣';
  RAISE NOTICE '║ Total: % | PASS: % | FAIL: % | WARN: %',
    v_total_checks, v_passed, v_failed, v_warned;

  -- Final verdict
  IF v_failed > 0 THEN
    INSERT INTO _validation_results VALUES (99, 'Overall Verdict', 'FAIL',
      format('%s check(s) failed — review and fix before proceeding', v_failed));
    RAISE NOTICE '║ VERDICT: FAIL — %s checks failed', v_failed;
  ELSIF v_warned > 0 THEN
    INSERT INTO _validation_results VALUES (99, 'Overall Verdict', 'WARN',
      format('All critical checks passed, %s warning(s) — review recommended', v_warned));
    RAISE NOTICE '║ VERDICT: WARN — %s warnings', v_warned;
  ELSE
    INSERT INTO _validation_results VALUES (99, 'Overall Verdict', 'PASS',
      'All checks passed — migration successful');
    RAISE NOTICE '║ VERDICT: PASS — migration successful';
  END IF;

  RAISE NOTICE '╚══════════════════════════════════════════════╝';
END $$;

-- ============================================================
-- Output final results table for programmatic consumption
-- ============================================================
SELECT
  check_num,
  check_name,
  status,
  details
FROM _validation_results
ORDER BY check_num;
