from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")
MONTH_RE = re.compile(
    r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+(\d{4})",
    re.IGNORECASE,
)

SKILL_ALIASES = {
    "py": "python",
    "python3": "python",
    "js": "javascript",
    "node": "javascript",
    "nodejs": "javascript",
    "node.js": "javascript",
    "react.js": "react",
    "postgres": "postgresql",
    "postgreSQL": "postgresql",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "aws cloud": "aws",
}

KNOWN_SKILLS = {
    "python",
    "javascript",
    "typescript",
    "react",
    "sql",
    "postgresql",
    "aws",
    "docker",
    "kubernetes",
    "machine learning",
    "data engineering",
    "etl",
    "spark",
    "airflow",
    "graphql",
    "rest api",
    "java",
    "go",
}

COUNTRY_CODES = {
    "united states": "US",
    "usa": "US",
    "us": "US",
    "india": "IN",
    "canada": "CA",
    "united kingdom": "GB",
    "uk": "GB",
}


def empty_canonical() -> dict[str, Any]:
    return {
        "candidate_id": None,
        "full_name": None,
        "emails": [],
        "phones": [],
        "location": {"city": None, "region": None, "country": None},
        "links": {"linkedin": None, "github": None, "portfolio": None, "other": []},
        "headline": None,
        "years_experience": None,
        "skills": [],
        "experience": [],
        "education": [],
        "provenance": [],
        "overall_confidence": 0.0,
    }


@dataclass
class Evidence:
    value: Any
    source: str
    method: str
    confidence: float


@dataclass
class CandidateAccumulator:
    key: str
    evidence: dict[str, list[Evidence]] = field(default_factory=dict)
    skill_sources: dict[str, set[str]] = field(default_factory=dict)
    records_seen: int = 0

    def add(self, field_path: str, value: Any, source: str, method: str, confidence: float) -> None:
        if value in (None, "", [], {}):
            return
        self.evidence.setdefault(field_path, []).append(Evidence(value, source, method, confidence))


def normalize_email(value: str | None) -> str | None:
    if not value:
        return None
    match = EMAIL_RE.search(value)
    return match.group(0).lower() if match else None


def normalize_phone(value: str | None, default_country: str = "US") -> str | None:
    if not value:
        return None
    match = PHONE_RE.search(value)
    if not match:
        return None
    raw = match.group(0)
    digits = re.sub(r"\D", "", raw)
    if raw.strip().startswith("+"):
        return "+" + digits
    if default_country == "US" and len(digits) == 10:
        return "+1" + digits
    if default_country == "IN" and len(digits) == 10:
        return "+91" + digits
    if len(digits) > 10:
        return "+" + digits
    return None


def normalize_country(value: str | None) -> str | None:
    if not value:
        return None
    clean = value.strip().lower()
    return COUNTRY_CODES.get(clean, value.strip().upper() if len(value.strip()) == 2 else None)


def normalize_skill(value: str) -> str | None:
    clean = re.sub(r"\s+", " ", value.strip().lower())
    clean = SKILL_ALIASES.get(clean, clean)
    return clean if clean in KNOWN_SKILLS else clean if len(clean) > 1 else None


def normalize_date(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    if re.fullmatch(r"\d{4}-\d{2}", value):
        return value
    match = MONTH_RE.search(value)
    if not match:
        year = re.search(r"\b(19|20)\d{2}\b", value)
        return f"{year.group(0)}-01" if year else None
    month_names = {
        "jan": "01",
        "feb": "02",
        "mar": "03",
        "apr": "04",
        "may": "05",
        "jun": "06",
        "jul": "07",
        "aug": "08",
        "sep": "09",
        "sept": "09",
        "oct": "10",
        "nov": "11",
        "dec": "12",
    }
    month = month_names[match.group(1).lower()[:3]]
    return f"{match.group(2)}-{month}"


def split_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in re.split(r"[,;/|]", value) if item.strip()]


def stable_candidate_id(seed: str) -> str:
    digest = hashlib.sha1(seed.lower().encode("utf-8")).hexdigest()[:10]
    return f"cand_{digest}"


def canonical_key(record: dict[str, Any]) -> str:
    emails = [normalize_email(e) for e in record.get("emails", [])]
    emails = [e for e in emails if e]
    if emails:
        return f"email:{emails[0]}"
    phones = [normalize_phone(p, record.get("country") or "US") for p in record.get("phones", [])]
    phones = [p for p in phones if p]
    if phones:
        return f"phone:{phones[0]}"
    return "name:" + re.sub(r"\W+", "", (record.get("full_name") or "unknown").lower())


