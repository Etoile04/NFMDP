-- ============================================================
-- NFM-10: NFMD v2 → Unified Schema Data Migration
-- Migrates 16,379 parameters, 163 literature refs, 89 materials
-- Source: NFMD v2 schema (schema_v2.sql)
-- Target: NFM unified schema (001–008)
--
-- IMPORTANT: This migration must run AFTER migrations 001–008
-- which create the unified schema tables. Source NFMD v2 tables
-- are renamed to _src_* prefix at the start to avoid name
-- collisions with unified tables that share the same name
-- (materials, material_aliases, terminology).
-- ============================================================

BEGIN;

-- ============================================================
-- Step 0: Pre-flight checks
-- ============================================================
DO $$
DECLARE
  missing_tables text := '';
BEGIN
  -- Check unified schema target tables exist
  IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'property_measurements') THEN
    missing_tables := missing_tables || 'property_measurements, ';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'property_types') THEN
    missing_tables := missing_tables || 'property_types, ';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'data_sources') THEN
    missing_tables := missing_tables || 'data_sources, ';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users') THEN
    missing_tables := missing_tables || 'users, ';
  END IF;
  IF missing_tables <> '' THEN
    RAISE EXCEPTION 'Unified schema incomplete. Missing: %. Apply migrations 001-008 first.', rtrim(missing_tables, ', ');
  END IF;

  -- Check NFMD v2 source tables exist
  missing_tables := '';
  IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'parameters') THEN
    missing_tables := missing_tables || 'parameters, ';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'literature') THEN
    missing_tables := missing_tables || 'literature, ';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'materials') THEN
    missing_tables := missing_tables || 'materials, ';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'categories') THEN
    missing_tables := missing_tables || 'categories, ';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'terminology') THEN
    missing_tables := missing_tables || 'terminology, ';
  END IF;
  IF missing_tables <> '' THEN
    RAISE EXCEPTION 'NFMD v2 source tables missing: %. Ensure source data is loaded.', rtrim(missing_tables, ', ');
  END IF;
END $$;

-- ============================================================
-- Step 1: Rename source tables that share names with target
-- This prevents self-referencing INSERT...SELECT on same table
-- ============================================================
ALTER TABLE IF EXISTS materials RENAME TO _src_materials;
ALTER TABLE IF EXISTS material_aliases RENAME TO _src_material_aliases;
ALTER TABLE IF EXISTS categories RENAME TO _src_categories;
ALTER TABLE IF EXISTS terminology RENAME TO _src_terminology;
ALTER TABLE IF EXISTS literature RENAME TO _src_literature;
ALTER TABLE IF EXISTS audit_log RENAME TO _src_audit_log;

-- ============================================================
-- Step 2: Temporary mapping tables for FK resolution
-- ============================================================
CREATE TEMP TABLE _map_materials (
  old_uuid UUID PRIMARY KEY,
  new_uuid UUID NOT NULL
);

CREATE TEMP TABLE _map_literature (
  old_slug TEXT PRIMARY KEY,
  new_uuid UUID NOT NULL
);

CREATE TEMP TABLE _map_categories (
  old_name TEXT PRIMARY KEY,
  new_uuid UUID NOT NULL
);

CREATE TEMP TABLE _map_property_types (
  param_name TEXT,
  category TEXT,
  new_uuid UUID,
  PRIMARY KEY (param_name, category)
);

-- Track auto-created property types for reporting
CREATE TEMP TABLE _auto_created_types (
  name TEXT NOT NULL,
  slug TEXT NOT NULL,
  category TEXT
);

-- ============================================================
-- Step 3: System user for audit trail
-- ============================================================
INSERT INTO users (id, username, full_name, email, role)
VALUES (
  '00000000-0000-4000-a000-000000000001',
  'nfmd_migration',
  'NFMD Migration System',
  'system@nfm.internal',
  'system'
)
ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- Step 4: Materials migration (89 records)
-- material_type text → enum; density g/cm³ → kg/m³
-- ============================================================

