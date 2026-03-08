CREATE TABLE IF NOT EXISTS supermarket (
    id BIGSERIAL PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    base_url TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS products (
    id BIGSERIAL PRIMARY KEY,
    ean TEXT UNIQUE,
    name TEXT,
    brand TEXT,
    content_amount NUMERIC(12,3),
    content_unit TEXT,
    envase TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_products_ean
        CHECK (ean IS NULL OR ean ~ '^[0-9]{8,14}$')
);

CREATE TABLE IF NOT EXISTS listings (
    id BIGSERIAL PRIMARY KEY,
    supermarket_id BIGINT NOT NULL REFERENCES supermarket(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    source_product_id TEXT NOT NULL,
    product_id BIGINT REFERENCES products(id),
    ean TEXT,
    name TEXT NOT NULL,
    brand TEXT,
    brand_id BIGINT,
    url_web TEXT NOT NULL,
    image_url TEXT,
    category TEXT NOT NULL,
    category_path TEXT NOT NULL,
    envase TEXT,
    measurement_unit TEXT,
    unit_multiplier NUMERIC,
    extra JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (supermarket_id, source_product_id)
);

CREATE TABLE IF NOT EXISTS price_snapshots (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    scraped_at TIMESTAMPTZ NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'ARS',
    price_list NUMERIC(12,2),
    price_final NUMERIC(12,2),
    price_per_unit_list NUMERIC(12,4),
    price_per_unit_final NUMERIC(12,4),
    content_amount NUMERIC(12,3),
    content_unit TEXT,
    units_per_pack INTEGER,
    raw JSONB NOT NULL DEFAULT '{}'::JSONB,
    UNIQUE (listing_id, scraped_at)
);

CREATE INDEX IF NOT EXISTS idx_listing_super ON listings(supermarket_id);
CREATE INDEX IF NOT EXISTS idx_snapshot_listing_time ON price_snapshots(listing_id, scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_listings_ean ON listings(ean);
CREATE INDEX IF NOT EXISTS idx_listing_extra_gin ON listings USING gin (extra);
CREATE INDEX IF NOT EXISTS idx_snapshot_raw_gin ON price_snapshots USING gin (raw);
CREATE INDEX IF NOT EXISTS idx_snapshot_scraped_at ON price_snapshots(scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_listings_product_id ON listings(product_id);

CREATE TABLE IF NOT EXISTS latest_prices (
    listing_id BIGINT PRIMARY KEY REFERENCES listings(id) ON DELETE CASCADE,
    scraped_at TIMESTAMPTZ NOT NULL,
    price_list NUMERIC(12,2),
    price_final NUMERIC(12,2),
    price_per_unit_list NUMERIC(12,4),
    price_per_unit_final NUMERIC(12,4),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cba_monthly (
    id BIGSERIAL PRIMARY KEY,
    month DATE NOT NULL,
    supermarket_code TEXT NOT NULL,
    total_cost NUMERIC(12,2) NOT NULL,
    items_found INT NOT NULL DEFAULT 0,
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (month, supermarket_code)
);
