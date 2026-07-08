"""Composition: progressions, chord families, and timelines.

Builds chord progressions from a key plan (:func:`build_progression`,
:func:`circle_of_fifths_sequence`) using the chord-family pickers (triads,
sevenths, ninths, extended, quartal, sus, add6, lydian-dominant, chromatic
mediants), then lays them onto beat timelines (:func:`build_chord_timeline`,
:func:`build_dense_timeline`) and turns those into playable harmony/bass
events (:func:`build_harmony_events`). Depends on mtheory, tokens, and voicing.
"""
import random

from mtheory import ChordDef, parse_key_name, pc
from tokens import parse_colon_key_token
from voicing import (
    build_arpeggio_events,
    build_bass_line,
    build_counterpoint_lines,
    realize_SATB,
    realize_dense,
)

__all__ = [
    "fill_chords_to_end",
    "make_triad",
    "make_seventh",
    "make_ninth",
    "make_quartal",
    "make_sus",
    "make_add6",
    "make_lyd_dom",
    "chromatic_mediant_from_key",
    "next_mode_picker",
    "compute_max_gap_beats",
    "truncate_timeline_to",
    "invert_chord",
    "make_extended_chord",
    "circle_of_fifths_sequence",
    "build_progression",
    "build_chord_timeline",
    "build_dense_timeline",
    "build_harmony_events",
]


def _invert_offsets(offs: list[int], inversion: int) -> list[int]:
    """
    Rotate semitone offsets upward by 'inversion' steps.
    We *raise* the rotated elements by +12 so order stays ascending.
    Example: [0,4,7,11], inv=1 -> [4,7,11,12]
    """
    if not offs or inversion <= 0:
        return offs[:]
    inv = inversion % len(offs)
    head = offs[:inv]
    tail = offs[inv:]
    head = [x + 12 for x in head]
    return sorted(tail + head)


def _pcs_from_offsets(pc_root: int, offs_abs: list[int]) -> list[int]:
    """Make unique pitch classes (0–11) from absolute offsets."""
    return sorted({(pc_root + o) % 12 for o in offs_abs})


def _apply_random_inversion(pc_root: int,
                            offs: list[int],
                            max_inv: int | None = None) -> list[int]:
    """
    Pick a random inversion and return pitch classes.
    max_inv can cap how deep inversions go (defaults to size-1).
    """
    if not offs:
        return []
    lim = (len(offs) - 1) if max_inv is None else min(max_inv, len(offs) - 1)
    inv = random.randint(0, max(0, lim))
    offs_inv = _invert_offsets(offs, inv)
    return _pcs_from_offsets(pc_root, offs_inv)


def fill_chords_to_end(ch_tl, beats_total):
    """If chord_tl ends early, sustain the last voiced chord to beats_total."""
    if not ch_tl:
        return ch_tl
    end = max(when + dur for (when, dur, _notes) in ch_tl)
    if end >= beats_total:
        return ch_tl
    last_when, last_dur, last_notes = ch_tl[-1]
    gap = beats_total - end
    ch_tl.append((end, gap, last_notes))
    return ch_tl


def make_triad(pc_root: int,
               quality: str | None = None,
               is_minor_key: bool = False) -> list[int]:
    if quality is None:
        quality = "min" if is_minor_key else "maj"
    offs = [0, 4, 7] if quality == "maj" else [0, 3, 7]
    return _apply_random_inversion(pc_root, offs)


def make_seventh(pc_root: int, is_minor_key: bool = False) -> list[int]:
    # Choose a quality that fits the key center more often
    if is_minor_key:
        bank = random.choice([[0, 3, 7, 10], [0, 3, 7, 11]])  # m7 or m(maj7)
    else:
        bank = random.choice([[0, 4, 7, 11], [0, 4, 7, 10]])  # maj7 or dom7
    return _apply_random_inversion(pc_root, bank)


def make_ninth(pc_root: int, is_minor_key: bool = False) -> list[int]:
    variants = ([[0, 3, 7, 10, 14], [0, 3, 7, 14], [0, 4, 7, 10, 14]]
                if is_minor_key else [[0, 4, 7, 11, 14], [0, 4, 7, 10, 14],
                                      [0, 4, 7, 14]])
    offs = random.choice(variants)
    return _apply_random_inversion(pc_root, offs)


def make_quartal(pc_root: int, is_minor_key: bool = False) -> list[int]:
    # stacked 4ths, 1–4–7–10(–13) flavor
    offs = [0, 5, 10, 15]  # extendable if you like: add 20 for a 5th tone
    return _apply_random_inversion(pc_root, offs)


def make_sus(pc_root: int, is_minor_key: bool = False) -> list[int]:
    offs = random.choice([[0, 2, 7], [0, 5, 7]])  # sus2 or sus4
    return _apply_random_inversion(pc_root, offs)