-- 4a. Build the material_type text→enum mapping
CREATE TEMP TABLE _material_type_map (
  old_type TEXT PRIMARY KEY,
  new_type TEXT NOT NULL
);

INSERT INTO _material_type_map (old_type, new_type) VALUES
  ('FuelMaterial', 'fuel'),
  ('StructuralMaterial', 'structural'),
  ('CoolantMaterial', 'coolant'),
  ('CeramicMaterial', 'ceramic'),
  ('CladdingMaterial', 'cladding'),
  ('BarrierMaterial', 'barrier'),
  ('PureElement', 'pure_element'),
  ('FissionProduct', 'fission_product'),
  ('Additive', 'additive'),
  ('Composite', 'composite'),
  ('Other', 'other')
ON CONFLICT (old_type) DO NOTHING;

-- 4b. Migrate materials from _src_materials → materials
INSERT INTO materials (
  id, name, name_zh, chemical_formula,
  material_type, alloy_system, crystal_structure,
  density_kg_m3, melting_point_k, description,
  created_at, updated_at
)
SELECT
  m.id,
  m.name,
  m.name_zh,
  m.chemical_formula,
  COALESCE(tmap.new_type, 'other'),
  m.alloy_system,
  m.structure,
  CASE
    WHEN m.density IS NOT NULL THEN m.density * 1000.0
    ELSE NULL
  END,
  m.melting_point,
  m.description,
  m.created_at,
  COALESCE(m.updated_at, m.created_at)
FROM _src_materials m
LEFT JOIN _material_type_map tmap ON m.material_type = tmap.old_type
ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name,
  name_zh = EXCLUDED.name_zh,
  chemical_formula = EXCLUDED.chemical_formula,
  material_type = EXCLUDED.material_type,
  alloy_system = EXCLUDED.alloy_system,
  crystal_structure = EXCLUDED.crystal_structure,
  density_kg_m3 = EXCLUDED.density_kg_m3,
  melting_point_k = EXCLUDED.melting_point_k,
  description = EXCLUDED.description,
  updated_at = EXCLUDED.updated_at;

-- 4c. Populate mapping table (UUIDs preserved)
INSERT INTO _map_materials (old_uuid, new_uuid)
SELECT id, id FROM materials;

-- ============================================================
-- Step 5: Material aliases (367 records)
-- ============================================================
INSERT INTO material_aliases (alias, material_id)
SELECT
  ma.alias,
  mm.new_uuid
FROM _src_material_aliases ma
JOIN _map_materials mm ON ma.material_id = mm.old_uuid
ON CONFLICT (alias) DO NOTHING;

-- ============================================================
-- Step 6: Categories → property_categories (hierarchical tree)
-- ============================================================

-- 6a. Insert top-level categories (parent IS NULL)
INSERT INTO property_categories (id, name, slug, description, parent_id)
SELECT
  gen_random_uuid(),
  c.name,
  lower(replace(regexp_replace(c.name, '[^a-zA-Z0-9]+', '-', 'g'), '^-', '')),
  c.description,
  NULL
FROM _src_categories c
WHERE c.parent IS NULL
ON CONFLICT (slug) DO NOTHING;

-- 6b. Build mapping for top-level categories
INSERT INTO _map_categories (old_name, new_uuid)
SELECT c.name, pc.id
FROM _src_categories c
JOIN property_categories pc
  ON pc.slug = lower(replace(regexp_replace(c.name, '[^a-zA-Z0-9]+', '-', 'g'), '^-', ''))
WHERE c.parent IS NULL
ON CONFLICT (old_name) DO NOTHING;

-- 6c. Insert child categories (parent IS NOT NULL)
INSERT INTO property_categories (id, name, slug, description, parent_id)
SELECT
  gen_random_uuid(),
  c.name,
  lower(replace(regexp_replace(c.name, '[^a-zA-Z0-9]+', '-', 'g'), '^-', '')),
  c.description,
  pm.new_uuid
