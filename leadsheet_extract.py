# Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
# https://github.com/galenspikes/music-generator
"""Deterministic text-layer lead-sheet extraction (Stage 1, option A from
docs/design-notes/leadsheet-import-plan.md) — no LLM in the loop.

Two layers, split so the reconstruction logic is testable without a real PDF:

- `words_to_chart(words)` — pure. Takes a flat list of word dicts shaped like
  `pdfplumber`'s `page.extract_words(extra_attrs=["size", "fontname"])`
  (`text`, `x0`, `x1`, `top`, `bottom`, `size`, `fontname`, `page`) and
  reconstructs an IR-shaped chart dict (the same shape
  `leadsheet.ir_to_song_yml` consumes): clusters words into visual lines,
  classifies each line as chords/section-label/other by asking
  `leadsheet.chordsym_to_token` whether its words look like chords, splits
  chord lines into measures on `|` barlines (a near-universal lead-sheet
  convention), and falls back to "the whole line is one measure" rather than
  guessing a chords-per-measure count when no barlines are present.
- `extract_pdf_chart(path_or_file)` — the thin `pdfplumber`-dependent
  wrapper: opens the PDF, extracts words per page, calls `words_to_chart`.

Only born-digital PDFs (a real text layer) work here — a scanned/photographed
chart has no words to extract, and `extract_pdf_chart` says so via a warning
rather than silently returning nothing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from leadsheet import LeadSheetError, _split_symbol, chordsym_to_token

__all__ = ["words_to_chart", "extract_pdf_chart", "ExtractionResult"]

# Words on the same visual line differ in `top` by less than this (points).
_LINE_TOLERANCE = 3.0

_TEMPO_RE = re.compile(r"(?:tempo|bpm)\D{0,3}(\d{2,3})", re.I)
_REPEAT_RE = re.compile(r"[x×]\s*(\d+)", re.I)

# A section label is short (<=3 words), never itself a recognized chord, and
# isn't blank. Matches "A", "B", "Intro", "Verse 1", "Chorus", etc.
_MAX_LABEL_WORDS = 3


@dataclass
class ExtractionResult:
    chart: dict
    warnings: list[str] = field(default_factory=list)


def _looks_like_chord(word: str) -> bool:
    if word in ("|", "‖", "||"):
        return False
    try:
        chordsym_to_token(word)
        return True
    except LeadSheetError:
        return False


def _cluster_lines(words: list[dict]) -> list[list[dict]]:
    """Group words into visual lines by `top`, then order left-to-right."""
    ordered = sorted(words, key=lambda w: (w.get("page", 0), w["top"], w["x0"]))
    lines: list[list[dict]] = []
    for w in ordered:
        if lines:
            last = lines[-1]
            same_page = last[-1].get("page", 0) == w.get("page", 0)
            same_row = abs(last[-1]["top"] - w["top"]) <= _LINE_TOLERANCE
            if same_page and same_row:
                last.append(w)
                continue
        lines.append([w])
    for line in lines:
        line.sort(key=lambda w: w["x0"])
    return lines


def _line_text(line: list[dict]) -> str:
    return " ".join(w["text"] for w in line)


def _is_chord_line(line: list[dict]) -> bool:
    """Every non-barline word on the line has to look like a chord — one
    lyric or label word among real chords means it isn't one."""
    chord_words = [w for w in line if w["text"] not in ("|", "‖", "||")]
    if not chord_words:
        return False
    chordish = sum(1 for w in chord_words if _looks_like_chord(w["text"]))
    return chordish > 0 and chordish == len(chord_words)


def _split_measures(line: list[dict]) -> list[list[str]]:
    """Split a chord line's words into measures on '|' barlines. No barlines
    at all -> the whole line is one measure (never guess a chords-per-measure
    count that isn't actually marked on the chart)."""
    measures: list[list[str]] = [[]]
    saw_barline = False
    for w in line:
        if w["text"] in ("|", "‖", "||"):
            saw_barline = True
            if measures[-1]:
                measures.append([])
            continue
        measures[-1].append(w["text"])
    measures = [m for m in measures if m]
    if not saw_barline:
        return [[w["text"] for w in line]]
    return measures


# Common section names, and the short-code pattern ("A", "B", "A1", "Verse2").
# A single-token line matching either of these counts as a section label even
# when the token *also* happens to parse as a bare major chord ("A" is both
# a valid chord and, far more likely on a real chart, the label for part A) —
# a deliberate, documented tie-break, not a silent guess.
_COMMON_SECTION_WORDS = {
    "intro", "verse", "chorus", "bridge", "outro", "coda", "interlude",
    "head", "solo", "tag", "vamp", "prechorus", "pre-chorus",
}
_SHORT_LABEL_RE = re.compile(r"^[A-Za-z]{1,2}\d{0,2}'?$")


def _is_bare_root_chord(token: str) -> bool:
    """True only for a root with no quality/extension at all ("A", "Bb",
    "F#") — the genuinely ambiguous case (also a valid major-triad symbol).
    "Dm7", "Cm6", "G7" etc. have a real quality and are never ambiguous."""
    try:
        _, quality, _ = _split_symbol(token)
        return quality == ""
    except LeadSheetError:
        return False


