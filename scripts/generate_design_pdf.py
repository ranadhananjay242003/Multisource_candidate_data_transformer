from __future__ import annotations

import textwrap
from pathlib import Path


OUT = Path("docs/YourFullName_YourEmail_Eightfold.pdf")

TITLE = "Eightfold Candidate Transformer - Technical Design"

SECTIONS = [
    (
        "Pipeline",
        "Detect source type, extract fields, normalize formats, merge candidate evidence, "
        "score confidence, project to the requested customer schema, then validate before output.",
    ),
    (
        "Canonical schema",
        "candidate_id, full_name, emails, phones, location, links, headline, years_experience, "
        "skills with confidence/sources, experience, education, provenance, and overall_confidence.",
    ),
    (
        "Normalized formats",
        "Emails are lowercased, phones are E.164, countries are ISO-3166 alpha-2, dates are YYYY-MM, "
        "and skills are canonical lowercase names using an alias map such as JS -> javascript.",
    ),
    (
        "Merge policy",
        "Records match by email first, phone second, normalized name last. Scalar conflicts are resolved "
        "by repeated evidence, average source confidence, then individual confidence. Lists are deduped.",
    ),
    (
        "Runtime config",
        "The transformer always builds a full canonical record first. A separate projection layer selects "
        "fields, renames paths, maps from canonical paths like emails[0] or skills[].name, applies optional "
        "normalizers, toggles confidence/provenance, and handles missing values as null, omit, or error.",
    ),
    (
        "Handled edge cases",
        "Missing or malformed source fields do not crash the run; bad phones are dropped instead of guessed; "
        "CSV and notes for the same person merge into one profile; every chosen value keeps provenance.",
    ),
    (
        "Scoped out",
        "ATS JSON, live GitHub/LinkedIn calls, and PDF/DOCX resume parsing are left as future extractors. "
        "They can emit the same intermediate evidence objects without changing merge or projection logic.",
    ),
]


def pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_content() -> str:
    lines = ["BT", "/F1 16 Tf", "72 755 Td", f"({pdf_escape(TITLE)}) Tj"]
    y_gap = 24
    for heading, body in SECTIONS:
        lines.extend(["/F1 11 Tf", f"0 -{y_gap} Td", f"({pdf_escape(heading)}) Tj"])
        wrapped = textwrap.wrap(body, width=96)
        for line in wrapped:
            lines.extend(["/F1 9 Tf", "0 -13 Td", f"({pdf_escape(line)}) Tj"])
        y_gap = 21
    lines.append("ET")
    return "\n".join(lines)


def write_pdf(path: Path, content: str) -> None:
    stream = content.encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    data = bytearray(b"%PDF-1.4\n")
    offsets = []
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(data))
        data.extend(f"{index} 0 obj\n".encode("ascii"))
        data.extend(obj)
        data.extend(b"\nendobj\n")
    xref_offset = len(data)
    data.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    data.extend(b"0000000000 65535 f \n")
    for offset in offsets:
        data.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    data.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode(
            "ascii"
        )
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


if __name__ == "__main__":
    write_pdf(OUT, build_content())
    print(OUT)
