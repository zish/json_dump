#!/usr/bin/env python3
"""Merge the `events` arrays of ggg1.json + ggg2.json into a sorted markdown
file and/or a paginated PDF.

- `end-date` is dropped up front, so it takes no part in dedup or output.
- Dedup key is the whole remaining record (start-date, summary, description).
- Sort is on the *parsed* timestamp, so the -05:00/-04:00 (EST/EDT) offsets
  compare as real instants rather than as strings.

The PDF is built straight from the parsed records, not by re-parsing the
markdown -- we already hold the structured data, so there is no reason to
round-trip it through a markup format and back.

    ./venv/bin/python build_events.py

PDF output needs reportlab (`pip install reportlab`); markdown output has no
dependencies. Missing reportlab only disables the PDF, with a warning.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

SOURCES = ("ggg1.json", "ggg2.json")
KEEP = ("start-date", "summary", "description")

# --- Outputs --------------------------------------------------------------
WRITE_MARKDOWN = True
WRITE_PDF = True
MD_OUT = Path("events.md")
PDF_OUT = Path("events.pdf")

# --- Date rendering -------------------------------------------------------
# Full form: "Tue, Jan 6, 2026 (day 6) · 6:00 pm"
SHOW_WEEKDAY = True  # the leading "Tue, "
SHOW_DAY_OF_YEAR = True  # the "(day 6)" ordinal, 1-366
# Two thirds of the entries are all-day events stamped 00:00:00, where a
# rendered "12:00 am" is noise. Flip this to True to time-stamp every entry.
SHOW_MIDNIGHT_TIME = False

# --- Description rendering (PDF only) -------------------------------------
# How a newline inside a note is drawn. The markdown output always keeps them
# verbatim; this only affects the PDF.
#   "hard"   - line break, no extra space. Matches the source exactly, but a
#              break is easy to miss when the line above it runs near-full.
#   "spaced" - line break plus a little air, so the author's structure reads
#              at a glance.
#   "flow"   - collapse newlines into spaces; one continuous wrapped block.
DESCRIPTION_BREAKS = "spaced"
BREAK_SPACING = 4  # points of air between lines in "spaced" mode

if DESCRIPTION_BREAKS not in ("hard", "spaced", "flow"):
    raise SystemExit(
        f"DESCRIPTION_BREAKS must be hard/spaced/flow, got {DESCRIPTION_BREAKS!r}"
    )

# Sans TTFs give the PDF full Unicode (the notes contain curly quotes, an em
# dash, an ellipsis and one emoji -- none of which survive reportlab's builtin
# Latin-1 Type1 fonts). Falls back to Helvetica if DejaVu is not installed.
FONT_DIRS = (
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/dejavu",
    "/usr/share/fonts/TTF",
    "/Library/Fonts",
)


def load_records():
    """Read every source, drop `end-date`, dedup, and sort chronologically."""
    records, total = [], 0
    for name in SOURCES:
        events = json.loads(Path(name).read_text(encoding="utf-8"))["events"]
        total += len(events)
        records.extend(tuple(e[k] for k in KEEP) for e in events)
    unique = sorted(
        set(records), key=lambda r: (datetime.fromisoformat(r[0]), r[1], r[2])
    )
    return unique, total


def pretty_date(stamp):
    """2026-01-06T18:00:00-05:00 -> 'Tue, Jan 6, 2026 (day 6) · 6:00 pm'.

    The offset is not rendered: every entry is local time in one zone, so the
    wall clock is what the reader wants. Day/hour are built by hand rather
    than with %-d/%-I, which are glibc extensions.
    """
    dt = datetime.fromisoformat(stamp)
    parts = []
    if SHOW_WEEKDAY:
        parts.append(f"{dt:%a},")
    parts.append(f"{dt:%b} {dt.day}, {dt.year}")
    if SHOW_DAY_OF_YEAR:
        parts.append(f"(day {dt.timetuple().tm_yday})")
    if dt.hour or dt.minute or SHOW_MIDNIGHT_TIME:
        parts.append(
            f"· {dt.hour % 12 or 12}:{dt.minute:02d} {'am' if dt.hour < 12 else 'pm'}"
        )
    return " ".join(parts)


def clean(text):
    """Strip trailing whitespace per line and blank lines off both ends."""
    return "\n".join(line.rstrip() for line in text.split("\n")).strip("\n")


# --------------------------------------------------------------------------
# Markdown
# --------------------------------------------------------------------------
def fenced(text):
    """Fence the note so markdown renders it verbatim -- no stray heading,
    list or emphasis interpretation.

    The fence is one backtick longer than the longest run inside the text
    (CommonMark rule), so a note containing ``` cannot close the block early.
    """
    longest = max((len(m.group()) for m in re.finditer(r"`+", text)), default=0)
    bar = "`" * max(3, longest + 1)
    return f"{bar}\n{text}\n{bar}"