def extract_csv(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            skills = [normalize_skill(s) for s in split_list(row.get("skills"))]
            rows.append(
                {
                    "source": f"csv:{path.name}",
                    "method": "csv-column-map",
                    "confidence": 0.9,
                    "full_name": row.get("name"),
                    "emails": [row.get("email")],
                    "phones": [row.get("phone")],
                    "country": row.get("country"),
                    "location": {
                        "city": row.get("city") or None,
                        "region": row.get("region") or None,
                        "country": normalize_country(row.get("country")),
                    },
                    "headline": row.get("title") or None,
                    "current_company": row.get("current_company") or None,
                    "years_experience": parse_number(row.get("years_experience")),
                    "skills": [s for s in skills if s],
                    "linkedin": row.get("linkedin") or None,
                    "github": row.get("github") or None,
                }
            )
    return rows


def parse_number(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"\d+(?:\.\d+)?", value)
    return float(match.group(0)) if match else None


def extract_notes(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    chunks = [c.strip() for c in re.split(r"\n\s*---+\s*\n", text) if c.strip()]
    records: list[dict[str, Any]] = []
    for index, chunk in enumerate(chunks, start=1):
        lines = [line.strip() for line in chunk.splitlines() if line.strip()]
        name = None
        for line in lines:
            if line.lower().startswith("candidate:"):
                name = line.split(":", 1)[1].strip()
                break
        emails = EMAIL_RE.findall(chunk)
        phones = PHONE_RE.findall(chunk)
        skills = sorted({s for s in (normalize_skill(x) for x in infer_skills(chunk)) if s})
        location = infer_location(chunk)
        records.append(
            {
                "source": f"notes:{path.name}#{index}",
                "method": "regex-and-keyword-extract",
                "confidence": 0.68,
                "full_name": name,
                "emails": emails,
                "phones": phones,
                "country": location.get("country"),
                "location": location,
                "headline": infer_headline(chunk),
                "years_experience": infer_years(chunk),
                "skills": skills,
                "linkedin": infer_link(chunk, "linkedin"),
                "github": infer_link(chunk, "github"),
                "experience": infer_experience(chunk),
                "education": infer_education(chunk),
            }
        )
    return records


def infer_skills(text: str) -> list[str]:
    found = []
    lower = text.lower()
    for skill in KNOWN_SKILLS | set(SKILL_ALIASES):
        if re.search(rf"\b{re.escape(skill.lower())}\b", lower):
            found.append(skill)
    skill_line = re.search(r"skills?\s*:\s*(.+)", text, re.IGNORECASE)
    if skill_line:
        found.extend(split_list(skill_line.group(1)))
    return found


def infer_location(text: str) -> dict[str, str | None]:
    location = {"city": None, "region": None, "country": None}
    match = re.search(r"location\s*:\s*([^,\n]+),\s*([^,\n]+),\s*([^,\n]+)", text, re.IGNORECASE)
    if match:
        location["city"] = match.group(1).strip()
        location["region"] = match.group(2).strip()
        location["country"] = normalize_country(match.group(3))
    return location


def infer_headline(text: str) -> str | None:
    match = re.search(r"(?:headline|role)\s*:\s*(.+)", text, re.IGNORECASE)
    return match.group(1).strip() if match else None


def infer_years(text: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)\+?\s*(?:years|yrs)", text, re.IGNORECASE)
    return float(match.group(1)) if match else None


def infer_link(text: str, kind: str) -> str | None:
    match = re.search(rf"https?://(?:www\.)?{kind}\.com/[^\s,)]+", text, re.IGNORECASE)
    return match.group(0) if match else None


def infer_experience(text: str) -> list[dict[str, Any]]:
    results = []
    for match in re.finditer(
        r"Experience:\s*([^,;\n]+),\s*([^,;\n]+),\s*([^,;\n]+),\s*([^.\n]+)",
        text,
        re.IGNORECASE,
    ):
        results.append(
            {
                "company": match.group(1).strip(),
                "title": match.group(2).strip(),
                "start": normalize_date(match.group(3)),
                "end": normalize_date(match.group(4)),
                "summary": None,
            }
        )
    return results


def infer_education(text: str) -> list[dict[str, Any]]:
    match = re.search(r"Education:\s*([^,;\n]+),\s*([^,;\n]+),\s*([^,;\n]+),\s*(\d{4})", text, re.IGNORECASE)
    if not match:
        return []
    return [
        {
            "institution": match.group(1).strip(),
            "degree": match.group(2).strip(),
            "field": match.group(3).strip(),
            "end_year": int(match.group(4)),
        }
    ]


def add_record(acc: CandidateAccumulator, record: dict[str, Any]) -> None:
    source = record["source"]
    method = record["method"]
    confidence = record["confidence"]
    acc.records_seen += 1
    acc.add("full_name", title_name(record.get("full_name")), source, method, confidence)
    for email in record.get("emails", []):
        acc.add("emails", normalize_email(email), source, method, confidence)
    country = record.get("location", {}).get("country") or record.get("country") or "US"
    for phone in record.get("phones", []):
        acc.add("phones", normalize_phone(phone, country), source, method, confidence)
    for key, value in (record.get("location") or {}).items():
        acc.add(f"location.{key}", value, source, method, confidence)
    for source_key, target_path in [
        ("linkedin", "links.linkedin"),
        ("github", "links.github"),
        ("portfolio", "links.portfolio"),
    ]:
        acc.add(target_path, record.get(source_key), source, method, confidence)
    acc.add("headline", record.get("headline"), source, method, confidence)
    acc.add("years_experience", record.get("years_experience"), source, method, confidence)
    for skill in record.get("skills", []):
        normalized = normalize_skill(skill)
        if normalized:
            acc.skill_sources.setdefault(normalized, set()).add(source)
    for item in record.get("experience", []):
        acc.add("experience", item, source, method, confidence)
    for item in record.get("education", []):
        acc.add("education", item, source, method, confidence)


def title_name(value: str | None) -> str | None:
    if not value:
        return None
    return " ".join(part.capitalize() for part in value.strip().split())


def choose_scalar(evidence: list[Evidence]) -> Evidence | None:
    if not evidence:
        return None
    grouped: dict[str, list[Evidence]] = {}
    for item in evidence:
        grouped.setdefault(json.dumps(item.value, sort_keys=True), []).append(item)
    ranked = sorted(
        grouped.values(),
        key=lambda items: (len(items), sum(i.confidence for i in items) / len(items), -len(str(items[0].value))),
        reverse=True,
    )
    return max(ranked[0], key=lambda item: item.confidence)


def build_canonical(acc: CandidateAccumulator) -> dict[str, Any]:
    result = empty_canonical()
    seed = acc.key
    result["candidate_id"] = stable_candidate_id(seed)
    for field_name in ["full_name", "headline", "years_experience"]:
        winner = choose_scalar(acc.evidence.get(field_name, []))
        result[field_name] = winner.value if winner else None
    for field_name in ["emails", "phones"]:
        values = []
        for item in sorted(acc.evidence.get(field_name, []), key=lambda e: (-e.confidence, str(e.value))):
            if item.value not in values:
                values.append(item.value)
        result[field_name] = values
    for subfield in ["city", "region", "country"]:
        winner = choose_scalar(acc.evidence.get(f"location.{subfield}", []))
        result["location"][subfield] = winner.value if winner else None
    for subfield in ["linkedin", "github", "portfolio"]:
        winner = choose_scalar(acc.evidence.get(f"links.{subfield}", []))
        result["links"][subfield] = winner.value if winner else None
    result["skills"] = [
        {"name": skill, "confidence": min(0.99, 0.62 + 0.15 * len(sources)), "sources": sorted(sources)}
        for skill, sources in sorted(acc.skill_sources.items())
    ]
    result["experience"] = unique_objects(acc.evidence.get("experience", []))
    result["education"] = unique_objects(acc.evidence.get("education", []))
    result["provenance"] = provenance(acc)
    result["overall_confidence"] = round(overall_confidence(result, acc), 2)
    return result


def unique_objects(items: list[Evidence]) -> list[dict[str, Any]]:
    seen = set()
    values = []
    for item in sorted(items, key=lambda e: -e.confidence):
        key = json.dumps(item.value, sort_keys=True)
        if key not in seen:
            seen.add(key)
            values.append(item.value)
    return values


def provenance(acc: CandidateAccumulator) -> list[dict[str, str]]:
    rows = []
    for field_path, evidence in sorted(acc.evidence.items()):
        winner = choose_scalar(evidence)
        if winner:
            rows.append({"field": field_path, "source": winner.source, "method": winner.method})
    for skill, sources in sorted(acc.skill_sources.items()):
        rows.append({"field": f"skills.{skill}", "source": ",".join(sorted(sources)), "method": "canonical-skill-map"})
    return rows


def overall_confidence(record: dict[str, Any], acc: CandidateAccumulator) -> float:
    required = ["full_name", "emails", "phones", "headline", "skills"]
    present = sum(1 for field_name in required if record.get(field_name))
    source_bonus = min(0.2, max(0, acc.records_seen - 1) * 0.1)
    return min(0.99, 0.45 + 0.07 * present + source_bonus)


def load_sources(input_paths: list[Path]) -> list[dict[str, Any]]:
    extracted = []
    for path in input_paths:
        if not path.exists():
            raise FileNotFoundError(path)
        if path.suffix.lower() == ".csv":
            extracted.extend(extract_csv(path))
        elif path.suffix.lower() == ".txt":
            extracted.extend(extract_notes(path))
        else:
            raise ValueError(f"Unsupported input type: {path}")
    return extracted


def merge_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    accumulators: dict[str, CandidateAccumulator] = {}
    for record in records:
        key = canonical_key(record)
        accumulators.setdefault(key, CandidateAccumulator(key=key))
        add_record(accumulators[key], record)
    return [build_canonical(acc) for acc in sorted(accumulators.values(), key=lambda a: a.key)]


def get_path(value: Any, path: str) -> Any:
    def walk(current: Any, parts: list[str]) -> Any:
        if not parts:
            return current
        part = parts[0]
        rest = parts[1:]
        if part.endswith("[]"):
            name = part[:-2]
            items = current.get(name) if isinstance(current, dict) else None
            if not isinstance(items, list):
                return None
            return [walk(item, rest) for item in items if walk(item, rest) is not None]
        if "[" in part:
            name, index_text = part.replace("]", "").split("[", 1)
            items = current.get(name) if isinstance(current, dict) else None
            if not isinstance(items, list):
                return None
            index = int(index_text)
            return walk(items[index], rest) if index < len(items) else None
        if isinstance(current, dict):
            return walk(current.get(part), rest)
        return None

    return walk(value, path.split("."))


def apply_normalizer(value: Any, normalizer: str | None) -> Any:
    if normalizer == "E164":
        return normalize_phone(str(value)) if value is not None else None
    if normalizer == "canonical":
        if isinstance(value, list):
            return [normalize_skill(str(v)) for v in value if normalize_skill(str(v))]
        return normalize_skill(str(value)) if value is not None else None
    return value


def coerce_type(value: Any, type_name: str) -> Any:
    if value is None:
        return None
    if type_name == "string":
        return str(value)
    if type_name == "string[]":
        if isinstance(value, list):
            return [str(v) for v in value]
        return [str(value)]
    if type_name == "number":
        return parse_number(str(value))
    if type_name == "boolean":
        return bool(value)
    return value


def project_record(record: dict[str, Any], config: dict[str, Any] | None) -> dict[str, Any]:
    if not config:
        return deepcopy(record)
    output: dict[str, Any] = {}
    on_missing = config.get("on_missing", "null")
    for field_config in config.get("fields", []):
        output_path = field_config["path"]
        source_path = field_config.get("from", output_path)
        value = get_path(record, source_path)
        value = apply_normalizer(value, field_config.get("normalize"))
        value = coerce_type(value, field_config.get("type", "any"))
        if value is None:
            if field_config.get("required") and on_missing == "error":
                raise ValueError(f"Missing required field: {output_path}")
            if on_missing == "omit":
                continue
        output[output_path] = value
    if config.get("include_confidence", False):
        output["overall_confidence"] = record["overall_confidence"]
    if config.get("include_provenance", False):
        output["provenance"] = record["provenance"]
    return output


def validate_record(record: dict[str, Any], projected: bool = False) -> list[str]:
    errors = []
    if not projected:
        if not record.get("candidate_id"):
            errors.append("candidate_id is required")
        for phone in record.get("phones", []):
            if not re.fullmatch(r"\+\d{8,15}", phone):
                errors.append(f"phone is not E.164: {phone}")
        country = (record.get("location") or {}).get("country")
        if country and not re.fullmatch(r"[A-Z]{2}", country):
            errors.append(f"country is not ISO-3166 alpha-2: {country}")
    return errors


def run(input_paths: list[Path], config_path: Path | None = None) -> list[dict[str, Any]]:
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path else None
    canonical = merge_records(load_sources(input_paths))
    errors = [error for record in canonical for error in validate_record(record)]
    if errors:
        raise ValueError("; ".join(errors))
    return [project_record(record, config) for record in canonical]


def main() -> int:
    parser = argparse.ArgumentParser(description="Multi-source candidate data transformer")
    parser.add_argument("--input", nargs="+", required=True, help="Input CSV/TXT files")
    parser.add_argument("--config", help="Optional projection config JSON")
    parser.add_argument("--output", help="Where to write JSON output; prints to stdout when omitted")
    args = parser.parse_args()

    records = run([Path(p) for p in args.input], Path(args.config) if args.config else None)
    payload = json.dumps(records, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