FROM _src_categories c
JOIN _map_categories pm ON c.parent = pm.old_name
WHERE c.parent IS NOT NULL
ON CONFLICT (slug) DO NOTHING;

-- 6d. Build mapping for child categories
INSERT INTO _map_categories (old_name, new_uuid)
SELECT c.name, pc.id
FROM _src_categories c
JOIN property_categories pc
  ON pc.slug = lower(replace(regexp_replace(c.name, '[^a-zA-Z0-9]+', '-', 'g'), '^-', ''))
WHERE c.parent IS NOT NULL
ON CONFLICT (old_name) DO NOTHING;

-- ============================================================
-- Step 7: Literature → data_sources + authors (163 records)
-- Split comma-separated author strings into individual records
-- ============================================================

-- 7a. Insert data_sources from literature
INSERT INTO data_sources (id, title, doi, journal, year, source_type, file_path, created_at)
SELECT
  gen_random_uuid(),
  l.title,
  l.doi,
  l.journal,
  l.year,
  'journal',
  l.file_path,
  l.created_at
FROM _src_literature l
ON CONFLICT DO NOTHING;

-- 7b. Populate literature mapping (match on title + year for determinism)
INSERT INTO _map_literature (old_slug, new_uuid)
SELECT l.id, ds.id
FROM _src_literature l
JOIN data_sources ds ON ds.title IS NOT DISTINCT FROM l.title
  AND ds.year IS NOT DISTINCT FROM l.year
  AND ds.created_at = l.created_at
ON CONFLICT (old_slug) DO NOTHING;

-- 7c. Extract and insert unique authors from comma/semicolon-separated strings
-- First, normalize separators: semicolons → commas
-- Then split on commas and trim whitespace
INSERT INTO authors (id, name)
SELECT DISTINCT gen_random_uuid(), trim(part)
FROM (
  SELECT unnest(regexp_split_to_array(
    regexp_replace(l.authors, ';\s*', ',', 'g'),
    ','
  )) AS part
  FROM _src_literature l
  WHERE l.authors IS NOT NULL AND l.authors <> ''
) sub
WHERE trim(part) <> ''
ON CONFLICT (name) DO NOTHING;

-- 7d. Link authors to data_sources with ordering
INSERT INTO data_source_authors (data_source_id, author_id, author_order)
SELECT
  ml.new_uuid,
  a.id,
  ord
FROM _src_literature l
JOIN _map_literature ml ON l.id = ml.old_slug
CROSS JOIN LATERAL unnest(
  regexp_split_to_array(
    regexp_replace(l.authors, ';\s*', ',', 'g'),
    ','
  )
) WITH ORDINALITY AS entry(name_str, ord)
JOIN authors a ON a.name = trim(entry.name_str)
WHERE trim(entry.name_str) <> ''
ON CONFLICT DO NOTHING;

-- ============================================================
-- Step 8: Parameters → property_measurements (16,379 records)
-- Build the property_type lookup + auto-create missing types
-- ============================================================

-- 8a. Build the property_type lookup from existing seed data
INSERT INTO _map_property_types (param_name, category, new_uuid)
SELECT pt.name, pc.name, pt.id
FROM property_types pt
JOIN property_categories pc ON pt.category_id = pc.id
ON CONFLICT DO NOTHING;

-- 8b. Auto-create property types for parameters that have a matching category
-- This ensures each unique (param_name, category) pair gets a property_type
INSERT INTO property_types (id, name, slug, category_id, unit, description, created_at)
SELECT DISTINCT
  gen_random_uuid(),
  p.name,
  lower(replace(regexp_replace(p.name, '[^a-zA-Z0-9]+', '-', 'g'), '^-', '')),
  mc.new_uuid,
  p.unit,
  COALESCE(p.name_en, p.name),
  now()
FROM parameters p
JOIN _map_categories mc ON p.category = mc.old_name
WHERE p.name IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM _map_property_types mpt
    WHERE mpt.param_name = p.name AND mpt.category = p.category
  )
