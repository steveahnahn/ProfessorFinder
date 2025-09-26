-- Seed Data for 5 Pilot Institutions
-- Structurally diverse US universities for methodology validation

-- =========================================
-- PILOT INSTITUTIONS (5 diverse types)
-- =========================================

-- 1. Williams College - Small Liberal Arts (Simple structure)
INSERT INTO institution (id, name, website, country, carnegie_classification, structure_profile) VALUES
(
    '11111111-1111-1111-1111-111111111111',
    'Williams College',
    'https://www.williams.edu',
    'US',
    'Baccalaureate Colleges--Arts & Sciences',
    '{"granularity": "institution", "pdf_ratio": 0.2, "js_heavy": false, "expected_complexity": "simple"}'
) ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    website = EXCLUDED.website,
    structure_profile = EXCLUDED.structure_profile;

-- 2. Arizona State University - Large Public (Moderate complexity)
INSERT INTO institution (id, name, website, country, carnegie_classification, structure_profile) VALUES
(
    '22222222-2222-2222-2222-222222222222',
    'Arizona State University',
    'https://www.asu.edu',
    'US',
    'Doctoral Universities--Very High Research Activity',
    '{"granularity": "school", "pdf_ratio": 0.6, "js_heavy": true, "expected_complexity": "moderate"}'
) ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    website = EXCLUDED.website,
    structure_profile = EXCLUDED.structure_profile;

-- 3. University of Chicago - Private R1 (Complex structure)
INSERT INTO institution (id, name, website, country, carnegie_classification, structure_profile) VALUES
(
    '33333333-3333-3333-3333-333333333333',
    'University of Chicago',
    'https://www.uchicago.edu',
    'US',
    'Doctoral Universities--Very High Research Activity',
    '{"granularity": "department", "pdf_ratio": 0.4, "js_heavy": false, "expected_complexity": "complex"}'
) ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    website = EXCLUDED.website,
    structure_profile = EXCLUDED.structure_profile;

-- 4. University of California, Berkeley - Large Public R1 (Very complex)
INSERT INTO institution (id, name, website, country, carnegie_classification, structure_profile) VALUES
(
    '44444444-4444-4444-4444-444444444444',
    'University of California, Berkeley',
    'https://www.berkeley.edu',
    'US',
    'Doctoral Universities--Very High Research Activity',
    '{"granularity": "program", "pdf_ratio": 0.8, "js_heavy": true, "expected_complexity": "very_complex"}'
) ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    website = EXCLUDED.website,
    structure_profile = EXCLUDED.structure_profile;

-- 5. California Institute of Technology - Small Tech (Moderate complexity)
INSERT INTO institution (id, name, website, country, carnegie_classification, structure_profile) VALUES
(
    '55555555-5555-5555-5555-555555555555',
    'California Institute of Technology',
    'https://www.caltech.edu',
    'US',
    'Doctoral Universities--Very High Research Activity',
    '{"granularity": "school", "pdf_ratio": 0.3, "js_heavy": false, "expected_complexity": "moderate"}'
) ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    website = EXCLUDED.website,
    structure_profile = EXCLUDED.structure_profile;

-- =========================================
-- SCHOOL STRUCTURES for each institution
-- =========================================

-- Williams College (unified graduate division)
INSERT INTO school (id, institution_id, name, website, type) VALUES
(
    '11111111-1111-1111-2222-111111111111',
    '11111111-1111-1111-1111-111111111111',
    'Graduate School of Williams College',
    'https://www.williams.edu/graduate',
    'graduate'
) ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    website = EXCLUDED.website;

-- Arizona State University (multiple schools)
INSERT INTO school (id, institution_id, name, website, type) VALUES
(
    '22222222-2222-2222-2222-111111111111',
    '22222222-2222-2222-2222-222222222222',
    'Ira A. Fulton Schools of Engineering',
    'https://engineering.asu.edu',
    'graduate'
),
(
    '22222222-2222-2222-2222-222222222222',
    '22222222-2222-2222-2222-222222222222',
    'W. P. Carey School of Business',
    'https://wpcarey.asu.edu',
    'graduate'
),
(
    '22222222-2222-2222-2222-333333333333',
    '22222222-2222-2222-2222-222222222222',
    'College of Liberal Arts and Sciences',
    'https://clas.asu.edu',
    'mixed'
) ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    website = EXCLUDED.website;

