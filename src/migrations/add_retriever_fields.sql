-- Migration: Add retriever_message_id and retriever_thread_id fields
-- Date: 2025-08-29
-- Description: Add fields to track the provider from whom we retrieved the email (vs the original provider)

-- Add retriever_message_id to email_messages table
ALTER TABLE email_messages 
ADD COLUMN retriever_message_id VARCHAR(255);

-- Add retriever_thread_id to email_threads table  
ALTER TABLE email_threads 
ADD COLUMN retriever_thread_id VARCHAR(255);

-- Add indexes for performance
CREATE INDEX idx_email_messages_retriever_message_id ON email_messages(retriever_message_id);
CREATE INDEX idx_email_threads_retriever_thread_id ON email_threads(retriever_thread_id);

-- Add comments to document the fields
COMMENT ON COLUMN email_messages.retriever_message_id IS 'Message ID from the provider who we retrieved this email from (e.g., Gmail ID for BYU forwarded emails)';
COMMENT ON COLUMN email_messages.provider_message_id IS 'Original message ID from the source provider (e.g., Outlook ID for BYU emails)';

COMMENT ON COLUMN email_threads.retriever_thread_id IS 'Thread ID from the provider who we retrieved this email from (e.g., Gmail thread ID for BYU forwarded emails)';
COMMENT ON COLUMN email_threads.provider_thread_id IS 'Original thread ID from the source provider (e.g., Outlook Thread-Index for BYU emails)';
