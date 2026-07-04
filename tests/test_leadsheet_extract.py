"""Tests for leadsheet_extract.py — the deterministic text-layer extractor
(Stage 1, option A from docs/design-notes/leadsheet-import-plan.md).

`words_to_chart` is tested against hand-built word-position fixtures (no PDF
needed — fast, and pins the reconstruction heuristics precisely). A handful
of tests generate a real PDF (via reportlab, dev-only) and drive
`extract_pdf_chart` end to end, through `leadsheet.ir_to_song_yml`, into a
real MIDI render — proving the whole pipeline, not just the parsing.
"""

import leadsheet as ls
import leadsheet_extract as le
import pytest

reportlab = pytest.importorskip("reportlab")


def _word(text, x0, top, *, size=11.0, page=0, width_per_char=7.0):
    return {
        "text": text, "x0": x0, "x1": x0 + len(text) * width_per_char,
        "top": top, "bottom": top + size, "size": size, "page": page,
    }


def _line(words_with_x, top, **kw):
    """words_with_x: list of (text, x0)."""
    return [_word(text, x0, top, **kw) for text, x0 in words_with_x]


# --- words_to_chart: basics ------------------------------------------------------

def test_empty_words_warns_and_returns_empty_chart():
    result = le.words_to_chart([])
    assert result.chart == {}
    assert "scanned/image" in result.warnings[0]


def test_simple_chart_with_barlines_and_section_labels():
    words = []
    words += _line([("Autumn Leaves", 72)], top=57, size=18)
    words += _line([("Tempo:", 72), ("116", 108)], top=84, size=10)
    words += _line([("A", 72)], top=122, size=12)
    words += _line(
        [("Cm7", 72), ("F7", 105), ("|", 131), ("Bbmaj7", 151), ("Ebmaj7", 204)],
        top=143)
    words += _line([("B", 72)], top=182, size=12)
    words += _line([("Cm7", 72), ("|", 105), ("F7", 124)], top=203)

    result = le.words_to_chart(words)
    chart = result.chart
    assert chart["title"] == "Autumn Leaves"
    assert chart["tempo"] == 116
    assert [s["name"] for s in chart["sections"]] == ["A", "B"]
    assert chart["sections"][0]["measures"] == [["Cm7", "F7"], ["Bbmaj7", "Ebmaj7"]]
    assert chart["sections"][1]["measures"] == [["Cm7"], ["F7"]]
    assert result.warnings == []


def test_no_barlines_falls_back_to_one_measure_per_line():
    words = _line([("Verse", 72)], top=100, size=12)
    words += _line([("C7", 72), ("F7", 100), ("G7", 128)], top=120)
    result = le.words_to_chart(words)
    assert result.chart["sections"][0]["measures"] == [["C7", "F7", "G7"]]


def test_repeat_annotation_on_a_section_label():
    words = _line([("Verse", 72), ("x4", 130)], top=100, size=12)
    words += _line([("C7", 72)], top=120)
    result = le.words_to_chart(words)
    sec = result.chart["sections"][0]
    assert sec["name"] == "Verse"
    assert sec["repeat"] == 4


def test_missing_tempo_warns_and_defaults():
    words = _line([("C7", 72)], top=120)
    result = le.words_to_chart(words)
    assert result.chart["tempo"] == 120
    assert any("tempo" in w.lower() for w in result.warnings)


def test_no_recognizable_chords_warns():
    words = _line([("Hello", 72), ("World", 120)], top=120)
    result = le.words_to_chart(words)
    assert any("No chord-like text" in w for w in result.warnings)


def test_ambiguous_single_letter_prefers_section_label_over_bare_chord():
    # "A" alone on its own line is (heuristically, deliberately) a section
    # label, not a one-measure "play an A major chord" section — see the
    # module docstring's documented tie-break.
    words = _line([("A", 72)], top=100, size=12)
    words += _line([("Cmaj7", 72), ("Dm7", 110)], top=120)
    result = le.words_to_chart(words)
    assert len(result.chart["sections"]) == 1
    assert result.chart["sections"][0]["name"] == "A"
    assert result.chart["sections"][0]["measures"] == [["Cmaj7", "Dm7"]]


