-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "ltree";

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    learning_goal VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Domains Table
CREATE TABLE IF NOT EXISTS domains (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) DEFAULT '1.0'
);

-- 3. Concepts Table (Using ltree for hierarchical paths)
CREATE TABLE IF NOT EXISTS concepts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    domain_id UUID REFERENCES domains(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    path ltree,
    difficulty FLOAT CHECK (difficulty >= 0 AND difficulty <= 1),
    metadata JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS path_gist_idx ON concepts USING GIST (path);
CREATE INDEX IF NOT EXISTS concept_metadata_idx ON concepts USING GIN (metadata);

-- 4. Concept Relationships Table (For cross-cutting DAG dependencies)
-- MVP restricts to strict prerequisite mapping to govern graph traversal
CREATE TABLE IF NOT EXISTS concept_relationships (
    source_id UUID REFERENCES concepts(id) ON DELETE CASCADE,
    target_id UUID REFERENCES concepts(id) ON DELETE CASCADE,
    relation_type VARCHAR(50) CHECK (relation_type IN ('prerequisite')),
    PRIMARY KEY (source_id, target_id, relation_type)
);

-- 5. Learner State Table
CREATE TABLE IF NOT EXISTS learner_state (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    concept_id UUID REFERENCES concepts(id) ON DELETE CASCADE,
    mastery FLOAT DEFAULT 0.0 CHECK (mastery >= 0 AND mastery <= 1),
    evidence_count INT DEFAULT 0,
    misconceptions JSONB DEFAULT '[]'::jsonb,
    last_interaction_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (user_id, concept_id)
);

-- 6. Assessments Table (One assessment per target concept; questions live in a child table)
CREATE TABLE IF NOT EXISTS assessments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    concept_id UUID REFERENCES concepts(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'generated',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6b. Assessment Questions Table (One row per generated free-text question + its response)
CREATE TABLE IF NOT EXISTS assessment_questions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assessment_id UUID REFERENCES assessments(id) ON DELETE CASCADE,
    position INT NOT NULL,
    question_text TEXT NOT NULL,
    user_response TEXT
);
CREATE INDEX IF NOT EXISTS assessment_questions_assessment_idx ON assessment_questions (assessment_id);

-- 7. Assessment Results Table (The Q-matrix multi-concept mapping)
CREATE TABLE IF NOT EXISTS assessment_results (
    assessment_id UUID REFERENCES assessments(id) ON DELETE CASCADE,
    concept_id UUID REFERENCES concepts(id) ON DELETE CASCADE,
    score_awarded FLOAT CHECK (score_awarded >= 0 AND score_awarded <= 1),
    evidence_quote TEXT,
    PRIMARY KEY (assessment_id, concept_id)
);

-- 8. Recommendations Table (Audit log for engine decisions)
CREATE TABLE IF NOT EXISTS recommendations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    concept_id UUID REFERENCES concepts(id) ON DELETE CASCADE,
    action_type VARCHAR(50) CHECK (action_type IN ('assess', 'teach', 'review')),
    score_calculated FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
