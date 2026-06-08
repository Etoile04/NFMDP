-- ============================================================
-- NFMDP: Unified Schema DDL (Consolidated)
-- Creates all tables needed for NFMD → Unified migration
-- Database: supabase_db_workspace (port 54322)
--
-- NOTE: Run this AFTER renaming conflicting source tables
-- (materials, material_aliases, terminology, categories,
--  literature, audit_log) to _src_* prefix.
-- See 009_nfmd_data_migration.sql Step 1.
-- ============================================================

-- ============================================================
-- 1. Custom Enum Types
-- ============================================================
CREATE TYPE material_type_enum AS ENUM (
  'fuel', 'structural', 'coolant', 'ceramic', 'cladding',
  'barrier', 'pure_element', 'fission_product', 'additive',
  'composite', 'other'
);

CREATE TYPE measurement_value_type AS ENUM (
  'scalar', 'range', 'expression', 'list', 'text'
);

CREATE TYPE confidence_level AS ENUM (
  'high', 'medium', 'low'
);

CREATE TYPE access_level_type AS ENUM (
  'public', 'shared', 'private'
);

CREATE TYPE review_status_type AS ENUM (
  'pending', 'approved', 'rejected', 'needs_review',
  'needs_data', 'duplicate', 'auto_approved'
);

CREATE TYPE uncertainty_type_enum AS ENUM (
  'absolute', 'relative_percent', 'relative'
);

-- ============================================================
-- 2. Users & Access
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  username    VARCHAR(64) UNIQUE NOT NULL,
  full_name   VARCHAR(128),
  email       TEXT,
  role        VARCHAR(16) DEFAULT 'contributor',
  avatar_url  TEXT,
  orcid       VARCHAR(19),
  affiliation TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS access_levels (
  id    SERIAL PRIMARY KEY,
  name  TEXT UNIQUE NOT NULL,
  description TEXT
);

