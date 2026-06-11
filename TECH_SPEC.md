This technical specification outlines the architecture, data models, and implementation details for the **AI Competency Mapping MVP**, specifically focused on the **Java Interview Preparation** domain.

---

# Technical Specification: AI Competency Mapping MVP

## 1. Product Overview

The platform operates on a dynamic graph-traversal paradigm, shifting away from a traditional "course consumption" model to a "continuous diagnostic and remediation" model. It addresses metacognitive blindness by providing users with a precise mathematical model of their actual capabilities, forgotten concepts, and optimal next steps. 
* **MVP Scope**: Java Interview Preparation.
* **User Journey**: Goal Initialization -> Baseline Diagnostic -> Active Learning Loop -> Maintenance Reassessment.
* **Core Interface**: "Competency Map" (a Directed Acyclic Graph rendering) overlaid with user's mastery states.

## 2. Architecture & Technology Stack
The backend architecture is built utilizing a modular monolith pattern.
* **Backend**: Python with FastAPI (for asynchronous endpoints capable of handling concurrent IO-bound LLM requests).
* **Database**: PostgreSQL (utilizing the `ltree` extension for hierarchical data and `JSONB` for unstructured payloads).
* **ORM & Migrations**: SQLAlchemy 2.0 with async engine and Alembic.
* **LLM Integration**: OpenAI `gpt-4o` (Diagnostic Evaluator) and `gpt-4o-mini` (Scenario Generator). Relies strictly on OpenAI's Structured Outputs with Pydantic schemas.
---

### 3\. Core Modules (Simplified MVP)

#### 3.1. Knowledge Graph Design

The domain (Java Interview Preparation) is represented as a lightweight Directed Acyclic Graph (DAG) to establish learning pathways.

*   **Nodes**: Represent discrete atomic concepts (e.g., "Polymorphism", "Volatile Keyword").    
*   **Edges**: Define pedagogical dependencies, strictly utilizing prerequisite_of relationships to govern graph traversal.
*   **Implementation**: Stored in PostgreSQL. Hierarchical traversal and path mapping are managed using the ltree extension, enabling rapid querying of dependencies.

#### 3.2. Learner Model Design

The mathematical representation of the user's cognitive state is decoupled from the static knowledge graph. For every user, a personalized overlay maps graph nodes to individual state vectors.

*   **State Vector Variables** (Stored per concept):

    1.  **Mastery (M)**: A continuous score from 0.0 to 1.0 representing understanding. This is updated using a weighted moving average when new evaluations occur.
    2.  **Evidence Count (E)**: An integer representing the number of times the user has been evaluated on a specific concept. This dictates the system's confidence in the current Mastery score.
    3.  **Misconceptions**: A JSON array of explicit anti-patterns, foundational errors, or critical flaws extracted by the LLM (e.g., "Believes wait() does not require holding a monitor lock"). The presence of data here flags the concept for immediate remediation.
        

#### 3.3. Assessment Engine

The engine orchestrates the evaluation process using a dependency-aware "Frontier" heuristic to minimize user fatigue.

*   **Target Selection**: The engine queries the database to identify "Frontier Concepts"—nodes where all prerequisites have achieved a minimum Mastery threshold (> 0.7), but the node itself has a low or zero Evidence Count.
*   **Scenario Generation**: The engine selects 2 to 3 related Frontier Concepts and prompts the LLM to construct a single, cohesive technical scenario (e.g., a specific debugging task or architectural review) that evaluates them simultaneously.
*   **Pruning**: If a user demonstrates high mastery on an advanced node, the engine cascades a baseline mastery score downwards to its immediate prerequisites, avoiding redundant testing.
    

#### 3.4. LLM System Design

The platform's generative capabilities are decoupled into distinct, single-purpose agents to ensure reliability. All system outputs are strictly enforced using OpenAI's Structured Outputs with Pydantic models mapped to JSON Schemas.

*   **Agent 1: Scenario Generator**: Receives a cluster of target concepts and generates a highly focused, open-ended technical question that weaves the concepts together naturally.

*   **Agent 2: Diagnostic Evaluator**: Analyzes the user's free-text or code response against the target concepts. It outputs a strict schema containing the updated Mastery scores and any explicitly detected Misconceptions.
    

#### 3.5. Recommendation Engine

The Recommendation Engine acts as the platform's navigational core, utilizing a deterministic, priority-based routing system to dictate the user's next action.

*   **Hard Blocking**: Any concept whose immediate prerequisites have a Mastery < 0.75 is entirely hidden from the recommendation pool.
    
*   **Next Best Action Logic**:
    
    1.  **Priority 1 (Remediation)**: If the user's state vector contains active Misconceptions, the system immediately surfaces a targeted micro-lesson to correct the specific flaw before allowing forward progress.
    2.  **Priority 2 (Exploration)**: If no critical remediation is required, the system selects the available Frontier Concept with the lowest Evidence Count to expand the user's mapped graph.
    3.  **Priority 3 (Improvement)**: To reinforce weak areas, the system selects an available concept with a low Mastery score that has already been encountered.

---

## 4. Database Schema (PostgreSQL)
The schema implements a **Directed Acyclic Graph (DAG)** to model knowledge and a decoupled **Learner State** for personalization.

Strict adherence to 3NF for transactional data, JSONB for unstructured data, and `ltree` for hierarchy.

### Schema Definition
The complete PostgreSQL schema definition is maintained separately and can be found at:

`database/schema.sql`

* `users`
* `domains`
* `concepts` (Uses `ltree` for hierarchical paths)
* `concept_relationships` (Cross-cutting DAG dependencies)
* `learner_state` (Tracks mastery, confidence, retention, evidence count, and misconceptions)
* `assessments` (The generated scenarios)
* `assessment_results` (The Q-matrix multi-concept mapping)
* `recommendations` (Audit log for engine decisions)

---

## 5. MVP API Endpoints
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET`  | `/api/v1/domains` | Get list of available domains. |
| `GET`  | `/api/v1/domains/{domain_id}/concepts` | Get concepts in a domain. |
| `GET`  | `/api/v1/domains/{domain_id}/graph` | Get concept graph. |
| `GET`  | `/api/v1/users/{user_id}/competency-map` | Get user competency map. |
| `GET`  | `/api/v1/users/{user_id}/recommendations/next` | Get the next recommendation for the user. |
| `POST` | `/api/v1/assessments/generate` | Generates a new assessment for the user. |
| `POST` | `/api/v1/assessments/{assessment_id}/submit` | Submits user response to the async evaluation queue. |
| `GET`  | `/api/v1/assessments/{assessment_id}/results` | Returns the results of the assessment. |

---

## 6. Project Folder Structure

```text
/backend
  /api
    /routes           # FastAPI endpoint definitions
    /dependencies     # Auth token validation and DB session injection
  /core
    /config           # Pydantic BaseSettings for env vars
    /security         # JWT generation and hashing logic
  /db
    /models           # SQLAlchemy ORM models
    /migrations       # Alembic version control
    /queries          # Raw SQL and ltree specific abstractions
  /services
    /llm              # OpenAI client wrappers, Prompts, Structured Outputs
    /graph            # DAG traversal algorithms
    /learner          # BKT heuristic and FSRS mathematical logic
    /recommender      # Scoring and ranking heuristic algorithms
  /schemas            # Pydantic models for I/O and LLM Strict Parsing
  /scripts            # Utility scripts
  main.py             # FastAPI application entrypoint

