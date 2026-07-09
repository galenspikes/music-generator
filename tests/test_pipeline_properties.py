"""Property-based fuzzing of the full generation pipeline (nice-to-have from
the 2026-07 code review).

Where test_tokens_properties.py fuzzes the parsers in isolation, this drives
``generator_api.generate`` end-to-end with generated *specs* and pins the
API's whole-pipeline contract:

- a spec either yields a structurally valid MIDI file (mido can parse it,
  it has notes, duration/track metadata are coherent) or fails as a
  ``GenerationError`` — never any other exception;
- the failure payload is always actionable (message + classification).

Kept to a modest number of examples: each success renders real MIDI
(~tens of ms), so this is a smoke-fuzz, not an exhaustive search.
"""
import io

import mido
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

import generator_api as api
import mtheory

# Building blocks that are individually valid — the interesting bugs are in
# their combinations (voicing × percussion × styles × durations).
ROOTS = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B",
         "Am", "Em", "Gm"]
# Real recipe names from the catalog, spread across it for variety.
RECIPES = sorted(mtheory.load_chord_recipes().keys())[::9] or ["maj7"]

chord_tokens = st.one_of(
    st.sampled_from(ROOTS),
    st.builds(lambda r, q: f"{r.rstrip('m')}::{q}",
              st.sampled_from(ROOTS), st.sampled_from(RECIPES)),
)

keys_strategy = st.lists(chord_tokens, min_size=1, max_size=4).map(", ".join)

perc_tokens = st.lists(
    st.sampled_from(["qb", "eg", "qc", "er", "sh", "ek", "qbc", "ei"]),
    min_size=1, max_size=6).map(", ".join)

valid_specs = st.fixed_dictionaries(
    {
        "keys": keys_strategy,
        "seconds": st.sampled_from([2, 4]),
        "seed": st.integers(min_value=0, max_value=2**31),
    },
    optional={
        "bpm": st.sampled_from([60, 120, 240]),
        "voicing": st.sampled_from(["satb", "dense"]),
        "satb_style": st.sampled_from(["block", "static", "counterpoint",
                                       "arpeggio"]),
        "perc_main": perc_tokens,
        "perc_fill_rate": st.sampled_from([0.0, 0.5, 1.0]),
        "swing": st.sampled_from([0.0, 0.3]),
        "chord_len": st.sampled_from(["q", "e", "h"]),
        "split_stems": st.booleans(),
        "bass_style": st.sampled_from(["follow", "root", "walking", "none"]),
    },
)

# Specs with junk mixed in: wrong types, garbage tokens, unknown keys.
junk_specs = st.dictionaries(
    keys=st.sampled_from(["keys", "perc_main", "bpm", "seconds", "voicing",
                          "seed", "not_a_flag", "chord_len"]),
    values=st.one_of(
        st.text(max_size=12),
        st.integers(min_value=-10, max_value=10**6),
        st.sampled_from(["ZZ, C", "q!, qb", "x", "", None, [1, 2], -1.5]),
    ),
    max_size=5,
)


def _assert_valid_result(spec, res):
    assert isinstance(res, api.GenerationResult)
    mid = mido.MidiFile(file=io.BytesIO(res.midi))  # parses as real MIDI
    assert res.duration_seconds > 0
    assert res.mode
    note_ons = sum(1 for t in mid.tracks for m in t
                   if m.type == "note_on" and m.velocity > 0)
    assert note_ons > 0, f"silent output for {spec}"
    assert sum(t.notes for t in res.tracks) == note_ons


class TestFullPipelineProperties:
    @settings(max_examples=25, deadline=None,
              suppress_health_check=[HealthCheck.too_slow])
    @given(spec=valid_specs)
    def test_valid_specs_render_valid_midi(self, spec):
        _assert_valid_result(spec, api.generate(spec))

    @settings(max_examples=50, deadline=None,
              suppress_health_check=[HealthCheck.too_slow])
    @given(spec=junk_specs)
    def test_junk_specs_never_crash_uncontrolled(self, spec):
        """Any spec either renders, or fails as a structured GenerationError."""
        try:
            res = api.generate(spec)
        except api.GenerationError as exc:
            assert str(exc)
            d = exc.as_dict()
            assert d["error_type"] and d["code"]
        else:
            _assert_valid_result(spec, res)
