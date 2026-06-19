# Unit Test Tracker

Tests live under `tests/unit/`. Run with:

```bash
PYTHONPATH=. pytest tests/unit/ -v
```

No DB, no LLM, no network required for any test in this section — all packages tested here are pure in-memory logic.

---

## 1a — ConceptGraph

**File under test:** `backend/services/graph/concept_graph.py`
**Test file:** `tests/unit/test_concept_graph.py`

| # | Test | What it covers | Done |
|---|------|----------------|------|
| 1 | `test_concept_difficulty_valid` | `Concept` accepts difficulty in [0, 1] | [x] |
| 2 | `test_concept_difficulty_out_of_range` | `Concept` raises `ValueError` when difficulty < 0 or > 1 | [x] |
| 3 | `test_graph_happy_path` | `ConceptGraph` constructs without error for a valid DAG | [x] |
| 4 | `test_graph_duplicate_id` | Raises `ValueError` on duplicate concept id | [x] |
| 5 | `test_graph_unknown_prerequisite` | Raises `ValueError` when a prereq id doesn't exist | [x] |
| 6 | `test_graph_cycle_detection` | Raises `ValueError` when the edge set contains a cycle | [x] |
| 7 | `test_topological_order_linear_chain` | Topo order respects linear A → B → C dependency | [x] |
| 8 | `test_topological_order_diamond` | Topo order respects diamond dependency (A → B, A → C, B → D, C → D) | [x] |
| 9 | `test_ancestors_linear` | `ancestors("C")` returns `{"A", "B"}` for A → B → C | [x] |
| 10 | `test_ancestors_diamond` | `ancestors("D")` returns `{"A", "B", "C"}` for diamond graph | [x] |
| 11 | `test_ancestors_root` | `ancestors("A")` returns empty set for a root concept | [x] |
| 12 | `test_descendants_linear` | `descendants("A")` returns `{"B", "C"}` for A → B → C | [x] |
| 13 | `test_descendants_leaf` | `descendants("C")` returns empty set for a leaf concept | [x] |
| 14 | `test_direct_dependents` | `direct_dependents("A")` returns only immediate dependents, not transitive | [x] |
| 15 | `test_prerequisites_accessor` | `prerequisites("B")` returns `("A",)` for A → B | [x] |

---

## 1b — BKT Math

**File under test:** `backend/services/learner/bkt.py`
**Test file:** `tests/unit/test_bkt.py`

| # | Test | What it covers | Done |
|---|------|----------------|------|
| 1 | `test_bkt_posterior_correct_raises_belief` | Correct answer → posterior > prior | [x] |
| 2 | `test_bkt_posterior_incorrect_lowers_belief` | Incorrect answer → posterior < prior | [x] |
| 3 | `test_bkt_posterior_bounds` | Posterior always in (0, 1) | [x] |
| 4 | `test_bkt_update_applies_transition` | `bkt_update` ≥ `bkt_posterior` (learning transition adds probability) | [x] |
| 5 | `test_bkt_update_correct_monotonic` | Repeated correct answers monotonically increase belief | [x] |
| 6 | `test_bkt_update_graded_correct_equals_binary` | `bkt_update_graded(..., CORRECT)` == `bkt_update(..., True)` | [x] |
| 7 | `test_bkt_update_graded_incorrect_equals_binary` | `bkt_update_graded(..., INCORRECT)` == `bkt_update(..., False)` | [x] |
| 8 | `test_bkt_update_graded_partial_is_between` | PARTIAL result produces belief between CORRECT and INCORRECT updates | [x] |
| 9 | `test_entropy_at_zero` | `entropy(0.0)` == 0.0 | [x] |
| 10 | `test_entropy_at_one` | `entropy(1.0)` == 0.0 | [x] |
| 11 | `test_entropy_max_at_half` | `entropy(0.5)` == 1.0 | [x] |
| 12 | `test_entropy_symmetric` | `entropy(p)` == `entropy(1 - p)` | [x] |
| 13 | `test_expected_information_gain_positive` | EIG is non-negative for any belief in (0, 1) | [x] |
| 14 | `test_expected_information_gain_low_near_extremes` | EIG near p=0 or p=1 is lower than at p=0.5 | [x] |

---

## 1c — Beta-Bernoulli Mastery

**File under test:** `backend/services/learner/beta_mastery.py`
**Test file:** `tests/unit/test_beta_mastery.py`

