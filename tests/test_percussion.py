"""Tests for the percussion timeline builders in percussion.py.

build_drum_timeline_from_main and build_drum_timeline_with_fills are thin
wrappers around build_drum_segment (collapsed from three near-duplicate
unroll loops during the code-quality pass in docs/design-notes/gap-analysis.md
Phase 0) — these tests pin their behavior directly, since previously nothing
exercised them except indirectly through build_perc_from_args/integration
tests.
"""

import music_generator as M

KICK = M.PercHit(note=36)
SNARE = M.PercHit(note=38)

MAIN = [(1.0, [KICK]), (1.0, [SNARE])]  # 2 beats, alternating kick/snare
FILL = [(1.0, [SNARE]), (1.0, [SNARE])]


def test_from_main_repeats_verbatim_and_truncates():
    tl = M.build_drum_timeline_from_main(MAIN, beats_total=3.0)
    # 1.5 repeats of the 2-beat pattern, truncated at 3.0 beats
    assert [w for w, _, _ in tl] == [0.0, 1.0, 2.0]
    assert [d for _, d, _ in tl] == [1.0, 1.0, 1.0]
    assert tl[-1][2] == [KICK]  # truncated mid-pattern, second hit dropped


def test_from_main_empty_pattern_is_silence():
    assert M.build_drum_timeline_from_main([], beats_total=4.0) == []


def test_with_fills_falls_back_to_main_when_no_interrupters():
    tl = M.build_drum_timeline_with_fills(MAIN, None, beats_total=2.0, fill_rate=0.5)
    assert [w for w, _, _ in tl] == [0.0, 1.0]
    assert [hits for _, _, hits in tl] == [[KICK], [SNARE]]


def test_with_fills_falls_back_to_main_when_fill_rate_zero():
    tl = M.build_drum_timeline_with_fills(MAIN, [FILL], beats_total=2.0, fill_rate=0.0)
    assert [hits for _, _, hits in tl] == [[KICK], [SNARE]]


def test_with_fills_can_choose_a_fill(monkeypatch):
    monkeypatch.setattr(M.random, "random", lambda: 0.0)
    monkeypatch.setattr(M.random, "choice", lambda seq: seq[0])
    tl = M.build_drum_timeline_with_fills(MAIN, [FILL], beats_total=2.0, fill_rate=1.0)
    assert [hits for _, _, hits in tl] == [[SNARE], [SNARE]]


def test_drum_segment_offsets_by_start_beats():
    seg = M.build_drum_segment(10.0, 2.0, MAIN, None, 0.0)
    assert [w for w, _, _ in seg] == [10.0, 11.0]


def test_drum_segment_zero_duration_is_empty():
    assert M.build_drum_segment(0.0, 0.0, MAIN, None, 0.0) == []
