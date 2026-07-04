# Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
# https://github.com/galenspikes/music-generator
"""Lead-sheet import: chord-symbol → DSL mapping, and IR → song.yml emission.

The reusable, deterministic core of the lead-sheet import pipeline (see
docs/design-notes/leadsheet-import-plan.md). Two independent pieces:

- `chordsym_to_token` — translates conventional lead-sheet chord symbols
  ("Cmaj7", "F#m7b5", "Bb7/D") into the project's colon-token DSL
  ("C::maj7", "F#::m7b5", "Bb::7/D"). Unknown qualities raise ValueError
  rather than guessing (the plan's "never a silent guess").
- `ir_to_song_yml` — turns a normalized chart (the small IR any extractor —
  vision-based or a future text-layer parser — produces) into a song.yml
  string for the arrangement layer.

Extraction itself (PDF -> IR) is not this module's job; it's a documented
agent workflow (a human/Claude reads the chart and fills in the IR dict),
per the plan's decision that vision-based extraction is the primary path.
"""

from __future__ import annotations

import re

import yaml

from mtheory import NOTE_TO_PC

__all__ = ["chordsym_to_token", "ir_to_song_yml", "LeadSheetError"]


class LeadSheetError(ValueError):
    """A chord symbol or chart couldn't be mapped — never silently guessed."""


# --- chord-symbol -> DSL token -------------------------------------------------

_ROOT_RE = re.compile(r"^([A-Ga-g])([#b♯♭]{0,2})")

# Case-sensitive markers where case carries meaning (M7 = major 7, m7 = minor
# 7) are listed explicitly; everything else is matched case-insensitively.
_UNICODE_AND_SHORTHAND = {
    "Δ": "maj7", "Δ7": "maj7",     # Δ, Δ7
    "ø": "m7b5", "ø7": "m7b5",     # ø, ø7
    "°": "dim", "°7": "dim7",       # °, °7
}

# Exact quality-body -> chord_recipes.py recipe name. Checked case-sensitively
# first (so "M7" vs "m7" isn't ambiguous), then case-insensitively.
_QUALITY_CASE_SENSITIVE = {
    "M": "maj", "M7": "maj7", "M9": "maj9",
    "m": "min", "m7": "min7", "m9": "min9", "m6": "minadd6",
    "m11": "min11", "m13": "min13",
}

_QUALITY_ANY_CASE = {
    "": "maj", "maj": "maj", "major": "maj",
    "min": "min", "-": "min", "minor": "min",
    "dim": "dim", "diminished": "dim",
    "dim7": "dim7",
    "aug": "aug", "+": "aug", "augmented": "aug",
    "7": "7", "dom7": "7",
    "maj7": "maj7", "ma7": "maj7", "maj7th": "maj7",
    "mmaj7": "mmaj7", "minmaj7": "mmaj7", "m(maj7)": "mmaj7", "mmaj": "mmaj7",
    "m7b5": "m7b5", "min7b5": "m7b5", "m7-5": "m7b5",
    "min7": "min7", "-7": "min7",
    "6": "majadd6", "maj6": "majadd6", "add6": "majadd6",
    "min6": "minadd6", "-6": "minadd6",
    "9": "9",
    "maj9": "maj9",
    "min9": "min9", "-9": "min9",
    "11": "11",
    "min11": "min11",
    "13": "13",
    "min13": "min13",
    "add9": "majadd9", "add11": "majadd11", "add13": "majadd13",
    "sus2": "sus2",
    "sus4": "sus4", "sus": "sus4",
    "7sus4": "sus4add7", "7sus": "sus4add7", "9sus4": "sus4add7",
    "7b5": "7b5",
    "7#5": "7#5", "7+5": "7#5",
    "7b9": "7b9",
    "7#9": "7#9",
    "7b11": "7b11",
    "7#11": "7#11",
    "7b13": "7b13",
    "7#13": "7#13",
    "7alt": "7alt", "alt": "7alt",
    "5": "5",
}


def _canonical_root(root: str) -> str:
    """Uppercase the letter, normalize accidental glyphs — pass the spelling
    through unchanged otherwise (parse_key_name accepts sharps or flats)."""
    letter, accidental = _ROOT_RE.match(root).groups()
    accidental = accidental.replace("♯", "#").replace("♭", "b")
    return letter.upper() + accidental


def _split_symbol(symbol: str) -> tuple[str, str, str | None]:
    """'Bb7/D' -> ('Bb', '7', 'D'); 'F#m7b5' -> ('F#', 'm7b5', None)."""
    s = symbol.strip()
    if not s:
        raise LeadSheetError("Empty chord symbol")
    bass = None
    if "/" in s:
        s, bass = s.rsplit("/", 1)
        bass = bass.strip()
        if not bass:
            raise LeadSheetError(f"Missing bass note after '/' in '{symbol}'")
    m = _ROOT_RE.match(s)
    if not m:
        raise LeadSheetError(f"Can't find a root note in chord symbol '{symbol}'")
    root = _canonical_root(m.group(0))
    quality = s[m.end():].strip()
    return root, quality, (_canonical_root(bass) if bass else None)


