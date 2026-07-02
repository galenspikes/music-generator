"""Voicing: turn chord pitch-classes into concrete notes and lines.

SATB realization (:func:`realize_SATB`), dense full-tone voicing
(:func:`realize_dense`), independent bass lines (:func:`build_bass_line`),
arpeggios (:func:`build_arpeggio_events`), and counterpoint lines
(:func:`build_counterpoint_lines`), plus their register/voice-leading helpers.
Depends only on :mod:`mtheory`.
"""
import math
import random

from mtheory import (
    ALTO_RANGE,
    BASS_RANGE,
    SOP_RANGE,
    TENOR_RANGE,
    VOICE_ORDER,
    VOICE_RANGE_MAP,
    clamp_to_range,
    nearest_in_register,
)

__all__ = [
    "build_counterpoint_lines",
    "build_arpeggio_events",
    "BASS_STYLES",
    "build_bass_line",
    "pick_soprano",
    "pick_in_part_range",
    "recenter_if_needed",
    "realize_SATB",
    "realize_dense",
]


def _snap_note_to_pcs(note_guess: int, pcs: set[int], voice: str) -> int:
    lo, hi = VOICE_RANGE_MAP[voice]
    if not pcs:
        return clamp_to_range(note_guess, lo, hi)
    best = None
    best_dist = float('inf')
    for candidate in range(lo, hi + 1):
        if candidate % 12 not in pcs:
            continue
        dist = abs(candidate - note_guess)
        if dist < best_dist:
            best = candidate
            best_dist = dist
    if best is None:
        return clamp_to_range(note_guess, lo, hi)
    return best


def _decorative_step(note: int, voice: str) -> int:
    lo, hi = VOICE_RANGE_MAP[voice]
    for step in (2, -2, 1, -1, 3, -3):
        candidate = note + step
        if lo <= candidate <= hi:
            return candidate
    return clamp_to_range(note, lo, hi)


def _fit_arpeggio_pitch(note: int, voice: str, previous: int | None) -> int:
    """Map chord tone to voice range with gentle contrary-motion bias."""

    lo, hi = VOICE_RANGE_MAP[voice]
    base = nearest_in_register(note, lo, hi)
    candidates = [p for p in (base - 12, base, base + 12) if lo <= p <= hi]
    if not candidates:
        return clamp_to_range(base, lo, hi)
    if previous is None:
        return min(candidates, key=lambda p: abs(p - base))

    best = min(candidates, key=lambda p: abs(p - previous))
    # encourage motion by nudging off repeated notes when possible
    if abs(best - previous) < 1 and len(candidates) > 1:
        motion = min((p for p in candidates if abs(p - previous) >= 1),
                     key=lambda p: abs(p - previous),
                     default=best)
        best = motion
    return best


def _counterpoint_sequence(start: int,
                           target: int,
                           pcs: set[int],
                           segments: int,
                           voice: str) -> list[int]:
    lo, hi = VOICE_RANGE_MAP[voice]
    start = clamp_to_range(start, lo, hi)
    target = clamp_to_range(target, lo, hi)
    if segments <= 1:
        return [start]

    seq: list[int] = []
    current = start
    for idx in range(segments):
        if idx == 0:
            note = _snap_note_to_pcs(start, pcs, voice)
        elif idx == segments - 1:
            note = _snap_note_to_pcs(target, pcs, voice)
        else:
            delta = target - current
            if abs(delta) >= 4:
                guess = current + (3 if delta > 0 else -3)
            elif delta == 0:
                guess = _decorative_step(current, voice)
                if random.random() < 0.35:
                    guess += random.choice([-2, 2])
            else:
                guess = current + delta
                if abs(delta) <= 2 and random.random() < 0.4:
                    guess += random.choice([-2, 2])
            note = _snap_note_to_pcs(guess, pcs, voice)
            if note == current:
                deco = _decorative_step(current, voice)
                note = _snap_note_to_pcs(deco, pcs, voice)
        current = note
        seq.append(current)

    seq[0] = start
    seq[-1] = _snap_note_to_pcs(target, pcs, voice)
    return seq