| # | Test | What it covers | Done |
|---|------|----------------|------|
| 1 | `test_beta_state_mastery` | `mastery()` == alpha / (alpha + beta) | [x] |
| 2 | `test_beta_state_concentration` | `concentration()` == alpha + beta | [x] |
| 3 | `test_beta_state_variance_formula` | `variance()` matches Beta variance formula | [x] |
| 4 | `test_apply_score_full_credit` | score=1.0 increments alpha by weight, beta unchanged | [x] |
| 5 | `test_apply_score_zero_credit` | score=0.0 increments beta by weight, alpha unchanged | [x] |
| 6 | `test_apply_score_partial` | score=0.7 splits weight 0.7/0.3 between alpha/beta | [x] |
| 7 | `test_apply_score_clamps_negative` | score=-0.5 treated as 0.0 (clamped) | [x] |
| 8 | `test_apply_score_clamps_above_one` | score=1.5 treated as 1.0 (clamped) | [x] |
| 9 | `test_decay_no_elapsed` | `decay_toward_prior` with elapsed=0 returns original state | [x] |
| 10 | `test_decay_half_life` | At elapsed == half_life, distance to prior halves | [x] |
| 11 | `test_decay_large_elapsed` | Very large elapsed → state converges near the prior | [x] |
| 12 | `test_decay_zero_half_life` | half_life=0 returns original state unchanged | [x] |
| 13 | `test_prior_from_mean_preserves_mean` | `prior_from_mean(mean, c).mastery()` ≈ mean | [x] |
| 14 | `test_prior_from_mean_concentration` | `prior_from_mean(m, c).concentration()` == c | [x] |
| 15 | `test_lower_bound_clamped` | `lower_bound` always in [0, 1] | [x] |
| 16 | `test_evidence_mass_non_negative` | `evidence_mass` >= 0 for any state at or above the prior | [x] |
| 17 | `test_evidence_mass_at_prior` | `evidence_mass(prior, prior)` == 0 | [x] |
| 18 | `test_is_mastered_both_gates` | Returns True only when both mean threshold and evidence floor are met | [x] |
| 19 | `test_is_mastered_fails_evidence_gate` | High mean but insufficient evidence → False | [x] |
| 20 | `test_is_mastered_fails_mean_gate` | Enough evidence but low mean → False | [x] |

---

## 1d — KnowledgeTracer

**File under test:** `backend/services/learner/tracer.py`
**Test file:** `tests/unit/test_tracer.py`

| # | Test | What it covers | Done |
|---|------|----------------|------|
| 1 | `test_cold_start_root_gets_base_prior` | Root concept belief == `params.base_prior` on init | [x] |
| 2 | `test_cold_start_downstream_gated_prior` | Non-root concept belief == `base_prior * mean(prereq beliefs)` | [x] |
| 3 | `test_observe_correct_raises_belief` | `observe(concept, True)` → mastery increases | [x] |
| 4 | `test_observe_incorrect_lowers_belief` | `observe(concept, False)` → mastery decreases | [x] |
| 5 | `test_observe_propagates_to_downstream_prior` | Observing a prereq updates the prior of its dependents | [x] |
| 6 | `test_observe_unknown_concept_raises` | `observe` on an unknown concept id raises `KeyError` | [x] |
| 7 | `test_from_state_loads_mastery` | `from_state` sets belief for known concepts | [x] |
| 8 | `test_from_state_unknown_keeps_dynamic_prior` | Unloaded concepts retain prerequisite-gated prior | [x] |
| 9 | `test_from_state_invalid_mastery_raises` | Mastery outside [0,1] raises `ValueError` | [x] |
| 10 | `test_from_events_matches_observe` | `from_events` replay produces same belief as sequential `observe` calls | [x] |
| 11 | `test_select_next_excludes_blocked` | Concept with unmastered prereq not returned by `select_next` | [x] |
| 12 | `test_select_next_prefers_uncertain` | Among candidates, most uncertain concept (entropy closest to 0.5) is chosen | [x] |
| 13 | `test_select_next_returns_none_when_done` | Returns `None` when all reachable concepts are mastered | [x] |
| 14 | `test_select_next_undersampled_floor` | Concept asked fewer than `min_questions` times is always a candidate | [x] |
| 15 | `test_recommend_next_to_study_scores_leverage` | Picks concept with highest `(1 - mastery) * (1 + unblocked_downstream)` | [x] |
| 16 | `test_recommend_next_to_study_ready_prereqs_only` | Only considers concepts whose prereqs meet the threshold | [x] |
| 17 | `test_recommend_next_to_study_none_when_all_mastered` | Returns `None` when everything reachable is mastered | [x] |
| 18 | `test_gap_report_buckets` | Concepts bucketed correctly into mastered / shaky / not_learned | [x] |
| 19 | `test_gap_report_recommended_next` | `recommended_next` matches `recommend_next_to_study()` | [x] |
| 20 | `test_preview_path_nonempty_cold_start` | Returns a non-empty path from a cold-start state | [x] |
| 21 | `test_preview_path_distinct_concepts` | All concepts in preview path are distinct | [x] |
| 22 | `test_preview_path_max_steps` | Path length never exceeds `max_steps` | [x] |
| 23 | `test_recommend_path_first_matches_recommend_next` | First element of `recommend_path` == `recommend_next_to_study()` | [x] |
| 24 | `test_preview_path_does_not_mutate_tracer` | Calling `preview_path` does not change the tracer's belief state | [x] |
| 25 | `test_cluster_empty_when_nothing_learnable` | `select_frontier_cluster` returns `[]` when all reachable concepts are mastered/settled | [x] |
| 26 | `test_cluster_single_seed_when_frontier_thin` | Returns just `[seed]` when only one concept is on the frontier | [x] |
| 27 | `test_cluster_first_element_is_select_next_seed` | `cluster[0]` equals `select_next()` | [x] |
| 28 | `test_cluster_prefers_related_over_unrelated` | A related frontier sibling is chosen over an unrelated frontier concept | [x] |
| 29 | `test_cluster_all_members_on_frontier` | Every cluster member has its prerequisites mastered; members are distinct | [x] |
| 30 | `test_cluster_size_one_returns_only_seed` | `size=1` returns only the seed | [x] |
| 31 | `test_cluster_does_not_mutate_tracer` | `select_frontier_cluster` leaves the belief state unchanged | [x] |

