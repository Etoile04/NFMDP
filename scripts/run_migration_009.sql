-- NFMDP Data Migration — Single-session execution
-- Run against: supabase_db_workspace (port 54322)
-- Prerequisites: source tables renamed to _src_*, unified schema applied

BEGIN;

-- ============================================================
-- System user
-- ============================================================
INSERT INTO users (id, username, full_name, email, role)
VALUES ('00000000-0000-4000-a000-000000000001', 'nfmd_migration', 'NFMD Migration System', 'system@nfm.internal', 'system')
ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- Temp mapping tables
-- ============================================================
CREATE TEMP TABLE _map_materials (old_uuid UUID PRIMARY KEY, new_uuid UUID NOT NULL);
CREATE TEMP TABLE _map_literature (old_slug TEXT PRIMARY KEY, new_uuid UUID NOT NULL);
CREATE TEMP TABLE _map_categories (old_name TEXT PRIMARY KEY, new_uuid UUID NOT NULL);
CREATE TEMP TABLE _map_property_types (param_name TEXT, category TEXT, new_uuid UUID, PRIMARY KEY (param_name, category));
CREATE TEMP TABLE _auto_created_types (name TEXT NOT NULL, slug TEXT NOT NULL, category TEXT);

CREATE TEMP TABLE _material_type_map (old_type TEXT PRIMARY KEY, new_type TEXT NOT NULL);
INSERT INTO _material_type_map VALUES
  ('FuelMaterial','fuel'),('StructuralMaterial','structural'),('CoolantMaterial','coolant'),
  ('CeramicMaterial','ceramic'),('CladdingMaterial','cladding'),('BarrierMaterial','barrier'),
  ('PureElement','pure_element'),('FissionProduct','fission_product'),('Additive','additive'),
  ('Composite','composite'),('Other','other') ON CONFLICT DO NOTHING;

-- ============================================================
-- Materials (89)
-- ============================================================
INSERT INTO materials (id, name, name_zh, chemical_formula, material_type, alloy_system, crystal_structure, density_kg_m3, melting_point_k, description, created_at, updated_at)
SELECT
  m.id, m.name, m.name_zh, m.chemical_formula,
  COALESCE(tmap.new_type, 'other')::material_type_enum,
  m.alloy_system, m.structure,
  CASE WHEN m.density IS NOT NULL THEN m.density * 1000.0 ELSE NULL END,
  m.melting_point, m.description,
  m.created_at, COALESCE(m.updated_at, m.created_at)
FROM _src_materials m
LEFT JOIN _material_type_map tmap ON m.material_type = tmap.old_type
ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name, material_type = EXCLUDED.material_type,
  density_kg_m3 = EXCLUDED.density_kg_m3, updated_at = EXCLUDED.updated_at;

INSERT INTO _map_materials (old_uuid, new_uuid) SELECT id, id FROM materials;

-- ============================================================
-- Material aliases (367)
-- ============================================================
INSERT INTO material_aliases (alias, material_id)
SELECT ma.alias, mm.new_uuid
FROM _src_material_aliases ma
JOIN _map_materials mm ON ma.material_id = mm.old_uuid
ON CONFLICT (alias) DO NOTHING;

-- ============================================================
-- Categories → property_categories
-- ============================================================
INSERT INTO property_categories (id, name, slug, description, parent_id)
SELECT gen_random_uuid(), c.name,
  lower(replace(regexp_replace(c.name, '[^a-zA-Z0-9]+', '-', 'g'), '^-', '')),
  c.description, NULL
FROM _src_categories c WHERE c.parent IS NULL
ON CONFLICT (slug) DO NOTHING;

INSERT INTO _map_categories (old_name, new_uuid)
SELECT c.name, pc.id FROM _src_categories c
JOIN property_categories pc ON pc.slug = lower(replace(regexp_replace(c.name, '[^a-zA-Z0-9]+', '-', 'g'), '^-', ''))
WHERE c.parent IS NULL
ON CONFLICT DO NOTHING;

INSERT INTO property_categories (id, name, slug, description, parent_id)
SELECT gen_random_uuid(), c.name,
  lower(replace(regexp_replace(c.name, '[^a-zA-Z0-9]+', '-', 'g'), '^-', '')),
  c.description, pm.new_uuid
FROM _src_categories c
JOIN _map_categories pm ON c.parent = pm.old_name
WHERE c.parent IS NOT NULL
ON CONFLICT (slug) DO NOTHING;

INSERT INTO _map_categories (old_name, new_uuid)
SELECT c.name, pc.id FROM _src_categories c
JOIN property_categories pc ON pc.slug = lower(replace(regexp_replace(c.name, '[^a-zA-Z0-9]+', '-', 'g'), '^-', ''))
WHERE c.parent IS NOT NULL
ON CONFLICT DO NOTHING;

