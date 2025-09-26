-- Row Level Security Configuration for Graduate Admissions Database
-- Implements proper access control for public, authenticated, and service roles

-- =========================================
-- ENABLE RLS on all tables
-- =========================================

ALTER TABLE institution ENABLE ROW LEVEL SECURITY;
ALTER TABLE school ENABLE ROW LEVEL SECURITY;
ALTER TABLE department ENABLE ROW LEVEL SECURITY;
ALTER TABLE program ENABLE ROW LEVEL SECURITY;
ALTER TABLE track ENABLE ROW LEVEL SECURITY;
ALTER TABLE term ENABLE ROW LEVEL SECURITY;
ALTER TABLE round ENABLE ROW LEVEL SECURITY;
ALTER TABLE requirement_set ENABLE ROW LEVEL SECURITY;
ALTER TABLE tests ENABLE ROW LEVEL SECURITY;
ALTER TABLE components ENABLE ROW LEVEL SECURITY;
ALTER TABLE intl ENABLE ROW LEVEL SECURITY;
ALTER TABLE deadlines ENABLE ROW LEVEL SECURITY;
ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE raw_capture ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit ENABLE ROW LEVEL SECURITY;
ALTER TABLE citation ENABLE ROW LEVEL SECURITY;
ALTER TABLE validation_issue ENABLE ROW LEVEL SECURITY;

-- =========================================
-- PUBLIC ACCESS POLICIES (Read-only for approved data)
-- =========================================

-- Allow public to read institution hierarchy
CREATE POLICY "Public can read institutions"
    ON institution FOR SELECT
    USING (true);

CREATE POLICY "Public can read schools"
    ON school FOR SELECT
    USING (true);

CREATE POLICY "Public can read departments"
    ON department FOR SELECT
    USING (true);

CREATE POLICY "Public can read programs"
    ON program FOR SELECT
    USING (true);

CREATE POLICY "Public can read tracks"
    ON track FOR SELECT
    USING (true);

CREATE POLICY "Public can read terms"
    ON term FOR SELECT
    USING (true);

-- Public can only see APPROVED requirement sets
CREATE POLICY "Public can read approved requirements"
    ON requirement_set FOR SELECT
    USING (status = 'approved');

-- Public can read requirement details for approved sets
CREATE POLICY "Public can read approved tests"
    ON tests FOR SELECT
    USING (
        requirement_set_id IN (
            SELECT id FROM requirement_set WHERE status = 'approved'
        )
    );

CREATE POLICY "Public can read approved components"
    ON components FOR SELECT
    USING (
        requirement_set_id IN (
            SELECT id FROM requirement_set WHERE status = 'approved'
        )
    );

CREATE POLICY "Public can read approved intl"
    ON intl FOR SELECT
    USING (
        requirement_set_id IN (
            SELECT id FROM requirement_set WHERE status = 'approved'
        )
    );

CREATE POLICY "Public can read approved deadlines"
    ON deadlines FOR SELECT
    USING (
        requirement_set_id IN (
            SELECT id FROM requirement_set WHERE status = 'approved'
        )
    );

CREATE POLICY "Public can read approved contacts"
    ON contacts FOR SELECT
    USING (
        requirement_set_id IN (
            SELECT id FROM requirement_set WHERE status = 'approved'
        )
    );

-- =========================================
-- SERVICE ROLE POLICIES (Full access for backend/ETL)
-- =========================================

-- Service role has full access to all tables
DO $$
DECLARE
    t text;