-- University of Chicago (professional schools + divisions)
INSERT INTO school (id, institution_id, name, website, type) VALUES
(
    '33333333-3333-3333-3333-111111111111',
    '33333333-3333-3333-3333-333333333333',
    'University of Chicago Booth School of Business',
    'https://www.chicagobooth.edu',
    'graduate'
),
(
    '33333333-3333-3333-3333-222222222222',
    '33333333-3333-3333-3333-333333333333',
    'Pritzker School of Medicine',
    'https://pritzker.uchicago.edu',
    'professional'
),
(
    '33333333-3333-3333-3333-333333333333',
    '33333333-3333-3333-3333-333333333333',
    'Physical Sciences Division',
    'https://physicalsciences.uchicago.edu',
    'graduate'
) ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    website = EXCLUDED.website;

-- UC Berkeley (colleges)
INSERT INTO school (id, institution_id, name, website, type) VALUES
(
    '44444444-4444-4444-4444-111111111111',
    '44444444-4444-4444-4444-444444444444',
    'College of Engineering',
    'https://engineering.berkeley.edu',
    'mixed'
),
(
    '44444444-4444-4444-4444-222222222222',
    '44444444-4444-4444-4444-444444444444',
    'Haas School of Business',
    'https://haas.berkeley.edu',
    'graduate'
) ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    website = EXCLUDED.website;

-- Caltech (divisions)
INSERT INTO school (id, institution_id, name, website, type) VALUES
(
    '55555555-5555-5555-5555-111111111111',
    '55555555-5555-5555-5555-555555555555',
    'Division of Engineering and Applied Science',
    'https://www.eas.caltech.edu',
    'mixed'
),
(
    '55555555-5555-5555-5555-222222222222',
    '55555555-5555-5555-5555-555555555555',
    'Division of Physics, Mathematics and Astronomy',
    'https://pma.caltech.edu',
    'mixed'
) ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    website = EXCLUDED.website;

-- =========================================
-- SAMPLE DEPARTMENTS
-- =========================================

-- Williams College departments
INSERT INTO department (id, school_id, name, website, cip_code) VALUES
(
    '11111111-1111-1111-1111-111111111112',
    '11111111-1111-1111-2222-111111111111',
    'Graduate Studies',
    'https://www.williams.edu/graduate/programs',
    '30.0101'
) ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    website = EXCLUDED.website;

-- Arizona State - Engineering departments
INSERT INTO department (id, school_id, name, website, cip_code) VALUES
(
    '22222222-2222-2222-2222-111111111112',
    '22222222-2222-2222-2222-111111111111',
    'Computer Science and Engineering',
    'https://engineering.asu.edu/computer-science-engineering',
    '11.0701'
),
(
    '22222222-2222-2222-2222-222222222223',
    '22222222-2222-2222-2222-222222222222',
    'Business Administration',
    'https://wpcarey.asu.edu/graduate-programs',
    '52.0201'
) ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    website = EXCLUDED.website;

-- University of Chicago departments
INSERT INTO department (id, school_id, name, website, cip_code) VALUES
(
    '33333333-3333-3333-3333-111111111112',
    '33333333-3333-3333-3333-111111111111',
    'Business Administration',
    'https://www.chicagobooth.edu/programs',
    '52.0201'
),
(
    '33333333-3333-3333-3333-333333333334',
    '33333333-3333-3333-3333-333333333333',
    'Computer Science',
    'https://www.cs.uchicago.edu',
    '11.0701'
) ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    website = EXCLUDED.website;

