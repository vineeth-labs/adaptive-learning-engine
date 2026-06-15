# Mastery update: Beta-Bernoulli model

How a learner's per-concept mastery is updated after each assessment. This is the
authoritative description of the update math; `TECH_SPEC.md` covers the surrounding
assessment / recommendation flow.

## Why this exists

Mastery used to be a **plain running average** of the LLM's single holistic score:

```
new = (old * count + answer_quality) / (count + 1)
```

That works, but it has no prior, no notion of confidence, and a 5-question assessment
only counts as one data point. We replaced it with **Beta-Bernoulli updating with
fractional (continuous-score) evidence** — the principled form of the same
"average + evidence count" idea. It is *not* machine learning: it's closed-form,
per-user Bayesian updating with hand-set parameters. No training corpus, no gradients.
(The only step that would count as ML is later *fitting* those parameters from
accumulated logs — and that wouldn't change the update code, only the constants.)

## The model

Each `(user, concept)` carries a `Beta(alpha, beta)` posterior, persisted as two
floats on `learner_state` (`backend/db/models/learner_state.py`):

- `alpha` accumulates fractional evidence **for** mastery, `beta` evidence **against**.
- **mastery** = posterior mean = `alpha / (alpha + beta)` — the headline number in
  `[0, 1]`, kept in the `mastery` column so the recommender / `KnowledgeTracer`
  (which read `mastery` + `evidence_count`) work unchanged.
- **concentration** = `alpha + beta` — grows with evidence; how confident we are.
- **variance** = `alpha·beta / (c²·(c+1))` — shrinks as concentration grows.
- **evidence mass** = `concentration − prior_concentration` — effective number of
  observations seen, excluding the prior.
- **credible lower bound** = `mean − z·std`, clamped to `[0, 1]` — low = uncertain;
  the natural signal for "what should we reassess". Computed on demand, not stored.

The math is a small pure module: `backend/services/learner/beta_mastery.py`.

## The update flow

`apply_diagnostic_result` (`backend/services/learner/mastery.py`) runs, per submission:

1. **Cold-start prior.** Compute a prior *mean* from the prerequisite-gated prior
   (`_prerequisite_gated_prior`): a root concept starts at `BKT_BASE_PRIOR`; otherwise
   `base_prior · mean(prereq masteries)`, so advanced concepts start low until their
   prerequisites look solid. Turn that mean into a Beta prior at the configured
   concentration: `prior = Beta(mean·C0, (1−mean)·C0)`.
2. **Starting belief.** Use the stored `(alpha, beta)` if the concept already has
   evidence; otherwise the prior.
3. **Forget.** Decay the belief toward the prior by the days since
   `last_interaction_at`: `gamma = 0.5 ** (elapsed_days / BETA_HALF_LIFE_DAYS)`,
   pulling `alpha`/`beta` toward the prior (not toward zero). This both drifts the
   estimate back and lowers confidence — what forgetting actually looks like.
4. **Apply evidence.** For **each question**, fold its `answer_score ∈ [0, 1]` (the
   LLM's per-question score) into the belief:
   `alpha += w·score`, `beta += w·(1 − score)` (`w = BETA_BASE_WEIGHT`). A continuous
   score splits one observation across the two counts instead of forcing 0/1. There is
   **no difficulty weighting** — every answer is weighted equally.
5. **Persist.** Write back `alpha`, `beta`, `mastery = mean`,
   `evidence_count += number_of_questions`, merged misconceptions, and
   `last_interaction_at`.

The "mastered" verdict (`beta_mastery.is_mastered`) gates on the mean clearing
`BETA_MASTERY_THRESHOLD` **and** evidence mass clearing `BETA_MIN_EVIDENCE_MASS` — the
evidence floor guards against a single lucky answer. Swap the mean for the lower bound
for a stricter, lucky-streak-proof gate.

## LLM contribution

The diagnostic evaluator (`backend/services/llm/diagnostic_evaluator.py`) returns, per
question, an `answer_score` float in `[0, 1]` (`QuestionGrade.answer_score`) alongside
the existing `grade` enum and evidence quote. That per-question score is the only LLM
output that drives mastery now; the holistic `answer_quality` is kept as a summary but
no longer updates the belief.

## Configuration

All knobs live on the `settings` singleton (`backend/core/config.py`) and in
`.env.example`:

| Setting | Default | Meaning |
|---|---|---|
| `BETA_PRIOR_ALPHA` | 2.0 | prior pseudo-evidence "for" (prior mean 0.5) |
| `BETA_PRIOR_BETA` | 2.0 | prior pseudo-evidence "against" |
| `BETA_BASE_WEIGHT` | 1.0 | evidence mass of one answer |
| `BETA_HALF_LIFE_DAYS` | 30.0 | forgetting half-life |
| `BETA_MIN_EVIDENCE_MASS` | 3.0 | evidence floor for the mastered gate |
| `BETA_MASTERY_THRESHOLD` | 0.7 | mean at/above which a concept is mastered |
| `BETA_CONFIDENCE_Z` | 1.2816 | z for the one-sided lower bound (~90%) |

The cold-start prior *mean* still derives from `BKT_BASE_PRIOR` so the Beta model and
the BKT-based tracer agree on where an unseen concept starts.

## Persistence note

`learner_state.alpha` / `beta` are nullable and populated on first write. For an
existing DB: `ALTER TABLE learner_state ADD COLUMN alpha FLOAT, ADD COLUMN beta FLOAT;`
Optional backfill from current values:
`alpha = BETA_PRIOR_ALPHA + mastery·evidence_count`,
`beta = BETA_PRIOR_BETA + (1 − mastery)·evidence_count`.
