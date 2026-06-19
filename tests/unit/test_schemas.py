import pytest
from uuid import uuid4
from pydantic import ValidationError

from backend.schemas import (
    ActionType,
    ConceptEvaluation,
    ConceptNode,
    DiagnosticResult,
    DomainResponse,
    GeneratedQuestion,
    GeneratedQuestions,
    GraphEdge,
    QuestionGrade,
    RecommendationDetail,
    RecommendationResponse,
)
from backend.schemas.domain import ConceptResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

UID = uuid4()
UID2 = uuid4()


def _question_grade(**overrides) -> dict:
    base = {
        "position": 1,
        "grade": "CORRECT",
        "answer_score": 0.9,
        "evidence_quote": "The user explained X correctly.",
        "misconception": None,
    }
    return {**base, **overrides}


def _diagnostic_result(**overrides) -> dict:
    base = {
        "question_grades": [_question_grade()],
        "answer_quality": 0.85,
        "misconception": None,
    }
    return {**base, **overrides}


# ---------------------------------------------------------------------------
# ActionType
# ---------------------------------------------------------------------------

class TestActionType:
    def test_assess_value(self):
        assert ActionType.ASSESS == "assess"

    def test_review_value(self):
        assert ActionType.REVIEW == "review"

    def test_teach_value(self):
        assert ActionType.TEACH == "teach"

    def test_three_members(self):
        assert len(ActionType) == 3

    def test_string_coercion(self):
        # ActionType is a str enum; "assess" == ActionType.ASSESS
        assert ActionType("assess") is ActionType.ASSESS

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            ActionType("learn")


# ---------------------------------------------------------------------------
# QuestionGrade
# ---------------------------------------------------------------------------

class TestQuestionGrade:
    def test_valid_round_trip(self):
        qg = QuestionGrade(**_question_grade())
        assert qg.position == 1
        assert qg.answer_score == 0.9
        assert qg.misconception is None

    def test_answer_score_at_zero_valid(self):
        QuestionGrade(**_question_grade(answer_score=0.0))

    def test_answer_score_at_one_valid(self):
        QuestionGrade(**_question_grade(answer_score=1.0))

    def test_answer_score_above_one_raises(self):
        with pytest.raises(ValidationError):
            QuestionGrade(**_question_grade(answer_score=1.1))

    def test_answer_score_below_zero_raises(self):
        with pytest.raises(ValidationError):
            QuestionGrade(**_question_grade(answer_score=-0.1))

    def test_grade_partial_valid(self):
        qg = QuestionGrade(**_question_grade(grade="PARTIAL", answer_score=0.5))
        assert qg.grade == "PARTIAL"

    def test_grade_incorrect_valid(self):
        qg = QuestionGrade(**_question_grade(grade="INCORRECT", answer_score=0.0))
        assert qg.grade == "INCORRECT"

    def test_grade_invalid_literal_raises(self):
        with pytest.raises(ValidationError):
            QuestionGrade(**_question_grade(grade="WRONG"))

    def test_missing_evidence_quote_raises(self):
        data = _question_grade()
        del data["evidence_quote"]
        with pytest.raises(ValidationError):
            QuestionGrade(**data)


# ---------------------------------------------------------------------------
# DiagnosticResult
# ---------------------------------------------------------------------------

class TestDiagnosticResult:
    def test_valid_round_trip(self):
        result = DiagnosticResult(**_diagnostic_result())
        assert len(result.question_grades) == 1
        assert result.answer_quality == 0.85

    def test_multiple_question_grades(self):
        data = _diagnostic_result(question_grades=[
            _question_grade(position=1),
            _question_grade(position=2, grade="PARTIAL", answer_score=0.5),
        ])
        result = DiagnosticResult(**data)
        assert len(result.question_grades) == 2

    def test_answer_quality_bounds(self):
        with pytest.raises(ValidationError):
            DiagnosticResult(**_diagnostic_result(answer_quality=1.5))
        with pytest.raises(ValidationError):
            DiagnosticResult(**_diagnostic_result(answer_quality=-0.1))

    def test_misconception_optional(self):
        result = DiagnosticResult(**_diagnostic_result(misconception="Confuses X with Y"))
        assert result.misconception == "Confuses X with Y"

    def test_missing_question_grades_raises(self):
        data = _diagnostic_result()
        del data["question_grades"]
        with pytest.raises(ValidationError):
            DiagnosticResult(**data)


