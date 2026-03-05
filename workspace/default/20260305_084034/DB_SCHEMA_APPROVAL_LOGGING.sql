-- SQL Schema Design for Approval Events and State Persistence
-- Target RDBMS: PostgreSQL (assuming modern SQL features)

-- 1. Session State Table (Core state management)
CREATE TABLE session_states (
    session_id UUID PRIMARY KEY,
    user_id BIGINT NOT NULL, -- ID of the user initiating the session/request
    current_state VARCHAR(50) NOT NULL DEFAULT 'WAITING_FOR_APPROVAL',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB -- For flexible storage of context/request details
);

-- Index for quick lookups by user and state
CREATE INDEX idx_session_state_user_state ON session_states (user_id, current_state);

-- 2. Approval Event Log Table (Audit Trail for Transitions)
CREATE TABLE approval_events (
    event_id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES session_states(session_id) ON DELETE CASCADE,
    approver_user_id BIGINT NOT NULL, -- The user who executed the /approve command
    event_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    action_type VARCHAR(50) NOT NULL, -- E.g., 'COMMAND_RECEIVED', 'STATE_TRANSITION_SUCCESS'
    details JSONB -- Specific details about the transition (e.g., previous_state, next_state)
);

-- Index for chronological querying of events for a specific session (critical for auditing)
CREATE INDEX idx_approval_events_session_time ON approval_events (session_id, event_timestamp DESC);

-- 3. Optimization Note: State transition from WAITING_FOR_APPROVAL to IN_PROGRESS
-- The transition itself should be logged in approval_events. The session_states table should only hold the *current* state.
-- This design prevents N+1 issues during state retrieval (fetch session state directly) and ensures high-throughput logging (append-only audit log).