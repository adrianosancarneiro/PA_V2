-- Safe to run multiple times
-- Add columns to store original email headers for cross-provider threading
ALTER TABLE email_messages
  ADD COLUMN IF NOT EXISTS internet_message_id TEXT,
  ADD COLUMN IF NOT EXISTS references_ids TEXT[];

-- Create index for efficient lookup by internet message ID
CREATE INDEX IF NOT EXISTS idx_email_messages_internet_message_id 
  ON email_messages(internet_message_id) 
  WHERE internet_message_id IS NOT NULL;
