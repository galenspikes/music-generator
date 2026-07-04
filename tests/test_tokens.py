"""Golden tests for the token DSL: chord colon-tokens, percussion tokens,
repetition / chain operators, and ostinato key expansion.

These pin down the *current* behavior of the parsers so the DSL (the core
asset of this project) can be refactored without silent regressions.
"""

import pytest

import music_generator as M

DM = M.get_drum_map()
KICK = DM["b"]["note"] if isinstance(DM["b"], dict) else DM["b"]


def note_of(letter):
    v = DM[letter]
    return v["note"] if isinstance(v, dict) else v


# --------------------------------------------------------------------------
# parse_key_name
# --------------------------------------------------------------------------

def test_key_name_natural():
    assert M.parse_key_name("C") == (0, False)
    assert M.parse_key_name("G") == (7, False)


def test_key_name_minor_flag():
    assert M.parse_key_name("Gm") == (7, True)


def test_key_name_sharp_is_recognized():
    # C# -> pitch class 1 (enharmonic handling lives downstream)
    assert M.parse_key_name("C#") == (1, False)


# --------------------------------------------------------------------------
# parse_colon_key_token  (root[:inv][:recipe][/bass])
# --------------------------------------------------------------------------

def test_colon_returns_none_without_colon():
    assert M.parse_colon_key_token("C") is None
    assert M.parse_colon_key_token("Am") is None
    assert M.parse_colon_key_token("") is None


def test_colon_basic_major():
    c = M.parse_colon_key_token("C::maj")
    assert c.root_pc == 0
    assert set(c.pcs) == {0, 4, 7}
    assert c.bass_pc is None
    assert c.label == "C::maj"


def test_colon_minor_default_from_m_suffix():
    c = M.parse_colon_key_token("Am::")
    assert c.root_pc == 9
    assert set(c.pcs) == {9, 0, 4}  # A C E


def test_colon_explicit_recipe():
    c = M.parse_colon_key_token("C::maj7")
    assert set(c.pcs) == {0, 4, 7, 11}


def test_colon_sharp_root():
    c = M.parse_colon_key_token("C#::maj")
    assert c.root_pc == 1
    assert set(c.pcs) == {1, 5, 8}


def test_colon_inversion_sets_bass():
    # root:inv:recipe ; 1st inversion of C major -> bass is the 3rd (E=4)
    c = M.parse_colon_key_token("C:1:maj")
    assert c.bass_pc == 4


# --- slash / pedal bass -------------------------------------------------

def test_slash_bass_chord_tone():
    c = M.parse_colon_key_token("C::maj/G")
    assert c.bass_pc == 7


def test_slash_bass_non_chord_tone_pedal():
    # G major over C: C is NOT in the chord, must still be allowed (pedal)
    c = M.parse_colon_key_token("G::maj/C")
    assert set(c.pcs) == {7, 11, 2}
    assert c.bass_pc == 0


def test_slash_bass_overrides_inversion():
    c = M.parse_colon_key_token("C:1:maj/G")
    assert c.bass_pc == 7  # slash wins over the inversion's E


def test_slash_bass_label_preserved():
    assert M.parse_colon_key_token("G::maj/C").label == "G::maj/C"


@pytest.mark.parametrize("bad", [
    ":::",          # too many colons
    "::",           # missing root
    "C::bogus",     # unknown recipe
    "C:x:maj",      # bad inversion
    "C::maj/",      # missing bass after slash
    "C::maj/H",     # bad bass note
])
def test_colon_errors(bad):
    with pytest.raises(ValueError):
        M.parse_colon_key_token(bad)


# --------------------------------------------------------------------------
# parse_single_token  (percussion)
# --------------------------------------------------------------------------

def test_perc_durations():
    assert M.parse_single_token("wb")[0] == 4.0
    assert M.parse_single_token("hb")[0] == 2.0
    assert M.parse_single_token("qb")[0] == 1.0
    assert M.parse_single_token("eb")[0] == 0.5
    assert M.parse_single_token("sb")[0] == 0.25
    assert M.parse_single_token("tb")[0] == 0.125


def test_perc_rest():
    assert M.parse_single_token("er") == (0.5, [])


def test_perc_multiple_hits():
    beats, hits = M.parse_single_token("qbc")
    assert beats == 1.0
    assert [h.note for h in hits] == [note_of("b"), note_of("c")]


