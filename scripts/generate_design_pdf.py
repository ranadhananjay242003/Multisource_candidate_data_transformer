from __future__ import annotations

import textwrap
from pathlib import Path


OUT = Path("docs/YourFullName_YourEmail_Eightfold.pdf")
PAGE_W = 612
PAGE_H = 792


def pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def rgb(hex_color: str) -> str:
    hex_color = hex_color.lstrip("#")
    parts = [int(hex_color[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    return f"{parts[0]:.3f} {parts[1]:.3f} {parts[2]:.3f}"


def rect(x: int, y: int, w: int, h: int, color: str) -> str:
    return f"{rgb(color)} rg\n{x} {y} {w} {h} re f"


def stroke_rect(x: int, y: int, w: int, h: int, color: str, width: float = 0.8) -> str:
    return f"{width} w\n{rgb(color)} RG\n{x} {y} {w} {h} re S"


def text(x: int, y: int, value: str, size: int = 9, font: str = "F1", color: str = "#111827") -> str:
    return f"BT\n{rgb(color)} rg\n/{font} {size} Tf\n{x} {y} Td\n({pdf_escape(value)}) Tj\nET"


def wrapped_text(
    x: int,
    y: int,
    value: str,
    width_chars: int,
    size: int = 8,
    leading: int = 10,
    font: str = "F1",
    color: str = "#111827",
) -> tuple[list[str], int]:
    commands = []
    cursor = y
    for line in textwrap.wrap(value, width=width_chars):
        commands.append(text(x, cursor, line, size=size, font=font, color=color))
        cursor -= leading
    return commands, cursor


def section(
    x: int,
    y: int,
    w: int,
    h: int,
    title: str,
    body: str,
    accent: str = "#2563eb",
    body_size: int = 7,
) -> list[str]:
    commands = [
        rect(x, y - h, w, h, "#f8fafc"),
        stroke_rect(x, y - h, w, h, "#cbd5e1"),
        rect(x, y - 18, w, 18, accent),
        text(x + 9, y - 13, title.upper(), size=8, font="F2", color="#ffffff"),
    ]
    body_commands, _ = wrapped_text(x + 9, y - 31, body, width_chars=max(35, int(w / 4.5)), size=body_size)
    commands.extend(body_commands)
    return commands


def bullet_list(x: int, y: int, items: list[str], width_chars: int, size: int = 7) -> list[str]:
    commands = []
    cursor = y
    for item in items:
        commands.append(text(x, cursor, "-", size=size, font="F2", color="#2563eb"))
        lines = textwrap.wrap(item, width=width_chars)
        for line in lines:
            commands.append(text(x + 10, cursor, line, size=size, color="#111827"))
            cursor -= 9
        cursor -= 2
    return commands


def build_content() -> str:
    commands: list[str] = []

    # Header
    commands.append(rect(0, 704, PAGE_W, 88, "#174ea6"))
    commands.append(rect(0, 696, PAGE_W, 8, "#38bdf8"))
    commands.append(text(42, 755, "Multi-Source Candidate Data Transformer", size=18, font="F2", color="#ffffff"))
    commands.append(text(42, 735, "One-page technical design for the Eightfold engineering intern assignment", size=9, color="#dbeafe"))
    commands.append(text(470, 755, "Deterministic", size=8, font="F2", color="#ffffff"))
    commands.append(text(470, 740, "Explainable", size=8, font="F2", color="#ffffff"))
    commands.append(text(470, 725, "Configurable", size=8, font="F2", color="#ffffff"))

    # Goal
    commands.append(text(42, 674, "Goal", size=11, font="F2", color="#174ea6"))
    goal = (
        "Build a pipeline that turns messy candidate data from structured and unstructured sources into one "
        "trustworthy canonical profile per candidate, then reshapes that profile through runtime config without "
        "changing transformation code."
    )
    goal_lines, _ = wrapped_text(42, 660, goal, 112, size=8, leading=10)
    commands.extend(goal_lines)

    # Pipeline strip
    commands.append(text(42, 626, "Pipeline", size=11, font="F2", color="#174ea6"))
    steps = ["Detect", "Extract", "Normalize", "Match + Merge", "Score", "Project", "Validate"]
    x = 42
    for i, step in enumerate(steps):
        commands.append(rect(x, 594, 67, 24, "#e0f2fe" if i % 2 == 0 else "#dbeafe"))
        commands.append(stroke_rect(x, 594, 67, 24, "#93c5fd"))
        commands.append(text(x + 8, 602, step, size=7, font="F2", color="#0f172a"))
        if i < len(steps) - 1:
            commands.append(text(x + 70, 602, ">", size=9, font="F2", color="#2563eb"))
        x += 75

    # Main sections
    commands.extend(
        section(
            42,
            560,
            250,
            96,
            "Canonical Schema",
            "candidate_id, full_name, emails, phones, location, links, headline, years_experience, "
            "skills with confidence and sources, experience, education, provenance, and overall_confidence. "
            "This internal record stays stable even when customer output shape changes.",
        )
    )
    commands.extend(
        section(
            320,
            560,
            250,
            96,
            "Normalization Choices",
            "Emails are lowercased; phones are converted to E.164; countries become ISO-3166 alpha-2; "
            "dates become YYYY-MM; skills are canonicalized through a deterministic alias map such as "
            "JS to javascript and Postgres to postgresql.",
            "#0891b2",
        )
    )
    commands.extend(
        section(
            42,
            438,
            250,
            110,
            "Merge + Confidence Policy",
            "Candidate identity uses email first, phone second, normalized name last. Scalar conflicts are "
            "resolved by repeated evidence, then average source confidence, then source confidence. CSV starts "
            "at 0.90; parsed notes start at 0.68. Cross-source agreement increases overall confidence.",
            "#1d4ed8",
        )
    )
    commands.extend(
        section(
            320,
            438,
            250,
            110,
            "Runtime Output Config",
            "Projection runs only after the canonical record is built and validated. Config fields can choose "
            "a subset, rename paths, read from canonical paths like emails[0] and skills[].name, apply per-field "
            "normalizers, toggle provenance/confidence, and set missing handling to null, omit, or error.",
            "#0f766e",
        )
    )

    # Edge cases and scoped-out row
    commands.append(rect(42, 174, 528, 126, "#ffffff"))
    commands.append(stroke_rect(42, 174, 528, 126, "#cbd5e1"))
    commands.append(text(58, 280, "Edge Cases Handled", size=10, font="F2", color="#174ea6"))
    commands.extend(
        bullet_list(
            58,
            263,
            [
                "Missing source fields become null or are omitted based on config; the run does not crash.",
                "Malformed phones are dropped instead of guessed, preserving trust over false precision.",
                "Duplicate CSV and notes records merge into one candidate with field-level provenance.",
                "Skill aliases like Node.js, JS, and Postgres map to canonical names.",
                "Required custom-output fields can fail fast when on_missing is set to error.",
            ],
            width_chars=68,
        )
    )
    commands.append(text(345, 280, "Deliberately Scoped Out", size=10, font="F2", color="#174ea6"))
    scoped = (
        "ATS JSON, live GitHub or LinkedIn enrichment, and PDF/DOCX resume parsing are future extractors. "
        "They would emit the same evidence objects, so merge, confidence, projection, and validation stay unchanged."
    )
    scoped_lines, _ = wrapped_text(345, 263, scoped, 39, size=7, leading=9)
    commands.extend(scoped_lines)

    # Footer
    commands.append(rect(0, 0, PAGE_W, 38, "#f1f5f9"))
    commands.append(text(42, 16, "Implementation: Python CLI | Sources: recruiter CSV + recruiter notes | Output: default JSON + configurable projection", size=7, color="#334155"))

    return "\n".join(commands)


def write_pdf(path: Path, content: str) -> None:
    stream = content.encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
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
