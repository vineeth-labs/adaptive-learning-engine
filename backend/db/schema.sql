-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "ltree";

-- Users table (required by learner_state foreign key)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Core Knowledge Graph
CREATE TABLE IF NOT EXISTS concepts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    path ltree, -- e.g., 'Java.Concurrency.Locks'
    difficulty_weight FLOAT CHECK (difficulty_weight BETWEEN 0 AND 1),
    metadata JSONB DEFAULT '{}' -- Stores interview traps, prompts, etc.
);

CREATE TABLE IF NOT EXISTS concept_relationships (
    source_id UUID REFERENCES concepts(id) ON DELETE CASCADE,
    target_id UUID REFERENCES concepts(id) ON DELETE CASCADE,
    relation_type VARCHAR(50), -- 'prerequisite_of', 'part_of'
    PRIMARY KEY (source_id, target_id, relation_type)
);

-- Learner Model (The Personalized Overlay)
CREATE TABLE IF NOT EXISTS learner_state (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    concept_id UUID REFERENCES concepts(id) ON DELETE CASCADE,
    mastery FLOAT DEFAULT 0.0,      -- Probabilistic estimate (0.0-1.0)
    confidence FLOAT DEFAULT 0.0,   -- Inferred psychological certainty
    fsrs_stability FLOAT DEFAULT 0.0, -- Memory stability in days
    evidence_count INT DEFAULT 0,   -- Number of interactions
    misconceptions JSONB DEFAULT '[]', -- Array of detected anti-patterns
    PRIMARY KEY (user_id, concept_id)
);
