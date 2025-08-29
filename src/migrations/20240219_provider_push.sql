-- Migration for push webhook state tracking
-- Supports Gmail push notifications and Outlook delta queries

-- Create enum for provider type if it doesn't exist
DO $provider_enum$ BEGIN
    CREATE TYPE provider AS ENUM ('gmail', 'outlook');
EXCEPTION
    WHEN duplicate_object THEN null;
END $provider_enum$;

-- Create push state table
CREATE TABLE IF NOT EXISTS provider_push_state (
  provider               provider PRIMARY KEY,        -- 'gmail' | 'outlook'
  gmail_last_history_id  BIGINT,
  gmail_watch_expires_at TIMESTAMPTZ,
  last_pubsub_at         TIMESTAMPTZ,
  graph_delta_link       TEXT,                        -- for Outlook delta
  last_graph_webhook_at  TIMESTAMPTZ,                 -- unused w/out webhooks
  last_poll_at           TIMESTAMPTZ,
  push_state             TEXT CHECK (push_state IN ('healthy','degraded','down')),
  created_at             TIMESTAMPTZ DEFAULT NOW(),
  updated_at             TIMESTAMPTZ DEFAULT NOW()
);

-- Insert initial rows for both providers
INSERT INTO provider_push_state (provider, push_state) VALUES ('gmail','down')
  ON CONFLICT (provider) DO NOTHING;
INSERT INTO provider_push_state (provider, push_state) VALUES ('outlook','down')
  ON CONFLICT (provider) DO NOTHING;

-- Create index for efficient queries
CREATE INDEX IF NOT EXISTS idx_provider_push_state_provider ON provider_push_state(provider);
