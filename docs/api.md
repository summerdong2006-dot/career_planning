#API

## Matching

### POST /api/v1/matching/recommend

Request:

```json
{
  "student_profile_id": 1,
  "top_k": 5,
  "persist": true,
  "weights": {
    "base_requirement": 0.25,
    "skill": 0.40,
    "soft_skill": 0.20,
    "growth": 0.15
  }
}
```

Response fields:
- `student_profile_id`: student profile primary key.
- `top_k`: requested recommendation count.
- `matches`: sorted recommendation list.
- `matches[].dimension_scores`: four-dimension scores.
- `matches[].dimension_details`: explainable evidence, gaps and structured details.
- `matches[].risk_flags`: low-confidence job profile, low student completeness and threshold warnings.
- `matches[].match_id`: persisted match identifier when `persist=true`.

### POST /api/v1/matching/recommend-batch

Request:

```json
{
  "student_profile_ids": [1, 2, 3],
  "top_k": 5,
  "persist": true
}
```

Response:
- `results[]`: one recommendation payload per student profile.

### GET /api/v1/matching/{match_id}

Returns a persisted match detail payload, including:
- total score
- four-dimension scores
- dimension explanations and evidence chain
- gap analysis
- recommendation reason
- risk flags

## Persistence

When persistence is enabled, the matching module writes:
- `match_results`
- `match_details`

`match_results` stores the summary score card and weight configuration.
`match_details` stores the explainable detail payload returned by the API.