ON CONFLICT (slug) DO NOTHING;

-- 8c. Rebuild mapping to include auto-created types
INSERT INTO _map_property_types (param_name, category, new_uuid)
SELECT pt.name, pc.name, pt.id
FROM property_types pt
JOIN property_categories pc ON pt.category_id = pc.id
ON CONFLICT DO NOTHING;

-- Track auto-created for reporting
INSERT INTO _auto_created_types (name, slug, category)
SELECT pt.name, pt.slug, pc.name
FROM property_types pt
JOIN property_categories pc ON pt.category_id = pc.id
WHERE pt.created_at >= now() - interval '1 minute';

-- 8d. Create "uncategorized" fallback property_type if not exists
INSERT INTO property_types (id, name, slug, category_id, description, created_at)
SELECT
  gen_random_uuid(),
  'Uncategorized',
  'uncategorized',
  (SELECT id FROM property_categories LIMIT 1),
  'Fallback for parameters without a matching property type',
  now()
WHERE NOT EXISTS (SELECT 1 FROM property_types WHERE slug = 'uncategorized');

-- ============================================================
-- Step 9: Migrate parameters → property_measurements
-- ============================================================
INSERT INTO property_measurements (
  id,
  property_type_id,
  material_id,
  data_source_id,
  value_type,
  value_scalar, value_min, value_max, value_expr, value_list, value_text,
  numeric_value,
  unit,
  uncertainty_value, uncertainty_type,
  conditions,
  confidence,
  method,
  notes,
  submitted_by,
  created_at,
  updated_at
)
SELECT
  gen_random_uuid(),

  -- 3-tier property_type resolution:
  --   Tier 1: exact (param_name, category) match
  --   Tier 2: fuzzy name match (same param_name, different category)
  --   Tier 3: "uncategorized" fallback
  COALESCE(
    pt_exact.new_uuid,
    pt_fuzzy.new_uuid,
    (SELECT id FROM property_types WHERE slug = 'uncategorized' LIMIT 1)
  ),

  -- Material FK (UUIDs preserved — unchanged)
  p.material_id,

  -- Data source FK from literature mapping
  ml.new_uuid,

  -- Value type (direct mapping)
  p.value_type,

  -- Value columns (pass through)
  p.value_scalar,
  p.value_min,
  p.value_max,
  p.value_expr,
  p.value_list,
  p.value_text,

  -- Canonical numeric value for sorting/filtering
  CASE p.value_type
    WHEN 'scalar' THEN p.value_scalar::numeric
    WHEN 'range' THEN (p.value_min + p.value_max) / 2.0
    ELSE NULL
  END,

  -- Unit
  p.unit,

  -- Uncertainty parsing: "±50%" → (50, 'relative_percent')
  --                     "±0.5"  → (0.5, 'absolute')
  CASE
    WHEN p.uncertainty ~ '±\s*[\d.]+\s*%' THEN
      regexp_replace(p.uncertainty, '.*±\s*([\d.]+)\s*%.*', '\1')::numeric
    WHEN p.uncertainty ~ '±\s*[\d.]+' THEN
      regexp_replace(p.uncertainty, '.*±\s*([\d.]+).*', '\1')::numeric
    ELSE NULL
  END,

  CASE
    WHEN p.uncertainty ~ '%' THEN 'relative_percent'
    WHEN p.uncertainty ~ '±\s*[\d.]+' THEN 'absolute'
    ELSE NULL
  END,

  -- Conditions → JSONB using jsonb_strip_nulls to remove null keys
  jsonb_strip_nulls(jsonb_build_object(
    'temperature_k', p.temperature_k,
    'temperature_str', nullif(p.temperature_str, ''),
    'burnup_range', nullif(p.burnup_range, ''),
    'method', nullif(p.method, ''),
    'subcategory', nullif(p.subcategory, ''),
    'equation', nullif(p.equation, ''),
    'symbol', nullif(p.symbol, ''),
    'name_zh', nullif(p.name_zh, ''),
    'name_en', nullif(p.name_en, ''),
    'source_file', nullif(p.source_file, ''),
    'material_raw', nullif(p.material_raw, '')
  )),

  -- Confidence (text values: high, medium, low)
  p.confidence,

  -- Method
  p.method,

  -- Notes
  p.notes,

  -- Submitted by (system user)
  '00000000-0000-4000-a000-000000000001'::uuid,

  -- Timestamps
  p.created_at,
  COALESCE(p.created_at, now())

