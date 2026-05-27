CREATE TABLE IF NOT EXISTS jobs (
    job_no INTEGER PRIMARY KEY,
    title TEXT,
    company TEXT,
    location TEXT,
    keyword TEXT,
    job_url TEXT,
    description TEXT,
    scraped_at TEXT,
    fingerprint TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_jobs_keyword ON jobs (keyword);
CREATE INDEX IF NOT EXISTS idx_jobs_title ON jobs (title);
CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs (company);
CREATE INDEX IF NOT EXISTS idx_jobs_location ON jobs (location);
CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_fingerprint ON jobs (fingerprint) WHERE fingerprint IS NOT NULL AND fingerprint <> '';

CREATE OR REPLACE FUNCTION set_jobs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_jobs_updated_at ON jobs;
CREATE TRIGGER trg_jobs_updated_at
BEFORE UPDATE ON jobs
FOR EACH ROW
EXECUTE FUNCTION set_jobs_updated_at();
