This technical specification outlines the architecture, data models, and implementation details for the **AI Competency Mapping MVP**, specifically focused on the **Java Interview Preparation** domain.

---

# Technical Specification: AI Competency Mapping MVP

## 1. Core Technology Stack
*   **Backend**: Python 3.10+ with **FastAPI** (asynchronous for LLM I/O).
*   **Database**: **PostgreSQL** with `ltree` (for hierarchies) and `JSONB` (for dynamic metadata).
*   **ORM**: SQLAlchemy 2.0 (Async) with Alembic for migrations.
*   **AI Orchestration**: OpenAI SDK using **Structured Outputs** (Pydantic-enforced).
*   **Task Queue**: Redis + Celery (for background LLM processing).
*   **Frontend**: React with **React Flow** or D3.js for the Directed Acyclic Graph (DAG) visualization.

---

## 2. Database Schema (PostgreSQL)
The schema implements a **Directed Acyclic Graph (DAG)** to model knowledge and a decoupled **Learner State** for personalization.

```sql
-- Core Knowledge Graph
CREATE EXTENSION IF NOT EXISTS "ltree";

CREATE TABLE concepts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    path ltree, -- e.g., 'Java.Concurrency.Locks'
    difficulty_weight FLOAT CHECK (difficulty_weight BETWEEN 0 AND 1),
    metadata JSONB DEFAULT '{}' -- Stores interview traps, prompts, etc.
);

CREATE TABLE concept_relationships (
    source_id UUID REFERENCES concepts(id),
    target_id UUID REFERENCES concepts(id),
    relation_type VARCHAR(50), -- 'prerequisite_of', 'part_of'
    PRIMARY KEY (source_id, target_id, relation_type)
);

-- Learner Model (The Personalized Overlay)
CREATE TABLE learner_state (
    user_id UUID REFERENCES users(id),
    concept_id UUID REFERENCES concepts(id),
    mastery FLOAT DEFAULT 0.0,      -- Probabilistic estimate (0.0-1.0)
    confidence FLOAT DEFAULT 0.0,   -- Inferred psychological certainty
    fsrs_stability FLOAT DEFAULT 0.0, -- Memory stability in days
    evidence_count INT DEFAULT 0,   -- Number of interactions
    misconceptions JSONB DEFAULT '[]', -- Array of detected anti-patterns
    PRIMARY KEY (user_id, concept_id)
);
```

---

## 3. System Architecture (Modular Monolith)
The project is organized into modular services to allow for future scaling while keeping the MVP simple.

```text
/backend
├── /api
│   └── /routes          # FastAPI endpoints (map, recommendation, assessment)
├── /db
│   ├── /models          # SQLAlchemy models
│   └── /queries         # Ltree-based graph traversal logic
├── /services
│   ├── /llm             # OpenAI wrappers (ScenarioGen, DiagnosticEval)
│   ├── /learner         # BKT and FSRS mathematical update logic
│   └── /recommender     # Entropy-based "Next Best Action" scoring
├── /schemas             # Pydantic models for type-safe I/O
└── /worker              # Celery background tasks for LLM calls
```

---

## 4. Key Implementation Logic

### A. The Mastery Update (BKT Heuristic)
Every time an LLM evaluates a user response ($S_{obs}$), the mastery ($M$) is updated using an exponentially weighted moving average:
$$M_{new} = M_{old} + \alpha \cdot (S_{obs} - M_{old})$$
Where the learning rate ($\alpha$) decays as evidence ($E$) grows: $\alpha = \frac{1}{1 + 0.5 \cdot E}$.

### B. Adaptive Questioning (Shannon Entropy)
To minimize fatigue, the engine selects concepts with the highest uncertainty ($M \approx 0.5$).
*   **Algorithm**: Identify "frontier" nodes where prerequisites are mastered but the node itself is unproven. Group these into clusters and generate a single multi-concept scenario.

### C. Recommendation Scoring
The engine ranks the "Next Best Action" using a weighted formula:
$$Score_i = w_1 \cdot f_{gap}(M_i) + w_2 \cdot f_{review}(R_i) + w_3 \cdot f_{centrality}(G_i) - w_4 \cdot f_{fatigue}(E_i)$$
*   **Hard Pruning**: Any node whose prerequisites have mastery $< 0.75$ is excluded from recommendations.

---

## 5. LLM Agent Specifications
The MVP uses two primary agents with **Strict JSON Outputs**.

### Agent 1: Diagnostic Evaluator (GPT-4o)
*   **Goal**: Analyze text/code for specific Java concepts.
*   **Pydantic Schema Output**:
    ```python
    class ConceptEvaluation(BaseModel):
        concept_id: str
        mastery_score: float  # 0.0 to 1.0
        evidence_quote: str   # Exact string from user response
        misconception: Optional[str]
    ```

### Agent 2: Scenario Generator (GPT-4o-mini)
*   **Goal**: Create a single cohesive scenario (debugging or design task) that simultaneously tests a cluster of 3–4 concepts.

---

## 6. MVP API Endpoints
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/users/{id}/map` | Returns the DAG with user mastery color-coding. |
| `GET` | `/api/v1/recommendation/next` | Returns the next action (Assess, Review, or Teach). |
| `POST` | `/api/v1/assessments/evaluate` | Submits user response to the async evaluation queue. |
| `GET` | `/api/v1/assessments/status/{id}` | Polls for LLM evaluation completion. |

---

## 7. Implementation Constraints
*   **Domain Focus**: Strictly Java Interview Preparation (Concurrent collections, JVM Memory, Threading).
*   **Excluded Features**: No video hosting, no social chat, no gamified leaderboards, no manual note-taking.
*   **Performance**: Graph traversals for prerequisite checks must execute in milliseconds using `ltree` indexes.