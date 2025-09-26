-- Enhancement Migration for Graduate Admissions Schema
-- Adds new comprehensive tables while keeping existing data

-- =========================================
-- NEW COMPREHENSIVE TABLES
-- =========================================

-- School/College level (new - between institution and department)
CREATE TABLE IF NOT EXISTS school (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
    name TEXT NOT NULL,
    website TEXT,
    type TEXT CHECK (type IN ('graduate', 'undergraduate', 'professional', 'mixed')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Programs (new - specific degree programs)
CREATE TABLE IF NOT EXISTS program (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    department_id UUID NOT NULL REFERENCES departments(id) ON DELETE RESTRICT,
    name TEXT NOT NULL,
    degree TEXT NOT NULL CHECK (degree IN ('MS', 'MA', 'MEng', 'MBA', 'PhD', 'EdD', 'JD', 'MD', 'DDS', 'PharmD', 'DVM', 'Other')),
    cip_code TEXT,
    website TEXT,
    priority_tier INTEGER DEFAULT 3 CHECK (priority_tier BETWEEN 1 AND 5),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tracks (new - modality variations of programs)
CREATE TABLE IF NOT EXISTS track (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    program_id UUID NOT NULL REFERENCES program(id) ON DELETE RESTRICT,
    modality TEXT DEFAULT 'in_person' CHECK (modality IN ('in_person', 'online', 'hybrid')),
    schedule TEXT DEFAULT 'full_time' CHECK (schedule IN ('full_time', 'part_time', 'executive', 'accelerated')),
    honors_flag BOOLEAN DEFAULT FALSE,
    website TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Terms (academic terms)
CREATE TABLE IF NOT EXISTS term (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL CHECK (name IN ('Fall', 'Spring', 'Summer', 'Winter')),
    year INTEGER NOT NULL CHECK (year >= 2024 AND year <= 2030),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(name, year)
);

-- Rounds (application rounds within terms)
CREATE TABLE IF NOT EXISTS round (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    program_id UUID NOT NULL REFERENCES program(id) ON DELETE RESTRICT,
    term_id UUID NOT NULL REFERENCES term(id) ON DELETE RESTRICT,
    label TEXT NOT NULL, -- 'Priority', 'Round 1', 'Round 2', 'Final', 'Rolling'
    round_index INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(program_id, term_id, round_index)
);

-- =========================================
-- COMPREHENSIVE REQUIREMENT MANAGEMENT
-- =========================================

-- Requirement sets (versioned requirement records)
CREATE TABLE IF NOT EXISTS requirement_set (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    track_id UUID NOT NULL REFERENCES track(id) ON DELETE RESTRICT,
    term_id UUID NOT NULL REFERENCES term(id) ON DELETE RESTRICT,
    round_id UUID REFERENCES round(id) ON DELETE RESTRICT,

    -- Source and verification
    source_url TEXT NOT NULL,
    last_verified_at TIMESTAMPTZ DEFAULT NOW(),
    confidence NUMERIC(3,2) DEFAULT 0.00 CHECK (confidence >= 0 AND confidence <= 1),

    -- Workflow status
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'needs_review', 'approved', 'archival')),
    reviewer_id UUID, -- Would reference auth.users in production

    -- Versioning
    parse_version TEXT DEFAULT '1.0',
    extraction_method TEXT CHECK (extraction_method IN ('manual', 'heuristic', 'llm', 'mixed')),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(track_id, term_id, round_id, parse_version)
);

-- Enhanced test requirements (extends existing)
CREATE TABLE IF NOT EXISTS tests (
    requirement_set_id UUID PRIMARY KEY REFERENCES requirement_set(id) ON DELETE CASCADE,

    -- Test statuses (more comprehensive than boolean)
    gre_status TEXT DEFAULT 'unknown' CHECK (gre_status IN ('required', 'optional', 'recommended', 'not_accepted', 'waived', 'unknown')),
    gmat_status TEXT DEFAULT 'unknown' CHECK (gmat_status IN ('required', 'optional', 'recommended', 'not_accepted', 'waived', 'unknown')),
    lsat_status TEXT DEFAULT 'unknown' CHECK (lsat_status IN ('required', 'optional', 'recommended', 'not_accepted', 'waived', 'unknown')),
    mcat_status TEXT DEFAULT 'unknown' CHECK (mcat_status IN ('required', 'optional', 'recommended', 'not_accepted', 'waived', 'unknown')),

    -- Enhanced English proficiency
    toefl_min INTEGER CHECK (toefl_min >= 0 AND toefl_min <= 120),
    toefl_section_min JSONB, -- {"reading": 22, "listening": 22, "speaking": 22, "writing": 22}
    ielts_min NUMERIC(2,1) CHECK (ielts_min >= 0 AND ielts_min <= 9),
    det_min INTEGER CHECK (det_min >= 0 AND det_min <= 160), -- Duolingo English Test

    -- Institution codes (validated format)
    code_toefl TEXT CHECK (code_toefl ~ '^[0-9]{4}$'),
    code_gre TEXT CHECK (code_gre ~ '^[0-9]{4}$'),
    code_gmat TEXT CHECK (code_gmat ~ '^[A-Z0-9]{3,4}$'),

    -- Score validity
    score_validity_months INTEGER DEFAULT 24,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Application components
CREATE TABLE IF NOT EXISTS components (
    requirement_set_id UUID PRIMARY KEY REFERENCES requirement_set(id) ON DELETE CASCADE,

    sop_required BOOLEAN,
    rec_min INTEGER CHECK (rec_min >= 0 AND rec_min <= 10),
    rec_max INTEGER CHECK (rec_max >= 0 AND rec_max <= 10),
    resume_required BOOLEAN,
    portfolio_required BOOLEAN,
    writing_sample_required BOOLEAN,
    prereq_list JSONB, -- ["Data Structures", "Algorithms", "Linear Algebra"]
    gpa_min NUMERIC(3,2) CHECK (gpa_min >= 0 AND gpa_min <= 4.00),
    experience_years_min INTEGER,

    -- Fees
    fee_amount NUMERIC(8,2) CHECK (fee_amount >= 0 AND fee_amount <= 1000),
    fee_waiver_policy_url TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- International student requirements
CREATE TABLE IF NOT EXISTS intl (
    requirement_set_id UUID PRIMARY KEY REFERENCES requirement_set(id) ON DELETE CASCADE,

    wes_required BOOLEAN DEFAULT FALSE,
    ece_required BOOLEAN DEFAULT FALSE,
    transcript_policy TEXT,
    english_exemptions TEXT, -- "Degree from English-speaking country or MOI English"
    funding_docs_required BOOLEAN DEFAULT TRUE,
    i20_processing_time_days INTEGER,
    intl_contact_email TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Deadlines (1:many with requirement_set)
CREATE TABLE IF NOT EXISTS deadlines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requirement_set_id UUID NOT NULL REFERENCES requirement_set(id) ON DELETE CASCADE,

    deadline_type TEXT NOT NULL CHECK (deadline_type IN ('priority', 'regular', 'final', 'scholarship', 'rolling')),
    deadline_ts TIMESTAMPTZ NOT NULL,
    rolling_flag BOOLEAN DEFAULT FALSE,
    audience TEXT DEFAULT 'both' CHECK (audience IN ('domestic', 'international', 'both')),

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(requirement_set_id, deadline_type, audience)
);

-- Contact information (1:many with requirement_set)
CREATE TABLE IF NOT EXISTS contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requirement_set_id UUID NOT NULL REFERENCES requirement_set(id) ON DELETE CASCADE,

    contact_type TEXT DEFAULT 'general' CHECK (contact_type IN ('general', 'admissions', 'international', 'financial_aid')),
    email TEXT,
    phone TEXT,
    address TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =========================================
-- PROVENANCE & AUDIT TRAIL
-- =========================================

-- Raw captured content
CREATE TABLE IF NOT EXISTS raw_capture (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url TEXT NOT NULL,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    mime_type TEXT,
    http_status INTEGER,
    etag TEXT,
    robots_ok BOOLEAN DEFAULT TRUE,
    storage_path TEXT, -- Path in Supabase Storage
    screenshot_path TEXT, -- Path to screenshot if JS-rendered
    dom_hash TEXT, -- For change detection

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Audit trail linking requirements to raw captures
CREATE TABLE IF NOT EXISTS audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requirement_set_id UUID NOT NULL REFERENCES requirement_set(id) ON DELETE CASCADE,
    raw_capture_id UUID NOT NULL REFERENCES raw_capture(id) ON DELETE RESTRICT,

    parse_version TEXT DEFAULT '1.0',
    rules_version TEXT DEFAULT '1.0',
    checksum TEXT, -- SHA256 of extracted data
    notes TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Citations mapping fields to source text
CREATE TABLE IF NOT EXISTS citation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requirement_set_id UUID NOT NULL REFERENCES requirement_set(id) ON DELETE CASCADE,
    field_name TEXT NOT NULL, -- 'toefl_min', 'gre_status', etc.

    kind TEXT NOT NULL CHECK (kind IN ('html', 'pdf', 'manual')),

    -- For HTML
    selector TEXT, -- XPath or CSS selector

    -- For PDF
    page_num INTEGER,
    line_start INTEGER,
    line_end INTEGER,

    -- The actual text that supports this field
    snippet TEXT NOT NULL,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Validation issues
CREATE TABLE IF NOT EXISTS validation_issue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requirement_set_id UUID NOT NULL REFERENCES requirement_set(id) ON DELETE CASCADE,

    field_name TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('error', 'warning', 'info')),
    message TEXT NOT NULL,
    current_value TEXT,
    expected_value TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

-- =========================================
-- INDEXES FOR PERFORMANCE
-- =========================================

CREATE INDEX IF NOT EXISTS idx_school_institution ON school(institution_id);
CREATE INDEX IF NOT EXISTS idx_program_department ON program(department_id);
CREATE INDEX IF NOT EXISTS idx_program_priority ON program(priority_tier);
CREATE INDEX IF NOT EXISTS idx_track_program ON track(program_id);
CREATE INDEX IF NOT EXISTS idx_requirement_set_track ON requirement_set(track_id);
CREATE INDEX IF NOT EXISTS idx_requirement_set_status ON requirement_set(status);
CREATE INDEX IF NOT EXISTS idx_requirement_set_confidence ON requirement_set(confidence);
CREATE INDEX IF NOT EXISTS idx_deadlines_requirement ON deadlines(requirement_set_id);
CREATE INDEX IF NOT EXISTS idx_deadlines_type ON deadlines(deadline_type);
CREATE INDEX IF NOT EXISTS idx_deadlines_ts ON deadlines(deadline_ts);
CREATE INDEX IF NOT EXISTS idx_raw_capture_url ON raw_capture(url);
CREATE INDEX IF NOT EXISTS idx_raw_capture_dom_hash ON raw_capture(dom_hash);
CREATE INDEX IF NOT EXISTS idx_citation_requirement ON citation(requirement_set_id);
CREATE INDEX IF NOT EXISTS idx_citation_field ON citation(field_name);
CREATE INDEX IF NOT EXISTS idx_validation_requirement ON validation_issue(requirement_set_id);
CREATE INDEX IF NOT EXISTS idx_validation_severity ON validation_issue(severity);

-- =========================================
-- SEED DATA: Terms for 2025-2027
-- =========================================

INSERT INTO term (name, year) VALUES
    ('Fall', 2025),
    ('Spring', 2026),
    ('Summer', 2026),
    ('Fall', 2026),
    ('Spring', 2027)
ON CONFLICT (name, year) DO NOTHING;

-- =========================================
-- UPDATED AT TRIGGERS
-- =========================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers to new tables
DO $$
DECLARE
    t text;
BEGIN
    FOR t IN
        SELECT table_name
        FROM information_schema.columns
        WHERE column_name = 'updated_at'
        AND table_schema = 'public'
        AND table_name IN ('school', 'program', 'track', 'requirement_set', 'tests', 'components', 'intl')
    LOOP
        EXECUTE format('
            DROP TRIGGER IF EXISTS trigger_update_%I_updated_at ON %I;
            CREATE TRIGGER trigger_update_%I_updated_at
            BEFORE UPDATE ON %I
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at();
        ', t, t, t, t);
    END LOOP;
END $$;

-- =========================================
-- ENHANCED VIEWS
-- =========================================

-- Current approved requirements view
CREATE OR REPLACE VIEW current_requirements_view AS
WITH ranked_requirements AS (
    SELECT
        rs.*,
        ROW_NUMBER() OVER (
            PARTITION BY rs.track_id, rs.term_id, COALESCE(rs.round_id, '00000000-0000-0000-0000-000000000000'::uuid)
            ORDER BY rs.last_verified_at DESC
        ) as rn
    FROM requirement_set rs
    WHERE rs.status = 'approved'
)
SELECT * FROM ranked_requirements WHERE rn = 1;

-- Enhanced program search view (combines old and new structure)
CREATE OR REPLACE VIEW program_search_view AS
SELECT
    COALESCE(p.id::text, d.id::text) as program_id,
    COALESCE(p.name, d.name) as program_name,
    COALESCE(p.degree, 'Unknown') as degree,
    d.name as department_name,
    COALESCE(s.name, 'Unknown School') as school_name,
    COALESCE(s.type, 'mixed') as school_type,
    i.name as institution_name,
    i.country_code as country,
    i.website_url as institution_website,
    COALESCE(p.website, d.homepage_url) as program_website,
    COALESCE(p.priority_tier, 3) as priority_tier,

    -- Track information (if available)
    COALESCE(ARRAY_AGG(DISTINCT t.modality) FILTER (WHERE t.modality IS NOT NULL), ARRAY['in_person']) as modalities,
    COALESCE(ARRAY_AGG(DISTINCT t.schedule) FILTER (WHERE t.schedule IS NOT NULL), ARRAY['full_time']) as schedules,

    -- Latest requirement info
    GREATEST(d.updated_at, MAX(rs.last_verified_at)) as last_updated,
    COALESCE(AVG(rs.confidence)::NUMERIC(3,2), 0.5) as avg_confidence,

    COUNT(DISTINCT rs.id) as requirement_count

FROM institutions i
LEFT JOIN departments d ON i.id = d.institution_id
LEFT JOIN school s ON d.institution_id = s.institution_id -- Approximate mapping
LEFT JOIN program p ON d.id = p.department_id
LEFT JOIN track t ON p.id = t.program_id
LEFT JOIN requirement_set rs ON t.id = rs.track_id AND rs.status = 'approved'
WHERE i.is_active = true
GROUP BY
    i.id, i.name, i.country_code, i.website_url,
    d.id, d.name, d.homepage_url, d.updated_at,
    s.name, s.type,
    p.id, p.name, p.degree, p.website, p.priority_tier;

-- =========================================
-- COMMENTS FOR DOCUMENTATION
-- =========================================

COMMENT ON TABLE school IS 'Schools or colleges within institutions (new hierarchical level)';
COMMENT ON TABLE program IS 'Specific degree programs offered by departments';
COMMENT ON TABLE track IS 'Modality/schedule variations of programs (online, part-time, etc.)';
COMMENT ON TABLE requirement_set IS 'Versioned requirement records with full audit trail';
COMMENT ON TABLE tests IS 'Enhanced test requirements with status enums and section minima';
COMMENT ON TABLE components IS 'Application components (SOP, letters, portfolio, etc.)';
COMMENT ON TABLE intl IS 'International student specific requirements and policies';
COMMENT ON TABLE raw_capture IS 'Raw HTML/PDF captures with change detection';
COMMENT ON TABLE citation IS 'Maps extracted fields to source text for verification';

COMMENT ON COLUMN requirement_set.confidence IS 'Confidence score 0-1, where >0.9 typically means auto-approve';
COMMENT ON COLUMN tests.det_min IS 'Duolingo English Test minimum score (0-160 range)';
COMMENT ON COLUMN tests.toefl_section_min IS 'JSON object with section minima: {"reading": 22, "listening": 22, "speaking": 22, "writing": 22}';

-- Migration completed successfully
SELECT 'Enhanced schema migration completed successfully' as result;