def _merge_voice_segment(line: list[tuple[float, float, int]],
                         start: float,
                         dur: float,
                         note: int) -> None:
    if not line:
        line.append((start, dur, note))
        return
    prev_start, prev_dur, prev_note = line[-1]
    if prev_note == note and math.isclose(prev_start + prev_dur,
                                          start,
                                          rel_tol=0.0,
                                          abs_tol=1e-4):
        line[-1] = (prev_start, prev_dur + dur, prev_note)
    else:
        line.append((start, dur, note))


def build_counterpoint_lines(
        chord_tl: list[tuple[float, float, tuple[int, int, int, int]]],
        step: float,
        suspension_prob: float,
        anticipation_prob: float) -> dict[str, list[tuple[float, float, int]]]:
    lines: dict[str, list[tuple[float, float, int]]] = {
        voice: [] for voice in VOICE_ORDER
    }
    if not chord_tl:
        return lines

    safe_step = max(0.1, step)
    current_pitch: dict[str, int] = {
        voice: chord_tl[0][2][idx] for idx, voice in enumerate(VOICE_ORDER)
    }
    pending_hold: dict[str, int] = {voice: 0 for voice in VOICE_ORDER}
    hold_next: dict[str, int] = {voice: 0 for voice in VOICE_ORDER}

    for idx, (when, dur, notes) in enumerate(chord_tl):
        if idx > 0:
            for voice in VOICE_ORDER:
                pending_hold[voice] = hold_next.get(voice, 0)
                hold_next[voice] = 0

        next_exists = idx + 1 < len(chord_tl)
        next_notes = chord_tl[idx + 1][2] if next_exists else notes
        pcs_now = {n % 12 for n in notes}
        pcs_next = {n % 12 for n in next_notes}
        pcs_union = pcs_now | pcs_next

        base_segments = max(1, int(round(dur / safe_step)))
        base_segments = max(1, min(8, base_segments))
        durations: list[float] = []
        remaining = dur
        for _ in range(base_segments):
            if remaining <= 1e-6:
                break
            jitter = random.uniform(0.75, 1.4)
            seg = safe_step * jitter
            if seg >= remaining:
                seg = remaining
            if seg <= 1e-6:
                seg = remaining
            durations.append(seg)
            remaining -= seg
        if remaining > 1e-6:
            durations.append(remaining)
        segments = len(durations)

        for v_idx, voice in enumerate(VOICE_ORDER):
            start_pitch = current_pitch.get(voice, notes[v_idx])
            target_pitch = next_notes[v_idx] if next_exists else start_pitch
            seq = _counterpoint_sequence(start_pitch, target_pitch, pcs_union,
                                         segments, voice)

            hold_segments = pending_hold.get(voice, 0)
            if hold_segments > 0:
                for i in range(min(hold_segments, len(seq))):
                    seq[i] = start_pitch
                pending_hold[voice] = 0

            suspension_applied = False

            if next_exists and segments >= 2:
                if random.random() < suspension_prob:
                    seq[-1] = start_pitch
                    if len(seq) >= 3:
                        seq[-2] = start_pitch
                    hold_next[voice] = max(hold_next.get(voice, 0), 1)
                    suspension_applied = True

            if (not suspension_applied and next_exists and segments >= 2
                    and random.random() < anticipation_prob):
                seq[-1] = target_pitch
                if len(seq) >= 3:
                    seq[-2] = target_pitch

            seq[-1] = clamp_to_range(seq[-1], *VOICE_RANGE_MAP[voice])

            pos = when
            for seg_idx, note in enumerate(seq):
                seg_dur = durations[seg_idx] if seg_idx < len(durations) else safe_step
                _merge_voice_segment(lines[voice], pos, seg_dur, note)
                pos += seg_dur

            current_pitch[voice] = seq[-1]

    return lines


