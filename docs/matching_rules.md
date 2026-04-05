# Matching Rules

## Default weights
- base requirement: `0.25`
- skill: `0.40`
- soft skill: `0.20`
- growth: `0.15`

## Base requirement
Checks education, experience and certificate requirements.
- Education uses rank comparison.
- Experience supports `应届/实习可投`, year ranges and minimum-year rules.
- Certificates use the same approximate matcher used by skill matching.

## Skill matching
- `must_have_skills` carries higher weight than `nice_to_have_skills`.
- Exact match, synonym match, evidence-only match and fuzzy match are supported.
- Missing must-have skills are surfaced separately in `unmet_items` and `gap_analysis`.

## Soft skill matching
Job soft skills are mapped into student abilities.
Examples:
- `沟通能力` -> communication
- `学习能力` -> learning
- `抗压能力` -> stress
- `执行力` -> internship ability

## Growth potential
Growth potential combines:
- profile completeness
- competitiveness
- current learning / innovation / professional ability
- transferability to the target role
- promotion path or inferred growth space

## Risk flags
The engine raises risk flags when:
- base requirements are not fully met
- job profile confidence is low
- student profile completeness is low
- total score is below the recommendation threshold