FROM parameters p

-- Tier 1: exact (param_name, category) match
LEFT JOIN _map_property_types pt_exact
  ON pt_exact.param_name = p.name
  AND pt_exact.category = p.category

-- Tier 2: fuzzy match — same param_name, any category
LEFT JOIN LATERAL (
  SELECT mpt.new_uuid
  FROM _map_property_types mpt
  WHERE mpt.param_name = p.name
    AND pt_exact.new_uuid IS NULL
  ORDER BY mpt.category = p.category DESC  -- prefer same category
  LIMIT 1
) pt_fuzzy ON pt_exact.new_uuid IS NULL

-- Literature mapping via source_file
LEFT JOIN LATERAL (
  SELECT ml2.new_uuid
  FROM _map_literature ml2
  WHERE
    -- Exact match: strip summaries/ prefix and .md extension
    ml2.old_slug = regexp_replace(
      regexp_replace(COALESCE(p.source_file, ''), '^summaries/', ''),
      '\.(md|txt\.md)$', ''
    )
    -- Fallback: source_file starts with literature slug
    OR (
      p.source_file IS NOT NULL
      AND ml2.old_slug = split_part(
        regexp_replace(p.source_file, '^summaries/', ''), '.', 1
      )
  ORDER BY
    -- Prefer exact matches over fallback matches
    (ml2.old_slug = regexp_replace(
      regexp_replace(COALESCE(p.source_file, ''), '^summaries/', ''),
      '\.(md|txt\.md)$', ''
    )) DESC
  LIMIT 1
) ml ON true;

-- ============================================================
-- Step 10: Terminology (direct copy from renamed source)
-- ============================================================
INSERT INTO terminology (term_zh, term_en, category, created_at)
SELECT
  t.term_zh,
  t.term_en,
  t.category,
  COALESCE(t.created_at, now())
FROM _src_terminology t
WHERE t.term_zh IS NOT NULL
ON CONFLICT (term_zh) DO UPDATE SET
  term_en = EXCLUDED.term_en,
  category = EXCLUDED.category;

-- ============================================================
-- Step 11: Review audit log → review_logs (FK resolution)
-- ============================================================
INSERT INTO review_logs (table_name, record_id, action, old_status, new_status, changes, reviewer, notes, created_at)
SELECT
  ral.table_name,
  ral.record_id,
  ral.action,
  ral.old_status,
  ral.new_status,
  ral.changes,
  COALESCE(ral.reviewer, 'nfmd_migration'),
  ral.notes,
  ral.created_at
FROM review_audit_log ral;

-- Also migrate the old audit_log table if it was renamed
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '_src_audit_log') THEN
    INSERT INTO review_logs (table_name, record_id, action, old_status, new_status, changes, reviewer, notes, created_at)
    SELECT
      al.table_name,
      al.record_id,
      al.action,
      NULL,
      NULL,
      al.changes,
      COALESCE(al.operator, 'nfmd_migration'),
      NULL,
      al.timestamp
    FROM _src_audit_log al;
  END IF;
END $$;

-- ============================================================
-- Step 12: Refresh search vectors
-- ============================================================

-- Refresh materials search vectors
UPDATE materials m SET search_vector =
  setweight(to_tsvector('english', coalesce(m.name, '')), 'A') ||
  setweight(to_tsvector('english', coalesce(m.chemical_formula, '')), 'B') ||
  setweight(to_tsvector('english', coalesce(m.alloy_system, '')), 'C') ||
  setweight(to_tsvector('english', coalesce(m.description, '')), 'D')
