-- latest_prices: always holds the most recent price for each listing
CREATE TABLE IF NOT EXISTS latest_prices (
    listing_id BIGINT PRIMARY KEY REFERENCES listings(id) ON DELETE CASCADE,
    scraped_at TIMESTAMPTZ NOT NULL,
    price_list NUMERIC(12,2),
    price_final NUMERIC(12,2),
    price_per_unit_list NUMERIC(12,4),
    price_per_unit_final NUMERIC(12,4),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_latest_prices_listing ON latest_prices(listing_id);

-- cba_monthly: pre-calculated monthly CBA costs per supermarket
CREATE TABLE IF NOT EXISTS cba_monthly (
    id BIGSERIAL PRIMARY KEY,
    month DATE NOT NULL,
    supermarket_code TEXT NOT NULL,
    total_cost NUMERIC(12,2) NOT NULL,
    items_found INT NOT NULL DEFAULT 0,
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (month, supermarket_code)
);