BEGIN
    FOR t IN
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE'
    LOOP
        -- Insert policy
        EXECUTE format('
            CREATE POLICY "Service role can insert %I"
            ON %I FOR INSERT
            TO service_role
            WITH CHECK (true);
        ', t, t);

        -- Update policy
        EXECUTE format('
            CREATE POLICY "Service role can update %I"
            ON %I FOR UPDATE
            TO service_role
            USING (true)
            WITH CHECK (true);
        ', t, t);

        -- Delete policy (restricted for audit trail)
        IF t NOT IN ('raw_capture', 'audit', 'citation') THEN
            EXECUTE format('
                CREATE POLICY "Service role can delete %I"
                ON %I FOR DELETE
                TO service_role
                USING (true);
            ', t, t);
        END IF;

        -- Select policy
        EXECUTE format('
            CREATE POLICY "Service role can read %I"
            ON %I FOR SELECT
            TO service_role
            USING (true);
        ', t, t);
    END LOOP;
END $$;

-- =========================================
-- REVIEWER ROLE POLICIES (Authenticated users with reviewer claim)
-- =========================================

-- Function to check if user is a reviewer
CREATE OR REPLACE FUNCTION is_reviewer()
RETURNS boolean AS $$
BEGIN
    RETURN (
        auth.jwt() ->> 'role' = 'reviewer' OR
        auth.jwt() ->> 'role' = 'admin' OR
        auth.jwt() -> 'user_metadata' ->> 'role' IN ('reviewer', 'admin')
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Reviewers can read all requirement sets (including drafts)
CREATE POLICY "Reviewers can read all requirement_sets"
    ON requirement_set FOR SELECT
    TO authenticated
    USING (is_reviewer());

-- Reviewers can update requirement set status
CREATE POLICY "Reviewers can update requirement_set status"
    ON requirement_set FOR UPDATE
    TO authenticated
    USING (is_reviewer())
    WITH CHECK (is_reviewer());

-- Reviewers can read all requirement details
CREATE POLICY "Reviewers can read all tests"
    ON tests FOR SELECT
    TO authenticated
    USING (is_reviewer());

CREATE POLICY "Reviewers can update tests"
    ON tests FOR UPDATE
    TO authenticated
    USING (is_reviewer())
    WITH CHECK (is_reviewer());

CREATE POLICY "Reviewers can read all components"
    ON components FOR SELECT
    TO authenticated
    USING (is_reviewer());

CREATE POLICY "Reviewers can update components"
    ON components FOR UPDATE
    TO authenticated
    USING (is_reviewer())
    WITH CHECK (is_reviewer());

-- Reviewers can read raw captures and citations
CREATE POLICY "Reviewers can read raw_capture"
    ON raw_capture FOR SELECT
    TO authenticated
    USING (is_reviewer());

CREATE POLICY "Reviewers can read citations"
    ON citation FOR SELECT
    TO authenticated
    USING (is_reviewer());

CREATE POLICY "Reviewers can create citations"
    ON citation FOR INSERT
    TO authenticated
    WITH CHECK (is_reviewer());

-- Reviewers can manage validation issues
CREATE POLICY "Reviewers can read validation_issues"
    ON validation_issue FOR SELECT
    TO authenticated
    USING (is_reviewer());

CREATE POLICY "Reviewers can update validation_issues"
    ON validation_issue FOR UPDATE
    TO authenticated
    USING (is_reviewer())
    WITH CHECK (is_reviewer());

-- =========================================
-- STORAGE BUCKET CONFIGURATION
-- =========================================

-- Note: These SQL commands are for documentation.
-- Actual bucket creation happens via Supabase Dashboard or Management API

-- Create storage buckets (run via Supabase Dashboard)
/*
INSERT INTO storage.buckets (id, name, public)
VALUES
    ('raw-captures', 'raw-captures', false),
    ('pdfs', 'pdfs', false),
    ('screenshots', 'screenshots', false)
ON CONFLICT DO NOTHING;
*/

-- Storage policies (run via Supabase Dashboard)
/*
-- Service role can upload to all buckets
CREATE POLICY "Service role can upload to raw-captures"
ON storage.objects FOR INSERT
TO service_role
WITH CHECK (bucket_id = 'raw-captures');

CREATE POLICY "Service role can upload to pdfs"
ON storage.objects FOR INSERT
TO service_role
WITH CHECK (bucket_id = 'pdfs');

CREATE POLICY "Service role can upload to screenshots"
ON storage.objects FOR INSERT
TO service_role
WITH CHECK (bucket_id = 'screenshots');

-- Reviewers can read from all buckets
CREATE POLICY "Reviewers can read raw-captures"
ON storage.objects FOR SELECT
TO authenticated
USING (bucket_id = 'raw-captures' AND is_reviewer());

CREATE POLICY "Reviewers can read pdfs"
ON storage.objects FOR SELECT
TO authenticated
USING (bucket_id = 'pdfs' AND is_reviewer());

CREATE POLICY "Reviewers can read screenshots"
ON storage.objects FOR SELECT
TO authenticated
USING (bucket_id = 'screenshots' AND is_reviewer());
*/

-- =========================================
-- HELPER FUNCTIONS
-- =========================================

-- Function to get current requirement for a track
CREATE OR REPLACE FUNCTION get_current_requirement(
    p_track_id UUID,
    p_term_id UUID,
    p_round_id UUID DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_requirement_id UUID;
BEGIN
    SELECT id INTO v_requirement_id
    FROM requirement_set
    WHERE track_id = p_track_id
    AND term_id = p_term_id
    AND (round_id = p_round_id OR (round_id IS NULL AND p_round_id IS NULL))
    AND status = 'approved'
    ORDER BY last_verified_at DESC
    LIMIT 1;

    RETURN v_requirement_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to calculate confidence score
CREATE OR REPLACE FUNCTION calculate_confidence(
    p_requirement_set_id UUID
)
RETURNS NUMERIC AS $$
DECLARE
    v_confidence NUMERIC(3,2) := 0.5; -- Base confidence
    v_has_citations BOOLEAN;
    v_has_tests BOOLEAN;
    v_issue_count INTEGER;
BEGIN
    -- Check for citations (+0.2)
    SELECT EXISTS(
        SELECT 1 FROM citation WHERE requirement_set_id = p_requirement_set_id
    ) INTO v_has_citations;
    IF v_has_citations THEN
        v_confidence := v_confidence + 0.2;
    END IF;

    -- Check for test requirements (+0.2)
    SELECT EXISTS(
        SELECT 1 FROM tests WHERE requirement_set_id = p_requirement_set_id
    ) INTO v_has_tests;
    IF v_has_tests THEN
        v_confidence := v_confidence + 0.2;
    END IF;

    -- Check validation issues (-0.1 per error)
    SELECT COUNT(*) INTO v_issue_count
    FROM validation_issue
    WHERE requirement_set_id = p_requirement_set_id
    AND severity = 'error'
    AND resolved_at IS NULL;

    v_confidence := v_confidence - (v_issue_count * 0.1);

    -- Clamp between 0 and 1
    RETURN GREATEST(0, LEAST(1, v_confidence));
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =========================================
-- GRANTS for proper access
-- =========================================

-- Grant usage on schema to authenticated users
GRANT USAGE ON SCHEMA public TO anon, authenticated;

-- Grant select on views to anon (public)
GRANT SELECT ON current_requirements_view TO anon;
GRANT SELECT ON program_search_view TO anon;

-- Grant execute on helper functions
GRANT EXECUTE ON FUNCTION is_reviewer() TO authenticated;
GRANT EXECUTE ON FUNCTION get_current_requirement(UUID, UUID, UUID) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION calculate_confidence(UUID) TO authenticated;