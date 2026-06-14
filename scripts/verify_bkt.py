#!/usr/bin/env python3
"""Focused integration check for the BKT learner-state update path.

Drives generate -> submit through the API in-process (LLM mock, no API key
needed) and asserts the LearnerState is updated by Bayesian Knowledge Tracing:
evidence accumulates, the belief moves and continues across submissions, and the
cold-start prerequisite-gated prior is applied.

Creates a temporary user and cleans it up (cascades to its learner_state /
assessments) at the end.

    PYTHONPATH=. python scripts/verify_bkt.py
"""
import asyncio
import sys
import uuid

import httpx
from sqlalchemy import delete, select

from backend.db.models import Concept, ConceptRelationship, LearnerState, User
from backend.db.session import async_session_maker
from backend.main import app
from backend.services.learner.mastery import _PARAMS, _prerequisite_gated_prior


def check(cond: bool, msg: str) -> None:
    if not cond:
        print(f"FAIL: {msg}", file=sys.stderr)
        sys.exit(1)
    print(f"PASS: {msg}")


async def main() -> None:
    print("Initializing BKT learner-state verification...\n")

    async with async_session_maker() as db:
        # A concept that has at least one prerequisite edge (to exercise gating).
        target_id = (
            await db.execute(
                select(ConceptRelationship.target_id).where(
                    ConceptRelationship.relation_type == "prerequisite"
                ).limit(1)
            )
        ).scalar_one_or_none()
        check(target_id is not None, "found a concept with a prerequisite edge")

        prereq_ids = (
            await db.execute(
                select(ConceptRelationship.source_id).where(
                    ConceptRelationship.target_id == target_id,
                    ConceptRelationship.relation_type == "prerequisite",
                )
            )
        ).scalars().all()

        target = (await db.execute(select(Concept).where(Concept.id == target_id))).scalar_one()
        print(f"  target concept: {target.name} ({len(prereq_ids)} prerequisite(s))\n")

        user = User(email=f"bkt-verify-{uuid.uuid4()}@example.com")
        db.add(user)
        await db.flush()  # populate user.id before creating dependent rows

        # Seed every prerequisite with a known mastery so the gated prior is predictable.
        seeded = 0.8
        for pid in prereq_ids:
            db.add(LearnerState(user_id=user.id, concept_id=pid, mastery=seeded, evidence_count=1))
        await db.commit()
        user_id = user.id

        # --- Cold-start prereq-gated prior --------------------------------
        prior = await _prerequisite_gated_prior(user_id, target_id, db)
        expected = _PARAMS.base_prior * seeded
        check(
            abs(prior - expected) < 1e-9,
            f"cold-start prior = base_prior*mean(prereqs) = {expected:.3f} (got {prior:.3f})",
        )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost:8000") as client:
        # --- Generate -> submit (first attempt) ---------------------------
        gen = await client.post(
            "/api/v1/assessments/generate",
            json={"user_id": str(user_id), "concept_id": str(target_id), "num_questions": 3},
        )
        check(gen.status_code == 200, f"generate returned 200 (got {gen.status_code}: {gen.text[:200]})")
        questions = gen.json()["questions"]
        n = len(questions)
        print(f"  generated {n} question(s)\n")

        submit = await client.post(
            f"/api/v1/assessments/{gen.json()['assessment_id']}/submit",
            json={
                "user_id": str(user_id),
                "responses": [
                    {"question_id": q["id"], "response_text": "A reasonable partial answer."}
                    for q in questions
                ],
            },
        )
        check(submit.status_code == 200, f"submit returned 200 (got {submit.status_code}: {submit.text[:200]})")
        mastery_1 = submit.json()["mastery_score"]
        print(f"  mastery after submit #1: {mastery_1:.3f}\n")

    async with async_session_maker() as db:
        state = (
            await db.execute(
                select(LearnerState).where(
                    LearnerState.user_id == user_id, LearnerState.concept_id == target_id
                )
            )
        ).scalar_one()
        check(state.evidence_count == n, f"evidence_count == #questions ({n})")
        check(0.0 < state.mastery < 1.0 and abs(state.mastery - mastery_1) < 1e-9,
              "mastery persisted and matches the response")
        check(state.last_interaction_at is not None, "last_interaction_at was set")

    # --- Second submission continues the trajectory (not a cold start) ----
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost:8000") as client:
        gen2 = await client.post(
            "/api/v1/assessments/generate",
            json={"user_id": str(user_id), "concept_id": str(target_id), "num_questions": 2},
        )
        q2 = gen2.json()["questions"]
        submit2 = await client.post(
            f"/api/v1/assessments/{gen2.json()['assessment_id']}/submit",
            json={
                "user_id": str(user_id),
                "responses": [
                    {"question_id": q["id"], "response_text": "Another partial answer."} for q in q2
                ],
            },
        )
        mastery_2 = submit2.json()["mastery_score"]
        print(f"  mastery after submit #2: {mastery_2:.3f}\n")

    async with async_session_maker() as db:
        state = (
            await db.execute(
                select(LearnerState).where(
                    LearnerState.user_id == user_id, LearnerState.concept_id == target_id
                )
            )
        ).scalar_one()
        check(state.evidence_count == n + len(q2), "evidence_count accumulated across submissions")
        # PARTIAL repeatedly nudges the belief upward from the prior trajectory.
        check(mastery_2 > mastery_1, "second submission continued from the stored prior (belief moved further)")

        # Cleanup: deleting the user cascades to learner_state / assessments.
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()
        print("\n  cleaned up temporary user")

    print("\nBKT VERIFICATION SUCCESSFUL!")


if __name__ == "__main__":
    asyncio.run(main())
