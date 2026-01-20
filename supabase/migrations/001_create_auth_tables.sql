-- =====================================================
-- Multi-Layer Context Foundation - Supabase Auth Schema
-- =====================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =====================================================
-- Users Table
-- =====================================================

CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    username TEXT UNIQUE NOT NULL,
    full_name TEXT,
    roles TEXT[] NOT NULL DEFAULT ARRAY['user']::TEXT[],
    disabled BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::JSONB
);

-- Indexes
CREATE INDEX idx_users_email ON public.users(email);
CREATE INDEX idx_users_username ON public.users(username);
CREATE INDEX idx_users_roles ON public.users USING GIN(roles);
CREATE INDEX idx_users_disabled ON public.users(disabled);

-- =====================================================
-- Rate Limiting Tables
-- =====================================================

CREATE TABLE IF NOT EXISTS public.rate_limit_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_ip TEXT NOT NULL,
    user_id UUID REFERENCES public.users(id),
    endpoint TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::JSONB
);

-- Indexes for rate limiting
CREATE INDEX idx_rate_limit_client_ip ON public.rate_limit_requests(client_ip, timestamp DESC);
CREATE INDEX idx_rate_limit_user_id ON public.rate_limit_requests(user_id, timestamp DESC);
CREATE INDEX idx_rate_limit_endpoint ON public.rate_limit_requests(endpoint, timestamp DESC);
CREATE INDEX idx_rate_limit_timestamp ON public.rate_limit_requests(timestamp DESC);

-- Partitioning by day for performance
CREATE TABLE IF NOT EXISTS public.rate_limit_violations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_ip TEXT NOT NULL,
    user_id UUID REFERENCES public.users(id),
    endpoint TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::JSONB
);

CREATE INDEX idx_rate_limit_violations_timestamp ON public.rate_limit_violations(timestamp DESC);

-- =====================================================
-- Access Logs for Audit Trail
-- =====================================================

CREATE TABLE IF NOT EXISTS public.access_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.users(id),
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    action TEXT NOT NULL,
    success BOOLEAN NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    metadata JSONB DEFAULT '{}'::JSONB,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_access_logs_user_id ON public.access_logs(user_id, timestamp DESC);
CREATE INDEX idx_access_logs_resource ON public.access_logs(resource_type, resource_id);
CREATE INDEX idx_access_logs_timestamp ON public.access_logs(timestamp DESC);

-- =====================================================
-- Contexts Table (with RLS)
-- =====================================================

CREATE TABLE IF NOT EXISTS public.contexts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    context_type TEXT NOT NULL,
    layer TEXT NOT NULL DEFAULT 'session',
    importance NUMERIC(3, 2) DEFAULT 0.5,
    metadata JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    accessed_at TIMESTAMPTZ,
    access_count INTEGER DEFAULT 0,
    embedding vector(384),  -- For pgvector
    
    -- Constraints
    CONSTRAINT contexts_importance_range CHECK (importance >= 0 AND importance <= 1),
    CONSTRAINT contexts_context_type_valid CHECK (
        context_type IN ('conversation', 'document', 'code', 'task', 'note')
    ),
    CONSTRAINT contexts_layer_valid CHECK (
        layer IN ('immediate', 'session', 'longterm')
    )
);

-- Indexes
CREATE INDEX idx_contexts_user_id ON public.contexts(user_id, created_at DESC);
CREATE INDEX idx_contexts_type ON public.contexts(context_type, created_at DESC);
CREATE INDEX idx_contexts_layer ON public.contexts(layer);
CREATE INDEX idx_contexts_importance ON public.contexts(importance DESC);
CREATE INDEX idx_contexts_accessed ON public.contexts(accessed_at DESC NULLS LAST);
CREATE INDEX idx_contexts_metadata ON public.contexts USING GIN(metadata);

-- Full-text search index
CREATE INDEX idx_contexts_content_fts ON public.contexts USING GIN(to_tsvector('english', content));