-- ============================================================
-- Literature → data_sources + authors (163)
-- ============================================================
INSERT INTO data_sources (id, title, doi, journal, year, source_type, file_path, created_at)
SELECT gen_random_uuid(), l.title, l.doi, l.journal, l.year, 'journal', l.file_path, l.created_at
FROM _src_literature l
ON CONFLICT DO NOTHING;

INSERT INTO _map_literature (old_slug, new_uuid)
SELECT l.id, ds.id FROM _src_literature l
JOIN data_sources ds ON ds.title IS NOT DISTINCT FROM l.title
  AND ds.year IS NOT DISTINCT FROM l.year AND ds.created_at = l.created_at
ON CONFLICT DO NOTHING;

INSERT INTO authors (id, name)
SELECT DISTINCT gen_random_uuid(), trim(part)
FROM (SELECT unnest(regexp_split_to_array(regexp_replace(l.authors, ';\s*', ',', 'g'), ',')) AS part
      FROM _src_literature l WHERE l.authors IS NOT NULL AND l.authors <> '') sub
WHERE trim(part) <> ''
ON CONFLICT (name) DO NOTHING;

INSERT INTO data_source_authors (data_source_id, author_id, author_order)
SELECT ml.new_uuid, a.id, ord
FROM _src_literature l
JOIN _map_literature ml ON l.id = ml.old_slug
CROSS JOIN LATERAL unnest(regexp_split_to_array(regexp_replace(l.authors, ';\s*', ',', 'g'), ',')) WITH ORDINALITY AS entry(name_str, ord)
JOIN authors a ON a.name = trim(entry.name_str)
WHERE trim(entry.name_str) <> ''
ON CONFLICT DO NOTHING;

-- ============================================================
-- Property types: build lookup + auto-create
-- ============================================================
INSERT INTO _map_property_types (param_name, category, new_uuid)
SELECT pt.name, pc.name, pt.id
FROM property_types pt JOIN property_categories pc ON pt.category_id = pc.id
ON CONFLICT DO NOTHING;

INSERT INTO property_types (id, name, slug, category_id, unit, description, created_at)
SELECT DISTINCT gen_random_uuid(), p.name,
  lower(replace(regexp_replace(p.name, '[^a-zA-Z0-9]+', '-', 'g'), '^-', '')),
  mc.new_uuid, p.unit, COALESCE(p.name_en, p.name), now()
FROM parameters p
JOIN _map_categories mc ON p.category = mc.old_name
WHERE p.name IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM _map_property_types mpt WHERE mpt.param_name = p.name AND mpt.category = p.category)
ON CONFLICT (slug) DO NOTHING;

INSERT INTO _map_property_types (param_name, category, new_uuid)
SELECT pt.name, pc.name, pt.id
FROM property_types pt JOIN property_categories pc ON pt.category_id = pc.id
ON CONFLICT DO NOTHING;

-- Fallback: uncategorized type
INSERT INTO property_types (id, name, slug, category_id, description, created_at)
SELECT gen_random_uuid(), 'Uncategorized', 'uncategorized',
  (SELECT id FROM property_categories LIMIT 1),
  'Fallback for unmatched parameters', now()
WHERE NOT EXISTS (SELECT 1 FROM property_types WHERE slug = 'uncategorized');

-- ============================================================
-- Parameters → property_measurements (16,379)
-- ============================================================
INSERT INTO property_measurements (
  id, property_type_id, material_id, data_source_id,
  value_type, value_scalar, value_min, value_max, value_expr, value_list, value_text,
  numeric_value, unit, uncertainty_value, uncertainty_type, conditions,
  confidence, method, notes, submitted_by, created_at, updated_at
)
SELECT
  gen_random_uuid(),
  COALESCE(pt_exact.new_uuid, pt_fuzzy.new_uuid,
    (SELECT id FROM property_types WHERE slug = 'uncategorized' LIMIT 1)),
  p.material_id,
  ml.new_uuid,
  p.value_type::measurement_value_type,
  p.value_scalar, p.value_min, p.value_max, p.value_expr, p.value_list, p.value_text,
  CASE p.value_type WHEN 'scalar' THEN p.value_scalar::numeric
    WHEN 'range' THEN (p.value_min + p.value_max) / 2.0 ELSE NULL END,
  p.unit,
  CASE WHEN p.uncertainty ~ '±\s*[\d.]+\s*%' THEN regexp_replace(p.uncertainty, '.*±\s*([\d.]+)\s*%.*', '\1')::numeric
    WHEN p.uncertainty ~ '±\s*[\d.]+' THEN regexp_replace(p.uncertainty, '.*±\s*([\d.]+).*', '\1')::numeric ELSE NULL END,
  CASE WHEN p.uncertainty ~ '%' THEN 'relative_percent'::uncertainty_type_enum
    WHEN p.uncertainty ~ '±\s*[\d.]+' THEN 'absolute'::uncertainty_type_enum ELSE NULL END,
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
  p.confidence::confidence_level,
  p.method,
  p.notes,
  '00000000-0000-4000-a000-000000000001'::uuid,
  p.created_at,
  COALESCE(p.created_at, now())