def test_lyric_like_short_line_is_not_mistaken_for_a_section_label():
    # A short non-chord phrase that doesn't start with a recognized section
    # word (verse/chorus/etc.) should NOT start a new section — safer to
    # under-detect than swallow real content as a bogus label.
    words = _line([("Cmaj7", 72)], top=100)
    words += _line([("the", 72), ("sky", 110)], top=118)  # lyric fragment
    words += _line([("Dm7", 72)], top=136)
    result = le.words_to_chart(words)
    assert len(result.chart["sections"]) == 1
    assert result.chart["sections"][0]["measures"] == [["Cmaj7"], ["Dm7"]]


def test_title_picks_the_largest_font_line():
    words = _line([("My Tune", 72)], top=50, size=24)
    words += _line([("small subtitle", 72)], top=80, size=9)
    words += _line([("C", 72)], top=120, size=11)
    result = le.words_to_chart(words)
    assert result.chart["title"] == "My Tune"


def test_multipage_chart_keeps_pages_separate_lines():
    words = _line([("A", 72)], top=100, size=12, page=0)
    words += _line([("C7", 72)], top=120, page=0)
    words += _line([("B", 72)], top=100, size=12, page=1)  # same `top`, page 2
    words += _line([("F7", 72)], top=120, page=1)
    result = le.words_to_chart(words)
    assert [s["name"] for s in result.chart["sections"]] == ["A", "B"]
    assert result.chart["sections"][0]["measures"] == [["C7"]]
    assert result.chart["sections"][1]["measures"] == [["F7"]]


# --- extract_pdf_chart: real PDFs, full pipeline -------------------------------

def _write_chart_pdf(path):
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, 720, "Test Tune")
    c.setFont("Helvetica", 10)
    c.drawString(72, 700, "Tempo: 130")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(72, 660, "A")
    c.setFont("Courier", 11)
    c.drawString(72, 640, "Cm7  F7  |  Bbmaj7  Ebmaj7")
    c.save()


def test_extract_pdf_chart_end_to_end(tmp_path):
    pdf_path = tmp_path / "chart.pdf"
    _write_chart_pdf(pdf_path)

    result = le.extract_pdf_chart(str(pdf_path))
    assert result.chart["title"] == "Test Tune"
    assert result.chart["tempo"] == 130
    assert result.chart["sections"][0]["name"] == "A"
    assert result.chart["sections"][0]["measures"] == [["Cm7", "F7"], ["Bbmaj7", "Ebmaj7"]]
    assert result.warnings == []


def test_extract_pdf_chart_accepts_a_file_object(tmp_path):
    # The webapp reads an uploaded file without saving it to disk first.
    pdf_path = tmp_path / "chart.pdf"
    _write_chart_pdf(pdf_path)
    with open(pdf_path, "rb") as f:
        result = le.extract_pdf_chart(f)
    assert result.chart["title"] == "Test Tune"


def test_full_pipeline_pdf_to_song_yml_to_midi(tmp_path):
    pdf_path = tmp_path / "chart.pdf"
    _write_chart_pdf(pdf_path)

    result = le.extract_pdf_chart(str(pdf_path))
    yml_text = ls.ir_to_song_yml(result.chart)
    yml_path = tmp_path / "song.yml"
    yml_path.write_text(yml_text, encoding="utf-8")

    import arrangement as arr
    spec = arr.load_spec(str(yml_path), vel_mode_chords="uniform",
                         vel_mode_drums="uniform")
    out = str(tmp_path / "song.mid")
    arr.render(spec, out)

    import mido
    mid = mido.MidiFile(out)
    notes = [m for tr in mid.tracks for m in tr
            if m.type == "note_on" and m.velocity > 0]
    assert len(notes) > 0