-- =====================================================
-- Shared Contexts (for team collaboration)
-- =====================================================

CREATE TABLE IF NOT EXISTS public.shared_contexts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    context_id UUID NOT NULL REFERENCES public.contexts(id) ON DELETE CASCADE,
    owner_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    shared_with_user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    shared_with_team TEXT,
    permissions TEXT[] NOT NULL DEFAULT ARRAY['read']::TEXT[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    
    CONSTRAINT shared_contexts_permissions_valid CHECK (
        permissions <@ ARRAY['read', 'write', 'delete']::TEXT[]
    ),
    CONSTRAINT shared_contexts_target CHECK (
        (shared_with_user_id IS NOT NULL) OR (shared_with_team IS NOT NULL)
    )
);

CREATE INDEX idx_shared_contexts_context_id ON public.shared_contexts(context_id);
CREATE INDEX idx_shared_contexts_shared_with_user ON public.shared_contexts(shared_with_user_id);
CREATE INDEX idx_shared_contexts_shared_with_team ON public.shared_contexts(shared_with_team);
CREATE INDEX idx_shared_contexts_expires ON public.shared_contexts(expires_at);

-- =====================================================
-- Functions
-- =====================================================

-- Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for contexts
CREATE TRIGGER update_contexts_updated_at
    BEFORE UPDATE ON public.contexts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for users
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- RPC Functions for Rate Limiting
-- =====================================================

CREATE OR REPLACE FUNCTION check_rate_limit(
    p_client_ip TEXT,
    p_user_id UUID,
    p_endpoint TEXT,
    p_limit_per_minute INTEGER DEFAULT 60,
    p_limit_per_hour INTEGER DEFAULT 1000
)
RETURNS JSONB AS $$
DECLARE
    v_count_minute INTEGER;
    v_count_hour INTEGER;
    v_allowed BOOLEAN;
    v_result JSONB;
BEGIN
    -- Count requests in last minute
    SELECT COUNT(*) INTO v_count_minute
    FROM public.rate_limit_requests
    WHERE client_ip = p_client_ip
      AND timestamp > NOW() - INTERVAL '1 minute';
    
    -- Count requests in last hour
    SELECT COUNT(*) INTO v_count_hour
    FROM public.rate_limit_requests
    WHERE client_ip = p_client_ip
      AND timestamp > NOW() - INTERVAL '1 hour';
    
    -- Check if allowed
    v_allowed := (v_count_minute < p_limit_per_minute) AND (v_count_hour < p_limit_per_hour);
    
    -- Build result
    v_result := jsonb_build_object(
        'allowed', v_allowed,
        'limits', jsonb_build_object(
            'ip_limit', p_limit_per_minute,
            'ip_remaining', GREATEST(0, p_limit_per_minute - v_count_minute),
            'hourly_limit', p_limit_per_hour,
            'hourly_remaining', GREATEST(0, p_limit_per_hour - v_count_hour),
            'reset_at', EXTRACT(EPOCH FROM (NOW() + INTERVAL '1 minute'))
        )
    );
    
    RETURN v_result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- RPC Functions for Permissions
-- =====================================================

CREATE OR REPLACE FUNCTION get_user_permissions(p_user_id UUID)
RETURNS JSONB AS $$
DECLARE
    v_user RECORD;
    v_permissions TEXT[];