def build_arpeggio_events(
        chord_tl: list[tuple[float, float, tuple[int, int, int, int]]],
        step: float,
        pattern_cycle: tuple[tuple[str, ...], ...] | None = None
) -> list[tuple[str, float, float, int]]:
    """Render arpeggiated SATB events with varied motion and light randomness."""

    default_patterns: tuple[tuple[str, ...], ...] = (
        VOICE_ORDER,
        tuple(reversed(VOICE_ORDER)),
        ("soprano", "tenor", "alto", "bass"),
        ("alto", "soprano", "tenor", "bass"),
        ("tenor", "alto", "soprano", "bass"),
    )

    if pattern_cycle is None:
        pattern_cycle = default_patterns

    step = max(0.05, float(step or 0.25))
    events: list[tuple[str, float, float, int]] = []
    if not chord_tl:
        return events

    last_pitch: dict[str, int | None] = {voice: None for voice in VOICE_ORDER}

    for chord_index, (when, dur, notes) in enumerate(chord_tl):
        if dur <= 0.0:
            continue

        total = dur
        steps = max(1, int(round(total / step)))

        patterns = list(pattern_cycle)
        random.shuffle(patterns)

        pattern_seq: list[str] = []
        while len(pattern_seq) < steps:
            pattern = random.choice(patterns)
            if chord_index % 2 and random.random() < 0.5:
                pattern = tuple(reversed(pattern))
            pattern_seq.extend(pattern)
        pattern_seq = pattern_seq[:steps]

        prev_voice: str | None = None
        for idx in range(steps):
            start = when + idx * step
            if start >= when + total:
                break
            end = min(start + step, when + total)
            seg_len = max(1e-6, end - start)

            voice = pattern_seq[idx]
            if voice == prev_voice:
                alternatives = [v for v in VOICE_ORDER if v != voice]
                voice = random.choice(alternatives)
            prev_voice = voice

            try:
                chord_index_for_voice = VOICE_ORDER.index(voice)
            except ValueError:
                continue
            note = notes[chord_index_for_voice]

            fitted = _fit_arpeggio_pitch(note, voice, last_pitch[voice])
            last_pitch[voice] = fitted

            jitter = (random.random() - 0.5) * step * 0.15
            start_jittered = min(max(when, start + jitter), when + total)
            end_jittered = min(start_jittered + seg_len, when + total)
            seg_len = max(1e-6, end_jittered - start_jittered)

            events.append((voice, start_jittered, seg_len, fitted))

    return events


BASS_STYLES = ("follow", "root", "octaves", "fifths", "walking", "arp")


def _bass_note_for_pc(pc: int, center: int, lo: int, hi: int) -> int:
    """Pick the octave of pitch-class `pc` in [lo,hi] nearest to `center`."""
    base = clamp_to_range(pc, lo, hi)
    cands = [c for c in (base - 12, base, base + 12) if lo <= c <= hi] or [base]
    return min(cands, key=lambda c: abs(c - center))


def _octave_partner(note: int, lo: int, hi: int) -> int:
    """The same pitch class an octave away, staying in [lo,hi] (for octave
    bass leaps). Prefers going down when there's no room above."""
    if note - 12 >= lo:
        return note - 12
    if note + 12 <= hi:
        return note + 12
    return note


def build_bass_line(
        chord_tl: list[tuple[float, float, tuple[int, int, int, int]]],
        style: str = "root",
        step: float = 0.5,
) -> list[tuple[float, float, int]]:
    """Generate an independent bass line from the realized chord timeline.

    Decouples the bass from the SATB voicing style so it can pulse, leap in
    octaves, alternate root/fifth, walk, or arpeggiate. Honors the realized
    bass note (so slash/pedal basses are respected). Returns
    ``[(when_beats, dur_beats, midi_note)]`` for the bass voice.
    """
    if not chord_tl or style in ("follow", None):
        return []

    lo, hi = BASS_RANGE
    out: list[tuple[float, float, int]] = []
    n = len(chord_tl)

    for i, (when, dur, notes) in enumerate(chord_tl):
        if dur <= 0.0:
            continue
        root = notes[3]  # realized bass note (pedal-aware)
        pcs = sorted({x % 12 for x in notes})
        nxt = chord_tl[(i + 1) % n][2][3] if n > 1 else root

        steps = max(1, int(round(dur / step))) if step > 0 else 1
        slen = dur / steps

        # non-root chord tones, voiced near the root register (for walk/arp)
        color = [
            _bass_note_for_pc(pc, root + 5, lo, hi) for pc in pcs
            if pc != root % 12
        ]
        color.sort()

        for k in range(steps):
            t = when + k * slen
            if style == "root":
                note = root
            elif style == "octaves":
                note = root if k % 2 == 0 else _octave_partner(root, lo, hi)
            elif style == "fifths":
                fifth = _bass_note_for_pc((root + 7) % 12, root + 7, lo, hi)
                note = root if k % 2 == 0 else fifth
            elif style == "arp":
                ladder = [root] + color
                note = ladder[k % len(ladder)]
            elif style == "walking":
                if k == 0:
                    note = root
                elif k == steps - 1 and nxt != root:
                    # chromatic approach into the next chord's bass
                    direction = 1 if nxt > root else -1
                    note = clamp_to_range(nxt - direction, lo, hi)
                elif color:
                    note = color[(k - 1) % len(color)]
                else:
                    note = root
            else:
                note = root
            out.append((t, slen, note))

    return out


