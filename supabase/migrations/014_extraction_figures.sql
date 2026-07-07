-- Migration 014: extraction_figures table (spec §6.1)
-- Stores extracted figure metadata and data from document processing.

CREATE TABLE IF NOT EXISTS extraction_figures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES extraction_jobs(id) ON DELETE CASCADE,
    source_id UUID REFERENCES data_sources(id) ON DELETE SET NULL,
    page_number INTEGER NOT NULL CHECK (page_number >= 1),
    figure_type VARCHAR(50) NOT NULL,
    bounding_box JSONB,
    caption TEXT,
    image_path VARCHAR(500),
    extracted_data JSONB NOT NULL DEFAULT '{}',
    confidence FLOAT NOT NULL DEFAULT 0.0 CHECK (confidence >= 0 AND confidence <= 1),
    extraction_method VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for querying figures by extraction job
CREATE INDEX IF NOT EXISTS idx_extraction_figures_job_id
    ON extraction_figures(job_id);

-- Index for querying figures by data source
CREATE INDEX IF NOT EXISTS idx_extraction_figures_source_id
    ON extraction_figures(source_id);

-- Index for querying figures by type
CREATE INDEX IF NOT EXISTS idx_extraction_figures_figure_type
    ON extraction_figures(figure_type);

-- Index for confidence-based filtering
CREATE INDEX IF NOT EXISTS idx_extraction_figures_confidence
    ON extraction_figures(confidence DESC);