# ---------------------------------------------------------------------------
# GeneratedQuestions
# ---------------------------------------------------------------------------

class TestGeneratedQuestions:
    def test_valid_single_question(self):
        gq = GeneratedQuestions(questions=[GeneratedQuestion(question_text="What is X?")])
        assert len(gq.questions) == 1

    def test_valid_multiple_questions(self):
        gq = GeneratedQuestions(questions=[
            GeneratedQuestion(question_text="Q1"),
            GeneratedQuestion(question_text="Q2"),
        ])
        assert len(gq.questions) == 2

    def test_empty_questions_list_valid(self):
        # Pydantic doesn't enforce min_length here; empty list is technically valid
        gq = GeneratedQuestions(questions=[])
        assert gq.questions == []

    def test_missing_question_text_raises(self):
        with pytest.raises(ValidationError):
            GeneratedQuestion()  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# DomainResponse
# ---------------------------------------------------------------------------

class TestDomainResponse:
    def test_valid_round_trip(self):
        dr = DomainResponse(id=UID, name="Java Interview Prep", version="1.0")
        assert dr.name == "Java Interview Prep"
        assert dr.id == UID

    def test_missing_name_raises(self):
        with pytest.raises(ValidationError):
            DomainResponse(id=UID, version="1.0")  # type: ignore[call-arg]

    def test_from_attributes(self):
        class Fake:
            id = UID
            name = "Java"
            version = "2"
        dr = DomainResponse.model_validate(Fake())
        assert dr.name == "Java"


# ---------------------------------------------------------------------------
# ConceptResponse
# ---------------------------------------------------------------------------

class TestConceptResponse:
    def test_valid_round_trip(self):
        cr = ConceptResponse.model_validate({
            "id": UID, "domain_id": UID2, "name": "Threads",
            "path": "java.concurrency.threads", "difficulty": 0.6,
            "metadata": {"tags": ["concurrency"]},
        })
        assert cr.difficulty == 0.6

    def test_metadata_alias_concept_metadata(self):
        cr = ConceptResponse.model_validate({
            "id": UID, "domain_id": UID2, "name": "Threads",
            "path": "java.concurrency.threads", "difficulty": 0.5,
            "concept_metadata": {"key": "val"},
        })
        assert cr.metadata == {"key": "val"}

    def test_difficulty_above_one_raises(self):
        with pytest.raises(ValidationError):
            ConceptResponse.model_validate({
                "id": UID, "domain_id": UID2, "name": "X",
                "path": "x", "difficulty": 1.5, "metadata": {},
            })

    def test_difficulty_below_zero_raises(self):
        with pytest.raises(ValidationError):
            ConceptResponse.model_validate({
                "id": UID, "domain_id": UID2, "name": "X",
                "path": "x", "difficulty": -0.1, "metadata": {},
            })


# ---------------------------------------------------------------------------
# ConceptNode (map schema)
# ---------------------------------------------------------------------------

