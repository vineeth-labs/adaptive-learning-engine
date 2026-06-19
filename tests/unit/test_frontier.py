"""Unit tests for the frontier-assessment building blocks that don't need a DB:
the multi-concept scenario generator's mock path and the submit grouping helper.
"""

import asyncio
from types import SimpleNamespace

import pytest

from backend.api.routes.assessments import _group_questions_by_concept
from backend.services.llm import scenario_generator


def _concept(name, difficulty=0.5):
    return SimpleNamespace(name=name, difficulty=difficulty, path=None, concept_metadata={})


# ---------------------------------------------------------------------------
# generate_cluster_scenario (mock path — no API key)
# ---------------------------------------------------------------------------

class TestGenerateClusterScenario:
    def test_one_question_per_concept_in_order(self, monkeypatch):
        monkeypatch.setattr(scenario_generator.settings, "SCENARIO_LLM_API_KEY", "")
        concepts = [_concept("Generics"), _concept("Concurrency"), _concept("Collections")]
        questions = asyncio.run(
            scenario_generator.generate_cluster_scenario(concepts, ["OOP Basics"])
        )
        assert len(questions) == 3
        # Each mock question mentions its own concept, in cluster order.
        assert "Generics" in questions[0]
        assert "Concurrency" in questions[1]
        assert "Collections" in questions[2]

    def test_empty_cluster_returns_empty(self, monkeypatch):
        monkeypatch.setattr(scenario_generator.settings, "SCENARIO_LLM_API_KEY", "")
        assert asyncio.run(scenario_generator.generate_cluster_scenario([], [])) == []


# ---------------------------------------------------------------------------
# _group_questions_by_concept (pure grouping for multi-concept submit)
# ---------------------------------------------------------------------------

def _q(position, concept_id, text="q"):
    return SimpleNamespace(position=position, concept_id=concept_id, question_text=text, user_response="")


class TestGroupQuestionsByConcept:
    def test_null_concept_falls_back_to_seed(self):
        seed = "seed-concept"
        questions = [_q(1, None), _q(2, None)]
        groups = _group_questions_by_concept(questions, seed)
        assert set(groups.keys()) == {seed}
        assert len(groups[seed]) == 2

    def test_splits_by_concept(self):
        questions = [_q(1, "c1"), _q(2, "c2"), _q(3, "c1")]
        groups = _group_questions_by_concept(questions, "seed")
        assert set(groups.keys()) == {"c1", "c2"}
        assert len(groups["c1"]) == 2
        assert len(groups["c2"]) == 1

    def test_ordered_by_position_within_group(self):
        questions = [_q(3, "c1", "third"), _q(1, "c1", "first"), _q(2, "c1", "second")]
        groups = _group_questions_by_concept(questions, "seed")
        assert [q.question_text for q in groups["c1"]] == ["first", "second", "third"]

    def test_mixed_null_and_tagged(self):
        # A NULL question folds into the seed group alongside an explicitly-seed-tagged one.
        questions = [_q(1, None), _q(2, "seed"), _q(3, "other")]
        groups = _group_questions_by_concept(questions, "seed")
        assert set(groups.keys()) == {"seed", "other"}
        assert len(groups["seed"]) == 2