def pick_soprano(chord_tones: list[int], prev_sop: int | None, root_pc: int,
                 guide_pcs: set[int], color_pcs: set[int],
                 root_optional: bool) -> int:
    candidates = [nearest_in_register(t, *SOP_RANGE) for t in chord_tones]
    if not candidates:
        return clamp_to_range(root_pc + 60, *SOP_RANGE)

    if prev_sop is None:
        baseline = sorted(candidates)[len(candidates) // 2]
        prev_sop = baseline

    def score(note: int) -> float:
        tone_pc = note % 12
        repeat_pen = 12 if note == prev_sop else 0
        step_cost = abs(note - prev_sop)
        height_pen = max(0, note - 77) / 2
        guide_bonus = -3 if tone_pc in guide_pcs else 0
        color_bonus = -1.5 if tone_pc in color_pcs else 0
        root_pen = 5 if root_optional and tone_pc == root_pc else 0
        return repeat_pen + step_cost + height_pen + root_pen + guide_bonus + color_bonus

    best = min(candidates, key=score)
    if best == prev_sop:
        for n in [prev_sop + 2, prev_sop - 2, prev_sop + 1, prev_sop - 1]:
            n = clamp_to_range(n, *SOP_RANGE)
            if n != prev_sop:
                return n
    return best


def pick_in_part_range(tone: int, lo: int, hi: int, avoid: int | None) -> int:
    n = nearest_in_register(tone, lo, hi)
    if avoid is not None and n == avoid:
        n2 = clamp_to_range(n + 3, lo, hi)
        if n2 != avoid:
            return n2
        n2 = clamp_to_range(n - 3, lo, hi)
        return n2
    return n


def recenter_if_needed(sop, alto, tenor, bass):
    shift = 0
    if sop > 78:
        shift = -12
    elif bass < 38:
        shift = +12
    if shift:
        return sop + shift, alto + shift, tenor + shift, bass + shift
    return sop, alto, tenor, bass


def realize_SATB(prev_sop: int | None,
                 root_pc: int,
                 chord_pcs: list[int],
                 bass_pc: int | None = None):
    """
    Voice a chord into SATB with:
      - bass at/near the root (or provided bass_pc) in BASS_RANGE
      - tenor/alto from other chord pcs in their ranges
      - soprano picked via anti-stagnation helper
    Returns (sop, alto, tenor, bass) as MIDI notes.
    """

    # choose concrete chord tones (as MIDI around reasonable default center)
    # start by mapping pitch classes to candidate mid-register notes
    def mid_note_for(pcval: int, mid=60):
        # choose octave of pcval nearest to 'mid'
        base = pcval
        # compute some candidates
        candidates = [base + 12 * k for k in range(-3, 6)]
        return min(candidates, key=lambda n: abs(n - mid))

    chord_mid = [mid_note_for(x, 60) for x in chord_pcs]
    chord_mid = sorted(chord_mid)

    pcs_set = {pc % 12 for pc in chord_pcs}
    intervals = {pc: (pc - root_pc) % 12 for pc in pcs_set}

    third_pcs = {(root_pc + ivl) % 12
                 for ivl in (3, 4)
                 if any(val == ivl for val in intervals.values())}
    guide_pcs = set(third_pcs)
    guide_pcs.update((root_pc + ivl) % 12
                     for ivl in (10, 11)
                     if any(val == ivl for val in intervals.values()))

    fifth_pc = (root_pc + 7) % 12 if any(
        val == 7 for val in intervals.values()) else None

    color_pcs = {
        pc for pc in pcs_set
        if pc not in guide_pcs and pc != root_pc and pc != fifth_pc
    }

    root_optional = len(pcs_set) > 3

    # pick soprano first (promote a chord tone selection bias)
    sop_choice = pick_soprano(chord_mid, prev_sop, root_pc, guide_pcs,
                              color_pcs, root_optional)

    available = chord_mid[:]
    if sop_choice in available:
        available.remove(sop_choice)

    # bass picks the root (or provided) in range
    broot = bass_pc if bass_pc is not None else root_pc
    bass = nearest_in_register(mid_note_for(broot, 43), *BASS_RANGE)

    satisfied_pcs = {sop_choice % 12, root_pc}

    def pop_best_for_pc(target_pc: int | None, center: int) -> int:
        if not available:
            return center
        if target_pc is not None:
            matches = [n for n in available if n % 12 == target_pc]
            if matches:
                chosen = min(matches, key=lambda n: abs(n - center))
                available.remove(chosen)
                return chosen
        chosen = min(available, key=lambda n: abs(n - center))
        available.remove(chosen)
        return chosen

    def choose_voice(center: int, desired_order: list[int],
                     already: set[int]) -> int:
        for pc in desired_order:
            if pc in already:
                continue
            if any(n % 12 == pc for n in available):
                return pop_best_for_pc(pc, center)
        return pop_best_for_pc(None, center)

    def sort_by_interval(pcs: set[int]) -> list[int]:
        return sorted(pcs, key=lambda pc: ((pc - root_pc) % 12))

    desired_sequence = sort_by_interval(guide_pcs) + sort_by_interval(color_pcs)
    if fifth_pc is not None:
        desired_sequence.append(fifth_pc)
    desired_sequence.append(root_pc)

    tenor_src = choose_voice(55, desired_sequence, satisfied_pcs)
    tenor = pick_in_part_range(tenor_src, *TENOR_RANGE, avoid=sop_choice)
    satisfied_pcs.add(tenor % 12)

    # rebuild desired sequence for alto with updated satisfied
    desired_sequence_alt = sort_by_interval(guide_pcs) + sort_by_interval(
        color_pcs)
    if fifth_pc is not None:
        desired_sequence_alt.append(fifth_pc)
    desired_sequence_alt.append(root_pc)

    alto_src = choose_voice(65, desired_sequence_alt, satisfied_pcs)
    alto = pick_in_part_range(alto_src, *ALTO_RANGE, avoid=sop_choice)
    if alto == tenor:
        for delta in (2, -2, 1, -1, 3, -3):
            candidate = clamp_to_range(alto + delta, *ALTO_RANGE)
            if candidate not in (sop_choice, tenor):
                alto = candidate
                break
    satisfied_pcs.add(alto % 12)

    # tidy spacing & recenter if needed
    sop, alto, tenor, bass = recenter_if_needed(sop_choice, alto, tenor, bass)
    return sop, alto, tenor, bass


def realize_dense(root_pc: int,
                  pcs: list[int],
                  bass_pc: int | None = None,
                  lo: int = 36,
                  hi: int = 88) -> list[int]:
    """Voice ALL chord tones as a wide spread stack across [lo,hi].

    Unlike 4-voice SATB (which discards tones), this sounds every pitch class in
    the chord — full 11ths/13ths, quartal stacks, mystic/messiaen sets, clusters
    — for dense, colorful harmony. Root (or slash bass) at the bottom, remaining
    tones stacked strictly upward, with a high doubling for shimmer if there's
    room.
    """
    ordered = sorted({p % 12 for p in pcs}, key=lambda pc: (pc - root_pc) % 12)
    broot = (bass_pc if bass_pc is not None else root_pc) % 12
    notes = [clamp_to_range(broot, lo, lo + 11)]
    cur = notes[0]
    for pc in ordered:
        nxt = cur + ((pc - cur) % 12)
        if nxt <= cur:
            nxt += 12
        if nxt > hi:
            break
        notes.append(nxt)
        cur = nxt
    if ordered and cur + 12 <= hi:
        notes.append(cur + 12)  # shimmer: double the top tone an octave up
    return sorted(set(notes))
