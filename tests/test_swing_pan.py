"""Swing (off-beat timing warp) and pan-spread (per-voice CC10) engine params.

These are real generator parameters — they change the emitted MIDI, not just
the browser preview — so the tests assert on the serialized event stream.
"""

import music_generator as mg
from midiout import MidiOut, VOICE_PAN_POS


# --- swing --------------------------------------------------------------------

def _soprano_onsets(swing):
    """Beat-onset (in beats) of two soprano notes at 0.0 and the off-beat 0.5,
    read back after render_events applies the swing warp."""
    midi = MidiOut(120, None, split_stems=True, swing=swing)
    events = [("voice", 0.0, 0.5, ("soprano", 60)),
              ("voice", 0.5, 0.5, ("soprano", 62))]
    mg.render_events(midi, events)
    midi.flush_to_end(1.0, 0.0, 1.0)
    ch0 = midi.chord_channels["soprano"]
    onsets, cursor = [], 0.0
    for tr in midi.mid.tracks:
        cursor = 0
        for msg in tr:
            cursor += msg.time
            if (msg.type == "note_on" and msg.velocity > 0
                    and msg.channel == ch0):
                onsets.append(round(cursor / midi.tpb, 4))
    return sorted(onsets)


def test_swing_helper_keeps_beat_boundaries():
    # Whole-beat positions are fixed points; only the interior "and" moves.
    assert mg._swing_time(0.0, 0.4) == 0.0
    assert mg._swing_time(1.0, 0.4) == 1.0
    assert mg._swing_time(2.0, 0.4) == 2.0


def test_swing_delays_the_offbeat():
    straight = _soprano_onsets(0.0)
    swung = _soprano_onsets(0.4)
    # on-beat note is unmoved; off-beat "and" is pushed later
    assert straight[0] == 0.0 and swung[0] == 0.0
    assert swung[1] > straight[1]
    # s=0.4 places the "and" at 0.5*(1+0.4) = 0.7 of the beat
    assert abs(swung[1] - 0.7) < 1e-6


def test_swing_zero_is_identity():
    assert _soprano_onsets(0.0) == [0.0, 0.5]


def test_apply_swing_recomputes_durations():
    # start+end both warped so durations stay consistent with warped positions
    warped = mg.apply_swing([("voice", 0.5, 0.5, ("soprano", 60))], 0.4)
    _, when, dur, _ = warped[0]
    assert abs(when - 0.7) < 1e-6
    assert abs((when + dur) - 1.0) < 1e-6  # lands exactly on the next beat


# --- pan ----------------------------------------------------------------------

def _pan_ccs(pan_spread):
    m = MidiOut(120, None, split_stems=True, pan_spread=pan_spread)
    out = {}
    for tr in m.mid.tracks:
        for msg in tr:
            if msg.type == "control_change" and msg.control == 10:
                out[msg.channel] = msg.value
    return out


def test_pan_spread_zero_emits_no_pan():
    assert _pan_ccs(0.0) == {}


def test_pan_spread_places_voices_across_the_field():
    ccs = _pan_ccs(1.0)
    m = MidiOut(120, None, split_stems=True)
    sop = m.chord_channels["soprano"]
    bass = m.chord_channels["bass"]
    # soprano hard right, bass hard left, all four present
    assert set(ccs) == {0, 1, 2, 3}
    assert ccs[sop] > 64 and ccs[bass] < 64
    assert ccs[sop] == 127 and ccs[bass] == 1


def test_pan_spread_scales_with_amount():
    wide = _pan_ccs(1.0)
    narrow = _pan_ccs(0.5)
    m = MidiOut(120, None, split_stems=True)
    sop = m.chord_channels["soprano"]
    # a narrower spread keeps the same side but sits closer to centre (64)
    assert 64 < narrow[sop] < wide[sop]


def test_pan_spread_clamped_and_ignored_without_stems():
    # ensemble (single channel) has no per-voice pan to emit
    m = MidiOut(120, None, split_stems=False, pan_spread=1.0)
    pans = [msg for tr in m.mid.tracks for msg in tr
            if msg.type == "control_change" and msg.control == 10]
    assert pans == []
    # out-of-range values are clamped on the way in
    assert MidiOut(120, None, pan_spread=5.0).pan_spread == 1.0
    assert MidiOut(120, None, swing=2.0).swing == 0.75


def test_voice_pan_positions_are_symmetric():
    assert VOICE_PAN_POS["soprano"] == -VOICE_PAN_POS["bass"]
    assert VOICE_PAN_POS["alto"] == -VOICE_PAN_POS["tenor"]


# --- wiring: arrangement + API surface ---------------------------------------

def test_arrangement_spec_carries_swing_and_pan():
    import arrangement as arr
    raw = {"title": "t", "tempo": 120,
           "defaults": {"key": "C", "mode": "major", "swing": 0.3,
                        "pan_spread": 0.7},
           "sections": [{"name": "a", "repeat": 1, "keys": "C::maj"}]}
    spec = arr.build_spec(raw)
    assert spec.swing == 0.3 and spec.pan_spread == 0.7


def test_api_schema_exposes_swing_and_pan():
    import generator_api as api
    schema = {p["name"]: p for p in api.parameter_schema()}
    assert schema["swing"]["group"] == "Dynamics"
    assert schema["swing"]["control"] == "knob"
    assert schema["pan_spread"]["max"] == 1


def test_api_song_pan_reaches_midi():
    import io
    import mido
    import generator_api as api
    res = api.generate({"song": "songs/kiss.yml", "pan_spread": 0.8})
    mid = mido.MidiFile(file=io.BytesIO(res.midi))
    pan_channels = {msg.channel for tr in mid.tracks for msg in tr
                    if msg.type == "control_change" and msg.control == 10}
    assert pan_channels == {0, 1, 2, 3}
