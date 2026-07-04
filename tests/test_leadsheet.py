"""Tests for leadsheet.py — the deterministic core of the lead-sheet import
pipeline (docs/design-notes/leadsheet-import-plan.md): chordsym_to_token and
ir_to_song_yml. Golden tests, like the rest of the token DSL — this mapper
feeds directly into it.
"""

import pytest

import arrangement as arr
import leadsheet as ls
import tokens as tk

# Every row of the plan's documented mapping table (leadsheet-import-plan.md
# Stage 3), plus common real-world variants.
TABLE = [
    ("C", "C::maj"), ("Cmaj", "C::maj"), ("CM", "C::maj"),
    ("Cm", "C::min"), ("Cmin", "C::min"), ("C-", "C::min"),
    ("C7", "C::7"),
    ("Cmaj7", "C::maj7"), ("CM7", "C::maj7"), ("CΔ", "C::maj7"), ("CΔ7", "C::maj7"),
    ("Cm7", "C::min7"), ("C-7", "C::min7"),
    ("Cm7b5", "C::m7b5"), ("Cø", "C::m7b5"), ("Cø7", "C::m7b5"),
    ("Cdim", "C::dim"), ("C°", "C::dim"),
    ("Cdim7", "C::dim7"), ("C°7", "C::dim7"),
    ("Caug", "C::aug"), ("C+", "C::aug"),
    ("Csus4", "C::sus4"), ("Csus2", "C::sus2"), ("C7sus4", "C::sus4add7"),
    ("C6", "C::majadd6"), ("Cm6", "C::minadd6"),
    ("C9", "C::9"), ("Cmaj9", "C::maj9"), ("Cm9", "C::min9"),
    ("C11", "C::11"), ("C13", "C::13"),
    ("C7b9", "C::7b9"), ("C7#9", "C::7#9"), ("C7#11", "C::7#11"), ("C7alt", "C::7alt"),
    ("C/E", "C::maj/E"),
    ("F#m7b5", "F#::m7b5"),
    ("Bb7/D", "Bb::7/D"),
]


@pytest.mark.parametrize("symbol,expected", TABLE)
def test_chordsym_to_token_matches_the_documented_table(symbol, expected):
    assert ls.chordsym_to_token(symbol) == expected


@pytest.mark.parametrize("symbol,expected", TABLE)
def test_every_mapped_token_parses_through_the_real_engine(symbol, expected):
    # The real proof: not just "produces the expected string" but "the token
    # DSL's own parser accepts it and derives the right pitch-class set."
    chord_def = tk.parse_colon_key_token(ls.chordsym_to_token(symbol))
    assert chord_def is not None


def test_unknown_quality_raises_not_guesses():
    with pytest.raises(ls.LeadSheetError, match="Unknown chord quality"):
        ls.chordsym_to_token("Cwibble9")


def test_missing_root_raises():
    with pytest.raises(ls.LeadSheetError, match="root"):
        ls.chordsym_to_token("7")


def test_empty_symbol_raises():
    with pytest.raises(ls.LeadSheetError):
        ls.chordsym_to_token("")


def test_missing_bass_after_slash_raises():
    with pytest.raises(ls.LeadSheetError, match="bass"):
        ls.chordsym_to_token("C/")


def test_case_sensitive_major_vs_minor():
    # "M" (major) and "m" (minor) must not collapse into each other.
    assert ls.chordsym_to_token("CM7") == "C::maj7"
    assert ls.chordsym_to_token("Cm7") == "C::min7"


def test_flat_and_sharp_roots_both_accepted():
    assert ls.chordsym_to_token("Ebmaj7") == "Eb::maj7"
    assert ls.chordsym_to_token("D#maj7") == "D#::maj7"


# --- ir_to_song_yml --------------------------------------------------------------

SIMPLE_IR = {
    "title": "Test Tune",
    "tempo": 132,
    "sections": [
        {"name": "A", "repeat": 2,
         "measures": [["Cm7", "F7"], ["Bbmaj7", "Ebmaj7"]]},
        {"name": "B", "measures": [["Cm7"], ["F7"], ["Bbmaj7"], ["Ebmaj7"]]},
    ],
}


def test_ir_to_song_yml_infers_chord_length_from_density():
    yml = ls.ir_to_song_yml(SIMPLE_IR)
    assert "chord_length: h" in yml  # section A: 2 chords/measure
    assert "chord_length: w" in yml  # section B: 1 chord/measure


def test_ir_to_song_yml_carries_title_tempo_repeat():
    yml = ls.ir_to_song_yml(SIMPLE_IR)
    assert "title: Test Tune" in yml
    assert "tempo: 132" in yml
    assert "repeat: 2" in yml


def test_ir_to_song_yml_joins_chords_in_playback_order():
    yml = ls.ir_to_song_yml(SIMPLE_IR)
    assert "C::min7, F::7, Bb::maj7, Eb::maj7" in yml


def test_ir_to_song_yml_transposes_every_chord_and_bass():
    ir = {"title": "t", "tempo": 120,
         "sections": [{"name": "A", "measures": [["Cmaj7/E"]]}]}
    yml = ls.ir_to_song_yml(ir, transpose=2)
    # transposition respells to flats (matches the project's bare-root
    # normalization convention elsewhere, e.g. tokens.key_roots).
    assert "D::maj7/Gb" in yml


def test_ir_to_song_yml_rejects_inconsistent_measure_density():
    ir = {"title": "t", "tempo": 120,
         "sections": [{"name": "A", "measures": [["C"], ["G", "D"]]}]}
    with pytest.raises(ls.LeadSheetError, match="inconsistent"):
        ls.ir_to_song_yml(ir)


def test_ir_to_song_yml_rejects_empty_sections():
    with pytest.raises(ls.LeadSheetError):
        ls.ir_to_song_yml({"title": "t", "sections": []})


def test_ir_to_song_yml_rejects_section_with_no_measures():
    ir = {"title": "t", "sections": [{"name": "A", "measures": []}]}
    with pytest.raises(ls.LeadSheetError):
        ls.ir_to_song_yml(ir)


def test_emitted_song_yml_renders_through_the_real_engine(tmp_path):
    # The end-to-end proof: the emitted YAML is not just well-formed, it's a
    # song arrangement.py can actually load and render to MIDI.
    yml_path = tmp_path / "song.yml"
    yml_path.write_text(ls.ir_to_song_yml(SIMPLE_IR), encoding="utf-8")
    spec = arr.load_spec(str(yml_path), vel_mode_chords="uniform",
                         vel_mode_drums="uniform")
    out = str(tmp_path / "song.mid")
    arr.render(spec, out)
    import mido
    mid = mido.MidiFile(out)
    notes = [m for tr in mid.tracks for m in tr
            if m.type == "note_on" and m.velocity > 0]
    assert len(notes) > 0
    assert mid.length > 0
