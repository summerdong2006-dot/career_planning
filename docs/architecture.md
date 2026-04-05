# Architecture

## Card 5 Matching Engine

The matching engine is implemented in `backend/app/modules/matching` and follows the same modular style as Card 3 and Card 4.

### Module layout
- `schema.py`: request and response contracts, normalized matching profile models, weight configuration.
- `config.py`: default weights, thresholds and skill / soft-skill mapping constants.
- `utils.py`: normalization, education parsing, approximate skill matching and helper utilities.
- `scorer.py`: four isolated scoring functions and weighted total score calculation.
- `matcher.py`: single-job matching and stable Top-K ranking.
- `service.py`: database loading, persistence, single recommendation, batch recommendation and detail query.
- `models.py`: `match_results` and `match_details` ORM tables.
- `cli.py`: command-line entry for single and batch matching.

### Scoring flow
1. Load one student profile and available job profiles from the existing Card 3 / Card 4 tables.
2. Normalize them into `StudentMatchProfile` and `JobMatchProfile`.
3. Compute four dimension scores independently:
   - base requirement
   - skill
   - soft skill
   - growth
4. Aggregate the weighted total score.
5. Build gap analysis, recommendation reason, evidence list and risk flags.
6. Rank by total score, then by skill score, then by base requirement score, then by `job_profile_id` for stable ordering.
7. Optionally persist summary and detail payloads for later inspection.

### Explainability
Every match result includes:
- `dimension_details[*].explanation`
- `dimension_details[*].evidence`
- `dimension_details[*].gaps`
- `dimension_details[*].details`

This keeps Card 6 free to consume either the summary score card or the richer evidence payload.