def test_perc_velocity_modifier():
    _, hits = M.parse_single_token("qb[vel+10]")
    assert hits[0].vel_offset == 10
    _, hits = M.parse_single_token("qb[vel-5]")
    assert hits[0].vel_offset == -5


def test_perc_probability_modifier_clamped():
    _, hits = M.parse_single_token("qb[prob0.5]")
    assert hits[0].probability == 0.5
    _, hits = M.parse_single_token("qb[prob2]")
    assert hits[0].probability == 1.0  # clamped to [0,1]


def test_perc_flam_modifier():
    _, hits = M.parse_single_token("qb[flam0.1]")
    assert hits[0].flam == pytest.approx(0.1)


@pytest.mark.parametrize("bad", [
    "",          # empty
    "q",         # duration with no instruments
    "zz",        # bad duration letter
    "q9",        # unknown drum letter
    "qb[bad]",   # unknown modifier
    "qb[vel",    # unclosed modifier block
])
def test_perc_errors(bad):
    with pytest.raises(ValueError):
        M.parse_single_token(bad, DM)


def test_parse_pattern_splits_on_commas():
    pat = M.parse_pattern("qb,ec,er")
    assert len(pat) == 3
    assert pat[0][0] == 1.0 and pat[1][0] == 0.5 and pat[2] == (0.5, [])


# --------------------------------------------------------------------------
# repetition / chain operators
# --------------------------------------------------------------------------

def test_repetition_token():
    assert M.parse_repetition_token("C") == ("C", 1)
    assert M.parse_repetition_token("C::maj*4") == ("C::maj", 4)


@pytest.mark.parametrize("bad", ["*4", "C*", "C*x", "C*0"])
def test_repetition_errors(bad):
    with pytest.raises(ValueError):
        M.parse_repetition_token(bad)


def test_chain_repetition():
    toks, count = M.parse_chain_repetition("[A:1:maj*2,B::min]*3")
    assert toks == ["A:1:maj*2", "B::min"]
    assert count == 3


@pytest.mark.parametrize("bad", ["A*3", "[A,B]", "[]*2"])
def test_chain_errors(bad):
    with pytest.raises(ValueError):
        M.parse_chain_repetition(bad)


# --------------------------------------------------------------------------
# key_roots  (ostinato expansion)
# --------------------------------------------------------------------------

def test_key_roots_repetition_expands():
    assert M.key_roots("ostinato", "C,Am*3,G") == ["C", "A", "A", "A", "G"]


def test_key_roots_chain_expands():
    assert M.key_roots("ostinato", "[C,G]*2,Am") == ["C", "G", "C", "G", "A"]


def test_key_roots_preserves_colon_tokens():
    assert M.key_roots("ostinato", "C::maj7,Bbm:1:min7") == [
        "C::maj7", "Bbm:1:min7"]


def test_key_roots_normalizes_enharmonic_and_strips_minor():
    # bare roots: sharps -> flats, minor marker stripped (quality comes from --chords)
    assert M.key_roots("ostinato", "C#,Gm,F#m") == ["Db", "G", "Gb"]


def test_key_roots_rejects_bad_key():
    with pytest.raises(ValueError):
        M.key_roots("ostinato", "C,Zz,G")


def test_key_roots_non_ostinato_uses_circle_of_fifths():
    # mixed/complete ignore --keys and walk a circle-of-fifths default
    circle = ["C", "G", "D", "A", "E", "B", "Gb", "Db", "Ab", "Eb", "Bb", "F"]
    assert M.key_roots("mixed", "C,F,G") == circle
    assert M.key_roots("complete", None) == circle


# --------------------------------------------------------------------------
# percussion parsing (bug fixes: bracket-aware split, 32nd quantize, lib default)
# --------------------------------------------------------------------------

def test_parse_pattern_bracket_aware_split():
    # BUG FIX: parse_pattern must preserve commas inside [...] modifier blocks.
    # Pattern: "qk[vel+10,prob0.5]sh, er, qb"
    # Should parse as 3 tokens, not broken.
    pattern = M.parse_pattern("qk[vel+10,prob0.5]sh, er, qb")
    assert len(pattern) == 3
    beats1, hits1 = pattern[0]
    beats2, hits2 = pattern[1]
    beats3, hits3 = pattern[2]
    # First token: quarter note + kick + snare + hat with modifiers
    assert beats1 == 1.0
    assert len(hits1) == 3  # 3 hits
    assert beats2 == 0.5
    assert beats3 == 1.0


