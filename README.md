# Multi-Source Candidate Data Transformer

This is a runnable submission for the Eightfold Engineering Intern assignment. It turns messy candidate sources into deterministic canonical candidate JSON, then optionally reshapes that canonical record through a runtime config.

## What it handles

- Structured source: recruiter CSV.
- Unstructured source: recruiter notes text file.
- Normalization: email casing, E.164 phone numbers, ISO-3166 alpha-2 countries, `YYYY-MM` dates, and canonical skill names.
- Merge and conflict policy: candidates are matched by email first, phone second, then normalized name. Repeated evidence and higher-confidence sources win scalar conflicts.
- Explainability: each chosen field includes provenance, and each candidate receives an overall confidence score.
- Configurable output: `samples/custom_config.json` selects/renames fields, maps from canonical paths, toggles confidence/provenance, and controls missing values.

## Run

Requires Python 3.10+ and no third-party packages.

```bash
python -m src.transformer --input samples/recruiter_export.csv samples/recruiter_notes.txt --output outputs/default_output.json
```

Custom output projection:

```bash
python -m src.transformer --input samples/recruiter_export.csv samples/recruiter_notes.txt --config samples/custom_config.json --output outputs/custom_output.json
```

Run tests:

```bash
python -m unittest discover -s tests
```

## Design document

The one-page design deliverable is in `docs/YourFullName_YourEmail_Eightfold.pdf`. Rename it with your actual full name and email before submission. I also included `docs/design_one_pager.md` so the reasoning is easy to review in text.

## Assumptions and scope

- The demo intentionally uses one structured source and one unstructured source, as required.
- Unknown or malformed values become `null`/empty fields instead of being invented.
- The CLI supports CSV and TXT for this submission. The code is organized so ATS JSON, GitHub API, LinkedIn profile exports, or PDF/DOCX parsers could be added as new extractors.
- Skill canonicalization is a small local map plus deterministic lowercasing, not a remote taxonomy service.
- The sample output files in `outputs/` were produced by the commands above.
