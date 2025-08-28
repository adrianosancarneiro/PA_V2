-- Migration: Inbound email storage schema
-- Date: 2024-02-18
-- Description: Create tables for storing inbound emails with threads, retention, and status tracking

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

-- threads
CREATE TABLE IF NOT EXISTS email_threads (
  id BIGSERIAL PRIMARY KEY,
  provider provider NOT NULL,
  provider_thread_id TEXT NOT NULL,
  subject_last TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(provider, provider_thread_id)
);

-- messages
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

-- drafts
CREATE TABLE IF NOT EXISTS email_drafts (
  id BIGSERIAL PRIMARY KEY,
  email_id BIGINT NOT NULL REFERENCES email_messages(id) ON DELETE CASCADE,
  draft_text TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- indexes
CREATE INDEX IF NOT EXISTS idx_email_messages_thread ON email_messages(thread_id);
CREATE INDEX IF NOT EXISTS idx_email_messages_provider_received ON email_messages(provider, received_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_messages_status ON email_messages(status);
CREATE INDEX IF NOT EXISTS idx_email_messages_tags_gin ON email_messages USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_email_threads_provider_updated ON email_threads(provider, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_messages_imported_at ON email_messages(imported_at DESC);

-- Comments for documentation
COMMENT ON TABLE email_threads IS 'Email conversation threads grouped by provider thread ID';
COMMENT ON TABLE email_messages IS 'Individual email messages (inbound and outbound)';
COMMENT ON TABLE email_drafts IS 'Draft replies and compositions';
COMMENT ON COLUMN email_messages.direction IS 'inbound: received emails, outbound: sent emails';
COMMENT ON COLUMN email_messages.provider_message_id IS 'Provider-specific unique message identifier';
COMMENT ON COLUMN email_messages.provider_thread_id IS 'Provider-specific thread/conversation identifier';