class TestConceptNode:
    def test_mastery_defaults_to_zero(self):
        node = ConceptNode(
            id=UID, domain_id=UID2, name="Threads",
            path="java.threads", difficulty=0.5,
        )
        assert node.mastery == 0.0

    def test_evidence_count_defaults_to_zero(self):
        node = ConceptNode(
            id=UID, domain_id=UID2, name="Threads",
            path="java.threads", difficulty=0.5,
        )
        assert node.evidence_count == 0

    def test_misconceptions_defaults_to_empty_list(self):
        node = ConceptNode(
            id=UID, domain_id=UID2, name="Threads",
            path="java.threads", difficulty=0.5,
        )
        assert node.misconceptions == []

    def test_last_interaction_at_defaults_to_none(self):
        node = ConceptNode(
            id=UID, domain_id=UID2, name="Threads",
            path="java.threads", difficulty=0.5,
        )
        assert node.last_interaction_at is None

    def test_difficulty_bounds(self):
        with pytest.raises(ValidationError):
            ConceptNode(id=UID, domain_id=UID2, name="X", path="x", difficulty=1.1)


# ---------------------------------------------------------------------------
# GraphEdge / ConceptEdge — relation_type literal
# ---------------------------------------------------------------------------

class TestGraphEdge:
    def test_prerequisite_valid(self):
        edge = GraphEdge(source_id=UID, target_id=UID2, relation_type="prerequisite")
        assert edge.relation_type == "prerequisite"

    def test_invalid_relation_type_raises(self):
        with pytest.raises(ValidationError):
            GraphEdge(source_id=UID, target_id=UID2, relation_type="related")


# ---------------------------------------------------------------------------
# RecommendationDetail / RecommendationResponse
# ---------------------------------------------------------------------------

class TestRecommendationResponse:
    def _detail(self) -> dict:
        return {
            "concept_id": str(UID),
            "concept_name": "Java Threads",
            "score_calculated": 0.75,
            "score_breakdown": {"gap": 0.5, "centrality": 1.5},
        }

    def test_recommendation_detail_via_model_validate(self):
        detail = RecommendationDetail.model_validate(self._detail())
        assert detail.score == 0.75
        assert detail.concept_name == "Java Threads"

    def test_recommendation_response_valid(self):
        detail = RecommendationDetail.model_validate(self._detail())
        resp = RecommendationResponse(
            action_type=ActionType.ASSESS,
            recommended_concepts=[detail],
            rationale="Study Java Threads next.",
            payload={"roadmap": []},
        )
        assert resp.action_type == ActionType.ASSESS
        assert len(resp.recommended_concepts) == 1

    def test_action_type_string_coercion(self):
        detail = RecommendationDetail.model_validate(self._detail())
        resp = RecommendationResponse(
            action_type="review",  # type: ignore[arg-type]
            recommended_concepts=[detail],
            rationale="Review this.",
        )
        assert resp.action_type is ActionType.REVIEW

    def test_payload_optional(self):
        detail = RecommendationDetail.model_validate(self._detail())
        resp = RecommendationResponse(
            action_type=ActionType.ASSESS,
            recommended_concepts=[],
            rationale="Nothing to recommend.",
        )
        assert resp.payload is None

    def test_missing_score_calculated_raises(self):
        data = self._detail()
        del data["score_calculated"]
        with pytest.raises(ValidationError):
            RecommendationDetail.model_validate(data)


# ---------------------------------------------------------------------------
# ConceptEvaluation
# ---------------------------------------------------------------------------

class TestConceptEvaluation:
    def test_mastery_score_at_bounds(self):
        ConceptEvaluation(
            concept_id=UID, mastery_score=0.0, evidence_quote="nothing", misconception=None
        )
        ConceptEvaluation(
            concept_id=UID, mastery_score=1.0, evidence_quote="perfect", misconception=None
        )

    def test_mastery_score_above_one_raises(self):
        with pytest.raises(ValidationError):
            ConceptEvaluation(
                concept_id=UID, mastery_score=1.1, evidence_quote="x", misconception=None
            )

    def test_mastery_score_below_zero_raises(self):
        with pytest.raises(ValidationError):
            ConceptEvaluation(
                concept_id=UID, mastery_score=-0.1, evidence_quote="x", misconception=None
            )
