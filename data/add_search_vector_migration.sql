-- Migration: add search_vector generated column to listings
-- Run this against existing deployments where the table already exists.
-- Safe to run multiple times (IF NOT EXISTS guards).

ALTER TABLE listings
    ADD COLUMN IF NOT EXISTS search_vector TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('simple',
            coalesce(name, '') || ' ' ||
            coalesce(brand, '') || ' ' ||
            coalesce(ean, '') || ' ' ||
            coalesce(category, '')
        )
    ) STORED;

CREATE INDEX IF NOT EXISTS idx_listings_search ON listings USING GIN(search_vector);