-- UC Berkeley departments
INSERT INTO department (id, school_id, name, website, cip_code) VALUES
(
    '44444444-4444-4444-4444-111111111112',
    '44444444-4444-4444-4444-111111111111',
    'Electrical Engineering and Computer Sciences',
    'https://eecs.berkeley.edu',
    '11.0701'
),
(
    '44444444-4444-4444-4444-222222222223',
    '44444444-4444-4444-4444-222222222222',
    'Business Administration',
    'https://haas.berkeley.edu/graduate',
    '52.0201'
) ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    website = EXCLUDED.website;

-- Caltech departments
INSERT INTO department (id, school_id, name, website, cip_code) VALUES
(
    '55555555-5555-5555-5555-111111111112',
    '55555555-5555-5555-5555-111111111111',
    'Computer Science',
    'https://www.cms.caltech.edu/academics/grad_cs',
    '11.0701'
),
(
    '55555555-5555-5555-5555-222222222223',
    '55555555-5555-5555-5555-222222222222',
    'Physics',
    'https://pma.caltech.edu/research-and-academics/physics',
    '40.0801'
) ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    website = EXCLUDED.website;

-- =========================================
-- SAMPLE PROGRAMS (10 per institution for pilot)
-- =========================================

-- Williams College Programs (limited graduate offerings)
INSERT INTO program (id, department_id, name, degree, website, priority_tier) VALUES
(
    '11111111-1111-1111-1111-111111111113',
    '11111111-1111-1111-1111-111111111112',
    'Development Economics',
    'MA',
    'https://www.williams.edu/graduate/programs/development-economics',
    3
),
(
    '11111111-1111-1111-1111-111111111114',
    '11111111-1111-1111-1111-111111111112',
    'History of Art',
    'MA',
    'https://www.williams.edu/graduate/programs/history-art',
    3
) ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    website = EXCLUDED.website;

-- Arizona State Programs
INSERT INTO program (id, department_id, name, degree, website, priority_tier) VALUES
(
    '22222222-2222-2222-2222-111111111113',
    '22222222-2222-2222-2222-111111111112',
    'Computer Science',
    'MS',
    'https://engineering.asu.edu/graduate-programs/computer-science-ms',
    2
),
(
    '22222222-2222-2222-2222-111111111114',
    '22222222-2222-2222-2222-111111111112',
    'Computer Science',
    'PhD',
    'https://engineering.asu.edu/graduate-programs/computer-science-phd',
    2
),
(
    '22222222-2222-2222-2222-222222222224',
    '22222222-2222-2222-2222-222222222223',
    'Master of Business Administration',
    'MBA',
    'https://wpcarey.asu.edu/graduate-programs/mba',
    1
) ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    website = EXCLUDED.website;

-- University of Chicago Programs
INSERT INTO program (id, department_id, name, degree, website, priority_tier) VALUES
(
    '33333333-3333-3333-3333-111111111113',
    '33333333-3333-3333-3333-111111111112',
    'Master of Business Administration',
    'MBA',
    'https://www.chicagobooth.edu/programs/full-time',
    1
),
(
    '33333333-3333-3333-3333-333333333335',
    '33333333-3333-3333-3333-333333333334',
    'Computer Science',
    'MS',
    'https://www.cs.uchicago.edu/graduate/masters',
    2
),
(
    '33333333-3333-3333-3333-333333333336',
    '33333333-3333-3333-3333-333333333334',
    'Computer Science',
    'PhD',
    'https://www.cs.uchicago.edu/graduate/phd',
    2
) ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    website = EXCLUDED.website;

-- UC Berkeley Programs
INSERT INTO program (id, department_id, name, degree, website, priority_tier) VALUES
(
    '44444444-4444-4444-4444-111111111113',
    '44444444-4444-4444-4444-111111111112',
    'Computer Science',
    'MS',
    'https://eecs.berkeley.edu/graduate/computer-science-ms',
    1
),
(
    '44444444-4444-4444-4444-111111111114',
    '44444444-4444-4444-4444-111111111112',
    'Computer Science',
    'PhD',
    'https://eecs.berkeley.edu/graduate/computer-science-phd',
    1
),
(
    '44444444-4444-4444-4444-222222222224',
    '44444444-4444-4444-4444-222222222223',
    'Master of Business Administration',
    'MBA',
    'https://haas.berkeley.edu/graduate/full-time-mba',
    1
) ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    website = EXCLUDED.website;