FROM parameters p
LEFT JOIN _map_property_types pt_exact ON pt_exact.param_name = p.name AND pt_exact.category = p.category
LEFT JOIN LATERAL (
  SELECT mpt.new_uuid FROM _map_property_types mpt
  WHERE mpt.param_name = p.name AND pt_exact.new_uuid IS NULL
  ORDER BY mpt.category = p.category DESC LIMIT 1
) pt_fuzzy ON pt_exact.new_uuid IS NULL
LEFT JOIN LATERAL (
  SELECT ml2.new_uuid FROM _map_literature ml2
  WHERE ml2.old_slug = regexp_replace(regexp_replace(COALESCE(p.source_file, ''), '^summaries/', ''), '\.(md|txt\.md)$', '')
     OR (p.source_file IS NOT NULL AND ml2.old_slug = split_part(regexp_replace(p.source_file, '^summaries/', ''), '.', 1))
  ORDER BY (ml2.old_slug = regexp_replace(regexp_replace(COALESCE(p.source_file, ''), '^summaries/', ''), '\.(md|txt\.md)$', '')) DESC
  LIMIT 1
) ml ON true;

-- ============================================================
-- Terminology
-- ============================================================
INSERT INTO terminology (term_zh, term_en, category, created_at)
SELECT t.term_zh, t.term_en, t.category, COALESCE(t.created_at, now())
FROM _src_terminology t WHERE t.term_zh IS NOT NULL
ON CONFLICT (term_zh) DO UPDATE SET term_en = EXCLUDED.term_en, category = EXCLUDED.category;

-- ============================================================
-- Review audit log
-- ============================================================
INSERT INTO review_logs (table_name, record_id, action, old_status, new_status, changes, reviewer, notes, created_at)
SELECT ral.table_name, ral.record_id, ral.action, ral.old_status, ral.new_status, ral.changes,
  COALESCE(ral.reviewer, 'nfmd_migration'), ral.notes, ral.created_at
FROM review_audit_log ral;

-- ============================================================
-- Refresh search vectors
-- ============================================================
UPDATE materials SET search_vector =
  setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
  setweight(to_tsvector('english', coalesce(chemical_formula, '')), 'B') ||
  setweight(to_tsvector('english', coalesce(alloy_system, '')), 'C') ||
  setweight(to_tsvector('english', coalesce(description, '')), 'D')
WHERE search_vector IS NULL OR search_vector = '';

UPDATE property_measurements pm SET search_vector =
  setweight(to_tsvector('english', coalesce((SELECT pt.name FROM property_types pt WHERE pt.id = pm.property_type_id), '')), 'A') ||
  setweight(to_tsvector('english', coalesce((SELECT m.name FROM materials m WHERE m.id = pm.material_id), '')), 'B') ||
  setweight(to_tsvector('english', coalesce(pm.unit, '')), 'C') ||
  setweight(to_tsvector('english', coalesce(pm.notes, '')), 'D')
WHERE pm.search_vector IS NULL OR pm.search_vector = '';

UPDATE data_sources ds SET search_vector =
  setweight(to_tsvector('english', coalesce(ds.title, '')), 'A') ||
  setweight(to_tsvector('english', coalesce(ds.journal, '')), 'C') ||
  setweight(to_tsvector('english', coalesce((SELECT string_agg(a.name, ' ') FROM data_source_authors dsa JOIN authors a ON a.id = dsa.author_id WHERE dsa.data_source_id = ds.id), '')), 'B')
WHERE ds.search_vector IS NULL OR ds.search_vector = '';

-- ============================================================
-- Summary
-- ============================================================
DO $$
DECLARE
  v_m integer; v_a integer; v_c integer; v_ds integer; v_au integer; v_pm integer; v_t integer; v_rl integer;
BEGIN
  SELECT count(*) INTO v_m FROM materials;
  SELECT count(*) INTO v_a FROM material_aliases;
  SELECT count(*) INTO v_c FROM property_categories;
  SELECT count(*) INTO v_ds FROM data_sources;
  SELECT count(*) INTO v_au FROM authors;
  SELECT count(*) INTO v_pm FROM property_measurements;
  SELECT count(*) INTO v_t FROM terminology;
  SELECT count(*) INTO v_rl FROM review_logs;
  RAISE NOTICE '=== Migration Complete ===';
  RAISE NOTICE 'Materials: % | Aliases: % | Categories: %', v_m, v_a, v_c;
  RAISE NOTICE 'DataSources: % | Authors: % | Measurements: %', v_ds, v_au, v_pm;
  RAISE NOTICE 'Terminology: % | ReviewLogs: %', v_t, v_rl;
END $$;

COMMIT;