BEGIN
    -- Get user with roles
    SELECT * INTO v_user
    FROM public.users
    WHERE id = p_user_id AND NOT disabled;
    
    IF NOT FOUND THEN
        RETURN jsonb_build_object('error', 'User not found');
    END IF;
    
    -- Map roles to permissions
    -- Admin gets all permissions
    IF 'admin' = ANY(v_user.roles) THEN
        v_permissions := ARRAY[
            'context:read', 'context:write', 'context:delete',
            'search:basic', 'search:advanced',
            'graph:read', 'graph:write',
            'admin:metrics', 'admin:users', 'admin:config'
        ];
    -- User gets standard permissions
    ELSIF 'user' = ANY(v_user.roles) THEN
        v_permissions := ARRAY[
            'context:read', 'context:write', 'context:delete',
            'search:basic', 'search:advanced',
            'graph:read', 'graph:write'
        ];
    -- Readonly gets read-only permissions
    ELSIF 'readonly' = ANY(v_user.roles) THEN
        v_permissions := ARRAY[
            'context:read', 'search:basic', 'graph:read'
        ];
    ELSE
        v_permissions := ARRAY[]::TEXT[];
    END IF;
    
    RETURN jsonb_build_object(
        'user_id', v_user.id,
        'roles', v_user.roles,
        'permissions', v_permissions
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION check_resource_access(
    p_user_id UUID,
    p_resource_type TEXT,
    p_resource_id TEXT,
    p_action TEXT
)
RETURNS BOOLEAN AS $$
DECLARE
    v_user RECORD;
    v_context RECORD;
    v_has_access BOOLEAN := FALSE;
BEGIN
    -- Get user
    SELECT * INTO v_user
    FROM public.users
    WHERE id = p_user_id AND NOT disabled;
    
    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;
    
    -- Admins have access to everything
    IF 'admin' = ANY(v_user.roles) THEN
        RETURN TRUE;
    END IF;
    
    -- Check resource-specific access
    IF p_resource_type = 'context' THEN
        -- Check if user owns the context
        SELECT * INTO v_context
        FROM public.contexts
        WHERE id::TEXT = p_resource_id
          AND user_id = p_user_id;
        
        IF FOUND THEN
            RETURN TRUE;
        END IF;
        
        -- Check if context is shared with user
        SELECT TRUE INTO v_has_access
        FROM public.shared_contexts
        WHERE context_id::TEXT = p_resource_id
          AND shared_with_user_id = p_user_id
          AND (expires_at IS NULL OR expires_at > NOW())
          AND p_action = ANY(permissions);
        
        RETURN COALESCE(v_has_access, FALSE);
    END IF;
    
    -- Default deny
    RETURN FALSE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- Automatic Cleanup Functions
-- =====================================================

CREATE OR REPLACE FUNCTION cleanup_old_rate_limit_requests()
RETURNS INTEGER AS $$
DECLARE
    v_deleted INTEGER;
BEGIN
    -- Delete rate limit requests older than 1 day
    DELETE FROM public.rate_limit_requests
    WHERE timestamp < NOW() - INTERVAL '1 day';
    
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    
    RETURN v_deleted;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION cleanup_expired_shared_contexts()
RETURNS INTEGER AS $$
DECLARE
    v_deleted INTEGER;
BEGIN
    -- Delete expired shared contexts
    DELETE FROM public.shared_contexts
    WHERE expires_at IS NOT NULL
      AND expires_at < NOW();
    
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    
    RETURN v_deleted;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- Scheduled Cleanup (using pg_cron if available)
-- =====================================================

-- Uncomment if pg_cron extension is available
-- CREATE EXTENSION IF NOT EXISTS pg_cron;
-- SELECT cron.schedule('cleanup-rate-limits', '0 * * * *', 'SELECT cleanup_old_rate_limit_requests()');
-- SELECT cron.schedule('cleanup-expired-shares', '0 */6 * * *', 'SELECT cleanup_expired_shared_contexts()');

-- =====================================================
-- Comments
-- =====================================================

COMMENT ON TABLE public.users IS 'User accounts with roles and metadata';
COMMENT ON TABLE public.rate_limit_requests IS 'Rate limiting request tracking';
COMMENT ON TABLE public.rate_limit_violations IS 'Rate limit violation audit log';
COMMENT ON TABLE public.access_logs IS 'Security audit log for resource access';
COMMENT ON TABLE public.contexts IS 'User contexts with embeddings and metadata';
COMMENT ON TABLE public.shared_contexts IS 'Shared context permissions';