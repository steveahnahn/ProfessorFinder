-- Graduate Admissions Requirements Database Schema
-- Comprehensive normalized structure for multi-level requirement management

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =========================================
-- ENTITIES: Institution Hierarchy
-- =========================================

-- Institution (University level)
CREATE TABLE IF NOT EXISTS institution (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    website TEXT,
    country TEXT DEFAULT 'US',
    carnegie_classification TEXT,
    ipeds_id INTEGER UNIQUE,
    structure_profile JSONB, -- {granularity: 'school'|'department'|'program', pdf_ratio: 0.5, js_heavy: true}
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- School/College within Institution
CREATE TABLE IF NOT EXISTS school (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id UUID NOT NULL REFERENCES institution(id) ON DELETE RESTRICT,
    name TEXT NOT NULL,
    website TEXT,
    type TEXT CHECK (type IN ('graduate', 'undergraduate', 'professional', 'mixed')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Department within School
CREATE TABLE IF NOT EXISTS department (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID NOT NULL REFERENCES school(id) ON DELETE RESTRICT,
    name TEXT NOT NULL,
    website TEXT,
    cip_code TEXT, -- Classification of Instructional Programs
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Program (Degree program)
CREATE TABLE IF NOT EXISTS program (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    department_id UUID NOT NULL REFERENCES department(id) ON DELETE RESTRICT,
    name TEXT NOT NULL,
    degree TEXT NOT NULL CHECK (degree IN ('MS', 'MA', 'MEng', 'MBA', 'PhD', 'EdD', 'JD', 'MD', 'DDS', 'PharmD', 'DVM', 'Other')),
    cip_code TEXT,
    website TEXT,
    priority_tier INTEGER DEFAULT 3, -- 1=P0 (top priority), 2=P1, 3=P2 (standard)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Track (Modality/Schedule variation of a program)
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

-- =========================================
-- CYCLE: Terms and Rounds
-- =========================================

CREATE TABLE IF NOT EXISTS term (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL CHECK (name IN ('Fall', 'Spring', 'Summer', 'Winter')),
    year INTEGER NOT NULL CHECK (year >= 2024 AND year <= 2030),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(name, year)
);

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
-- REQUIREMENTS: Core requirement sets
-- =========================================

CREATE TABLE IF NOT EXISTS requirement_set (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    track_id UUID NOT NULL REFERENCES track(id) ON DELETE RESTRICT,
    term_id UUID NOT NULL REFERENCES term(id) ON DELETE RESTRICT,
    round_id UUID REFERENCES round(id) ON DELETE RESTRICT, -- NULL for general requirements

    -- Source and verification
    source_url TEXT NOT NULL,
    last_verified_at TIMESTAMPTZ DEFAULT NOW(),
    confidence NUMERIC(3,2) DEFAULT 0.00 CHECK (confidence >= 0 AND confidence <= 1),

    -- Workflow status
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'needs_review', 'approved', 'archival')),
    reviewer_id UUID, -- References auth.users

    -- Versioning
    parse_version TEXT DEFAULT '1.0',
    extraction_method TEXT CHECK (extraction_method IN ('manual', 'heuristic', 'llm', 'mixed')),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Prevent duplicates for same track/term/round/version
    UNIQUE(track_id, term_id, round_id, parse_version)
);

-- =========================================
-- ATTRIBUTES: Requirement details (1:1 with requirement_set)
-- =========================================

-- Test requirements
CREATE TABLE IF NOT EXISTS tests (
    requirement_set_id UUID PRIMARY KEY REFERENCES requirement_set(id) ON DELETE CASCADE,

    -- Test statuses
    gre_status TEXT DEFAULT 'unknown' CHECK (gre_status IN ('required', 'optional', 'recommended', 'not_accepted', 'waived', 'unknown')),
    gmat_status TEXT DEFAULT 'unknown' CHECK (gmat_status IN ('required', 'optional', 'recommended', 'not_accepted', 'waived', 'unknown')),
    lsat_status TEXT DEFAULT 'unknown' CHECK (lsat_status IN ('required', 'optional', 'recommended', 'not_accepted', 'waived', 'unknown')),
    mcat_status TEXT DEFAULT 'unknown' CHECK (mcat_status IN ('required', 'optional', 'recommended', 'not_accepted', 'waived', 'unknown')),

    -- English proficiency minimums
    toefl_min INTEGER CHECK (toefl_min >= 0 AND toefl_min <= 120),
    toefl_section_min JSONB, -- {"reading": 22, "listening": 22, "speaking": 22, "writing": 22}
    ielts_min NUMERIC(2,1) CHECK (ielts_min >= 0 AND ielts_min <= 9),
    det_min INTEGER CHECK (det_min >= 0 AND det_min <= 160), -- Duolingo English Test

    -- Institution codes
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
-- PROVENANCE & AUDIT
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

    created_at TIMESTAMPTZ DEFAULT NOW(),

    INDEX idx_raw_capture_url (url),
    INDEX idx_raw_capture_dom_hash (dom_hash)
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

    created_at TIMESTAMPTZ DEFAULT NOW(),

    INDEX idx_citation_requirement (requirement_set_id),
    INDEX idx_citation_field (field_name)
);

-- =========================================
-- VALIDATION & CONFLICTS
-- =========================================

CREATE TABLE IF NOT EXISTS validation_issue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requirement_set_id UUID NOT NULL REFERENCES requirement_set(id) ON DELETE CASCADE,

    field_name TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('error', 'warning', 'info')),
    message TEXT NOT NULL,
    current_value TEXT,
    expected_value TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,

    INDEX idx_validation_requirement (requirement_set_id),
    INDEX idx_validation_severity (severity)
);

-- =========================================
-- VIEWS for easy access
-- =========================================

-- Current approved requirements (latest per track/term/round)
CREATE OR REPLACE VIEW current_requirements_view AS
WITH ranked_requirements AS (
    SELECT
        rs.*,
        t.track_id,
        t.term_id,
        t.round_id,
        ROW_NUMBER() OVER (
            PARTITION BY rs.track_id, rs.term_id, COALESCE(rs.round_id, '00000000-0000-0000-0000-000000000000')
            ORDER BY rs.last_verified_at DESC
        ) as rn
    FROM requirement_set rs
    JOIN (
        SELECT DISTINCT track_id, term_id, round_id
        FROM requirement_set
        WHERE status = 'approved'
    ) t ON rs.track_id = t.track_id
       AND rs.term_id = t.term_id
       AND (rs.round_id = t.round_id OR (rs.round_id IS NULL AND t.round_id IS NULL))
    WHERE rs.status = 'approved'
)
SELECT * FROM ranked_requirements WHERE rn = 1;

-- Denormalized search view
CREATE OR REPLACE VIEW program_search_view AS
SELECT
    p.id as program_id,
    p.name as program_name,
    p.degree,
    d.name as department_name,
    s.name as school_name,
    s.type as school_type,
    i.name as institution_name,
    i.country,
    i.website as institution_website,
    p.website as program_website,
    p.priority_tier,

    -- Aggregate track modalities
    ARRAY_AGG(DISTINCT t.modality) as modalities,
    ARRAY_AGG(DISTINCT t.schedule) as schedules,

    -- Latest requirement info
    MAX(rs.last_verified_at) as last_updated,
    AVG(rs.confidence)::NUMERIC(3,2) as avg_confidence,

    COUNT(DISTINCT rs.id) as requirement_count
FROM program p
JOIN department d ON p.department_id = d.id
JOIN school s ON d.school_id = s.id
JOIN institution i ON s.institution_id = i.id
LEFT JOIN track t ON p.id = t.program_id
LEFT JOIN requirement_set rs ON t.id = rs.track_id AND rs.status = 'approved'
GROUP BY p.id, p.name, p.degree, d.name, s.name, s.type, i.name, i.country, i.website, p.website, p.priority_tier;

-- =========================================
-- INDEXES for performance
-- =========================================

CREATE INDEX idx_school_institution ON school(institution_id);
CREATE INDEX idx_department_school ON department(school_id);
CREATE INDEX idx_program_department ON program(department_id);
CREATE INDEX idx_program_priority ON program(priority_tier);
CREATE INDEX idx_track_program ON track(program_id);
CREATE INDEX idx_requirement_set_track ON requirement_set(track_id);
CREATE INDEX idx_requirement_set_status ON requirement_set(status);
CREATE INDEX idx_requirement_set_confidence ON requirement_set(confidence);
CREATE INDEX idx_deadlines_requirement ON deadlines(requirement_set_id);
CREATE INDEX idx_deadlines_type ON deadlines(deadline_type);
CREATE INDEX idx_deadlines_ts ON deadlines(deadline_ts);

-- =========================================
-- TRIGGERS for updated_at
-- =========================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to all tables with updated_at
DO $$
DECLARE
    t text;
BEGIN
    FOR t IN
        SELECT table_name
        FROM information_schema.columns
        WHERE column_name = 'updated_at'
        AND table_schema = 'public'
    LOOP
        EXECUTE format('
            CREATE TRIGGER trigger_update_%I_updated_at
            BEFORE UPDATE ON %I
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at();
        ', t, t);
    END LOOP;
END $$;

-- =========================================
-- SEED DATA: Terms for 2025-2026
-- =========================================

INSERT INTO term (name, year) VALUES
    ('Fall', 2025),
    ('Spring', 2026),
    ('Summer', 2026),
    ('Fall', 2026),
    ('Spring', 2027)
ON CONFLICT DO NOTHING;

-- =========================================
-- COMMENTS for documentation
-- =========================================

COMMENT ON TABLE institution IS 'Top-level university/college entity';
COMMENT ON TABLE school IS 'Schools or colleges within an institution (e.g., School of Engineering)';
COMMENT ON TABLE department IS 'Academic departments within schools';
COMMENT ON TABLE program IS 'Degree programs offered by departments';
COMMENT ON TABLE track IS 'Variations of programs (online, part-time, etc.)';
COMMENT ON TABLE requirement_set IS 'Core requirement record linking to all requirement details';
COMMENT ON TABLE tests IS 'Test requirements and scores';
COMMENT ON TABLE components IS 'Application components (SOP, letters, etc.)';
COMMENT ON TABLE intl IS 'International student specific requirements';
COMMENT ON TABLE deadlines IS 'Application deadlines';
COMMENT ON TABLE raw_capture IS 'Raw HTML/PDF captures from crawling';
COMMENT ON TABLE citation IS 'Maps extracted fields to source text';
COMMENT ON COLUMN requirement_set.confidence IS 'Confidence score 0-1, where >0.9 means auto-approve';
COMMENT ON COLUMN tests.det_min IS 'Duolingo English Test minimum score';