def write_markdown(unique, total):
    chunks = [
        f"# Events\n\n{len(unique)} entries, sorted by start-date "
        f"(merged from {', '.join(SOURCES)}; {total - len(unique)} duplicates removed).\n"
    ]
    chunks += [
        f"**{pretty_date(start)}** — {summary.strip()}\n\n{fenced(clean(description))}\n"
        for start, summary, description in unique
    ]
    MD_OUT.write_text("\n---\n\n".join(chunks), encoding="utf-8")
    return MD_OUT


# --------------------------------------------------------------------------
# PDF
# --------------------------------------------------------------------------
def register_fonts():
    """Return (regular, bold) font names, preferring a Unicode TTF."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    for directory in FONT_DIRS:
        regular = Path(directory) / "DejaVuSans.ttf"
        bold = Path(directory) / "DejaVuSans-Bold.ttf"
        if regular.exists() and bold.exists():
            pdfmetrics.registerFont(TTFont("DejaVuSans", str(regular)))
            pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", str(bold)))
            pdfmetrics.registerFontFamily(
                "DejaVuSans", normal="DejaVuSans", bold="DejaVuSans-Bold"
            )
            return "DejaVuSans", "DejaVuSans-Bold"
    print(
        "  warning: DejaVu not found; falling back to Helvetica "
        "(the emoji and curly quotes may not render)",
        file=sys.stderr,
    )
    return "Helvetica", "Helvetica-Bold"


def markup(text):
    """Escape for reportlab's Paragraph mini-HTML, keeping the line breaks.

    Paragraph parses its input as markup, so a literal & or < in a note would
    otherwise raise or silently swallow text.
    """
    return escape(text).replace("\n", "<br/>")


def write_pdf(unique, total):
    from reportlab.lib.enums import TA_JUSTIFY
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        BaseDocTemplate,
        Frame,
        HRFlowable,
        PageTemplate,
        Paragraph,
        Spacer,
    )

    regular, bold = register_fonts()
    title_style = ParagraphStyle(
        "title", fontName=bold, fontSize=18, leading=22, spaceAfter=4
    )
    sub_style = ParagraphStyle(
        "sub",
        fontName=regular,
        fontSize=9,
        leading=12,
        textColor="#666666",
        spaceAfter=18,
    )
    # keepWithNext stops a date heading stranding at the foot of a page.
    head_style = ParagraphStyle(
        "head", fontName=bold, fontSize=11, leading=14, spaceAfter=5, keepWithNext=True
    )
    body_style = ParagraphStyle(
        "body", fontName=regular, fontSize=9.5, leading=13.5, alignment=TA_JUSTIFY
    )
    # "spaced" renders each source line as its own flowable, so the gap comes
    # from real paragraph spacing rather than a doubled <br/>.
    line_style = ParagraphStyle("line", parent=body_style, spaceAfter=BREAK_SPACING)

    def description(text):
        """Return the flowables for one note, per DESCRIPTION_BREAKS."""
        text = clean(text)
        if DESCRIPTION_BREAKS == "flow":
            return [Paragraph(markup(re.sub(r"\s*\n\s*", " ", text)), body_style)]
        if DESCRIPTION_BREAKS == "spaced":
            lines = [ln for ln in text.split("\n") if ln.strip()]
            return [Paragraph(markup(ln), line_style) for ln in lines]
        return [Paragraph(markup(text), body_style)]

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(regular, 8)
        canvas.setFillColor("#888888")
        canvas.drawCentredString(letter[0] / 2, 0.5 * inch, str(canvas.getPageNumber()))
        canvas.restoreState()

    doc = BaseDocTemplate(
        str(PDF_OUT),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title="Events",
        author="",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="body")
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=footer)])

    story = [
        Paragraph("Events", title_style),
        Paragraph(
            f"{len(unique)} entries, sorted by start-date &mdash; merged from "
            f"{escape(', '.join(SOURCES))}; {total - len(unique)} duplicates removed.",
            sub_style,
        ),
    ]
    for i, (start, summary, desc) in enumerate(unique):
        if i:
            story.append(
                HRFlowable(
                    width="100%",
                    thickness=0.5,
                    color="#cccccc",
                    spaceBefore=10,
                    spaceAfter=10,
                )
            )
        story.append(
            Paragraph(
                f"{escape(pretty_date(start))} &nbsp;&mdash;&nbsp; "
                f"{markup(summary.strip())}",
                head_style,
            )
        )
        story.extend(description(desc))
    story.append(Spacer(1, 2))

    doc.build(story)
    return PDF_OUT


unique, total = load_records()
written = []
if WRITE_MARKDOWN:
    written.append(write_markdown(unique, total))
if WRITE_PDF:
    try:
        written.append(write_pdf(unique, total))
    except ImportError:
        print(
            "  warning: reportlab not installed; skipping PDF (pip install reportlab)",
            file=sys.stderr,
        )

print(f"{total} events in -> {len(unique)} unique")
for path in written:
    print(f"  {path} ({path.stat().st_size:,} bytes)")
