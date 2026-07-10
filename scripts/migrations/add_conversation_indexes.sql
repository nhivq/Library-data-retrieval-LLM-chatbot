-- =========================
-- CONVERSATION PERFORMANCE
-- =========================

CREATE INDEX IF NOT EXISTS idx_conversations_user_id_id
ON conversations(user_id, id);

CREATE INDEX IF NOT EXISTS idx_conversations_user_id_session_id
ON conversations(user_id, session_id);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id_role_id
ON messages(conversation_id, role, id);
