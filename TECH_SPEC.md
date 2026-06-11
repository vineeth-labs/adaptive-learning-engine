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
* **Cache & Background Jobs**: Redis paired with Celery (to handle LLM calls taking 2-10 seconds asynchronously).
* **LLM Integration**: OpenAI `gpt-4o` (Diagnostic Evaluator) and `gpt-4o-mini` (Scenario Generator). Relies strictly on OpenAI's Structured Outputs with Pydantic schemas.
---

## 3. Core Modules

### 3.1. Knowledge Graph Design
* Represented as a highly structured **Directed Acyclic Graph (DAG)**.
* **Nodes**: Encapsulate discrete atomic concepts (e.g., "Polymorphism"). Contains metadata (cognitive difficulty, semantic embeddings) via JSONB.
* **Edges**: Define pedagogical relationships such as `prerequisite_of`, `related_to`, and `part_of`. Modeled using PostgreSQL `ltree` and secondary associative tables.

### 3.2. Learner Model Design
* Decoupled from the static knowledge graph. For every user, a personalized overlay maps graph nodes to state vectors.
* **State Vector Variables**:
  1. **Mastery (M)**: Probabilistic estimate (0.0 to 1.0) of understanding. Updated via a modified Bayesian Knowledge Tracing (BKT) heuristic.
  2. **Confidence (C)**: Inferred/self-reported psychological certainty (0.0 to 1.0).
  3. **Retention (R)**: Probability of recall, modeled via Free Spaced Repetition Scheduler (FSRS).
  4. **Evidence Count (E)**: Number of historical interactions. Defines system certainty and dictates the dynamic learning rate.
  5. **Misconceptions**: JSON array of detected anti-patterns, forcing immediate targeted remediation.

### 3.3. Assessment Engine
* Employs modified Computerized Adaptive Testing (CAT) integrated with Item Response Theory (IRT) and graph topology.
* **Q-Matrix**: Bipartite mapping connecting a single crafted technical scenario to multiple concepts simultaneously.
* **Algorithm**: Calculates Shannon Entropy for candidate "frontier" nodes. Groups related nodes into clusters and prompts the LLM to generate a scenario that resolves the maximum amount of uncertainty (Information Gain).
* **Graph Pruning**: Demonstrating mastery of foundational concepts implicitly updates/prunes dependent nodes.

### 3.4. LLM System Design
Modular, single-purpose agents communicating via strict Pydantic schemas to prevent hallucinations.
* **Agent 1: Scenario Generator**: Creates minimal-fatigue, multi-concept assessment items based on entropy clusters.
* **Agent 2: Diagnostic Evaluator**: Evaluates user response against targeted concepts, returning continuous mastery scores, identifying explicit misconceptions, and assessing linguistic confidence.
* **Agent 3: Concept Extractor**: Parses raw docs/transcripts into atomic nodes and edges for PostgreSQL ingestion.

### 3.5. Recommendation Engine
* Operates as a personalized ranking system computing an **Action Priority Score** to determine the "Next Best Topic".
* **Pruning**: Nodes lacking minimum prerequisite mastery ($M < 0.75$) are filtered out.
* **Scoring Heuristics**:
  * **Gap Function**: Prioritizes low mastery.
  * **Review Function**: Spikes if spaced-repetition retention drops below the optimal threshold (90%).
  * **Centrality Function**: Prioritizes nodes with high out-degree (foundational bottlenecks).
  * **Fatigue Function**: Penalizes recently interacted nodes.

### 3.6. Spaced Repetition (FSRS)
* Replaces legacy SM-2 with Free Spaced Repetition Scheduler (FSRS) tracking Retrievability (R), Stability (S), and Difficulty (D).
* Utilizes advanced power function approximation for memory decay. Background chronological jobs continuously calculate $R$ and inject review prompts when $R$ approaches 0.90.

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
* `learning_sessions`

---

## 5. MVP API Endpoints
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/users/{id}/map` | Returns the DAG with user mastery color-coding. |
| `GET` | `/api/v1/recommendation/next` | Returns the next action (Assess, Review, or Teach). |
| `POST` | `/api/v1/assessments/evaluate` | Submits user response to the async evaluation queue. |
| `GET` | `/api/v1/assessments/status/{id}` | Polls for completion of the asynchronous LLM evaluation. |

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
  /worker             # Celery background task definitions
  main.py             # FastAPI application entrypoint

