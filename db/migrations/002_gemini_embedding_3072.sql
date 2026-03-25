-- Migration: widen embedding column from 1536 to 3072 dimensions
-- Required because gemini-embedding-001 outputs 3072-dim vectors.
-- Any existing 1536-dim rows must be re-indexed after this migration.

ALTER TABLE regulation_embeddings
  ALTER COLUMN embedding TYPE vector(3072);

-- Recreate the search function with the new dimension
CREATE OR REPLACE FUNCTION match_regulations(
  query_embedding vector(3072),
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
  WHERE r.is_current = true
    AND (
      filter_jurisdiction IS NULL
      OR r.jurisdiction_id = filter_jurisdiction
      OR r.jurisdiction_id IN (
        SELECT j.id FROM jurisdictions j WHERE j.type = 'federal'
      )
      OR EXISTS (
        SELECT 1
        FROM jurisdictions sel
        WHERE sel.id = filter_jurisdiction
          AND sel.type = 'city'
          AND r.jurisdiction_id = sel.parent_id
      )
    )
  ORDER BY e.embedding <=> query_embedding
  LIMIT match_count;
END; $$;
