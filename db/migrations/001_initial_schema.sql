-- Run this entire file in the Supabase SQL editor before starting the app.

CREATE EXTENSION IF NOT EXISTS vector;

-- Core hierarchy
CREATE TABLE IF NOT EXISTS jurisdictions (
  id SERIAL PRIMARY KEY,
  type TEXT NOT NULL,
  name TEXT NOT NULL,
  parent_id INT NULL REFERENCES jurisdictions(id) ON DELETE SET NULL,
  state_code CHAR(2) NULL,
  fips_code TEXT NULL
);

CREATE INDEX IF NOT EXISTS jurisdictions_parent_id_idx ON jurisdictions(parent_id);
CREATE INDEX IF NOT EXISTS jurisdictions_state_code_idx ON jurisdictions(state_code);
-- Enables idempotent seeds (ON CONFLICT DO NOTHING style)
CREATE UNIQUE INDEX IF NOT EXISTS jurisdictions_type_name_parent_uidx
  ON jurisdictions(type, name, parent_id);
CREATE UNIQUE INDEX IF NOT EXISTS jurisdictions_state_code_uidx
  ON jurisdictions(state_code)
  WHERE state_code IS NOT NULL;

-- Regulations + versions
CREATE TABLE IF NOT EXISTS regulations (
  id SERIAL PRIMARY KEY,
  jurisdiction_id INT NOT NULL REFERENCES jurisdictions(id) ON DELETE CASCADE,
  domain TEXT NOT NULL,
  category TEXT NOT NULL,
  source_name TEXT NOT NULL,
  url TEXT NOT NULL,
  content TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  version INT NOT NULL DEFAULT 1,
  is_current BOOL NOT NULL DEFAULT TRUE,
  effective_date DATE NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS regulations_jurisdiction_id_idx ON regulations(jurisdiction_id);
CREATE INDEX IF NOT EXISTS regulations_is_current_idx ON regulations(is_current);
CREATE INDEX IF NOT EXISTS regulations_jurisdiction_current_idx ON regulations(jurisdiction_id, is_current);
CREATE INDEX IF NOT EXISTS regulations_content_hash_idx ON regulations(content_hash);
-- Allows multiple regulation versions per URL (history)
-- IDs/versions are tracked via `version` + `is_current`
CREATE INDEX IF NOT EXISTS regulations_url_idx ON regulations(url);

-- Vector chunks
CREATE TABLE IF NOT EXISTS regulation_embeddings (
  id SERIAL PRIMARY KEY,
  regulation_id INT NOT NULL REFERENCES regulations(id) ON DELETE CASCADE,
  embedding vector(1536) NOT NULL,
  chunk_text TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS regulation_embeddings_regulation_id_idx ON regulation_embeddings(regulation_id);

-- Email subscriptions
CREATE TABLE IF NOT EXISTS email_subscriptions (
  id SERIAL PRIMARY KEY,
  email TEXT NOT NULL,
  jurisdiction_id INT NOT NULL REFERENCES jurisdictions(id) ON DELETE CASCADE,
  subscribed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  is_active BOOL NOT NULL DEFAULT TRUE
);

CREATE UNIQUE INDEX IF NOT EXISTS email_subscriptions_email_jurisdiction_uidx
  ON email_subscriptions(email, jurisdiction_id);
CREATE INDEX IF NOT EXISTS email_subscriptions_jurisdiction_id_idx ON email_subscriptions(jurisdiction_id);

-- Update log
CREATE TABLE IF NOT EXISTS regulation_updates (
  id SERIAL PRIMARY KEY,
  regulation_id INT NOT NULL REFERENCES regulations(id) ON DELETE CASCADE,
  update_summary TEXT NOT NULL,
  affected_jurisdictions JSONB NOT NULL DEFAULT '[]'::jsonb,
  detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS regulation_updates_regulation_id_idx ON regulation_updates(regulation_id);
CREATE INDEX IF NOT EXISTS regulation_updates_detected_at_idx ON regulation_updates(detected_at);

-- Structured policy tables
CREATE TABLE IF NOT EXISTS pet_policies (
  id SERIAL PRIMARY KEY,
  jurisdiction_id INT NOT NULL REFERENCES jurisdictions(id) ON DELETE CASCADE,
  esa_deposit_allowed BOOL NOT NULL,
  service_animal_fee BOOL NOT NULL,
  breed_restrictions JSONB NOT NULL DEFAULT '[]'::jsonb,
  max_pet_deposit_amount NUMERIC NULL,
  source_regulation_id INT NOT NULL REFERENCES regulations(id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX IF NOT EXISTS pet_policies_jurisdiction_uidx ON pet_policies(jurisdiction_id);
CREATE INDEX IF NOT EXISTS pet_policies_source_regulation_id_idx ON pet_policies(source_regulation_id);

CREATE TABLE IF NOT EXISTS insurance_requirements (
  id SERIAL PRIMARY KEY,
  jurisdiction_id INT NOT NULL REFERENCES jurisdictions(id) ON DELETE CASCADE,
  landlord_can_require BOOL NOT NULL,
  min_liability_coverage NUMERIC NULL,
  tenant_must_show_proof BOOL NOT NULL,
  notes TEXT NULL,
  source_regulation_id INT NOT NULL REFERENCES regulations(id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX IF NOT EXISTS insurance_requirements_jurisdiction_uidx ON insurance_requirements(jurisdiction_id);
CREATE INDEX IF NOT EXISTS insurance_requirements_source_regulation_id_idx ON insurance_requirements(source_regulation_id);

-- pgvector search function
CREATE OR REPLACE FUNCTION match_regulations(
  query_embedding vector(1536),
  match_count int,
  filter_jurisdiction int DEFAULT NULL
) RETURNS TABLE(id int, chunk_text text, similarity float, metadata jsonb)
LANGUAGE plpgsql AS $$
BEGIN RETURN QUERY
  SELECT e.id, e.chunk_text,
    1 - (e.embedding <=> query_embedding) AS similarity,
    row_to_json(r)::jsonb AS metadata
  FROM regulation_embeddings e
  JOIN regulations r ON r.id = e.regulation_id
  WHERE (filter_jurisdiction IS NULL OR r.jurisdiction_id = filter_jurisdiction)
    AND r.is_current = true
  ORDER BY e.embedding <=> query_embedding
  LIMIT match_count;
END; $$;

