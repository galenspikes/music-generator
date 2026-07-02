"""Arrangement melody wiring: a section `melody` puts a real monophonic tune on
the soprano channel and suppresses the SATB soprano (the arpeggio/block top)."""

import arrangement as arr


def _sop(events):
    notes = [(round(w, 3), round(d, 3), n)
             for (k, w, d, p) in events if k == "voice"
             for (v, n) in [p] if v == "soprano"]
    notes.sort()
    return notes


def _spec(section):
    raw = {"title": "t", "tempo": 120,
           "defaults": {"instrument": "piano", "key": "C", "mode": "major",
                        "satb": "arpeggio", "chord_length": "q"},
           "sections": [section]}
    return arr.build_spec(raw)


def test_melody_becomes_monophonic_soprano():
    spec = _spec({"name": "a", "repeat": 1, "melody": "q1 q3 q5 q3",
                  "keys": "C::maj, F::maj, G::maj, C::maj"})
    events, _ = arr.build_events(spec)
    sop = _sop(events)
    # exactly the four melody notes, as C-major degrees 1 3 5 3 = C E G E
    assert [n for _, _, n in sop] == [60, 64, 67, 64]
    # monophonic: no soprano note starts before the previous one ends
    assert all(sop[i][0] >= sop[i - 1][0] + sop[i - 1][1] - 1e-6
               for i in range(1, len(sop)))


def test_melody_replaces_arpeggio_not_augments():
    section = {"name": "a", "repeat": 1, "keys": "C::maj, F::maj, G::maj, C::maj"}
    no_mel = _sop(arr.build_events(_spec(dict(section)))[0])
    with_mel = _sop(arr.build_events(
        _spec(dict(section, melody="q1 q3 q5 q3")))[0])
    # arpeggio produces many soprano notes; the melody replaces them with 4.
    assert len(with_mel) == 4
    assert len(no_mel) != 4 or no_mel != with_mel  # sanity: they differ


def test_no_melody_leaves_soprano_untouched():
    spec = _spec({"name": "a", "repeat": 1, "keys": "C::maj, F::maj"})
    sop = _sop(arr.build_events(spec)[0])
    assert sop, "arpeggio should still produce a soprano line when no melody set"
