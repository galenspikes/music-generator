"""Tests for the static/literal SATB voicing option (build_chord_timeline's
`static=` flag) — the fix for the "wobble" documented in
docs/design-notes/literal-mode-workflow-audit.md and
docs/design-notes/controllability-audit.md: repeating an unchanged chord used
to reshuffle the soprano between two chord tones on every hit.
"""

import music_generator as M

# Cmaj7: root C, pcs {C, E, G, B}
CMAJ7 = M.ChordDef(root_pc=0, pcs=(0, 4, 7, 11))


def test_default_block_voicing_wobbles_on_repeated_chord():
    # Regression guard for the bug itself: without `static`, repeating the
    # same chord re-invokes the anti-stagnation logic in pick_soprano, which
    # deliberately avoids repeating the previous soprano note.
    tl = M.build_chord_timeline([CMAJ7], beats_total=4.0, base_len_beats=1.0)
    sopranos = [notes[0] for _, _, notes in tl]
    assert len(set(sopranos)) > 1, "expected the known wobble without static=True"


def test_static_freezes_the_voicing_across_an_unchanged_chord():
    tl = M.build_chord_timeline([CMAJ7], beats_total=4.0, base_len_beats=1.0,
                                static=True)
    voicings = [notes for _, _, notes in tl]
    assert all(v == voicings[0] for v in voicings)


def test_static_still_revoices_on_a_real_chord_change():
    g7 = M.ChordDef(root_pc=7, pcs=(7, 11, 2, 5))  # G7
    tl = M.build_chord_timeline([CMAJ7, g7], beats_total=4.0, base_len_beats=1.0,
                                static=True)
    # two chords alternate over 4 beats -> voicings shouldn't all be identical
    voicings = [notes for _, _, notes in tl]
    assert len(set(voicings)) > 1


def test_satb_style_static_is_a_valid_cli_choice():
    args = M.build_parser().parse_args([
        "--mode", "ostinato", "--keys", "C::maj7", "--seconds", "4",
        "--satb-style", "static",
    ])
    assert args.satb_style == "static"
