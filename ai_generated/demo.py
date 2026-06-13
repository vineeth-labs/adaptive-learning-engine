"""Runnable demo: run the diagnostic agent loop against a simulated learner.

    python demo.py

The 'LLM' steps (generate question, grade answer) are stubbed by a simulator so
the loop runs offline. In the real system you swap `simulate_answer` for an LLM
call that generates a question for `concept_id` and grades the learner's reply.
"""

from __future__ import annotations

import random

from knowledge_tracing import BKTParams, KnowledgeTracer
from knowledge_tracing.example_graph import sql_graph


def simulate_answer(rng: random.Random, knows: bool, params: BKTParams) -> bool:
    if knows:
        return rng.random() > params.p_slip
    return rng.random() < params.p_guess


def main() -> None:
    rng = random.Random(0)
    graph = sql_graph()
    params = BKTParams()

    # Ground truth we are pretending not to know.
    truth = {
        "select": True, "where": True, "joins": True, "group_by": True,
        "aggregates": False, "having": False, "subqueries": True,
        "window": False, "ctes": False,
    }

    tracer = KnowledgeTracer(graph, params)

    print("Running diagnostic...\n")
    for step in range(1, 81):
        concept_id = tracer.select_next()
        if concept_id is None:
            print(f"Converged after {step - 1} questions.\n")
            break
        correct = simulate_answer(rng, truth[concept_id], params)
        tracer.observe(concept_id, correct=correct)
        mark = "correct" if correct else "wrong"
        print(f"  q{step:>2}  probe {concept_id:<11} -> {mark:<7}  belief={tracer.mastery(concept_id):.2f}")

    print("Final belief vs ground truth")
    print("-" * 48)
    for cid in graph.topological_order():
        inferred = "known" if tracer.mastery(cid) >= 0.5 else "gap"
        actual = "known" if truth[cid] else "gap"
        flag = "" if inferred == actual else "  <- mismatch"
        print(f"  {cid:<12} belief={tracer.mastery(cid):.2f}  inferred={inferred:<5} actual={actual}{flag}")

    report = tracer.gap_report()
    print("\nGap report")
    print("-" * 48)
    print(f"  mastered:     {report.mastered}")
    print(f"  shaky:        {report.shaky}")
    print(f"  not learned:  {report.not_learned}")
    print(f"\n  Highest-leverage next concept to study: {report.recommended_next}")


if __name__ == "__main__":
    main()
