CREATE EXTENSION IF NOT EXISTS pgcrypto;

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

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS email_otps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    otp_hash TEXT NOT NULL,
    purpose TEXT NOT NULL DEFAULT 'register',
    expires_at TIMESTAMPTZ NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    consumed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS analyses (
    id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    target_role TEXT NOT NULL,
    analysis_mode TEXT NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    verdict TEXT NOT NULL DEFAULT 'Analisis Selesai',
    cv_text TEXT,
    result_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions (expires_at);
CREATE INDEX IF NOT EXISTS idx_email_otps_user_id ON email_otps (user_id);
CREATE INDEX IF NOT EXISTS idx_email_otps_email_purpose ON email_otps (email, purpose);
CREATE INDEX IF NOT EXISTS idx_email_otps_expires_at ON email_otps (expires_at);
CREATE INDEX IF NOT EXISTS idx_analyses_user_created_at ON analyses (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analyses_target_role ON analyses (target_role);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
CREATE TRIGGER trg_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