---

## 1e — BKT Models

**File under test:** `backend/services/learner/bkt_models.py`
**Test file:** `tests/unit/test_bkt_models.py`

| # | Test | What it covers | Done |
|---|------|----------------|------|
| 1 | `test_bkt_params_defaults_valid` | Default `BKTParams()` passes validation | [x] |
| 2 | `test_bkt_params_zero_raises` | Any param == 0.0 raises `ValueError` | [x] |
| 3 | `test_bkt_params_one_raises` | Any param == 1.0 raises `ValueError` | [x] |
| 4 | `test_bkt_params_identifiability` | `p_slip + p_guess >= 1.0` raises `ValueError` | [x] |
| 5 | `test_grade_correct_value` | `Grade.CORRECT.value` == 1.0 | [x] |
| 6 | `test_grade_partial_value` | `Grade.PARTIAL.value` == 0.5 | [x] |
| 7 | `test_grade_incorrect_value` | `Grade.INCORRECT.value` == 0.0 | [x] |

---

## 1f — Pydantic Schemas

**Files under test:** `backend/schemas/assessment.py`, `recommendation.py`, `domain.py`, `map.py`
**Test file:** `tests/unit/test_schemas.py`

| # | Test | What it covers | Done |
|---|------|----------------|------|
| 1 | `test_action_type_enum_values` | `ActionType` has ASSESS, REVIEW, TEACH values | [x] |
| 2 | `test_action_type_invalid_raises` | Unknown string raises `ValidationError` | [x] |
| 3 | `test_recommendation_response_valid` | `RecommendationResponse` round-trips with valid data | [x] |
| 4 | `test_diagnostic_result_valid` | `DiagnosticResult` round-trips with valid question grades | [x] |
| 5 | `test_question_grade_score_bounds` | `answer_score` outside [0, 1] raises `ValidationError` (if validated) | [x] |
| 6 | `test_generated_questions_nonempty` | `GeneratedQuestions` requires at least one question | [x] |
| 7 | `test_domain_response_valid` | `DomainResponse` round-trips with name and id | [x] |
| 8 | `test_concept_node_mastery_default` | `ConceptNode` defaults mastery to 0.0 when not provided | [x] |

---

## 1g — Frontier Assessment building blocks

**Files under test:** `backend/services/llm/scenario_generator.py` (`generate_cluster_scenario`),
`backend/api/routes/assessments.py` (`_group_questions_by_concept`)
**Test file:** `tests/unit/test_frontier.py`

| # | Test | What it covers | Done |
|---|------|----------------|------|
| 1 | `test_one_question_per_concept_in_order` | Mock cluster scenario returns one question per concept, in cluster order | [x] |
| 2 | `test_empty_cluster_returns_empty` | `generate_cluster_scenario([])` returns `[]` | [x] |
| 3 | `test_null_concept_falls_back_to_seed` | Questions with no `concept_id` group under the seed concept | [x] |
| 4 | `test_splits_by_concept` | Questions group correctly by their `concept_id` | [x] |
| 5 | `test_ordered_by_position_within_group` | Each group is ordered by question position | [x] |
| 6 | `test_mixed_null_and_tagged` | NULL and seed-tagged questions fold into the same group | [x] |

---

## Placeholder Sections (future trackers)

The following will be tracked in separate docs under `tests/` once unit tests are complete:

- **`tests/service-test-tracker.md`** — DB-mocked service tests (`mastery.py`, `recommender/service.py`)
- **`tests/llm-test-tracker.md`** — Mocked LLM client tests (`scenario_generator.py`, `diagnostic_evaluator.py`)
- **`tests/api-test-tracker.md`** — API integration tests (`routes/assessments.py`, `routes/recommendations.py`, etc.)
