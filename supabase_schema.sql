-- ============================================================
-- Supabase Schema for Quiz App Backend
-- Run this in the Supabase SQL Editor (one-time setup)
-- ============================================================

-- 1. quiz_usage table
-- Tracks daily quiz generation per user for rate limiting.
CREATE TABLE IF NOT EXISTS quiz_usage (
    user_id TEXT NOT NULL,
    date DATE NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, date)
);

-- 2. Auto-update updated_at on row modification
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trigger_quiz_usage_updated_at ON quiz_usage;
CREATE TRIGGER trigger_quiz_usage_updated_at
    BEFORE UPDATE ON quiz_usage
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 3. RPC function: atomically check limit and increment usage
-- Returns JSON: { "allowed": bool, "current_count": int, "message": str }
CREATE OR REPLACE FUNCTION check_and_increment_quiz_usage(
    p_user_id TEXT,
    p_date DATE,
    p_max_count INTEGER DEFAULT 5
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_count INTEGER;
    v_result JSONB;
BEGIN
    -- Ensure a row exists for this user + date
    INSERT INTO quiz_usage (user_id, date, count)
    VALUES (p_user_id, p_date, 0)
    ON CONFLICT (user_id, date)
    DO NOTHING;

    -- Lock the row and read current count (serializes concurrent requests)
    SELECT count INTO v_count
    FROM quiz_usage
    WHERE user_id = p_user_id AND date = p_date
    FOR UPDATE;

    -- Check if the user has reached their daily limit
    IF v_count >= p_max_count THEN
        v_result := jsonb_build_object(
            'allowed', false,
            'current_count', v_count,
            'message', 'Daily quiz limit reached'
        );
    ELSE
        -- Atomically increment
        UPDATE quiz_usage
        SET count = count + 1
        WHERE user_id = p_user_id AND date = p_date
        RETURNING count INTO v_count;

        v_result := jsonb_build_object(
            'allowed', true,
            'current_count', v_count,
            'message', 'OK'
        );
    END IF;

    RETURN v_result;
END;
$$;

-- 4. Row-Level Security (optional but recommended)
-- Enable RLS on the table
ALTER TABLE quiz_usage ENABLE ROW LEVEL SECURITY;

-- Allow service role full access
CREATE POLICY "Service role has full access to quiz_usage"
    ON quiz_usage
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Allow authenticated users to read their own usage data
CREATE POLICY "Users can read own usage"
    ON quiz_usage
    FOR SELECT
    TO authenticated
    USING (auth.uid()::text = user_id);

-- 5. Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_quiz_usage_user_date
    ON quiz_usage (user_id, date);
