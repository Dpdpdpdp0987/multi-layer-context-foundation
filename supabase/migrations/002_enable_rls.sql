-- =====================================================
-- Row Level Security (RLS) Policies
-- =====================================================

-- Enable RLS on all tables
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.contexts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.shared_contexts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.access_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rate_limit_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rate_limit_violations ENABLE ROW LEVEL SECURITY;

-- =====================================================
-- Users Table RLS Policies
-- =====================================================

-- Users can read their own data
CREATE POLICY "Users can read own data"
    ON public.users
    FOR SELECT
    USING (auth.uid()::UUID = id);

-- Users can update their own data (except roles)
CREATE POLICY "Users can update own data"
    ON public.users
    FOR UPDATE
    USING (auth.uid()::UUID = id)
    WITH CHECK (auth.uid()::UUID = id);

-- Admins can read all users
CREATE POLICY "Admins can read all users"
    ON public.users
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.users
            WHERE id = auth.uid()::UUID
              AND 'admin' = ANY(roles)
        )
    );

-- Admins can update any user
CREATE POLICY "Admins can update users"
    ON public.users
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM public.users
            WHERE id = auth.uid()::UUID
              AND 'admin' = ANY(roles)
        )
    );

-- Admins can delete users
CREATE POLICY "Admins can delete users"
    ON public.users
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM public.users
            WHERE id = auth.uid()::UUID
              AND 'admin' = ANY(roles)
        )
    );

-- =====================================================
-- Contexts Table RLS Policies
-- =====================================================

-- Users can read their own contexts
CREATE POLICY "Users can read own contexts"
    ON public.contexts
    FOR SELECT
    USING (user_id = auth.uid()::UUID);

-- Users can read contexts shared with them
CREATE POLICY "Users can read shared contexts"
    ON public.contexts
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.shared_contexts
            WHERE context_id = public.contexts.id
              AND shared_with_user_id = auth.uid()::UUID
              AND 'read' = ANY(permissions)
              AND (expires_at IS NULL OR expires_at > NOW())
        )
    );

-- Users can insert their own contexts
CREATE POLICY "Users can create contexts"
    ON public.contexts
    FOR INSERT
    WITH CHECK (user_id = auth.uid()::UUID);

-- Users can update their own contexts
CREATE POLICY "Users can update own contexts"
    ON public.contexts
    FOR UPDATE
    USING (user_id = auth.uid()::UUID)
    WITH CHECK (user_id = auth.uid()::UUID);

-- Users can update shared contexts with write permission
CREATE POLICY "Users can update shared contexts with write permission"
    ON public.contexts
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM public.shared_contexts
            WHERE context_id = public.contexts.id
              AND shared_with_user_id = auth.uid()::UUID
              AND 'write' = ANY(permissions)
              AND (expires_at IS NULL OR expires_at > NOW())
        )
    );

-- Users can delete their own contexts
CREATE POLICY "Users can delete own contexts"
    ON public.contexts
    FOR DELETE
    USING (user_id = auth.uid()::UUID);

-- Users can delete shared contexts with delete permission
CREATE POLICY "Users can delete shared contexts with delete permission"
    ON public.contexts
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM public.shared_contexts
            WHERE context_id = public.contexts.id
              AND shared_with_user_id = auth.uid()::UUID
              AND 'delete' = ANY(permissions)
              AND (expires_at IS NULL OR expires_at > NOW())
        )
    );

-- Admins can do anything
CREATE POLICY "Admins can manage all contexts"
    ON public.contexts
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.users
            WHERE id = auth.uid()::UUID
              AND 'admin' = ANY(roles)
        )
    );

-- =====================================================
-- Shared Contexts RLS Policies
-- =====================================================

-- Users can read shares for their own contexts
CREATE POLICY "Users can read own context shares"
    ON public.shared_contexts
    FOR SELECT
    USING (owner_id = auth.uid()::UUID);

-- Users can read shares they're part of
CREATE POLICY "Users can read shares for them"
    ON public.shared_contexts
    FOR SELECT
    USING (shared_with_user_id = auth.uid()::UUID);

-- Users can create shares for their own contexts
CREATE POLICY "Users can share own contexts"
    ON public.shared_contexts
    FOR INSERT
    WITH CHECK (
        owner_id = auth.uid()::UUID
        AND EXISTS (
            SELECT 1 FROM public.contexts
            WHERE id = context_id
              AND user_id = auth.uid()::UUID
        )
    );

-- Users can delete their own shares
CREATE POLICY "Users can revoke own shares"
    ON public.shared_contexts
    FOR DELETE
    USING (owner_id = auth.uid()::UUID);

-- =====================================================
-- Access Logs RLS Policies
-- =====================================================

-- Users can read their own access logs
CREATE POLICY "Users can read own access logs"
    ON public.access_logs
    FOR SELECT
    USING (user_id = auth.uid()::UUID);

-- Service role can insert access logs
CREATE POLICY "Service can insert access logs"
    ON public.access_logs
    FOR INSERT
    WITH CHECK (TRUE);

-- Admins can read all access logs
CREATE POLICY "Admins can read all access logs"
    ON public.access_logs
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.users
            WHERE id = auth.uid()::UUID
              AND 'admin' = ANY(roles)
        )
    );

-- =====================================================
-- Rate Limiting RLS Policies
-- =====================================================

-- Service role can manage rate limit data
CREATE POLICY "Service can manage rate limits"
    ON public.rate_limit_requests
    FOR ALL
    USING (TRUE)
    WITH CHECK (TRUE);

CREATE POLICY "Service can manage rate limit violations"
    ON public.rate_limit_violations
    FOR ALL
    USING (TRUE)
    WITH CHECK (TRUE);

-- Admins can read rate limit data
CREATE POLICY "Admins can read rate limits"
    ON public.rate_limit_requests
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.users
            WHERE id = auth.uid()::UUID
              AND 'admin' = ANY(roles)
        )
    );

CREATE POLICY "Admins can read rate limit violations"
    ON public.rate_limit_violations
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.users
            WHERE id = auth.uid()::UUID
              AND 'admin' = ANY(roles)
        )
    );

-- =====================================================
-- Grant Permissions
-- =====================================================

-- Grant execute permissions on functions
GRANT EXECUTE ON FUNCTION check_rate_limit TO authenticated;
GRANT EXECUTE ON FUNCTION get_user_permissions TO authenticated;
GRANT EXECUTE ON FUNCTION check_resource_access TO authenticated;
GRANT EXECUTE ON FUNCTION cleanup_old_rate_limit_requests TO service_role;
GRANT EXECUTE ON FUNCTION cleanup_expired_shared_contexts TO service_role;

-- Grant table permissions
GRANT SELECT, INSERT, UPDATE ON public.users TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.contexts TO authenticated;
GRANT SELECT, INSERT, DELETE ON public.shared_contexts TO authenticated;
GRANT SELECT, INSERT ON public.access_logs TO authenticated;
GRANT ALL ON public.rate_limit_requests TO service_role;
GRANT ALL ON public.rate_limit_violations TO service_role;