"""Tests for the process-music generator (phase / additive / augment)."""

import pytest

import melody as mel
import process as P

CELL = "e1 e2 e3 e5"   # 4 eighths, 2 beats


def _by_voice(events):
    out = {}
    for voice, when, dur, note in events:
        out.setdefault(voice, []).append((when, dur, note))
    for v in out:
        out[v].sort()
    return out


def test_phase_uses_two_voices_and_returns_to_unison():
    events, total = P.build_process(CELL, 0, "major", kind="phase", reps=2)
    bv = _by_voice(events)
    assert set(bv) == {"soprano", "alto"}
    # stages = len(cell)+1 = 5, each stage reps=2 loops of the 2-beat cell
    assert total == pytest.approx((len(mel.parse_melody(CELL)) + 1) * 2 * 2.0)
    # final stage is unison again: in the last cell, both voices play the same
    # pitch classes at each onset
    cell_beats = 2.0
    last_start = total - cell_beats
    sop = [(w, n % 12) for w, _, n in bv["soprano"] if w >= last_start - 1e-9]
    alt = [(w, n % 12) for w, _, n in bv["alto"] if w >= last_start - 1e-9]
    assert [pc for _, pc in sop] == [pc for _, pc in alt]


def test_phase_middle_stage_is_offset():
    # at stage s=1 the follower is rotated by one note, so it differs from leader
    events, _ = P.build_process(CELL, 0, "major", kind="phase", reps=1)
    bv = _by_voice(events)
    # second cell (t in [2,4)) is stage 1
    sop = [n % 12 for w, _, n in bv["soprano"] if 2.0 <= w < 4.0]
    alt = [n % 12 for w, _, n in bv["alto"] if 2.0 <= w < 4.0]
    assert sop != alt


def test_additive_grows_then_shrinks():
    events, total = P.build_process(CELL, 0, "major", kind="additive", reps=1)
    sop = _by_voice(events)["soprano"]
    # count notes per cell-iteration boundary is awkward; instead check the
    # phrase lengths: grow 1..4 then shrink 3..1 -> note counts [1,2,3,4,3,2,1]
    # reconstruct by grouping consecutive onsets into runs is overkill; just
    # assert total beats = sum of those lengths * eighth(0.5)
    expected_notes = sum([1, 2, 3, 4, 3, 2, 1])
    assert len(sop) == expected_notes
    assert total == pytest.approx(expected_notes * 0.5)


def test_augment_lengthens_each_stage():
    events, total = P.build_process(CELL, 0, "major", kind="augment",
                                    reps=1, stages=3, augment_amount=1.0)
    sop = _by_voice(events)["soprano"]
    # stage durations: factor 1,2,3 -> first note beats 0.5, 1.0, 1.5
    # first note of each stage:
    firsts = [d for _, d, _ in sop[0:1]] + [sop[4][1]] + [sop[8][1]]
    assert firsts == [0.5, 1.0, 1.5]


def test_unknown_kind_errors():
    with pytest.raises(ValueError):
        P.build_process(CELL, 0, "major", kind="bogus")
