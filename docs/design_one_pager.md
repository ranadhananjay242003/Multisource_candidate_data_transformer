# Eightfold Candidate Transformer - One-Page Technical Design

## Goal

Build a deterministic pipeline that accepts multiple messy candidate sources and emits one trustworthy canonical profile per person, plus a runtime projection layer that can reshape output without changing transformation code.

## Pipeline

1. **Detect and extract**: select an extractor by source type. This implementation supports recruiter CSV and free-text recruiter notes. CSV uses column mapping; notes use bounded regex/key-value extraction for emails, phones, locations, skills, links, experience, and education.
2. **Normalize**: convert emails to lowercase, phones to E.164, countries to ISO-3166 alpha-2, dates to `YYYY-MM`, and skills to canonical lowercase names through an alias map.
3. **Match and merge**: group records by email first, phone second, and normalized name last. Scalar conflicts are resolved by evidence count, then average source confidence, then individual source confidence. Lists are deduped deterministically.
4. **Confidence and provenance**: every accepted value stores `{ field, source, method }`. Overall confidence increases when core fields are present and when independent sources agree.
5. **Project and validate**: keep canonical records fixed, then apply a runtime config that selects fields, renames output paths, reads from canonical paths like `emails[0]`, applies per-field normalizers, toggles confidence/provenance, and chooses `null`, `omit`, or `error` for missing values.

## Canonical schema

The canonical record contains `candidate_id`, `full_name`, `emails`, `phones`, `location { city, region, country }`, `links { linkedin, github, portfolio, other }`, `headline`, `years_experience`, `skills [{ name, confidence, sources }]`, `experience [{ company, title, start, end, summary }]`, `education [{ institution, degree, field, end_year }]`, `provenance`, and `overall_confidence`.

## Conflict policy

Email is the strongest match key because it is globally specific and already normalized. Phone is the fallback. Name-only matching is last because it risks false positives. Structured CSV starts at `0.90` confidence; notes start at `0.68` because parsing is less precise. If two sources disagree, repeated evidence wins before raw confidence so cross-source agreement beats one isolated high-confidence value.

## Runtime config handling

Projection happens after canonical validation. This avoids mixing business logic with customer-specific output shape. A config field defines `path`, optional `from`, `type`, optional `normalize`, and `required`. The same canonical profile can therefore produce default JSON or a custom schema such as `{ name, primary_email, primary_phone, top_skills }`.

## Edge cases handled

- Missing phone, email, country, or experience values do not crash the run.
- Bad phones are dropped rather than guessed.
- Skill aliases such as `JS`, `Node.js`, and `Postgres` become canonical names.
- Conflicting titles/headlines prefer more corroborated or higher-confidence evidence.
- Duplicate candidate rows from multiple sources merge into one profile with provenance.

## Deliberately scoped out

ATS JSON, live GitHub/LinkedIn lookups, and PDF/DOCX resume parsing are not implemented in this compact submission. They would be added as extractors that emit the same intermediate evidence objects, leaving normalization, merge, confidence, projection, and validation unchanged.