def _is_section_label(line: list[dict]) -> bool:
    if not line or len(line) > _MAX_LABEL_WORDS:
        return False
    text = _line_text(line).strip()
    if not text:
        return False
    if len(line) == 1:
        token = _REPEAT_RE.sub("", line[0]["text"]).strip()
        if token.lower() in _COMMON_SECTION_WORDS:
            return True
        if _SHORT_LABEL_RE.match(token):
            # A short, label-shaped token still yields to an unambiguous
            # chord reading (Dm7, Cm6) — only a bare root is truly ambiguous.
            return _is_bare_root_chord(token) or not _looks_like_chord(token)
        return False
    # Multi-word: only a label if it *starts* with a recognized section word
    # ("Verse 1", "Pre Chorus 2"). A short non-chord phrase that doesn't is
    # more likely a lyric fragment than a label — safer to under-detect a
    # section boundary (recoverable in review) than swallow real content.
    first_token = _REPEAT_RE.sub("", line[0]["text"]).strip().lower()
    return first_token in _COMMON_SECTION_WORDS


def _find_title(lines: list[list[dict]]) -> str | None:
    """The title candidate is the largest-font line among the first few lines
    of page 1 — restricted to *near the top* (titles don't appear mid-chart)
    and excluding anything that's itself a section label or a chord line
    (both are also often bold/larger, so "biggest font anywhere" would as
    easily pick up a later section header). No plausible candidate -> no
    title (the caller defaults to "untitled"), rather than force-picking
    something that's already meaningful content."""
    page0 = [line for line in lines if line[0].get("page", 0) == 0]
    candidates = [
        line for line in page0[:5]
        if not _is_section_label(line) and not _is_chord_line(line)
    ]
    if not candidates:
        return None
    sized = [line for line in candidates if all("size" in w for w in line)]
    if not sized:
        return _line_text(candidates[0]).strip()
    best = max(sized, key=lambda line: max(w["size"] for w in line))
    return _line_text(best).strip()


def _find_tempo(lines: list[list[dict]]) -> tuple[int | None, list | None]:
    """Returns (tempo, matched_line) so the caller can skip that line when
    walking the chart body (it's metadata, not chords or a section label)."""
    for line in lines:
        m = _TEMPO_RE.search(_line_text(line))
        if m:
            return int(m.group(1)), line
    return None, None


def words_to_chart(words: list[dict]) -> ExtractionResult:
    """Reconstruct an IR-shaped chart from a flat word list. See module
    docstring for the word-dict shape and the reconstruction heuristics."""
    warnings: list[str] = []
    if not words:
        warnings.append(
            "No text found on the page(s) — this looks like a scanned/image "
            "PDF, which this extractor can't read. Use the agent workflow "
            "(docs/how-to/import-a-lead-sheet.md) instead.")
        return ExtractionResult(chart={}, warnings=warnings)

    lines = _cluster_lines(words)
    title = _find_title(lines)
    tempo, tempo_line = _find_tempo(lines)
    if tempo is None:
        warnings.append("No tempo found on the chart — defaulted to 120 bpm.")
        tempo = 120

    title_line = lines[0] if lines and _line_text(lines[0]).strip() == title else None

    sections: list[dict] = []
    current_name: str | None = None
    current_repeat: int | None = None
    current_measures: list[list[str]] = []
    saw_any_chords = False

    def flush():
        if not current_measures:
            return
        entry = {
            "name": current_name or f"section{len(sections) + 1}",
            "measures": list(current_measures),
        }
        if current_repeat:
            entry["repeat"] = current_repeat
        sections.append(entry)

    for line in lines:
        if line is title_line or line is tempo_line:
            continue
        text = _line_text(line).strip()
        if not text:
            continue
        chord_words = [w for w in line if w["text"] not in ("|", "‖", "||")]
        if not chord_words:
            continue

        # Section-label detection wins over chord-likeness for the ambiguous
        # single-token case ("A" parses as a valid bare chord *and* is a
        # section marker) — checked first, deliberately, not as a fallback.
        if _is_section_label(line):
            flush()
            current_measures = []
            repeat_match = _REPEAT_RE.search(text)
            current_repeat = int(repeat_match.group(1)) if repeat_match else None
            current_name = _REPEAT_RE.sub("", text).strip() or None
            continue

        if _is_chord_line(line):
            saw_any_chords = True
            current_measures.extend(_split_measures(line))
            continue
        # anything else (lyrics, chord-symbol footnotes, etc.) is ignored —
        # v1 is chords/form only, per the plan.

    flush()

    if not saw_any_chords:
        warnings.append(
            "No chord-like text recognized anywhere on the chart — check "
            "that the PDF has a real text layer (not a scan), and that the "
            "chord spellings are ones chordsym_to_token understands.")

    chart = {
        "title": title or "untitled",
        "tempo": tempo,
        "sections": sections,
    }
    return ExtractionResult(chart=chart, warnings=warnings)


def extract_pdf_chart(path_or_file) -> ExtractionResult:
    """Open a PDF and extract its chart via the text layer. `path_or_file` is
    anything `pdfplumber.open` accepts (a path, or a file-like object — the
    latter lets the webapp read an uploaded file without saving it to disk)."""
    import pdfplumber

    words: list[dict] = []
    with pdfplumber.open(path_or_file) as pdf:
        for page_num, page in enumerate(pdf.pages):
            for w in page.extract_words(extra_attrs=["size", "fontname"]):
                w = dict(w)
                w["page"] = page_num
                words.append(w)
    return words_to_chart(words)