def make_add6(pc_root: int, is_minor_key: bool = False) -> list[int]:
    # classic add6 (major color); feel free to branch on is_minor_key if desired
    offs = [0, 4, 7, 9]
    return _apply_random_inversion(pc_root, offs)


def make_lyd_dom(pc_root: int, is_minor_key: bool = False) -> list[int]:
    # 1, 3, #4, b7 (can add 9/13 later)
    offs = [0, 4, 6, 10]
    return _apply_random_inversion(pc_root, offs)


# If you have other families, route them through _apply_random_inversion the same way.


def chromatic_mediant_from_key(pc_key: int,
                               is_minor_key: bool = False
                              ) -> tuple[int, list[int]]:
    """Pick a chromatic mediant (±3 or ±4 semitones) and choose maj/min by common-tone vs key triad."""
    candidates = [(pc_key + d) % 12 for d in (3, 9, 4, 8)]
    root = random.choice(candidates)
    key_triad = {
        (pc_key + o) % 12 for o in ([0, 3, 7] if is_minor_key else [0, 4, 7])
    }
    maj = {(root + o) % 12 for o in [0, 4, 7]}
    minr = {(root + o) % 12 for o in [0, 3, 7]}
    pcs = sorted(maj) if len(maj &
                             key_triad) >= len(minr &
                                               key_triad) else sorted(minr)
    return root, pcs


def next_mode_picker(modes: list[str], order: str):
    """Return a callable that yields the next chord family per step."""
    if not modes:
        modes = ["extended-chords"]
    if order == "roundrobin":
        idx = {"i": 0}

        def rr():
            m = modes[idx["i"] % len(modes)]
            idx["i"] += 1
            return m

        return rr
    # random (duplicates in modes act as weighting)
    def rnd():
        return random.choice(modes)

    return rnd


def compute_max_gap_beats(bpm: int, chord_len_beats: float) -> float:
    """
    Adaptive ceiling for consecutive harmony rests, in BEATS.
    - Faster tempos => smaller allowed silent window.
    - Never smaller than the chord slice, never huge.
    """
    # target ~0.9s of max silence, converted to beats
    beats_for_0p9s = (0.9 * bpm) / 60.0  # e.g. 120 bpm -> 1.8 beats
    base = max(chord_len_beats,
               beats_for_0p9s)  # never less than one chord slice
    return max(0.5, min(base, 2.5))  # clamp to [0.5, 2.5] beats


def truncate_timeline_to(tl, end_beats):
    out = []
    for when, dur, payload in tl:
        if when >= end_beats:
            break
        ndur = min(dur, max(0.0, end_beats - when))
        if ndur > 0.0:
            out.append((when, ndur, payload))
    return out


def invert_chord(chord_pcs: list[int], inversion: int) -> list[int]:
    """
    Rotate chord pcs up by 'inversion' steps (mod 12).
    Example: Cmaj7 [0,4,7,11], inversion=1 → [4,7,11,12]
    """
    if not chord_pcs:
        return chord_pcs
    pcs = chord_pcs[:]
    for _ in range(inversion):
        pcs[0] += 12
        pcs = pcs[1:] + [pcs[0]]
    return pcs


def make_extended_chord(pc_root: int, is_minor_key: bool = False) -> list[int]:
    """
    Pick from 9/11/13 families with key-sensitive 3rd/7th, then apply a random inversion.
    """
    pools_major = [
        [0, 4, 7, 11, 14],  # maj9
        [0, 4, 7, 10, 14],  # dom9
        [0, 4, 7, 11, 14, 17],  # maj9(11)
        [0, 4, 7, 10, 14, 21],  # 13
    ]
    pools_minor = [
        [0, 3, 7, 10, 14],  # min9
        [0, 3, 7, 14],  # m(add9)
        [0, 3, 7, 10, 14, 17],  # min9(11)
        [0, 3, 7, 10, 14, 21],  # min13
    ]
    offs = random.choice(pools_minor if is_minor_key else pools_major)
    # allow inversions up to the number of chord tones - 1
    return _apply_random_inversion(pc_root, offs)


def circle_of_fifths_sequence(keys: list[str],
                              max_chords: int | None = None) -> list[ChordDef]:
    """
    Build a progression as chord definitions cycling through the provided keys.
    """
    seq: list[ChordDef] = []
    order = keys[:] if keys else [
        "C", "G", "D", "A", "E", "B", "Gb", "Db", "Ab", "Eb", "Bb", "F"
    ]
    count = max_chords if max_chords else len(order) * 4
    i = 0
    while len(seq) < count:
        k = order[i % len(order)]
        r = pc(k)
        chord = make_extended_chord(r)
        seq.append(
            ChordDef(root_pc=r, pcs=tuple(sorted({n % 12 for n in chord}))))
        i += 1
    return seq


