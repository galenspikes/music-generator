"""Tests for the independent bass-line generator (build_bass_line)."""

import music_generator as M

LO, HI = M.BASS_RANGE

# A tiny timeline: two chords, each 2 beats. notes = (sop, alto, tenor, bass).
# C major (bass C3=48) then G major (bass G2=43).
TL = [
    (0.0, 2.0, (72, 64, 55, 48)),
    (2.0, 2.0, (74, 67, 59, 43)),
]


def test_follow_returns_empty():
    assert M.build_bass_line(TL, "follow") == []
    assert M.build_bass_line([], "root") == []


def test_none_returns_empty():
    assert M.build_bass_line(TL, "none") == []


def test_none_is_a_valid_bass_style():
    assert "none" in M.BASS_STYLES


def test_bass_style_none_drops_satb_bass_entirely():
    # bass_style="none" must not just skip build_bass_line — it also has to
    # drop the SATB-generated bass note, so there's no bass at all (gap I3:
    # bass used to be mandatory even when nobody asked for it).
    events, _end = M.build_harmony_events(TL, satb_style="block",
                                          bass_style="none",
                                          split_stems=True)
    assert not any(e[0] == "voice" and e[3][0] == "bass" for e in events)
    # the other three voices are still there
    voices_present = {e[3][0] for e in events if e[0] == "voice"}
    assert voices_present == {"soprano", "alto", "tenor"}


def test_root_pulses_the_bass_note():
    line = M.build_bass_line(TL, "root", step=0.5)
    # 2 beats / 0.5 = 4 notes per chord, 8 total
    assert len(line) == 8
    # every note in the first chord is the realized bass (48)
    assert all(note == 48 for _, _, note in line[:4])
    assert all(note == 43 for _, _, note in line[4:])


def test_steps_tile_the_duration():
    line = M.build_bass_line(TL, "root", step=0.5)
    whens = [w for w, _, _ in line]
    assert whens[:4] == [0.0, 0.5, 1.0, 1.5]
    assert all(abs(d - 0.5) < 1e-9 for _, d, _ in line)


def test_octaves_alternate_root_and_octave():
    line = M.build_bass_line(TL, "octaves", step=0.5)
    first = [note for _, _, note in line[:4]]
    assert first[0] == 48 and first[2] == 48      # on-beats = root (C3)
    # off-beats leap an octave; C4=60 is out of bass range so it drops to C2=36
    assert first[1] == 36 and first[3] == 36
    assert all(LO <= n <= HI for _, _, n in line)


def test_fifths_alternate_root_and_fifth():
    line = M.build_bass_line(TL, "fifths", step=0.5)
    first = [note for _, _, note in line[:4]]
    assert first[0] == 48                          # root C
    assert first[1] % 12 == (48 + 7) % 12          # a G in the bass register
    assert LO <= first[1] <= HI


def test_walking_starts_on_root_and_approaches_next():
    line = M.build_bass_line(TL, "walking", step=0.5)
    chord1 = [note for _, _, note in line[:4]]
    assert chord1[0] == 48                          # downbeat = root
    # last step of chord 1 is a chromatic approach to next bass (43)
    assert chord1[-1] in (42, 44)


def test_all_styles_stay_in_bass_range():
    for style in ("root", "octaves", "fifths", "walking", "arp"):
        line = M.build_bass_line(TL, style, step=0.5)
        assert line, style
        assert all(LO <= n <= HI for _, _, n in line), style


# --- Thread 3 v2: bass locked to the drum pattern's kick hits --------------

def test_kick_times_locks_bass_onsets_to_kick_hits():
    kicks = [0.5, 1.5, 2.5]
    line = M.build_bass_line(TL, "root", step=0.5, kick_times=kicks)
    whens = sorted(w for w, _, _ in line)
    assert whens == kicks
    notes = {w: n for w, _, n in line}
    assert notes[0.5] == 48 and notes[1.5] == 48  # chord 1's root
    assert notes[2.5] == 43                       # chord 2's root


def test_kick_times_falls_back_to_step_for_uncovered_chords():
    # kicks only land in the first chord; the second chord has none, so it
    # falls back to the even step subdivision instead of going silent.
    line = M.build_bass_line(TL, "root", step=1.0, kick_times=[0.5])
    whens = sorted(w for w, _, _ in line)
    assert 0.5 in whens                    # locked onset in chord 1
    assert 2.0 in whens and 3.0 in whens   # step-based fallback in chord 2


def test_kick_times_empty_list_behaves_like_none():
    line_default = M.build_bass_line(TL, "root", step=0.5)
    line_empty_kicks = M.build_bass_line(TL, "root", step=0.5, kick_times=[])
    assert line_default == line_empty_kicks
