-- Database schema for inbound email storage
-- Run this against pa_v2_postgres_db database

-- providers enum
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'provider') THEN
    CREATE TYPE provider AS ENUM ('gmail','outlook');
  END IF;
END $$;

-- email status enum
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'email_status') THEN
    CREATE TYPE email_status AS ENUM ('pending','draft','sent','replied','ignored','deleted','failed');
  END IF;
END $$;

-- threads table
CREATE TABLE IF NOT EXISTS email_threads (
  id BIGSERIAL PRIMARY KEY,
  provider provider NOT NULL,
  provider_thread_id TEXT NOT NULL,
  subject_last TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(provider, provider_thread_id)
);

-- messages table
CREATE TABLE IF NOT EXISTS email_messages (
  id BIGSERIAL PRIMARY KEY,
  provider provider NOT NULL,
  provider_message_id TEXT NOT NULL,
  thread_id BIGINT REFERENCES email_threads(id) ON DELETE CASCADE,
  direction TEXT NOT NULL DEFAULT 'inbound', -- inbound or outbound
  from_display TEXT,
  from_email TEXT,
  to_emails TEXT[],
  cc_emails TEXT[],
  bcc_emails TEXT[],
  subject TEXT,
  snippet TEXT,
  body_plain TEXT,
  body_html TEXT,
  received_at TIMESTAMPTZ,
  imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  status email_status NOT NULL DEFAULT 'pending',
  tags TEXT[] NOT NULL DEFAULT '{}',
  last_accessed_at TIMESTAMPTZ,
  last_action TEXT,
  deleted_at TIMESTAMPTZ,
  deleted_by TEXT,
  deletion_mode TEXT CHECK (deletion_mode IN ('soft','hard') OR deletion_mode IS NULL),
  UNIQUE(provider, provider_message_id)
);

-- drafts table
CREATE TABLE IF NOT EXISTS email_drafts (
  id BIGSERIAL PRIMARY KEY,
  email_id BIGINT NOT NULL REFERENCES email_messages(id) ON DELETE CASCADE,
  draft_text TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- indexes for performance
CREATE INDEX IF NOT EXISTS idx_email_messages_thread ON email_messages(thread_id);
CREATE INDEX IF NOT EXISTS idx_email_messages_provider_received ON email_messages(provider, received_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_messages_status ON email_messages(status);
CREATE INDEX IF NOT EXISTS idx_email_messages_tags_gin ON email_messages USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_email_threads_provider ON email_threads(provider, updated_at DESC);

-- Add some helpful views
CREATE OR REPLACE VIEW recent_emails AS
SELECT 
  m.id,
  m.provider,
  m.provider_message_id,
  m.from_display,
  m.from_email,
  m.subject,
  m.snippet,
  m.received_at,
  m.status,
  t.provider_thread_id,
  t.subject_last as thread_subject
FROM email_messages m
JOIN email_threads t ON m.thread_id = t.id
WHERE m.deleted_at IS NULL
ORDER BY m.received_at DESC;

-- Add a function to clean up old emails
CREATE OR REPLACE FUNCTION cleanup_old_emails(provider_name provider, keep_count INTEGER DEFAULT 10000)
RETURNS INTEGER AS $$
DECLARE
  deleted_count INTEGER;
BEGIN
  WITH ranked AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY received_at DESC NULLS LAST) as rn
    FROM email_messages 
    WHERE provider = provider_name AND deleted_at IS NULL
  )
  DELETE FROM email_messages
  WHERE id IN (SELECT id FROM ranked WHERE rn > keep_count);
  
  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Insert some test data to verify the schema works
INSERT INTO email_threads (provider, provider_thread_id, subject_last) 
VALUES ('gmail', 'test_thread_1', 'Test Email Thread')
ON CONFLICT (provider, provider_thread_id) DO NOTHING;

SELECT 'Schema created successfully! Tables: email_threads, email_messages, email_drafts' as result;