def build_progression(keys: list[str],
                      chord_modes: list[str],
                      order: str,
                      max_chords: int | None = None) -> list[ChordDef]:
    """Return chord definitions cycling through the provided key plan."""

    key_ring = keys[:] if keys else [
        "C", "G", "D", "A", "E", "B", "Gb", "Db", "Ab", "Eb", "Bb", "F"
    ]
    colon_tokens_present = any(
        isinstance(k, str) and ":" in k for k in key_ring)
    if max_chords is not None:
        count = max_chords
    elif colon_tokens_present:
        count = len(key_ring)
    else:
        count = len(key_ring) * 4

    pick = next_mode_picker(chord_modes, order)

    seq: list[ChordDef] = []
    i = 0
    while len(seq) < count:
        kname = key_ring[i % len(key_ring)]
        colon_def = parse_colon_key_token(kname) if isinstance(
            kname, str) and ":" in kname else None
        if colon_def:
            seq.append(colon_def)
            i += 1
            continue

        rkey, is_minor_key = parse_key_name(kname)
        mode = pick()

        if mode == "chromatic-mediants":
            chord_root, chord_pcs = chromatic_mediant_from_key(
                rkey, is_minor_key=is_minor_key)
        elif mode == "extended-chords":
            chord_root, chord_pcs = rkey, make_extended_chord(
                rkey, is_minor_key=is_minor_key)
        elif mode == "triads":
            chord_root, chord_pcs = rkey, make_triad(rkey,
                                                     is_minor_key=is_minor_key)
        elif mode == "sevenths":
            chord_root, chord_pcs = rkey, make_seventh(
                rkey, is_minor_key=is_minor_key)
        elif mode == "ninths":
            chord_root, chord_pcs = rkey, make_ninth(rkey,
                                                     is_minor_key=is_minor_key)
        elif mode == "quartal":
            chord_root, chord_pcs = rkey, make_quartal(
                rkey, is_minor_key=is_minor_key)
        elif mode == "sus":
            chord_root, chord_pcs = rkey, make_sus(rkey,
                                                   is_minor_key=is_minor_key)
        elif mode == "add6":
            chord_root, chord_pcs = rkey, make_add6(rkey,
                                                    is_minor_key=is_minor_key)
        elif mode == "lyd-dom":
            chord_root, chord_pcs = rkey, make_lyd_dom(
                rkey, is_minor_key=is_minor_key)
        else:
            chord_root, chord_pcs = rkey, make_extended_chord(
                rkey, is_minor_key=is_minor_key)

        pcs = tuple(sorted({n % 12 for n in chord_pcs}))
        seq.append(ChordDef(root_pc=chord_root, pcs=pcs, label=mode))
        i += 1

    return seq


def build_chord_timeline(
        seq: list[ChordDef],
        beats_total: float,
        base_len_beats: float,
        interrupters: list[list[tuple[float, str]]] | None = None,
        chord_fill_rate: float = 0.0,  # <-- add this
        static: bool = False,
        prev_sop: int | None = None,
        bass_anchor: int = 43,
) -> list[tuple[float, float, tuple[int, int, int, int]]]:
    """
    Returns [(when_beats, dur_beats, (s,a,t,b))].
    At each step, either place a straight chord slice of base_len_beats,
    or (with probability chord_fill_rate) place a random interrupter motif.
    Truncates at beats_total and sustains the last chord to reach the end.

    `static=True` freezes the voicing across an unchanged chord: identical
    consecutive (root, pcs, bass) reuse the exact previous (s,a,t,b) instead of
    re-voicing through `realize_SATB` (whose anti-stagnation logic would
    otherwise wobble the soprano between two chord tones every hit).

    `prev_sop`/`bass_anchor` seed the voice-leading state (the soprano note
    and bass register to lead from for the very first chord); pass the
    previous section's final (soprano, bass) to keep the arrangement's voices
    continuous across a section boundary instead of resetting each section.
    """
    out: list[tuple[float, float, tuple[int, int, int, int]]] = []
    pos = 0.0
    prev_chord_key: tuple | None = None
    prev_voicing: tuple[int, int, int, int] | None = None
    i = 0

    while pos < beats_total:
        entry = seq[i % len(seq)]
        root_pc = entry.root_pc
        pcs = list(entry.pcs)
        bass_pc = entry.bass_pc
        chord_key = (root_pc, tuple(sorted(pcs)), bass_pc)

        use_intr = (interrupters and chord_fill_rate > 0.0 and
                    random.random() < chord_fill_rate)
        motif = random.choice(interrupters) if use_intr else [(base_len_beats,
                                                               'c')]

        for beats, flag in motif:
            if pos >= beats_total:
                break
            dur = min(beats, max(0.0, beats_total - pos))
            if dur <= 0.0:
                break
            if flag == 'c':
                if static and prev_voicing is not None and chord_key == prev_chord_key:
                    sop, alto, tenor, bass = prev_voicing
                else:
                    sop, alto, tenor, bass = realize_SATB(prev_sop,
                                                          root_pc,
                                                          pcs,
                                                          bass_pc=bass_pc,
                                                          bass_anchor=bass_anchor)
                out.append((pos, dur, (sop, alto, tenor, bass)))
                prev_sop = sop
                bass_anchor = bass
                prev_chord_key = chord_key
                prev_voicing = (sop, alto, tenor, bass)
            pos += dur

        i += 1

    # sustain last chord to end if needed
    if out:
        end = max(when + dur for (when, dur, _n) in out)
        if end < beats_total:
            gap = beats_total - end
            out.append((end, gap, out[-1][2]))

    return out


