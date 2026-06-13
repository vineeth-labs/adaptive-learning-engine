# knowledge-tracing engine

The deterministic core of an adaptive diagnostic: a graph-aware Bayesian
Knowledge Tracing engine that maintains a belief over a learner's mastery of
every concept, decides what to probe next, and recommends the highest-leverage
concept to study.

The LLM is deliberately **not** in here. Question generation and grading live at
the edges; this package only consumes a `Grade` and turns evidence into an
updated belief. That separation is the point: the intelligence is in the belief
state and the selection rule, not the prompt, and all of it is unit-testable
without any model calls.

## What's inside

| Module | Responsibility |
|---|---|
| `models.py` | `Concept`, `BKTParams`, `Grade`, `GapReport` |
| `graph.py` | `ConceptGraph` — DAG with cycle detection, topo order, ancestors/descendants |
| `bkt.py` | Pure BKT math: posterior, update, soft-evidence update, entropy, expected information gain |
| `tracer.py` | `KnowledgeTracer` — belief state, prerequisite-gated priors, selection, recommendation, gap report |
| `example_graph.py` | A small SQL concept graph for the demo and tests |

## Design notes

**Bayesian Knowledge Tracing** estimates `P(mastery)` per concept from a stream
of right/wrong answers using four parameters (prior, learn rate, slip, guess).

**Prerequisite-gated priors** are the extension over textbook per-skill BKT: a
concept with no direct evidence carries a prior of `base_prior * mean(prereq
beliefs)`, recomputed in topological order after every observation. So advanced
concepts start low until their prerequisites look solid, and evidence on a
prerequisite lifts the priors of everything downstream — this is what surfaces
"blocking" concepts.

**Selection** probes the concept on the learning frontier (prerequisites
mastered) with the highest uncertainty, with a minimum-questions floor so a
single unlucky slip can't write a concept off. An expected-information-gain
strategy is available as an upgrade.

**Recommendation** scores each learnable, not-yet-mastered concept by how shaky
it is times how many downstream concepts it unblocks, and returns the highest —
an explainable, graph-based "what to learn next."

## Run it

```bash
pip install pytest
python -m pytest -q     # 20 tests
python demo.py          # run the diagnostic loop against a simulated learner
```

The final test, `test_full_diagnostic_recovers_known_gaps`, is the end-to-end
validation: a synthetic learner with a known ground-truth mastery vector is run
through the whole loop and the inferred gaps are checked against the truth —
the system evaluated with zero real users. It holds above 77% accuracy across
seeds (mean ~98%).

## Next steps (not in this core)

- LLM question generator and grader behind a typed interface, with an eval set
  measuring grader/ground-truth agreement.
- FastAPI endpoints driving the loop (`/sessions`, `/next`, `/answer`, `/report`).
- Persist the answer-event log in Postgres as the source of truth; recompute
  beliefs from it.
- Misconception tagging (grade into specific error types), FSRS scheduling for
  review.