-- Caltech Programs
INSERT INTO program (id, department_id, name, degree, website, priority_tier) VALUES
(
    '55555555-5555-5555-5555-111111111113',
    '55555555-5555-5555-5555-111111111112',
    'Computer Science',
    'MS',
    'https://www.cms.caltech.edu/academics/grad_cs',
    2
),
(
    '55555555-5555-5555-5555-111111111114',
    '55555555-5555-5555-5555-111111111112',
    'Computer Science',
    'PhD',
    'https://www.cms.caltech.edu/academics/grad_cs_phd',
    2
),
(
    '55555555-5555-5555-5555-222222222224',
    '55555555-5555-5555-5555-222222222223',
    'Physics',
    'PhD',
    'https://pma.caltech.edu/research-and-academics/physics/graduate',
    2
) ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    website = EXCLUDED.website;

-- =========================================
-- TRACKS (modality variations)
-- =========================================

-- Create default full-time, in-person tracks for all programs
INSERT INTO track (program_id, modality, schedule)
SELECT
    p.id,
    'in_person',
    'full_time'
FROM program p
WHERE p.id IN (
    '11111111-1111-1111-1111-111111111113',
    '11111111-1111-1111-1111-111111111114',
    '22222222-2222-2222-2222-111111111113',
    '22222222-2222-2222-2222-111111111114',
    '22222222-2222-2222-2222-222222222224',
    '33333333-3333-3333-3333-111111111113',
    '33333333-3333-3333-3333-333333333335',
    '33333333-3333-3333-3333-333333333336',
    '44444444-4444-4444-4444-111111111113',
    '44444444-4444-4444-4444-111111111114',
    '44444444-4444-4444-4444-222222222224',
    '55555555-5555-5555-5555-111111111113',
    '55555555-5555-5555-5555-111111111114',
    '55555555-5555-5555-5555-222222222224'
)
ON CONFLICT DO NOTHING;

-- Add some online/part-time variations for selected programs
INSERT INTO track (program_id, modality, schedule) VALUES
(
    '22222222-2222-2222-2222-222222222224', -- ASU MBA
    'online',
    'part_time'
),
(
    '33333333-3333-3333-3333-111111111113', -- UChicago MBA
    'in_person',
    'executive'
) ON CONFLICT DO NOTHING;

-- =========================================
-- GET FALL 2026 TERM ID
-- =========================================

DO $$
DECLARE
    fall_2026_id UUID;
BEGIN
    SELECT id INTO fall_2026_id FROM term WHERE name = 'Fall' AND year = 2026;

    -- Store in a variable for use in requirement_set insertion
    -- This is a placeholder - actual requirement sets will be created by ETL pipeline
    RAISE NOTICE 'Fall 2026 term ID: %', fall_2026_id;
END $$;

-- =========================================
-- SUMMARY VIEW for validation
-- =========================================

-- Create a summary view to validate seed data
CREATE OR REPLACE VIEW pilot_seed_summary AS
SELECT
    i.name as institution,
    COUNT(DISTINCT s.id) as schools,
    COUNT(DISTINCT d.id) as departments,
    COUNT(DISTINCT p.id) as programs,
    COUNT(DISTINCT t.id) as tracks,
    i.structure_profile->>'expected_complexity' as expected_complexity
FROM institution i
LEFT JOIN school s ON i.id = s.institution_id
LEFT JOIN department d ON s.id = d.school_id
LEFT JOIN program p ON d.id = p.department_id
LEFT JOIN track t ON p.id = t.program_id
WHERE i.id IN (
    '11111111-1111-1111-1111-111111111111',
    '22222222-2222-2222-2222-222222222222',
    '33333333-3333-3333-3333-333333333333',
    '44444444-4444-4444-4444-444444444444',
    '55555555-5555-5555-5555-555555555555'
)
GROUP BY i.id, i.name, i.structure_profile
ORDER BY i.name;