WHERE m.search_vector IS NULL OR m.search_vector = '';

-- Refresh property_measurements search vectors
UPDATE property_measurements pm SET search_vector =
  setweight(to_tsvector('english', coalesce(
    (SELECT pt.name FROM property_types pt WHERE pt.id = pm.property_type_id), '')), 'A') ||
  setweight(to_tsvector('english', coalesce(
    (SELECT m.name FROM materials m WHERE m.id = pm.material_id), '')), 'B') ||
  setweight(to_tsvector('english', coalesce(pm.unit, '')), 'C') ||
  setweight(to_tsvector('english', coalesce(pm.notes, '')), 'D')
WHERE pm.search_vector IS NULL OR pm.search_vector = '';

-- Refresh property_types search vectors
UPDATE property_types pt SET search_vector =
  setweight(to_tsvector('english', coalesce(pt.name, '')), 'A') ||
  setweight(to_tsvector('english', coalesce(pt.description, '')), 'C')
WHERE pt.search_vector IS NULL OR pt.search_vector = '';

-- Refresh data_sources search vectors
UPDATE data_sources ds SET search_vector =
  setweight(to_tsvector('english', coalesce(ds.title, '')), 'A') ||
  setweight(to_tsvector('english', coalesce(ds.journal, '')), 'C') ||
  setweight(to_tsvector('english', coalesce(
    (SELECT string_agg(a.name, ' ') FROM data_source_authors dsa
     JOIN authors a ON a.id = dsa.author_id WHERE dsa.data_source_id = ds.id), '')), 'B')
WHERE ds.search_vector IS NULL OR ds.search_vector = '';

-- ============================================================
-- Step 13: Migration summary report
-- ============================================================
DO $$
DECLARE
  v_materials_count integer;
  v_aliases_count integer;
  v_categories_count integer;
  v_data_sources_count integer;
  v_authors_count integer;
  v_measurements_count integer;
  v_terminology_count integer;
  v_review_logs_count integer;
  v_auto_types_count integer;
  v_src_materials integer;
  v_src_params integer;
BEGIN
  SELECT count(*) INTO v_materials_count FROM materials;
  SELECT count(*) INTO v_aliases_count FROM material_aliases;
  SELECT count(*) INTO v_categories_count FROM property_categories;
  SELECT count(*) INTO v_data_sources_count FROM data_sources;
  SELECT count(*) INTO v_authors_count FROM authors;
  SELECT count(*) INTO v_measurements_count FROM property_measurements;
  SELECT count(*) INTO v_terminology_count FROM terminology;
  SELECT count(*) INTO v_review_logs_count FROM review_logs;
  SELECT count(*) INTO v_auto_types_count FROM _auto_created_types;
  SELECT count(*) INTO v_src_materials FROM _src_materials;
  SELECT count(*) INTO v_src_params FROM parameters;

  RAISE NOTICE '';
  RAISE NOTICE '╔══════════════════════════════════════════════╗';
  RAISE NOTICE '║     NFMD → NFM Migration Summary             ║';
  RAISE NOTICE '╠══════════════════════════════════════════════╣';
  RAISE NOTICE '║ Source: % materials, % parameters', v_src_materials, v_src_params;
  RAISE NOTICE '║ Materials:        %', v_materials_count;
  RAISE NOTICE '║ Material aliases: %', v_aliases_count;
  RAISE NOTICE '║ Property categories: %', v_categories_count;
  RAISE NOTICE '║ Data sources:     %', v_data_sources_count;
  RAISE NOTICE '║ Authors:          %', v_authors_count;
  RAISE NOTICE '║ Measurements:     %', v_measurements_count;
  RAISE NOTICE '║ Terminology:      %', v_terminology_count;
  RAISE NOTICE '║ Review logs:      %', v_review_logs_count;
  RAISE NOTICE '║ Auto-created types: %', v_auto_types_count;
  RAISE NOTICE '╚══════════════════════════════════════════════╝';
END $$;

COMMIT;
