"""Tests for the fugue exposition generator."""

import melody as mel
import fugue as F


SUBJECT = "q1 q3 q5 q1"   # 4 beats


def _by_voice(events):
    out = {}
    for voice, when, dur, note in events:
        out.setdefault(voice, []).append((when, dur, note))
    for v in out:
        out[v].sort()
    return out


def test_answer_is_subject_up_a_fifth():
    S = mel.parse_melody(SUBJECT)
    A = mel.transpose_diatonic(S, 4)
    assert [n.degree for n in A] == [5, 7, 2, 5]


def test_entries_are_staggered_by_subject_length():
    events, total = F.build_fugue(SUBJECT, key_pc=0, mode="major")
    by_voice = _by_voice(events)
    # all four voices present
    assert set(by_voice) == {"soprano", "alto", "tenor", "bass"}
    # each voice's first note starts at its entry block * subject length (4 beats)
    first_start = {v: notes[0][0] for v, notes in by_voice.items()}
    # ENTRY_PLAN order: tenor(0), alto(1), soprano(2), bass(3)
    assert first_start["tenor"] == 0.0
    assert first_start["alto"] == 4.0
    assert first_start["soprano"] == 8.0
    assert first_start["bass"] == 12.0


def test_first_entry_states_the_subject_in_tonic():
    events, _ = F.build_fugue(SUBJECT, key_pc=0, mode="major")
    tenor = _by_voice(events)["tenor"]
    # first 4 notes (the subject) are scale degrees 1 3 5 1 -> pcs C E G C
    pcs = [note % 12 for _, _, note in tenor[:4]]
    assert pcs == [0, 4, 7, 0]


def test_total_length_covers_exposition_plus_cadence():
    events, total = F.build_fugue(SUBJECT, key_pc=0, mode="major")
    # 4 entries * 4 beats = 16, plus a cadence block
    assert total > 16.0
    assert max(w + d for _, w, d, _ in events) <= total + 1e-6


def test_notes_stay_in_their_voice_ranges():
    events, _ = F.build_fugue(SUBJECT, key_pc=0, mode="major")
    for voice, _w, _d, note in events:
        lo, hi = F.VOICE_RANGES[voice]
        assert lo <= note <= hi, (voice, note)


def test_custom_countersubject_respected():
    # tenor enters block 0; at block 1 it should play the countersubject.
    events, _ = F.build_fugue(SUBJECT, key_pc=0, mode="major",
                              countersubject="w1")  # one whole note, degree 1
    tenor = _by_voice(events)["tenor"]
    # block 1 starts at beat 4: a single whole-note tonic
    at_b4 = [(d, note) for w, d, note in tenor if abs(w - 4.0) < 1e-6]
    assert len(at_b4) == 1
    assert at_b4[0][0] == 4.0          # whole note
    assert at_b4[0][1] % 12 == 0       # tonic