def build_dense_timeline(
        seq: list[ChordDef],
        beats_total: float,
        base_len_beats: float,
        lo: int = 36,
        hi: int = 88) -> list[tuple[float, float, list[int]]]:
    """Like build_chord_timeline but emits full dense voicings (every tone)."""
    out: list[tuple[float, float, list[int]]] = []
    if not seq:
        return out
    pos = 0.0
    i = 0
    while pos < beats_total:
        entry = seq[i % len(seq)]
        notes = realize_dense(entry.root_pc, list(entry.pcs), entry.bass_pc,
                              lo, hi)
        dur = min(base_len_beats, max(0.0, beats_total - pos))
        if dur <= 0.0:
            break
        out.append((pos, dur, notes))
        pos += base_len_beats
        i += 1
    return out


def build_harmony_events(
        chord_tl: list[tuple[float, float, tuple[int, int, int, int]]],
        *,
        satb_style: str,
        bass_style: str = "follow",
        bass_step: float = 0.5,
        counterpoint_step: float = 0.25,
        counterpoint_suspension_prob: float = 0.0,
        counterpoint_anticipation_prob: float = 0.0,
        split_stems: bool = True,
        when_offset: float = 0.0,
        logger=None,
) -> tuple[list[tuple[str, float, float, object]], float]:
    """Turn a chord timeline into playable harmony + bass events.

    Shared by the flat single-render path and the arrangement orchestrator.
    `when_offset` shifts every event in time so a section can be placed on a
    global timeline. Returns ``(events, end_beats)``.
    """
    events: list[tuple[str, float, float, object]] = []
    voice_max = when_offset

    custom_bass = bass_style not in ("follow", None)
    if custom_bass and not split_stems:
        if logger:
            logger.warning(
                "--bass-style needs split stems (bass needs its own channel); "
                "falling back to 'follow'.")
        custom_bass = False

    if satb_style == "counterpoint":
        voice_lines = build_counterpoint_lines(chord_tl, counterpoint_step,
                                               counterpoint_suspension_prob,
                                               counterpoint_anticipation_prob)
        for voice, parts in voice_lines.items():
            for when, dur, note in parts:
                if dur <= 0.0:
                    continue
                events.append(("voice", when + when_offset, dur, (voice, note)))
                voice_max = max(voice_max, when + when_offset + dur)
    elif satb_style == "arpeggio":
        for voice, start, dur, note in build_arpeggio_events(
                chord_tl, counterpoint_step):
            if dur <= 0.0:
                continue
            events.append(("voice", start + when_offset, dur, (voice, note)))
            voice_max = max(voice_max, start + when_offset + dur)
    elif custom_bass:
        # block upper voices as per-voice events so the SATB bass is omitted
        for when, dur, notes in chord_tl:
            s, a, t, _b = notes
            for vname, vnote in (("soprano", s), ("alto", a), ("tenor", t)):
                events.append(("voice", when + when_offset, dur, (vname, vnote)))
            voice_max = max(voice_max, when + when_offset + dur)
    else:
        for when, dur, notes in chord_tl:
            events.append(("chord", when + when_offset, dur, notes))
            voice_max = max(voice_max, when + when_offset + dur)

    if custom_bass:
        # drop any SATB-generated bass, then lay down the independent bass line
        # (bass_style == "none" drops it and stops here: no bass at all)
        events = [
            e for e in events if not (e[0] == "voice" and e[3][0] == "bass")
        ]
        if bass_style != "none":
            for when, dur, note in build_bass_line(chord_tl, bass_style, bass_step):
                events.append(("voice", when + when_offset, dur, ("bass", note)))
                voice_max = max(voice_max, when + when_offset + dur)

    return events, voice_max