def _resolve_recipe(quality: str, symbol: str) -> str:
    if quality in _UNICODE_AND_SHORTHAND:
        quality = _UNICODE_AND_SHORTHAND[quality]
    if quality in _QUALITY_CASE_SENSITIVE:
        recipe = _QUALITY_CASE_SENSITIVE[quality]
    else:
        recipe = _QUALITY_ANY_CASE.get(quality.lower())
    if recipe is None:
        raise LeadSheetError(
            f"Unknown chord quality '{quality}' in symbol '{symbol}' — "
            "no matching recipe; add one to _QUALITY_ANY_CASE rather than guess.")
    return recipe


def chordsym_to_token(symbol: str) -> str:
    """Translate one lead-sheet chord symbol into a colon token.

    >>> chordsym_to_token("Cmaj7")
    'C::maj7'
    >>> chordsym_to_token("F#m7b5")
    'F#::m7b5'
    >>> chordsym_to_token("Bb7/D")
    'Bb::7/D'

    Raises LeadSheetError on an unrecognized quality — this never silently
    falls back to a guessed chord.
    """
    root, quality, bass = _split_symbol(symbol)
    recipe = _resolve_recipe(quality, symbol)
    token = f"{root}::{recipe}"
    if bass:
        token += f"/{bass}"
    return token


# --- transpose (capo / instrument transposition) -------------------------------

_PC_TO_FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]


def _transpose_root(root: str, semitones: int) -> str:
    letter, accidental = _ROOT_RE.match(root).groups()
    accidental = accidental.replace("♯", "#").replace("♭", "b")
    pc = NOTE_TO_PC[letter.upper() + accidental]
    return _PC_TO_FLAT[(pc + semitones) % 12]


def _transpose_symbol(symbol: str, semitones: int) -> str:
    if semitones == 0:
        return symbol
    root, quality, bass = _split_symbol(symbol)
    out = _transpose_root(root, semitones) + quality
    if bass:
        out += f"/{_transpose_root(bass, semitones)}"
    return out


# --- IR -> song.yml -------------------------------------------------------------

def _section_chord_length(measures: list[list[str]], section_name: str) -> str:
    """Infer --chord-length from a uniform chords-per-measure count (the
    documented, still-open policy from the plan: 1/measure -> whole note,
    2/measure -> half, 4/measure -> quarter). A section with inconsistent
    density per measure isn't guessed at — that's exactly the ambiguity the
    plan says to never silently resolve.
    """
    counts = {len(m) for m in measures if m}
    if len(counts) != 1:
        raise LeadSheetError(
            f"Section '{section_name}': inconsistent chords-per-measure "
            f"({sorted(counts)}) — can't infer a single --chord-length. "
            "Split into sections with uniform density, or set chord_length "
            "explicitly in the emitted song.yml.")
    per_measure = counts.pop()
    return {1: "w", 2: "h", 4: "q"}.get(per_measure, "e")


def ir_to_song_yml(ir: dict, *, transpose: int = 0) -> str:
    """Turn a normalized chart (IR, see leadsheet-import-plan.md Stage 2) into
    a song.yml string for the arrangement layer.

    `transpose` shifts every chord's root (and slash bass) by N semitones —
    for capo charts or transposing instruments (a Bb lead sheet read at
    concert pitch needs -2, etc.).
    """
    title = ir.get("title") or "untitled"
    tempo = int(ir.get("tempo") or 120)
    sections_in = ir.get("sections") or []
    if not sections_in:
        raise LeadSheetError("IR has no sections to emit")

    sections_out = []
    for sec in sections_in:
        name = sec.get("name") or f"section{len(sections_out) + 1}"
        measures = sec.get("measures") or []
        if not measures:
            raise LeadSheetError(f"Section '{name}' has no measures")
        chord_length = _section_chord_length(measures, name)

        tokens = []
        for measure in measures:
            for symbol in measure:
                shifted = _transpose_symbol(symbol, transpose)
                tokens.append(chordsym_to_token(shifted))

        entry = {
            "name": name,
            "chord_length": chord_length,
            "keys": ", ".join(tokens),
        }
        repeat = sec.get("repeat")
        if repeat and repeat != 1:
            entry["repeat"] = int(repeat)
        sections_out.append(entry)

    song = {
        "title": title,
        "tempo": tempo,
        "sections": sections_out,
    }
    return yaml.safe_dump(song, sort_keys=False, allow_unicode=True)