def test_parse_pattern_modifier_blocks_nested():
    # Multiple tokens, some with modifier blocks, some without.
    pattern = M.parse_pattern("qb, eg[prob0.3], qr, sh[vel+5,prob0.8]")
    assert len(pattern) == 4
    for beats, hits in pattern:
        assert beats > 0
        assert isinstance(hits, list)


def test_quantize_32nds_not_dropped():
    # BUG FIX: GRID_STEP = 0.125 (32nd), quantize ensures slots >= 1.
    # 32nd token 't' = 0.125 beats should NOT round to 0 slots.
    pattern = M.parse_pattern("tb, tr, tb, tr")  # 4 thirty-second kicks
    assert len(pattern) == 4
    quantized = M.quantize_to_grid(pattern)
    # Each 32nd (0.125) at 0.125 grid step = 1 slot each. Total 4 slots.
    assert len(quantized) == 4
    hits = [h for _, h in quantized]
    # First and third have the kick hit.
    assert len(hits[0]) == 1
    assert len(hits[1]) == 0
    assert len(hits[2]) == 1
    assert len(hits[3]) == 0


def test_quantize_mixed_resolutions():
    # Mixing 8th (e=0.5), 16th (s=0.25), 32nd (t=0.125).
    pattern = M.parse_pattern("eb, sb, tb")  # 8th + 16th + 32nd kick
    assert len(pattern) == 3
    quantized = M.quantize_to_grid(pattern)
    # 0.5 / 0.125 = 4 slots
    # 0.25 / 0.125 = 2 slots
    # 0.125 / 0.125 = 1 slot
    # Total = 7 slots
    assert len(quantized) == 7
    kicks = sum(1 for _, h in quantized if h)
    assert kicks == 3  # One kick hit per token


def test_perc_main_key_without_explicit_lib():
    # BUG FIX: perc_main_key should work without explicit --perc-lib.
    # We default to the bundled library in build_perc_from_args.
    args = M.build_parser().parse_args([
        "--mode", "ostinato",
        "--keys", "C::maj7",
        "--perc-main-key", "funk:4/4:med",
        "--seconds", "8",
    ])
    # Should not raise; perc_main_key should resolve from the default lib.
    perc_plan = M.build_perc_from_args(args)
    assert perc_plan.main is not None
    assert len(perc_plan.main) > 0


def _base_args(**overrides):
    argv = ["--mode", "ostinato", "--keys", "C::maj7", "--seconds", "8"]
    for flag, value in overrides.items():
        if value is True:
            argv.append(flag)
        else:
            argv += [flag, value]
    return M.build_parser().parse_args(argv)


def test_perc_main_defaults_to_the_forced_groove_when_unspecified():
    # Regression guard: today's un-neutral default is unchanged unless the
    # caller explicitly asks for silence (gap-analysis I1's fix must not
    # flip the default for existing callers).
    plan = M.build_perc_from_args(_base_args())
    assert len(plan.main) > 0


def test_perc_main_explicit_empty_string_means_silence():
    # gap-analysis I1: an explicit empty --perc-main used to be
    # indistinguishable from "not specified" and got forced to a hi-hat
    # groove. It must now mean silence.
    plan = M.build_perc_from_args(_base_args(**{"--perc-main": ""}))
    assert plan.main == []


def test_no_perc_flag_means_silence():
    plan = M.build_perc_from_args(_base_args(**{"--no-perc": True}))
    assert plan.main == []


def test_perc_interrupters_explicit_empty_is_honored():
    # gap-analysis I2: passing --perc-interrupters with zero values used to
    # be indistinguishable from not passing the flag at all, and got the
    # default fill vocabulary forced in anyway.
    plan = M.build_perc_from_args(_base_args(**{"--perc-interrupters": True}))
    assert plan.interrupters == []


def test_perc_interrupters_default_to_forced_fill_when_unspecified():
    plan = M.build_perc_from_args(_base_args())
    assert plan.interrupters is not None
    assert len(plan.interrupters) > 0