CREATE TABLE IF NOT EXISTS dataset_access (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dataset_id  UUID NOT NULL,
  user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
  access_level_id INTEGER REFERENCES access_levels(id),
  granted_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 3. Units
-- ============================================================
CREATE TABLE IF NOT EXISTS units (
  id          SERIAL PRIMARY KEY,
  name        TEXT UNIQUE NOT NULL,
  symbol      TEXT NOT NULL,
  dimension   TEXT NOT NULL,
  si_base     BOOLEAN DEFAULT FALSE,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS unit_conversions (
  id              SERIAL PRIMARY KEY,
  from_unit_id    INTEGER REFERENCES units(id),
  to_unit_id      INTEGER REFERENCES units(id),
  factor          DOUBLE PRECISION NOT NULL,
  offset          DOUBLE PRECISION DEFAULT 0
);

-- ============================================================
-- 4. Materials Domain
-- ============================================================
CREATE TABLE IF NOT EXISTS material_categories (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT NOT NULL,
  slug        TEXT UNIQUE NOT NULL,
  name_zh     TEXT,
  description TEXT,
  parent_id   UUID REFERENCES material_categories(id),
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS materials (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name                TEXT NOT NULL UNIQUE,
  name_zh             TEXT,
  chemical_formula    TEXT,
  material_type       material_type_enum NOT NULL DEFAULT 'other',
  category_id         UUID REFERENCES material_categories(id),
  alloy_system        TEXT,
  crystal_structure   TEXT,
  density_kg_m3       NUMERIC(12,4),
  melting_point_k     NUMERIC(10,2),
  description         TEXT,
  search_vector       TSVECTOR,
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_materials_type ON materials (material_type);
CREATE INDEX IF NOT EXISTS idx_materials_system ON materials (alloy_system);
CREATE INDEX IF NOT EXISTS idx_materials_category ON materials (category_id);
CREATE INDEX IF NOT EXISTS idx_materials_search ON materials USING GIN (search_vector);

CREATE TABLE IF NOT EXISTS material_aliases (
  id              SERIAL PRIMARY KEY,
  alias           TEXT NOT NULL UNIQUE,
  material_id     UUID NOT NULL REFERENCES materials(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_aliases_material ON material_aliases (material_id);

CREATE TABLE IF NOT EXISTS material_compositions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  material_id     UUID NOT NULL REFERENCES materials(id) ON DELETE CASCADE,
  element         TEXT NOT NULL,
  weight_fraction NUMERIC(8,6),
  atom_fraction   NUMERIC(8,6)
);

-- ============================================================
-- 5. Properties Domain (Core)
-- ============================================================
CREATE TABLE IF NOT EXISTS property_categories (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT NOT NULL,
  slug        TEXT UNIQUE NOT NULL,
  name_zh     TEXT,
  description TEXT,
  parent_id   UUID REFERENCES property_categories(id),
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_propcat_parent ON property_categories (parent_id);

CREATE TABLE IF NOT EXISTS data_sources (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title         TEXT,
  doi           TEXT,
  journal       TEXT,
  year          INTEGER,
  source_type   TEXT DEFAULT 'journal',
  file_path     TEXT,
  url           TEXT,
  notes         TEXT,
  search_vector TSVECTOR,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ds_doi ON data_sources (doi) WHERE doi IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ds_year ON data_sources (year);
CREATE INDEX IF NOT EXISTS idx_ds_search ON data_sources USING GIN (search_vector);

CREATE TABLE IF NOT EXISTS authors (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT NOT NULL UNIQUE,
  orcid       VARCHAR(19),
  affiliation TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS data_source_authors (
  data_source_id  UUID NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
  author_id       UUID NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
  author_order    INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (data_source_id, author_id)
);

CREATE TABLE IF NOT EXISTS property_types (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name            TEXT NOT NULL,
  slug            TEXT UNIQUE NOT NULL,
  name_zh         TEXT,
  category_id     UUID REFERENCES property_categories(id),
  unit            TEXT,
  description     TEXT,
  search_vector   TSVECTOR,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_proptype_category ON property_types (category_id);
CREATE INDEX IF NOT EXISTS idx_proptype_search ON property_types USING GIN (search_vector);

CREATE TABLE IF NOT EXISTS datasets (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name            TEXT NOT NULL,
  description     TEXT,
  version         TEXT DEFAULT '1.0',
  access_level_id INTEGER REFERENCES access_levels(id),
  created_by      UUID REFERENCES users(id),
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS property_measurements (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  property_type_id    UUID REFERENCES property_types(id),
  material_id         UUID REFERENCES materials(id) ON DELETE SET NULL,
  dataset_id          UUID REFERENCES datasets(id),
  data_source_id      UUID REFERENCES data_sources(id),
  value_type          measurement_value_type NOT NULL DEFAULT 'scalar',
  value_scalar        NUMERIC,
  value_min           NUMERIC,
  value_max           NUMERIC,
  value_expr          TEXT,
  value_list          JSONB,
  value_text          TEXT,
  numeric_value       NUMERIC,
  unit                TEXT,
  unit_id             INTEGER REFERENCES units(id),
  uncertainty_value   NUMERIC,
  uncertainty_type    uncertainty_type_enum,
  conditions          JSONB,
  confidence          confidence_level,
  method              TEXT,
  notes               TEXT,
  review_status       review_status_type,
  search_vector       TSVECTOR,
  submitted_by        UUID REFERENCES users(id),
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pm_property_type ON property_measurements (property_type_id);
CREATE INDEX IF NOT EXISTS idx_pm_material ON property_measurements (material_id);
CREATE INDEX IF NOT EXISTS idx_pm_data_source ON property_measurements (data_source_id);
CREATE INDEX IF NOT EXISTS idx_pm_value_type ON property_measurements (value_type);
CREATE INDEX IF NOT EXISTS idx_pm_confidence ON property_measurements (confidence);
CREATE INDEX IF NOT EXISTS idx_pm_search ON property_measurements USING GIN (search_vector);
CREATE INDEX IF NOT EXISTS idx_pm_created ON property_measurements (created_at DESC);

CREATE TABLE IF NOT EXISTS measurement_conditions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  measurement_id  UUID NOT NULL REFERENCES property_measurements(id) ON DELETE CASCADE,
  condition_type  TEXT NOT NULL,
  value           NUMERIC,
  unit            TEXT,
  notes           TEXT
);

-- ============================================================
-- 6. Remaining Domain Tables
-- ============================================================

-- Potentials (from NucPot)
CREATE TABLE IF NOT EXISTS potentials (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name          VARCHAR(256) NOT NULL UNIQUE,
  type          VARCHAR(64) NOT NULL,
  elements      TEXT[] NOT NULL,
  description   TEXT,
  file_url      TEXT,
  lammps_config JSONB DEFAULT '{}',
  year          INTEGER,
  source        TEXT,
  source_doi    VARCHAR(128),
  version       VARCHAR(16) NOT NULL DEFAULT '1.0',
  submitted_by  UUID REFERENCES users(id),
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS potential_elements (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  potential_id  UUID NOT NULL REFERENCES potentials(id) ON DELETE CASCADE,
  element       TEXT NOT NULL,
  concentration NUMERIC(8,6)
);

-- Verification
CREATE TABLE IF NOT EXISTS verification_jobs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  potential_id    UUID NOT NULL REFERENCES potentials(id) ON DELETE CASCADE,
  status          VARCHAR(16) DEFAULT 'pending',
  properties_req  JSONB NOT NULL DEFAULT '[]',
  created_by      VARCHAR(64) DEFAULT 'system',
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  started_at      TIMESTAMPTZ,
  completed_at    TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS verification_results (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id          UUID NOT NULL REFERENCES verification_jobs(id) ON DELETE CASCADE,
  property_name   VARCHAR(64) NOT NULL,
  computed_value   DOUBLE PRECISION,
  reference_value  DOUBLE PRECISION,
  relative_error   DOUBLE PRECISION,
  grade           VARCHAR(2),
  details         JSONB DEFAULT '{}'
);

-- Correlations
CREATE TABLE IF NOT EXISTS correlations (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  property_type_a_id  UUID NOT NULL REFERENCES property_types(id),
  property_type_b_id  UUID NOT NULL REFERENCES property_types(id),
  material_id         UUID REFERENCES materials(id),
  correlation_type    TEXT DEFAULT 'none',
  coefficient         NUMERIC,
  p_value             NUMERIC,
  sample_size         INTEGER,
  data_source_id      UUID REFERENCES data_sources(id),
  notes               TEXT,
  created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Irradiation behavior
CREATE TABLE IF NOT EXISTS irradiation_behavior (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  material_id     UUID NOT NULL REFERENCES materials(id) ON DELETE CASCADE,
  property_name   TEXT NOT NULL,
  neutron_fluence NUMERIC,
  fluence_unit    TEXT,
  dpa             NUMERIC,
  temperature_k   NUMERIC(10,2),
  value           NUMERIC,
  unit            TEXT,
  data_source_id  UUID REFERENCES data_sources(id),
  notes           TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Ontology
CREATE TABLE IF NOT EXISTS ontology_classes (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT NOT NULL UNIQUE,
  class_type  TEXT NOT NULL,
  parent_id   UUID REFERENCES ontology_classes(id),
  description TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ontology_nodes (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  class_id        UUID NOT NULL REFERENCES ontology_classes(id),
  label           TEXT NOT NULL,
  label_zh        TEXT,
  uri             TEXT,
  definition      TEXT,
  synonyms        TEXT[],
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 7. Review, Terminology, Audit
-- ============================================================

-- Terminology (zh→en mapping for search)
CREATE TABLE IF NOT EXISTS terminology (
  id          SERIAL PRIMARY KEY,
  term_zh     TEXT UNIQUE NOT NULL,
  term_en     TEXT NOT NULL,
  category    TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Review logs (audit trail)
CREATE TABLE IF NOT EXISTS review_logs (
  id          BIGSERIAL PRIMARY KEY,
  table_name  TEXT NOT NULL,
  record_id   TEXT NOT NULL,
  action      TEXT NOT NULL,
  old_status  TEXT,
  new_status  TEXT,
  changes     JSONB,
  reviewer    TEXT,
  notes       TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_review_logs_record ON review_logs (table_name, record_id);
CREATE INDEX IF NOT EXISTS idx_review_logs_time ON review_logs (created_at DESC);

-- Unified audit log
CREATE TABLE IF NOT EXISTS audit_log (
  id          BIGSERIAL PRIMARY KEY,
  action      TEXT NOT NULL,
  table_name  TEXT NOT NULL,
  record_id   TEXT,
  changes     JSONB,
  operator    TEXT DEFAULT 'system',
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_table ON audit_log (table_name);
CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log (created_at DESC);

-- Contributions
CREATE TABLE IF NOT EXISTS contributions (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  table_name    TEXT NOT NULL,
  record_id     TEXT NOT NULL,
  action        TEXT NOT NULL,
  user_id       UUID REFERENCES users(id),
  notes         TEXT,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Feedback
CREATE TABLE IF NOT EXISTS feedback (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID REFERENCES users(id),
  type        VARCHAR(32) NOT NULL,
  title       TEXT NOT NULL,
  description TEXT,
  email       VARCHAR(255),
  status      VARCHAR(16) DEFAULT 'open',
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 8. Seed Data
-- ============================================================

-- Access levels
INSERT INTO access_levels (name, description) VALUES
  ('public', 'Visible to all users'),
  ('shared', 'Visible to granted users'),
  ('private', 'Visible only to owner')
ON CONFLICT (name) DO NOTHING;

-- Material categories
INSERT INTO material_categories (id, name, slug, name_zh) VALUES
  (gen_random_uuid(), 'Fuel Materials', 'fuel-materials', '燃料材料'),
  (gen_random_uuid(), 'Structural Materials', 'structural-materials', '结构材料'),
  (gen_random_uuid(), 'Coolant Materials', 'coolant-materials', '冷却剂材料'),
  (gen_random_uuid(), 'Ceramic Materials', 'ceramic-materials', '陶瓷材料'),
  (gen_random_uuid(), 'Cladding Materials', 'cladding-materials', '包壳材料'),
  (gen_random_uuid(), 'Pure Elements', 'pure-elements', '纯元素'),
  (gen_random_uuid(), 'Composite Materials', 'composite-materials', '复合材料'),
  (gen_random_uuid(), 'Other Materials', 'other-materials', '其他材料')
ON CONFLICT (slug) DO NOTHING;

-- Property categories
INSERT INTO property_categories (id, name, slug, name_zh) VALUES
  (gen_random_uuid(), 'Thermal', 'thermal', '热学'),
  (gen_random_uuid(), 'Mechanical', 'mechanical', '力学'),
  (gen_random_uuid(), 'Diffusion', 'diffusion', '扩散'),
  (gen_random_uuid(), 'Irradiation', 'irradiation', '辐照'),
  (gen_random_uuid(), 'Physical', 'physical', '物理'),
  (gen_random_uuid(), 'Thermodynamic', 'thermodynamic', '热力学'),
  (gen_random_uuid(), 'Elastic', 'elastic', '弹性'),
  (gen_random_uuid(), 'Microstructure', 'microstructure', '微观结构')
ON CONFLICT (slug) DO NOTHING;

-- Units
INSERT INTO units (name, symbol, dimension, si_base) VALUES
  ('kelvin', 'K', 'temperature', TRUE),
  ('pascal', 'Pa', 'pressure', TRUE),
  ('meter', 'm', 'length', TRUE),
  ('kilogram', 'kg', 'mass', TRUE),
  ('second', 's', 'time', TRUE),
  ('gigapascal', 'GPa', 'pressure', FALSE),
  ('electronvolt', 'eV', 'energy', FALSE),
  ('eV/atom', 'eV/atom', 'energy', FALSE),
  ('angstrom', 'Å', 'length', FALSE),
  ('gigawatt-day per metric ton uranium', 'GWd/MTU', 'burnup', FALSE),
  ('centimeter per second squared', 'cm/s²', 'acceleration', FALSE),
  ('gram per cubic centimeter', 'g/cm³', 'density', FALSE),
  ('kilogram per cubic meter', 'kg/m³', 'density', TRUE),
  ('watt per meter kelvin', 'W/(m·K)', 'thermal_conductivity', FALSE),
  ('joule per kilogram kelvin', 'J/(kg·K)', 'specific_heat', FALSE),
  ('1/K', '1/K', 'thermal_expansion', FALSE),
  ('square meter per second', 'm²/s', 'diffusion', FALSE),
  ('percent', '%', 'fraction', FALSE),
  ('displacements per atom', 'dpa', 'radiation_damage', FALSE),
  ('dimensionless', '-', 'dimensionless', TRUE)
ON CONFLICT (name) DO NOTHING;

-- ============================================================
-- 9. Triggers
-- ============================================================

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER materials_updated_at
  BEFORE UPDATE ON materials
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER users_updated_at
  BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER potentials_updated_at
  BEFORE UPDATE ON potentials
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER property_measurements_updated_at
  BEFORE UPDATE ON property_measurements
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Materials search vector trigger
CREATE OR REPLACE FUNCTION materials_search_vector_update()
RETURNS trigger AS $$
BEGIN
  NEW.search_vector :=
    setweight(to_tsvector('english', coalesce(NEW.name, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(NEW.chemical_formula, '')), 'B') ||
    setweight(to_tsvector('english', coalesce(NEW.alloy_system, '')), 'C') ||
    setweight(to_tsvector('english', coalesce(NEW.description, '')), 'D');
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_materials_search
  BEFORE INSERT OR UPDATE ON materials
  FOR EACH ROW EXECUTE FUNCTION materials_search_vector_update();

-- Verification
SELECT 'NFMDP Unified Schema created successfully' AS status;
