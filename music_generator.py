#!/usr/bin/env python3
# Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
# https://github.com/galenspikes/music-generator
import argparse
import importlib.util
import json
import math
import random
import subprocess
import shlex
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from mido import Message, MidiFile, MidiTrack, MetaMessage, bpm2tempo

from logging_config import music_generator_logger, log_function_call, log_performance, log_file_operation, log_music_generation, log_error

# --- project folders (relative to the script location) ---
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "output"
AUDIO_DIR = OUTPUT_DIR / "audio"
META_DIR = OUTPUT_DIR / "metadata"
LIB_DIR = SCRIPT_DIR / "library"
CHORD_RECIPES_PATH = LIB_DIR / "chord_recipes.py"
KEY_PRESETS_PATH = LIB_DIR / "keys_presets.json"
MIDI_DIR = OUTPUT_DIR / "midi"


@dataclass(frozen=True)
class ChordDef:
    root_pc: int
    pcs: tuple[int, ...]
    bass_pc: int | None = None
    label: str | None = None


# Drum/percussion token payload
@dataclass(frozen=True)
class PercHit:
    note: int
    vel_offset: int = 0
    probability: float = 1.0
    flam: float | None = None


@dataclass(frozen=True)
class PercStage:
    beats: float
    main: list[tuple[float, list[PercHit]]]
    fills: tuple[list[tuple[float, list[PercHit]]], ...] | None = None


@dataclass
class PercPlan:
    main: list[tuple[float, list[PercHit]]]
    interrupters: list[list[tuple[float, list[PercHit]]]] | None
    stages: list[PercStage] | None
    fill_curve: tuple[float, float] | None


# Channel constants
CHORD_CH = 0
DRUM_CH = 9  # GM percussion = channel 10

BASS_RANGE = (28, 55)  # E1–G3  (keeps foundation deep but not muddy)
TENOR_RANGE = (43, 67)  # G2–G4  (gives strong mid-low movement)
ALTO_RANGE = (50, 76)  # D3–E5  (bridges mid to high)
SOP_RANGE = (60, 91)  # C4–G6  (lets top voice soar and scream)

VOICE_ORDER = ("soprano", "alto", "tenor", "bass")
VOICE_RANGE_MAP = {
    "soprano": SOP_RANGE,
    "alto": ALTO_RANGE,
    "tenor": TENOR_RANGE,
    "bass": BASS_RANGE,
}

DEFAULT_PERC_LIB = LIB_DIR / "percussion_library.json"

FALLBACK_DRUM_MAP = {
    # Kicks / snares
    "a": 35,  # Acoustic Bass Drum
    "b": 36,  # Bass Drum 1
    "c": 38,  # Acoustic Snare
    "d": 40,  # Electric Snare
    "e": 37,  # Side Stick / Rimshot
    "f": 39,  # Hand Clap

    # Hi-hats
    "g": 42,  # Closed Hi-Hat
    "h": 44,  # Pedal Hi-Hat
    "i": 46,  # Open Hi-Hat

    # Cymbals
    "j": 49,  # Crash Cymbal 1
    "k": 51,  # Ride Cymbal 1
    "l": 53,  # Ride Bell
    "m": 57,  # Crash Cymbal 2
    "n": 59,  # Ride Cymbal 2
    "o": 55,  # Splash Cymbal
    "p": 52,  # Chinese Cymbal

    # Toms
    "q": 41,  # Low Floor Tom
    "s": 45,  # Low Tom
    "t": 47,  # Low-Mid Tom
    "u": 48,  # Hi-Mid Tom
    "v": 50,  # High Tom

    # Percussion / toys
    "w": 54,  # Tambourine
    "x": 56,  # Cowbell
    "y": 69,  # Cabasa
    "z": 70,  # Maracas
}

_DRUM_MAP_CACHE: dict[str, int] | None = None
_KEY_PRESETS_CACHE: dict[str, list[str]] | None = None


def load_drum_map_from(path: Path | None) -> dict[str, int]:
    mapping = FALLBACK_DRUM_MAP.copy()
    if path is None:
        return mapping
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return mapping
    except Exception:
        return mapping

    payload = data.get("drum_map")
    if isinstance(payload, dict):
        parsed: dict[str, int] = {}
        for raw_key, raw_val in payload.items():
            key = str(raw_key).strip().lower()
            if not key:
                continue
            note_val = raw_val.get("note") if isinstance(raw_val, dict) else raw_val
            try:
                note_int = int(note_val)
            except (TypeError, ValueError):
                continue
            parsed[key] = note_int
        if parsed:
            mapping.update(parsed)
    return mapping


def set_active_drum_map(source: str | Path | None) -> dict[str, int]:
    path = Path(source) if source is not None else DEFAULT_PERC_LIB
    mapping = load_drum_map_from(path)
    global _DRUM_MAP_CACHE
    _DRUM_MAP_CACHE = mapping
    return mapping


def get_drum_map() -> dict[str, int]:
    global _DRUM_MAP_CACHE
    if _DRUM_MAP_CACHE is None:
        set_active_drum_map(None)
    return _DRUM_MAP_CACHE


def load_key_presets(force_reload: bool = False) -> dict[str, list[str]]:
    """Load key presets from metadata/keys_presets.json (cached)."""

    global _KEY_PRESETS_CACHE
    if _KEY_PRESETS_CACHE is not None and not force_reload:
        return _KEY_PRESETS_CACHE

    if not KEY_PRESETS_PATH.exists():
        _KEY_PRESETS_CACHE = {}
        return _KEY_PRESETS_CACHE

    try:
        with open(KEY_PRESETS_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"Failed to load key presets: {exc}") from exc

    presets_raw = data.get("presets", {})
    out: dict[str, list[str]] = {}
    if isinstance(presets_raw, dict):
        for name, payload in presets_raw.items():
            if not isinstance(name, str):
                continue
            seq: list[str] | None = None
            if isinstance(payload, dict):
                if 'keys' in payload:
                    raw_seq = payload.get('keys')
                    if isinstance(raw_seq, list):
                        seq = raw_seq
                elif 'blocks' in payload:
                    blocks = payload.get('blocks')
                    if isinstance(blocks, list):
                        flattened: list[str] = []
                        for block in blocks:
                            if isinstance(block, dict):
                                sequence = block.get('sequence')
                                repeat = block.get('repeat', 1)
                            else:
                                sequence = block
                                repeat = 1
                            if not isinstance(sequence, list):
                                continue
                            cleaned_seq = [str(item).strip() for item in sequence if isinstance(item, str) and item.strip()]
                            if not cleaned_seq:
                                continue
                            repeat = int(repeat) if isinstance(repeat, (int, float)) else 1
                            repeat = max(1, repeat)
                            flattened.extend(cleaned_seq * repeat)
                        if flattened:
                            seq = flattened
                else:
                    # fallback to preview if provided
                    raw_seq = payload.get('preview')
                    if isinstance(raw_seq, list):
                        seq = raw_seq
            else:
                if isinstance(payload, list):
                    seq = payload
            if not seq:
                continue
            cleaned = [item.strip() for item in seq if isinstance(item, str) and item.strip()]
            if cleaned:
                out[name] = cleaned

    _KEY_PRESETS_CACHE = out
    return out

# --- GM instrument aliases (add/edit as you like) ---
GM_ALIASES = {
    # pianos
    "piano": 0,
    "brightpiano": 1,
    "epiano": 4,
    "epiano2": 5,
    # organs
    "organ": 16,
    "rockorgan": 18,
    "churchorgan": 19,
    # guitars
    "guitar": 24,
    "distguitar": 30,
    "jazzguitar": 26,
    "nylongt": 24,
    "clav": 7,
    # basses
    "bass": 32,
    "slapbass": 36,
    "synthbass": 38,
    "pickbass": 34,
    # strings / pads / choir
    "strings": 48,
    "slowstrings": 50,
    "choir": 52,
    "vox": 54,
    "pad": 88,
    # winds / brass
    "flute": 73,
    "clarinet": 71,
    "sax": 66,
    "trumpet": 56,
    "trombone": 57,
    # mallets / percussion
    "marimba": 12,
    "vibes": 11,
    "harpsi": 6,
    # synth leads
    "lead": 80,
    "saw": 81,
    "square": 80,
    "warm": 89,
    "synthbrass": 62,
}

# -------- Key parsing --------
NOTE_TO_PC = {
    "C": 0,
    "B#": 0,
    "C#": 1,
    "Db": 1,
    "D": 2,
    "D#": 3,
    "Eb": 3,
    "E": 4,
    "Fb": 4,
    "F": 5,
    "E#": 5,
    "F#": 6,
    "Gb": 6,
    "G": 7,
    "G#": 8,
    "Ab": 8,
    "A": 9,
    "A#": 10,
    "Bb": 10,
    "B": 11,
    "Cb": 11,
}


def ensure_dirs():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    META_DIR.mkdir(parents=True, exist_ok=True)
    LIB_DIR.mkdir(parents=True, exist_ok=True)
    MIDI_DIR.mkdir(parents=True, exist_ok=True)


def parse_key_name(kname: str) -> tuple[int, bool]:
    """
    Parse a key token like 'C', 'Eb', 'F#', 'Gm', 'Bbm', 'F#m'.
    Returns (pitch_class, is_minor).
    Raises ValueError on bad input.
    """
    s = kname.strip()
    if not s:
        raise ValueError("Empty key name")
    is_minor = s.endswith("m")
    core = s[:-1] if is_minor else s
    core = core.replace("♭", "b").replace("♯", "#")
    if core not in NOTE_TO_PC:
        raise ValueError(f"Bad key '{kname}'")
    return NOTE_TO_PC[core], is_minor


def resolve_instrument(arg: str) -> int:
    """
    Accepts either a GM program number (0-127) or a friendly alias string.
    Returns the GM program number.
    """
    s = arg.strip()
    if s.isdigit():
        return max(0, min(127, int(s)))
    return GM_ALIASES.get(s.lower(), 0)  # default to Acoustic Grand (0)


def clamp_to_range(n: int, lo: int, hi: int) -> int:
    while n < lo:
        n += 12
    while n > hi:
        n -= 12
    return n


def nearest_in_register(target: int, lo: int, hi: int) -> int:
    c = clamp_to_range(target, lo, hi)
    candidates = [c, c + 12, c - 12]
    return min(candidates,
               key=lambda x: (abs(x - target), 0 if lo <= x <= hi else 1e9))


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
            anticipation_applied = False

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
                anticipation_applied = True

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


_CHORD_RECIPES_CACHE: dict[str, tuple[int, ...]] | None = None


def load_chord_recipes(
        force_reload: bool = False) -> dict[str, tuple[int, ...]]:
    """Load chord recipes from library/chord_recipes.json (cached)."""

    global _CHORD_RECIPES_CACHE
    if _CHORD_RECIPES_CACHE is not None and not force_reload:
        return _CHORD_RECIPES_CACHE

    if not CHORD_RECIPES_PATH.exists():
        _CHORD_RECIPES_CACHE = {}
        return _CHORD_RECIPES_CACHE

    module_name = "_fs_chord_recipes"
    sys.modules.pop(module_name, None)

    spec = importlib.util.spec_from_file_location(module_name,
                                                  CHORD_RECIPES_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"Could not import chord recipes from {CHORD_RECIPES_PATH}")

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # pragma: no cover - developer-facing failure
        raise RuntimeError(f"Failed to load chord_recipes.py: {exc}") from exc

    data = getattr(module, "CHORD_RECIPES", {})
    if not isinstance(data, dict):
        raise RuntimeError("chord_recipes.py must define CHORD_RECIPES = {...}")

    # normalise payload to int lists
    recipes: dict[str, tuple[int, ...]] = {}
    for key, values in data.items():
        if not isinstance(key, str) or not isinstance(values, (list, tuple)):
            continue
        cleaned: list[int] = []
        for val in values:
            try:
                cleaned.append(int(val))
            except Exception:
                continue
        if cleaned:
            immutable = tuple(cleaned)
            recipes[key] = immutable
            lower_key = key.lower()
            if lower_key not in recipes:
                recipes[lower_key] = immutable

    _CHORD_RECIPES_CACHE = recipes
    return recipes


def get_chord_recipe(name: str) -> list[int] | None:
    """Fetch a chord recipe by name (case-insensitive)."""

    if not name:
        return None
    recipes = load_chord_recipes()
    recipe = recipes.get(name) or recipes.get(name.lower())
    if recipe is None:
        return None
    return list(recipe)


def parse_colon_key_token(token: str) -> ChordDef | None:
    """Parse root[:inv][:recipe][/bass] tokens into a chord definition.

    The optional ``/bass`` suffix sets an explicit bass pitch class (a slash
    chord / pedal), e.g. ``G::maj/C`` is a G major triad voiced over C. The
    bass note need not be a chord tone, so pedals like ``E/A`` are supported.
    An explicit ``/bass`` overrides any inversion-derived bass.
    """

    if ":" not in token:
        return None

    raw = token.strip()
    if not raw:
        raise ValueError("Empty colon chord token")

    # Optional slash-bass suffix.
    slash_bass_pc: int | None = None
    if "/" in raw:
        raw, bass_part = raw.rsplit("/", 1)
        raw = raw.strip()
        bass_part = bass_part.strip()
        if not bass_part:
            raise ValueError(f"Missing bass note after '/' in token '{token}'")
        try:
            slash_bass_pc, _ = parse_key_name(bass_part)
        except Exception as exc:
            raise ValueError(
                f"Bad slash bass '{bass_part}' in token '{token}'") from exc

    parts = raw.split(":")
    if len(parts) > 3:
        raise ValueError(f"Too many ':' sections in '{token}'")

    # pad to [root, inversion?, recipe?]
    while len(parts) < 3:
        parts.append("")

    root_part, inv_part, recipe_part = (p.strip() for p in parts[:3])
    if not root_part:
        raise ValueError(f"Missing root in colon token '{token}'")

    root_pc, is_minor = parse_key_name(root_part)

    inversion: int | None = None
    if inv_part:
        try:
            inversion = int(inv_part)
        except ValueError as exc:
            raise ValueError(
                f"Bad inversion '{inv_part}' in colon token '{token}'") from exc

    recipe_name = recipe_part or ("min" if is_minor else "maj")
    recipe = get_chord_recipe(recipe_name)
    if recipe is None:
        raise ValueError(
            f"Unknown chord recipe '{recipe_name}' in token '{token}'")

    if not recipe:
        raise ValueError(f"Chord recipe '{recipe_name}' has no tones")

    pcs = tuple(sorted({(root_pc + off) % 12 for off in recipe}))
    bass_pc = None
    if inversion is not None:
        idx = inversion % len(recipe)
        bass_pc = (root_pc + recipe[idx]) % 12
    if slash_bass_pc is not None:
        bass_pc = slash_bass_pc  # explicit slash bass overrides inversion

    return ChordDef(root_pc=root_pc, pcs=pcs, bass_pc=bass_pc, label=token.strip())


_last_sop = None


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


def write_manifest(out_path: str, args_ns) -> str:
    """Create/overwrite the args sidecar JSON and return its path."""
    sidecar = out_path.replace(".mid", ".args.json")

    # Predicted companion paths (mirror the slug subdir layout render.py uses:
    # output/{midi,audio,metadata}/<slug>/<base>.*)
    base_name = Path(out_path).stem
    slug = Path(out_path).parent.name
    audio_path = str(AUDIO_DIR / slug / f"{base_name}.wav")
    metadata_path = str(META_DIR / slug / f"{base_name}.json")
    
    data = {
        "generated_utc":
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "midi": out_path,
        "audio": audio_path,
        "metadata": metadata_path,
        "args": vars(args_ns),
        "file_catalog": {
            "midi_file": out_path,
            "audio_file": audio_path,
            "metadata_file": metadata_path,
            "args_file": sidecar,
            "base_name": base_name,
            "output_dir": str(OUTPUT_DIR),
            "midi_dir": str(MIDI_DIR),
            "audio_dir": str(AUDIO_DIR),
            "metadata_dir": str(META_DIR)
        }
    }
    with open(sidecar, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return sidecar


def append_manifest_fields(sidecar: str, extra: dict):
    """Safely merge extra fields into the sidecar JSON."""
    try:
        with open(sidecar, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    data.update(extra or {})
    with open(sidecar, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def update_master_catalog(manifest_path: str):
    """Update the master catalog with a new song entry."""
    catalog_path = OUTPUT_DIR / "master_catalog.json"
    
    # Load existing catalog or create new one
    try:
        with open(catalog_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        catalog = {"songs": [], "last_updated": None}
    
    # Load the manifest data
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception:
        return  # Skip if manifest can't be read
    
    # Add song entry
    song_entry = {
        "base_name": manifest.get("file_catalog", {}).get("base_name", "unknown"),
        "generated_utc": manifest.get("generated_utc", "unknown"),
        "manifest_file": manifest_path,
        "midi_file": manifest.get("midi", ""),
        "audio_file": manifest.get("audio", ""),
        "metadata_file": manifest.get("metadata", ""),
        "args": manifest.get("args", {}),
        "keys": manifest.get("args", {}).get("keys", ""),
        "bpm": manifest.get("args", {}).get("bpm", 0),
        "seconds": manifest.get("args", {}).get("seconds", 0),
        "instrument": manifest.get("args", {}).get("instrument", ""),
        "out": manifest.get("args", {}).get("out", "")
    }
    
    # Add to catalog (avoid duplicates)
    existing = next((s for s in catalog["songs"] if s["manifest_file"] == manifest_path), None)
    if not existing:
        catalog["songs"].append(song_entry)
        catalog["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Keep only last 100 songs to prevent catalog from growing too large
        if len(catalog["songs"]) > 100:
            catalog["songs"] = catalog["songs"][-100:]
        
        # Write updated catalog
        with open(catalog_path, "w", encoding="utf-8") as f:
            json.dump(catalog, f, indent=2)


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


def choose_perc_pattern(main, interrupters, fill_rate):
    """
    Returns either the main percussion pattern or a fill interrupter
    depending on fill_rate probability.
    """
    if interrupters and fill_rate > 0.0 and random.random() < fill_rate:
        return random.choice(interrupters)
    return main


# ----- duration map -----
DUR_MAP = {"w": 4.0, "h": 2.0, "q": 1.0, "e": 0.5, "s": 0.25, "t": 0.125}


def parse_single_token(tok: str,
                       drum_map: dict[str, int] | None = None
                       ) -> tuple[float, list[PercHit]]:
    """
    Token grammar:
      <len><letters>  e.g., 'qksh' (quarter: kick+snare+hat)
      <len>r          rest (no hits) e.g., 'er' (eighth rest)
    Letter symbols follow the active drum map (see library/percussion_library.json).
    Modifiers per letter:
      [vel±N] adjust velocity before humanisation
      [probX] plays with probability X (0–1)
      [flamX] adds a second hit X beats later (>=0)
    Returns (beats, [PercHit,...])
    """
    tok = tok.strip()
    if not tok:
        raise ValueError("Empty percussion token")
    ln = tok[0].lower()
    if ln not in DUR_MAP:
        raise ValueError(f"Bad duration in token '{tok}'")
    beats = DUR_MAP[ln]
    if len(tok) == 1:
        raise ValueError(f"Incomplete token '{tok}' (needs instruments or 'r')")
    rest = tok[1:]
    if rest.lower() == "r":
        return (beats, [])
    drum_map = drum_map or get_drum_map()
    hits: list[PercHit] = []
    i = 0
    rest_len = len(rest)
    while i < rest_len:
        ch = rest[i]
        if ch.isspace():
            i += 1
            continue
        if ch == '[':
            raise ValueError(f"Unexpected '[' in token '{tok}'")
        key = ch.lower()
        if key not in drum_map:
            raise ValueError(f"Unknown drum letter '{ch}' in token '{tok}'")
        i += 1
        vel_offset = 0
        probability = 1.0
        flam = None
        if i < rest_len and rest[i] == '[':
            end = rest.find(']', i)
            if end == -1:
                raise ValueError(f"Unclosed modifier block in token '{tok}'")
            block = rest[i + 1:end]
            i = end + 1
            if block.strip():
                for raw in block.split(','):
                    part = raw.strip()
                    if not part:
                        continue
                    lower = part.lower()
                    if lower.startswith('vel'):
                        payload = part[3:]
                        if payload.startswith(('=', '+', '-')):
                            payload = payload[1:] if payload.startswith('=') else payload
                        payload = payload.strip()
                        if not payload:
                            raise ValueError(
                                f"Missing velocity offset in modifier '{part}'")
                        try:
                            offset_val = int(payload)
                        except ValueError as exc:
                            raise ValueError(
                                f"Bad velocity offset '{part}' in token '{tok}'") from exc
                        if lower.startswith('vel-') and not lower.startswith('vel-='):
                            offset_val = -abs(offset_val)
                        elif lower.startswith('vel+') and not lower.startswith('vel+='):
                            offset_val = abs(offset_val)
                        vel_offset = offset_val
                    elif lower.startswith('prob'):
                        payload = part[4:]
                        if payload.startswith('='):
                            payload = payload[1:]
                        try:
                            probability = float(payload)
                        except ValueError as exc:
                            raise ValueError(
                                f"Bad probability '{part}' in token '{tok}'") from exc
                        probability = max(0.0, min(1.0, probability))
                    elif lower.startswith('flam'):
                        payload = part[4:]
                        if payload.startswith('='):
                            payload = payload[1:]
                        try:
                            flam_val = float(payload)
                        except ValueError as exc:
                            raise ValueError(
                                f"Bad flam offset '{part}' in token '{tok}'") from exc
                        if flam_val < 0.0:
                            raise ValueError(
                                f"Flam offset must be >=0 in token '{tok}'")
                        flam = flam_val
                    else:
                        raise ValueError(
                            f"Unknown modifier '{part}' in token '{tok}'")
        note_val = drum_map[key]
        hits.append(
            PercHit(note=note_val,
                    vel_offset=int(vel_offset),
                    probability=probability,
                    flam=flam))
    return (beats, hits)


def parse_pattern(text: str,
                  drum_map: dict[str, int] | None = None
                  ) -> list[tuple[float, list[PercHit]]]:
    """
    Comma-separated percussion tokens -> list of (beats, hits)
    Example: "qk,eh,esh,er,ek"
    """
    parts = [p for p in text.split(",") if p.strip() != ""]
    drum_map = drum_map or get_drum_map()
    return [parse_single_token(p, drum_map) for p in parts]


def parse_many_patterns(items: list[str],
                        drum_map: dict[str, int] | None = None
                        ) -> list[list[tuple[float, list[PercHit]]]]:
    """List of pattern strings -> list of parsed patterns."""
    drum_map = drum_map or get_drum_map()
    return [parse_pattern(s, drum_map) for s in items]


GRID_STEP = 0.25  # 16th = 0.25 beats


def quantize_to_grid(pattern: list[tuple[float, list[PercHit]]],
                     step: float = GRID_STEP) -> list[tuple[float, list[PercHit]]]:
    """
    Expand a pattern into fixed-step slots (e.g., 16ths), so it loops exactly.
    Input pattern: list of (beats, hits_set). Rest = empty set().
    Output: list of (step_beats, hits) slots, length is multiple of step.
    """
    out: list[tuple[float, list[PercHit]]] = []
    for beats, hits in pattern:
        if beats <= 0:
            continue
        slots = int(round(beats / step))
        # distribute duration across 'slots' fixed cells
        for i in range(slots):
            out.append(
                (step,
                 hits if i == 0 and hits else []))  # hit on first slot only
    return out


# ----- pitch utilities -----


def pc(name: str) -> int:
    return NOTE_TO_PC[name]


def parse_repetition_token(token: str) -> tuple[str, int]:
    """Parse token with optional repetition operator *N. Returns (base_token, count)."""
    if "*" not in token:
        return token, 1
    
    parts = token.split("*")
    if len(parts) != 2:
        raise ValueError(f"Bad repetition syntax in '{token}' (use *N format)")
    
    base_token = parts[0].strip()
    count_str = parts[1].strip()
    
    if not base_token:
        raise ValueError(f"Empty base token in '{token}'")
    
    try:
        count = int(count_str)
        if count < 1:
            raise ValueError(f"Repetition count must be >= 1, got {count}")
    except ValueError as exc:
        raise ValueError(f"Bad repetition count '{count_str}' in '{token}'") from exc
    
    return base_token, count


def parse_chain_repetition(token: str) -> tuple[list[str], int]:
    """Parse chain repetition token like [A:1:maj*2,B:0:min*2]*3. Returns (chain_tokens, count)."""
    if not token.startswith("["):
        raise ValueError(f"Chain repetition must start with bracket: '{token}'")
    
    # Find the last *N pattern by looking for * followed by digits at the end
    import re
    match = re.search(r'\*(\d+)$', token)
    if not match:
        raise ValueError(f"Chain repetition must have *N count at the end: '{token}'")
    
    count_str = match.group(1)
    chain_part = token[:match.start()].strip()
    
    # Remove the opening bracket from chain_part
    if chain_part.startswith("["):
        chain_part = chain_part[1:]
    else:
        raise ValueError(f"Chain repetition must start with bracket: '{token}'")
    
    # Remove the closing bracket if it exists
    if chain_part.endswith("]"):
        chain_part = chain_part[:-1]
    
    if not chain_part:
        raise ValueError(f"Empty chain in '{token}'")
    
    try:
        count = int(count_str)
        if count < 1:
            raise ValueError(f"Chain repetition count must be >= 1, got {count}")
    except ValueError as exc:
        raise ValueError(f"Bad chain repetition count '{count_str}' in '{token}'") from exc
    
    # Parse the chain tokens (comma-separated)
    chain_tokens = [t.strip() for t in chain_part.split(",") if t.strip()]
    if not chain_tokens:
        raise ValueError(f"Empty chain in '{token}'")
    
    return chain_tokens, count


_KEY_SHARP_TO_FLAT = {"C#": "Db", "D#": "Eb", "F#": "Gb", "G#": "Ab", "A#": "Bb"}


def _normalize_key_token(base_token: str) -> str:
    """Validate one key token and return its canonical form.

    Colon tokens (e.g. ``C::maj7``) are validated and returned as-is. Bare roots
    are unicode-normalized, have minor markers stripped, and sharps folded to the
    project's flat spelling. Raises ValueError on an unknown key.
    """
    if ":" in base_token:
        parse_colon_key_token(base_token)  # validate early; keep original token
        return base_token
    t = base_token.replace("♭", "b").replace("♯", "#")
    low = t.lower()
    if low.endswith("min"):
        t = t[:-3]
    elif low.endswith("m"):
        t = t[:-1]
    t = (t[0].upper() + t[1:]) if t else t
    t = _KEY_SHARP_TO_FLAT.get(t, t)
    if t not in NOTE_TO_PC:
        raise ValueError(f"Bad key '{base_token}'")
    return t


def _emit_key_token(tok: str, out: list[str]) -> None:
    """Expand one comma token (with optional ``*N``) into normalized keys."""
    base_token, count = parse_repetition_token(tok)
    out.extend([_normalize_key_token(base_token)] * count)


def _emit_key_chain(chain_token: str, out: list[str]) -> None:
    """Expand a ``[a,b,...]*N`` chain into normalized keys."""
    chain_tokens, chain_count = parse_chain_repetition(chain_token)
    for _ in range(chain_count):
        for chain_tok in chain_tokens:
            _emit_key_token(chain_tok, out)


def key_roots(mode: str, keys_csv: str | None) -> list[str]:
    if mode == "ostinato" and keys_csv:
        # Pull [..]*N chains out to placeholders so the comma-split won't break
        # them, then expand each token through a single shared code path.
        import re
        placeholder_map: dict[str, str] = {}
        processed = keys_csv
        for i, chain in enumerate(re.findall(r'\[[^\]]+\]\*\d+', keys_csv)):
            ph = f"__CHAIN_{i}__"
            placeholder_map[ph] = chain
            processed = processed.replace(chain, ph)

        out: list[str] = []
        for tok in (t.strip() for t in processed.split(",") if t.strip()):
            chain = placeholder_map.get(tok) or (tok if tok.startswith("[") else None)
            if chain is not None:
                try:
                    _emit_key_chain(chain, out)
                except ValueError as e:
                    raise ValueError(f"Invalid chain repetition '{chain}': {e}")
            else:
                _emit_key_token(tok, out)
        return out
    # default: stroll through a circle-ish order for 'mixed'/'complete'
    return ["C", "G", "D", "A", "E", "B", "Gb", "Db", "Ab", "Eb", "Bb", "F"]


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
) -> list[tuple[float, float, tuple[int, int, int, int]]]:
    """
    Returns [(when_beats, dur_beats, (s,a,t,b))].
    At each step, either place a straight chord slice of base_len_beats,
    or (with probability chord_fill_rate) place a random interrupter motif.
    Truncates at beats_total and sustains the last chord to reach the end.
    """
    out: list[tuple[float, float, tuple[int, int, int, int]]] = []
    pos = 0.0
    prev_sop: int | None = None
    i = 0

    while pos < beats_total:
        entry = seq[i % len(seq)]
        root_pc = entry.root_pc
        pcs = list(entry.pcs)
        bass_pc = entry.bass_pc

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
                sop, alto, tenor, bass = realize_SATB(prev_sop,
                                                      root_pc,
                                                      pcs,
                                                      bass_pc=bass_pc)
                out.append((pos, dur, (sop, alto, tenor, bass)))
                prev_sop = sop
            pos += dur

        i += 1

    # sustain last chord to end if needed
    if out:
        end = max(when + dur for (when, dur, _n) in out)
        if end < beats_total:
            gap = beats_total - end
            out.append((end, gap, out[-1][2]))

    return out


def build_drum_timeline_from_main(
        main_pat: list[tuple[float, list[PercHit]]],
        beats_total: float
        ) -> list[tuple[float, float, list[PercHit]]]:
    """
    Repeat 'main_pat' verbatim on a fixed grid until 'beats_total' is reached.
    Assumes 'main_pat' already quantized (e.g., via quantize_to_grid).
    Returns list of (when_beats, duration_beats, hits_set).
    """
    if not main_pat:
        return []
    motif_len = sum(b for b, _ in main_pat)
    out = []
    pos = 0.0
    while pos < beats_total:
        for beats, hits in main_pat:
            if pos >= beats_total:
                break
            dur = min(beats, max(0.0, beats_total - pos))
            out.append((pos, dur, hits))
            pos += dur
    return out


def build_drum_timeline_with_fills(
        main_pat: list[tuple[float, list[PercHit]]],
        intr_pats: list[list[tuple[float, list[PercHit]]]] | None,
        beats_total: float,
        fill_rate: float) -> list[tuple[float, float, list[PercHit]]]:
    """
    Bar-less unroll: each iteration chooses either main or a fill motif
    based on fill_rate. If intr_pats is None or fill_rate==0, falls back to main only.
    """
    tl: list[tuple[float, float, list[PercHit]]] = []
    pos = 0.0
    if not main_pat:
        return tl

    while pos < beats_total:
        pattern = choose_perc_pattern(main_pat, intr_pats, fill_rate)
        for beats, hits in pattern:
            if pos >= beats_total:
                break
            dur = min(beats, max(0.0, beats_total - pos))
            if dur <= 0.0:
                break
            tl.append((pos, dur, hits))
            pos += dur
    return tl


def build_drum_segment(start_beats: float,
                       duration: float,
                       main_pat: list[tuple[float, list[PercHit]]],
                       intr_pats: list[list[tuple[float, list[PercHit]]]] | None,
                       fill_rate: float) -> list[tuple[float, float, list[PercHit]]]:
    """Unroll a single percussion segment starting at start_beats."""
    if not main_pat or duration <= 0.0:
        return []
    out: list[tuple[float, float, list[PercHit]]] = []
    local = 0.0
    while local < duration:
        pattern = choose_perc_pattern(main_pat, intr_pats, fill_rate)
        for beats, hits in pattern:
            if local >= duration:
                break
            dur = min(beats, max(0.0, duration - local))
            if dur <= 0.0:
                break
            out.append((start_beats + local, dur, hits))
            local += dur
    return out


def build_drum_timeline_stages(
        stages: list[PercStage],
        beats_total: float,
        fallback_main: list[tuple[float, list[PercHit]]],
        fallback_intr: list[list[tuple[float, list[PercHit]]]] | None,
        base_fill_rate: float,
        fill_curve: tuple[float, float] | None) -> list[tuple[float, float, list[PercHit]]]:
    if beats_total <= 0.0 or not stages:
        return []

    out: list[tuple[float, float, list[PercHit]]] = []
    total_stage_beats = sum(stage.beats for stage in stages)
    pos = 0.0

    for stage in stages:
        if pos >= beats_total:
            break
        segment_len = min(stage.beats, max(0.0, beats_total - pos))
        if segment_len <= 0.0:
            pos += stage.beats
            continue
        if fill_curve and total_stage_beats > 0:
            start_val, end_val = fill_curve
            frac = max(0.0, min(1.0, pos / total_stage_beats))
            stage_fill = start_val + (end_val - start_val) * frac
        else:
            stage_fill = base_fill_rate
        stage_fill = max(0.0, min(1.0, stage_fill))
        stage_fills = list(stage.fills) if stage.fills else fallback_intr
        out.extend(
            build_drum_segment(pos, segment_len, stage.main, stage_fills,
                               stage_fill))
        pos += stage.beats

    if pos < beats_total and fallback_main:
        remainder = beats_total - pos
        out.extend(
            build_drum_segment(pos, remainder, fallback_main, fallback_intr,
                               base_fill_rate))

    return out


class MidiOut:

    STEM_VOICES = VOICE_ORDER

    def __init__(self,
                 bpm: int,
                 fname: str | None = None,
                 tpb: int = 480,
                 vel_mode_chords: str = "uniform",
                 vel_mode_drums: str = "uniform",
                 split_stems: bool = False) -> None:
        self.bpm = bpm
        self.fname = fname
        self.tpb = tpb
        self.vel_mode_chords = (vel_mode_chords or "uniform").lower()
        self.vel_mode_drums = (vel_mode_drums or "uniform").lower()
        self.split_stems = bool(split_stems)

        self.mid = MidiFile(type=1, ticks_per_beat=self.tpb)
        self.chord_tracks: dict[str, MidiTrack] = {}
        self.chord_channels: dict[str, int] = {}
        self.active_ch: dict[str, set[int]] = {}
        self.voice_positions: dict[str, float] = {}
        self.active_dr: set[int] = set()

        tempo = bpm2tempo(self.bpm)

        if self.split_stems:
            for idx, voice in enumerate(self.STEM_VOICES):
                channel = idx
                track = MidiTrack()
                self.mid.tracks.append(track)
                self.chord_tracks[voice] = track
                self.chord_channels[voice] = channel
                self.active_ch[voice] = set()
                self.voice_positions[voice] = 0.0
                track.append(MetaMessage('set_tempo', tempo=tempo, time=0))
                track.append(
                    Message('control_change',
                            control=7,
                            value=96,
                            channel=channel,
                            time=0))
                track.append(
                    Message('control_change',
                            control=11,
                            value=110,
                            channel=channel,
                            time=0))
        else:
            track = MidiTrack()
            self.mid.tracks.append(track)
            self.chord_tracks["ensemble"] = track
            self.chord_channels["ensemble"] = CHORD_CH
            self.active_ch["ensemble"] = set()
            self.voice_positions["ensemble"] = 0.0
            track.append(MetaMessage('set_tempo', tempo=tempo, time=0))
            track.append(
                Message('control_change',
                        control=7,
                        value=96,
                        channel=CHORD_CH,
                        time=0))
            track.append(
                Message('control_change',
                        control=11,
                        value=110,
                        channel=CHORD_CH,
                        time=0))

        # expose primary chord track for legacy accessors
        self.tr_ch = next(iter(self.chord_tracks.values()))

        self.tr_dr = MidiTrack()
        self.mid.tracks.append(self.tr_dr)  # drums (CH10)
        self.tr_dr.append(MetaMessage('set_tempo', tempo=tempo, time=0))
        self.tr_dr.append(
            Message('control_change',
                    control=7,
                    value=118,
                    channel=DRUM_CH,
                    time=0))
        self.tr_dr.append(
            Message('control_change',
                    control=11,
                    value=120,
                    channel=DRUM_CH,
                    time=0))
        # harmless on ch10:
        self.tr_dr.append(
            Message('program_change', program=0, channel=DRUM_CH, time=0))

        # Dedicated conductor track for a tempo map (set_tempo changes mid-piece,
        # e.g. per-section tempo in arrangements). Kept separate from note tracks
        # so it never interferes with their cursors.
        self.tr_meta = MidiTrack()
        self.mid.tracks.insert(0, self.tr_meta)
        self.meta_pos = 0.0
        self.tr_meta.append(MetaMessage('set_tempo', tempo=tempo, time=0))

    def _chord_track_items(self) -> list[tuple[str, MidiTrack]]:
        return list(self.chord_tracks.items())

    def set_program(self, program: int, bank_msb: int = 0, bank_lsb: int = 0):
        """Set one program for every chord track (back-compat)."""
        self.set_voice_programs(None, program, bank_msb=bank_msb,
                                bank_lsb=bank_lsb)

    def set_voice_programs(self,
                           programs: dict[str, int] | None,
                           default_program: int,
                           bank_msb: int = 0,
                           bank_lsb: int = 0):
        """Assign a GM program per chord track.

        `programs` maps a voice name (soprano/alto/tenor/bass) to a GM program
        number. Voices not listed — and the single 'ensemble' track when stems
        are disabled — fall back to `default_program`. Per-voice instruments
        therefore only take effect with split stems (the default).
        """
        programs = programs or {}
        for key, track in self._chord_track_items():
            channel = self.chord_channels[key]
            program = programs.get(key, default_program)
            # Optional bank select (helps with some SF2 layouts)
            track.append(
                Message('control_change',
                        control=0,
                        value=bank_msb,
                        channel=channel,
                        time=0))
            track.append(
                Message('control_change',
                        control=32,
                        value=bank_lsb,
                        channel=channel,
                        time=0))
            track.append(
                Message('program_change',
                        program=program,
                        channel=channel,
                        time=0))

    def ticks(self, beats: float) -> int:
        return int(round(beats * self.tpb))

    def _seek_meta(self, when_beats: float) -> None:
        delta = when_beats - self.meta_pos
        if delta > 0:
            self.tr_meta.append(
                MetaMessage('text', text='', time=self.ticks(delta)))
            self.meta_pos = when_beats

    def set_tempo_at(self, bpm: float, when_beats: float = 0.0) -> None:
        """Insert a tempo change at a beat offset (builds a tempo map)."""
        self._seek_meta(when_beats)
        self.tr_meta.append(
            MetaMessage('set_tempo', tempo=bpm2tempo(int(round(bpm))), time=0))

    def program_change_at(self,
                          voice: str,
                          program: int,
                          when_beats: float,
                          bank_msb: int = 0,
                          bank_lsb: int = 0) -> None:
        """Change a voice's program mid-track at a beat offset (re-orchestrate
        at section boundaries). Requires split stems (per-voice channels)."""
        if voice not in self.chord_tracks:
            return
        track = self.chord_tracks[voice]
        channel = self.chord_channels[voice]
        self._seek_voice(voice, when_beats)
        track.append(
            Message('control_change', control=0, value=bank_msb,
                    channel=channel, time=0))
        track.append(
            Message('control_change', control=32, value=bank_lsb,
                    channel=channel, time=0))
        track.append(
            Message('program_change', program=program, channel=channel,
                    time=0))

    def _seek_voice(self, voice: str, target_beats: float) -> None:
        current = self.voice_positions.get(voice, 0.0)
        delta = target_beats - current
        if delta <= 0:
            self.voice_positions[voice] = max(current, target_beats)
            return
        ticks = self.ticks(delta)
        if ticks > 0:
            self.chord_tracks[voice].append(
                MetaMessage('text', text='', time=ticks))
        self.voice_positions[voice] = target_beats

    def advance_ch(self, beats: float) -> None:
        if beats <= 0:
            return
        for voice in self.chord_tracks.keys():
            current = self.voice_positions.get(voice, 0.0)
            self._seek_voice(voice, current + beats)

    def advance_dr(self, beats: float) -> None:
        self.tr_dr.append(MetaMessage('text', text='', time=self.ticks(beats)))

    @staticmethod
    def _clamp_velocity(val: float) -> int:
        return max(1, min(127, int(round(val))))

    def _compute_chord_velocity(self, when_beats: float, base: int = 78) -> int:
        mode = self.vel_mode_chords
        if mode == "random":
            return self._clamp_velocity(base + random.randint(-36, 38))
        if mode == "human":
            beat_pos = (when_beats or 0.0) % 4.0
            accent = 0
            if beat_pos < 0.01:
                accent += 10
            elif abs(beat_pos - 2.0) < 0.01:
                accent += 6
            elif abs(beat_pos - 1.0) < 0.01 or abs(beat_pos - 3.0) < 0.01:
                accent += 3
            jitter = random.randint(-5, 5)
            return self._clamp_velocity(base + accent + jitter)
        return self._clamp_velocity(base)

    def play_voice_note(self,
                        voice: str,
                        note: int,
                        start_beats: float,
                        duration: float,
                        base: int = 78) -> None:
        if duration <= 0.0:
            return
        if voice not in self.chord_tracks:
            return
        velocity = self._compute_chord_velocity(start_beats, base)
        self._seek_voice(voice, start_beats)
        track = self.chord_tracks[voice]
        channel = self.chord_channels[voice]
        track.append(
            Message('note_on',
                    note=note,
                    velocity=velocity,
                    channel=channel,
                    time=0))
        self.active_ch[voice].add(note)
        ticks = max(1, self.ticks(duration))
        track.append(
            Message('note_off',
                    note=note,
                    velocity=0,
                    channel=channel,
                    time=ticks))
        self.active_ch[voice].discard(note)
        self.voice_positions[voice] = start_beats + duration

    def _compute_drum_velocity(self,
                               midi_note: int,
                               base: int,
                               when_beats: float) -> int:
        mode = self.vel_mode_drums
        if mode == "random":
            return self._clamp_velocity(base + random.randint(-35, 35))
        if mode == "human":
            beat_pos = (when_beats or 0.0) % 4.0
            accent = 0
            if beat_pos < 0.01:
                accent += 9
            elif abs(beat_pos - 2.0) < 0.01:
                accent += 6
            elif abs(beat_pos - 1.0) < 0.01 or abs(beat_pos - 3.0) < 0.01:
                accent += 3
            if midi_note in (35, 36):  # kicks
                accent += 3
            elif midi_note in (38, 37):  # snares / rim
                accent += 2
            elif midi_note in (42, 46):  # hats
                accent += 1
            jitter = random.randint(-6, 6)
            return self._clamp_velocity(base + accent + jitter)
        return self._clamp_velocity(base)

    def chord_block(self,
                    notes: tuple[int, int, int, int],
                    beats: float,
                    when_beats: float,
                    base: int = 78) -> None:
        vel = self._compute_chord_velocity(when_beats, base)
        s, a, t, b = notes
        dur_ticks = self.ticks(beats)
        if self.split_stems:
            voice_to_note = {
                "soprano": s,
                "alto": a,
                "tenor": t,
                "bass": b,
            }
            for voice, note in voice_to_note.items():
                self.play_voice_note(voice, note, when_beats, beats, base)
        else:
            track_key = "ensemble"
            track = self.chord_tracks[track_key]
            channel = self.chord_channels[track_key]
            self._seek_voice(track_key, when_beats)
            for note in (s, a, t, b):
                track.append(
                    Message('note_on',
                            note=note,
                            velocity=vel,
                            channel=channel,
                            time=0))
                self.active_ch[track_key].add(note)
            track.append(
                Message('note_off',
                        note=s,
                        velocity=0,
                        channel=channel,
                        time=dur_ticks))
            self.active_ch[track_key].discard(s)
            for n in (a, t, b):
                track.append(
                    Message('note_off',
                            note=n,
                            velocity=0,
                            channel=channel,
                            time=0))
                self.active_ch[track_key].discard(n)
            self.voice_positions[track_key] = when_beats + beats

    def dense_block(self,
                    notes: list[int],
                    beats: float,
                    when_beats: float,
                    base: int = 74) -> None:
        """Emit an arbitrary-length chord (full dense voicing) on the ensemble
        channel. Used by --voicing dense to sound every chord tone."""
        notes = list(dict.fromkeys(int(n) for n in notes))
        track_key = "ensemble"
        track = self.chord_tracks[track_key]
        channel = self.chord_channels[track_key]
        self._seek_voice(track_key, when_beats)
        if not notes:
            self.voice_positions[track_key] = when_beats + beats
            return
        vel = self._compute_chord_velocity(when_beats, base)
        dur_ticks = self.ticks(beats)
        for note in notes:
            track.append(
                Message('note_on', note=note, velocity=vel, channel=channel,
                        time=0))
            self.active_ch[track_key].add(note)
        track.append(
            Message('note_off', note=notes[0], velocity=0, channel=channel,
                    time=dur_ticks))
        self.active_ch[track_key].discard(notes[0])
        for n in notes[1:]:
            track.append(
                Message('note_off', note=n, velocity=0, channel=channel,
                        time=0))
            self.active_ch[track_key].discard(n)
        self.voice_positions[track_key] = when_beats + beats

    def drums_block(
            self,
            hits: list[PercHit],
            beats: float,
            when_beats: float,
            velk: int = 100,
            vels: int = 96,
            velh: int = 78,
            vel_o: int = 104,
            vel_c: int = 112,
            vel_w: int = 118,
            vel_m: int = 96,
            vel_p: int = 102,
            vel_t: int = 100,
            choke_openhat: bool = False,
            choke_after_beats: float = 0.06) -> None:
        if not hits:
            self.advance_dr(beats)
            return

        def base_velocity(note: int) -> int:
            if note == 36:
                return velk
            if note == 38:
                return vels
            if note == 42:
                return velh
            if note == 46:
                return vel_o
            if note == 49:
                return vel_c
            if note == 56:
                return vel_w
            if note == 47:
                return vel_m
            if note == 39:
                return vel_p
            if note == 37:
                return vel_t
            return 80

        events: list[tuple[float, int, int]] = []

        for hit in hits:
            if random.random() > hit.probability:
                continue
            note = hit.note
            base = base_velocity(note) + hit.vel_offset
            vel = self._compute_drum_velocity(note, base, when_beats)
            events.append((0.0, note, vel))

            if hit.flam is not None:
                flam_offset = max(0.0, float(hit.flam))
                if beats > 0.0:
                    flam_offset = min(flam_offset, max(0.0, beats))
                flam_base = base - 14
                flam_vel = self._compute_drum_velocity(
                    note, flam_base, when_beats + flam_offset)
                events.append((flam_offset, note, flam_vel))

        if not events:
            self.advance_dr(beats)
            return

        events.sort(key=lambda item: item[0])
        current_tick = 0
        active_notes: set[int] = set()
        for offset, note, velocity in events:
            ticks = max(0, self.ticks(offset))
            delta = max(0, ticks - current_tick)
            self.tr_dr.append(
                Message('note_on',
                        note=note,
                        velocity=self._clamp_velocity(velocity),
                        channel=DRUM_CH,
                        time=delta))
            current_tick = ticks
            self.active_dr.add(note)
            active_notes.add(note)

        block_ticks = self.ticks(beats)
        remaining_ticks = max(0, block_ticks - current_tick)

        if 46 in active_notes and choke_openhat and choke_after_beats > 0:
            choke_tick = max(1, self.ticks(min(choke_after_beats, beats)))
            delta_to_choke = max(0, choke_tick - current_tick)
            self.tr_dr.append(
                Message('note_on',
                        note=42,
                        velocity=1,
                        channel=DRUM_CH,
                        time=delta_to_choke))
            self.active_dr.add(42)
            current_tick = max(current_tick, choke_tick)
            rem = max(0, block_ticks - current_tick)
            self.tr_dr.append(
                Message('note_off',
                        note=42,
                        velocity=0,
                        channel=DRUM_CH,
                        time=rem or 1))
            self.active_dr.discard(42)
            for note in sorted(active_notes):
                self.tr_dr.append(
                    Message('note_off',
                            note=note,
                            velocity=0,
                            channel=DRUM_CH,
                            time=0))
                self.active_dr.discard(note)
            return

        ordered_notes = sorted(active_notes)
        if ordered_notes:
            first_note = ordered_notes[0]
            release_delta = remaining_ticks or 1
            self.tr_dr.append(
                Message('note_off',
                        note=first_note,
                        velocity=0,
                        channel=DRUM_CH,
                        time=release_delta))
            self.active_dr.discard(first_note)
            for note in ordered_notes[1:]:
                self.tr_dr.append(
                    Message('note_off',
                            note=note,
                            velocity=0,
                            channel=DRUM_CH,
                            time=0))
                self.active_dr.discard(note)

    def save(self, path: str | None = None) -> None:
        target = path or self.fname
        if target is None:
            raise ValueError("MidiOut.save() needs a path (none set at init)")
        self.mid.save(target)

    def to_bytes(self) -> bytes:
        """Serialize the MIDI to an in-memory bytes object (no disk write).

        This is the seam the web API renders through: generation stays in
        memory instead of round-tripping a file through ``output/``.
        """
        import io

        buf = io.BytesIO()
        self.mid.save(file=buf)
        return buf.getvalue()

    def _flush_active_chords(self) -> None:
        for key, notes in self.active_ch.items():
            if not notes:
                continue
            track = self.chord_tracks[key]
            channel = self.chord_channels[key]
            first = True
            for note in list(notes):
                track.append(
                    Message('note_off',
                            note=note,
                            velocity=0,
                            channel=channel,
                            time=1 if first else 0))
                first = False
                notes.discard(note)

    def _flush_active_drums(self) -> None:
        if not self.active_dr:
            return
        first = True
        for note in list(self.active_dr):
            self.tr_dr.append(
                Message('note_off',
                        note=note,
                        velocity=0,
                        channel=DRUM_CH,
                        time=1 if first else 0))
            first = False
            self.active_dr.discard(note)

    def flush_to_end(self,
                     chord_pos: float,
                     drum_pos: float,
                     end_beat: float) -> None:
        """Advance tracks to end_beat, release notes, and close MIDI streams."""
        for voice in self.chord_tracks.keys():
            current = self.voice_positions.get(voice, 0.0)
            if end_beat > current:
                self._seek_voice(voice, end_beat)

        drum_delta = max(0.0, end_beat - drum_pos)
        if drum_delta > 0:
            self.advance_dr(drum_delta)

        self._flush_active_chords()
        self._flush_active_drums()

        for key, track in self._chord_track_items():
            channel = self.chord_channels[key]
            track.append(
                Message('control_change',
                        control=123,
                        value=0,
                        channel=channel,
                        time=0))
            track.append(
                Message('control_change',
                        control=120,
                        value=0,
                        channel=channel,
                        time=0))
            track.append(MetaMessage('end_of_track', time=0))

        self.tr_dr.append(
            Message('control_change',
                    control=123,
                    value=0,
                    channel=DRUM_CH,
                    time=0))
        self.tr_dr.append(
            Message('control_change',
                    control=120,
                    value=0,
                    channel=DRUM_CH,
                    time=0))
        self.tr_dr.append(MetaMessage('end_of_track', time=0))


def ts_filename(stem: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    base = stem if stem else "out"
    return f"{base}_{ts}.mid"


def parse_chord_interrupters(
        motifs: list[str]) -> list[list[tuple[float, str]]]:
    """
    Motif token grammar (chords): same lengths; 'c' means play chord, 'r' rest.
    Example: "ec,er,sc" -> [(0.5,'c'), (0.5,'r'), (0.25,'c')]
    """
    out = []
    for m in motifs:
        seq = []
        for tok in [t.strip() for t in m.split(",") if t.strip()]:
            ln = tok[0].lower()
            if ln not in DUR_MAP:
                raise ValueError(f"Bad chord interrupter token '{tok}'")
            beats = DUR_MAP[ln]
            flag = tok[1:].lower()
            if flag not in ("c", "r"):
                raise ValueError(
                    f"Chord interrupter must end with c/r: '{tok}'")
            seq.append((beats, flag))
        out.append(seq)
    return out


def build_perc_from_args(args) -> PercPlan:
    """Build percussion plan (main loop, fills, staged evolution) from CLI args."""

    drum_map = get_drum_map()

    def parse_main(text: str) -> list[tuple[float, list[PercHit]]]:
        return quantize_to_grid(parse_pattern(text, drum_map))

    def parse_intr_list(items: list[str]) -> list[list[tuple[float, list[PercHit]]]]:
        return [quantize_to_grid(parse_pattern(item, drum_map)) for item in items]

    plan_main: list[tuple[float, list[PercHit]]] | None = None
    plan_intr: list[list[tuple[float, list[PercHit]]]] | None = None
    stage_specs: list[PercStage] = []
    fill_curve: tuple[float, float] | None = None

    if getattr(args, "perc_main", None):
        plan_main = parse_main(args.perc_main)

    if getattr(args, "perc_interrupters", None) and args.perc_interrupters:
        plan_intr = parse_intr_list(args.perc_interrupters)

    groups: dict[str, dict] = {}
    if getattr(args, "perc_lib", None):
        with open(args.perc_lib, "r", encoding="utf-8") as f:
            data = json.load(f)
        groups = data.get("groups", {})

    def fetch_group(key: str) -> tuple[list[tuple[float, list[PercHit]]] | None,
                                        list[list[tuple[float, list[PercHit]]]] | None]:
        grp = groups.get(key)
        if not grp:
            return (None, None)
        mains = grp.get("main", [])
        intrs = grp.get("interrupters", [])
        main_seq = parse_main(mains[0]) if mains else None
        intr_seq = parse_intr_list(intrs) if intrs else None
        return (main_seq, intr_seq)

    if getattr(args, "perc_main_key", None):
        main_from_group, intr_from_group = fetch_group(args.perc_main_key)
        if main_from_group is not None:
            plan_main = main_from_group
        if intr_from_group:
            plan_intr = (plan_intr or []) + intr_from_group

    if getattr(args, "perc_intr_keys", None) and args.perc_intr_keys:
        for key in args.perc_intr_keys:
            _, intr_from_group = fetch_group(key)
            if intr_from_group:
                plan_intr = (plan_intr or []) + intr_from_group

    stage_tokens = getattr(args, "perc_stages", None) or []

    def parse_stage_descriptor(token: str) -> PercStage:
        if ':' not in token:
            raise ValueError(f"Percussion stage must be 'beats:pattern': '{token}'")
        beats_part, payload = token.split(":", 1)
        try:
            beats_val = float(beats_part.strip())
        except ValueError as exc:
            raise ValueError(f"Bad perc stage length in '{token}'") from exc
        if beats_val <= 0.0:
            raise ValueError(f"Percussion stage beats must be >0 in '{token}'")
        pieces = [p.strip() for p in payload.split("|") if p.strip()]
        if not pieces:
            raise ValueError(f"Percussion stage '{token}' missing pattern payload")

        stage_main: list[tuple[float, list[PercHit]]] | None = None
        stage_fills: list[list[tuple[float, list[PercHit]]]] = []

        for piece in pieces:
            if piece.startswith('@'):
                if not groups:
                    raise ValueError(
                        f"Percussion stage '{token}' references @{piece[1:]} without --perc-lib")
                g_main, g_intr = fetch_group(piece[1:])
                if g_main is not None and stage_main is None:
                    stage_main = g_main
                if g_intr:
                    stage_fills.extend(g_intr)
                continue
            if stage_main is None:
                stage_main = parse_main(piece)
            else:
                stage_fills.extend(parse_intr_list([piece]))

        if stage_main is None:
            raise ValueError(f"Percussion stage '{token}' did not resolve a main pattern")

        fills_tuple = tuple(stage_fills) if stage_fills else None
        return PercStage(beats=beats_val, main=stage_main, fills=fills_tuple)

    for token in stage_tokens:
        stage_specs.append(parse_stage_descriptor(token))

    def parse_fill_curve(raw: str) -> tuple[float, float]:
        parts = [p.strip() for p in raw.split(":") if p.strip()]
        if len(parts) != 2:
            raise ValueError("--perc-fill-curve must be 'start:end' within [0,1]")
        try:
            start_val = float(parts[0])
            end_val = float(parts[1])
        except ValueError as exc:
            raise ValueError("--perc-fill-curve expects numeric values") from exc
        for val in (start_val, end_val):
            if not 0.0 <= val <= 1.0:
                raise ValueError("perc fill curve values must be within [0,1]")
        return (start_val, end_val)

    if getattr(args, "perc_fill_curve", None):
        fill_curve = parse_fill_curve(args.perc_fill_curve)

    if plan_main is None:
        plan_main = parse_main("sh,sh,sh,sh")

    if not plan_intr:
        plan_intr = parse_intr_list(["qk,er,qs,er"])

    return PercPlan(
        main=plan_main,
        interrupters=plan_intr,
        stages=stage_specs or None,
        fill_curve=fill_curve,
    )


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
        events = [
            e for e in events if not (e[0] == "voice" and e[3][0] == "bass")
        ]
        for when, dur, note in build_bass_line(chord_tl, bass_style, bass_step):
            events.append(("voice", when + when_offset, dur, ("bass", note)))
            voice_max = max(voice_max, when + when_offset + dur)

    return events, voice_max


def _apply_melody(args, events, seq, chord_len, beats_total, voice_max):
    """Replace the generated soprano voice with a hand-written melody line
    (audition path for the melody primitive). Key/mode inferred from `seq`
    unless overridden. Requires split stems."""
    import melody as mel

    if not args.split_stems:
        music_generator_logger.warning(
            "--melody needs split stems (the melody rides the soprano channel); "
            "ignoring melody.")
        return events, voice_max

    if args.melody_key:
        key_pc, _ = parse_key_name(args.melody_key)
        mode = args.melody_mode or "major"
    else:
        key_pc, mode = mel.infer_key(seq)
        if args.melody_mode:
            mode = args.melody_mode

    notes = mel.parse_melody(args.melody)
    if args.melody_transform == "invert":
        notes = mel.invert(notes)
    elif args.melody_transform == "retrograde":
        notes = mel.retrograde(notes)
    elif args.melody_transform == "augment":
        notes = mel.augment(notes, 2.0)

    mlen = sum(n.beats for n in notes)
    if mlen <= 0:
        return events, voice_max

    looped: list = []
    t = 0.0
    while t < beats_total:
        looped.extend(notes)
        t += mlen

    spans = None
    if args.melody_relative == "chord":
        spans, tt, i = [], 0.0, 0
        while tt < beats_total:
            spans.append((tt, tt + chord_len, seq[i % len(seq)].root_pc))
            tt += chord_len
            i += 1

    lo, hi = SOP_RANGE
    realized = mel.realize_melody(looped, key_pc, mode,
                                  base_octave=args.melody_octave, lo=lo, hi=hi,
                                  relative=args.melody_relative,
                                  chord_roots=spans)

    # strip the generated soprano; expand any block 'chord' events into a/t/b
    new_events: list = []
    for e in events:
        if e[0] == "voice" and e[3][0] == "soprano":
            continue
        if e[0] == "chord":
            when, dur, (_s, a, ten, b) = e[1], e[2], e[3]
            new_events.append(("voice", when, dur, ("alto", a)))
            new_events.append(("voice", when, dur, ("tenor", ten)))
            new_events.append(("voice", when, dur, ("bass", b)))
            continue
        new_events.append(e)

    for when, dur, note in realized:
        if when >= beats_total:
            break
        new_events.append(("voice", when, dur, ("soprano", note)))
        voice_max = max(voice_max, when + dur)

    music_generator_logger.info(
        "melody: key_pc=%s mode=%s relative=%s transform=%s notes=%d",
        key_pc, mode, args.melody_relative, args.melody_transform, len(notes))
    return new_events, voice_max


_EVENT_PRIORITY = {
    "tempo": 0, "program": 1, "voice": 2, "chord": 3, "densechord": 3, "drum": 4,
}


def resolve_out_path(out_arg: str | None, default_slug: str) -> str:
    """Build output/midi/<slug>/<timestamp>.mid, making the dir. <slug> is the
    --out value (unless it's empty/the default 'out'), else default_slug."""
    slug = out_arg if (out_arg and out_arg != "out") else default_slug
    subdir = MIDI_DIR / slug
    subdir.mkdir(parents=True, exist_ok=True)
    return str(subdir / ts_filename(slug))


def render_events(midi: "MidiOut",
                  events: list) -> tuple[float, float, float]:
    """Dispatch a time-sorted event stream onto a MidiOut. Handles every event
    kind (tempo, program, voice, chord, densechord, drum). Returns the final
    (chord_cursor, drum_cursor, voice_max) so the caller can flush to the end.

    Shared by the flat render, the arrangement renderer, and the fugue/process
    modes — one dispatch loop instead of several copies.
    """
    t_ch = 0.0
    t_dr = 0.0
    voice_max = 0.0
    for kind, when, dur, payload in sorted(
            events, key=lambda e: (e[1], _EVENT_PRIORITY.get(e[0], 9))):
        if kind == "voice":
            voice, note = payload
            midi.play_voice_note(voice, note, when, dur)
            voice_max = max(voice_max, when + dur)
        elif kind == "chord":
            if when > t_ch:
                midi.advance_ch(when - t_ch)
                t_ch = when
            if when > t_dr:
                midi.advance_dr(when - t_dr)
                t_dr = when
            midi.chord_block(payload, dur, when)
            t_ch += dur
        elif kind == "densechord":
            if when > t_ch:
                midi.advance_ch(when - t_ch)
                t_ch = when
            midi.dense_block(payload, dur, when)
            t_ch += dur
        elif kind == "drum":
            if when > t_dr:
                midi.advance_dr(when - t_dr)
                t_dr = when
            midi.drums_block(payload, dur, when)
            t_dr += dur
        elif kind == "tempo":
            midi.set_tempo_at(payload, when)
        elif kind == "program":
            voice, prog = payload
            midi.program_change_at(voice, prog, when)
    return t_ch, t_dr, voice_max


def build_generated(bpm: int, voice_events: list, total: float,
                    instrument: str, vel_chords: str,
                    vel_drums: str) -> "MidiOut":
    """Create a single-timbre MidiOut for the fugue/process modes and return it
    in memory (no save). They emit raw (voice, when, dur, note) tuples — wrap
    them into the standard ('voice', when, dur, (voice, note)) event form."""
    midi = MidiOut(bpm, None, vel_mode_chords=vel_chords,
                   vel_mode_drums=vel_drums, split_stems=True)
    midi.set_program(resolve_instrument(instrument))
    events = [("voice", when, dur, (voice, note))
              for (voice, when, dur, note) in voice_events]
    render_events(midi, events)
    midi.flush_to_end(total, 0.0, total)
    return midi


def _render_generated(out_path: str, bpm: int, voice_events: list, total: float,
                      instrument: str, vel_chords: str, vel_drums: str) -> None:
    """Build the fugue/process MIDI and save it to ``out_path`` (CLI path)."""
    build_generated(bpm, voice_events, total, instrument, vel_chords,
                    vel_drums).save(out_path)


def build_flat_midi(args) -> tuple["MidiOut", dict]:
    """Render the flat ostinato/mixed/complete path into an in-memory MidiOut.

    Shared by the CLI (``main``) and the web API. Pure with respect to disk: it
    writes nothing and performs no manifest/catalog side effects — the caller
    owns output paths and metadata. Returns ``(midi, meta)`` where ``meta``
    carries the derived fields the CLI manifest records. RNG-consumption order
    matches the original inline ``main`` body, so seeded output is identical.
    """
    tpb = 480
    beats_total = (args.seconds * args.bpm) / 60.0
    chord_len_beats = DUR_MAP[args.chord_len]

    roots = key_roots(args.mode, args.keys)
    if args.mode == "complete":
        max_ch = None
    elif args.mode == "ostinato":
        max_ch = 9999
    else:  # mixed
        random.shuffle(roots)
        max_ch = 9999

    seq = build_progression(roots, args.chords, args.chords_order,
                            max_chords=max_ch)

    picker = next_mode_picker(args.chords, args.chords_order)
    preview_modes = [picker() for _ in range(16)]

    chord_intr = parse_chord_interrupters(
        args.chord_interrupters) if args.chord_interrupters else None

    chord_tl = build_chord_timeline(seq, beats_total, chord_len_beats,
                                    chord_intr,
                                    chord_fill_rate=args.chord_fill_rate)
    chord_tl = fill_chords_to_end(chord_tl, beats_total)

    perc_plan = build_perc_from_args(args)
    main_pat = perc_plan.main
    intr_pats = perc_plan.interrupters
    stage_specs = perc_plan.stages or []
    fill_curve = perc_plan.fill_curve

    if stage_specs:
        drum_tl = build_drum_timeline_stages(stage_specs, beats_total, main_pat,
                                             intr_pats, args.perc_fill_rate,
                                             fill_curve)
    elif intr_pats and args.perc_fill_rate > 0.0:
        drum_tl = build_drum_timeline_with_fills(main_pat, intr_pats,
                                                 beats_total,
                                                 args.perc_fill_rate)
    else:
        drum_tl = build_drum_timeline_from_main(main_pat, beats_total)

    ch_end = 0.0 if not chord_tl else max(
        when + dur for (when, dur, _n) in chord_tl)
    drum_tl = truncate_timeline_to(drum_tl, ch_end)

    midi = MidiOut(args.bpm, None, tpb=tpb,
                   vel_mode_chords=args.velocity_mode_chords,
                   vel_mode_drums=args.velocity_mode_drums,
                   split_stems=args.split_stems)

    program = resolve_instrument(args.instrument)

    voice_programs: dict[str, int] = {}
    for spec in args.voice_instrument:
        if "=" not in spec:
            raise SystemExit(
                f"--voice-instrument expects VOICE=NAME, got '{spec}'")
        voice, name = (part.strip() for part in spec.split("=", 1))
        voice = voice.lower()
        if voice not in VOICE_ORDER:
            raise SystemExit(
                f"--voice-instrument unknown voice '{voice}'; "
                f"choose from {', '.join(VOICE_ORDER)}")
        if not name:
            raise SystemExit(
                f"--voice-instrument missing instrument name in '{spec}'")
        voice_programs[voice] = resolve_instrument(name)
    if voice_programs and not args.split_stems:
        music_generator_logger.warning(
            "--voice-instrument has no effect without split stems "
            "(all voices share one channel); ignoring per-voice instruments.")
        voice_programs = {}

    midi.set_voice_programs(voice_programs, program)

    if args.voicing == "dense":
        dense_tl = build_dense_timeline(seq, beats_total, chord_len_beats)
        events = [("densechord", w, d, notes) for (w, d, notes) in dense_tl]
        voice_max = max((w + d for w, d, _ in dense_tl), default=0.0)
    else:
        events, voice_max = build_harmony_events(
            chord_tl,
            satb_style=args.satb_style,
            bass_style=args.bass_style,
            bass_step=args.bass_step,
            counterpoint_step=args.counterpoint_step,
            counterpoint_suspension_prob=args.counterpoint_suspension_prob,
            counterpoint_anticipation_prob=args.counterpoint_anticipation_prob,
            split_stems=args.split_stems,
            logger=music_generator_logger,
        )

    if args.melody and args.voicing != "dense":
        events, voice_max = _apply_melody(args, events, seq, chord_len_beats,
                                          beats_total, voice_max)

    for when, dur, hits in drum_tl:
        events.append(("drum", when, dur, hits))

    t_ch, t_dr, vmax = render_events(midi, events)
    voice_max = max(voice_max, vmax)
    midi.flush_to_end(max(t_ch, voice_max), t_dr, beats_total)

    meta = {
        "chord_family_preview_first16": preview_modes,
        "perc_stages_declared": len(stage_specs),
        "perc_fill_curve": fill_curve,
    }
    return midi, meta


def build_parser() -> argparse.ArgumentParser:
    """Construct the full CLI parser.

    Extracted from ``main`` so the web API can introspect every flag (its type,
    choices, default, help) and render a control for each — the UI schema is
    generated from this, never hand-mirrored.
    """
    ap = argparse.ArgumentParser(
        description=
        "Harmony + Percussion generator (independent parts, SATB, interrupters)."
    )
    ap.add_argument("--mode",
                    choices=["complete", "mixed", "ostinato"],
                    default="mixed")
    ap.add_argument(
        "--song",
        type=str,
        default=None,
        help="Path to a YAML song file (arrangement of sections). When set, "
        "section-based rendering is used and most other flags are ignored.")
    ap.add_argument(
        "--fugue",
        type=str,
        default=None,
        nargs="?",
        const="__default__",
        help="Generate a fugal exposition from a melody subject (scale-degree "
        "syntax). Bare --fugue uses a built-in subject. Key via --melody-key/"
        "--melody-mode (default C major); voice timbre via --instrument.")
    ap.add_argument("--fugue-countersubject", type=str, default=None,
                    help="Optional countersubject (defaults to the inverted "
                    "subject).")
    ap.add_argument(
        "--process",
        choices=["phase", "additive", "augment"],
        default=None,
        help="Generate a process-music piece from a melodic cell: phase "
        "(Reich), additive (Glass), or augment (Four Organs). Cell via "
        "--process-cell; key via --melody-key/--melody-mode.")
    ap.add_argument("--process-cell", type=str, default=None,
                    help="Melodic cell (scale-degree syntax) for --process.")
    ap.add_argument("--process-reps", type=int, default=4,
                    help="Repetitions held at each stage of the process.")
    ap.add_argument("--process-stages", type=int, default=6,
                    help="Number of stages (for --process augment).")
    ap.add_argument("--keys",
                    type=str,
                    default=None,
                    help="Comma list of keys (Eb,Bb,...) for ostinato")
    ap.add_argument("--keys-preset",
                    type=str,
                    default=None,
                    help="Name of preset from metadata/keys_presets.json")
    ap.add_argument("--chords",
                    nargs="+",
                    default=["triads"],
                    choices=[
                        "chromatic-mediants", "extended-chords", "triads",
                        "sevenths", "ninths", "quartal", "sus", "add6",
                        "lyd-dom"
                    ],
                    help="Chord families to use.")
    ap.add_argument("--chords-order",
                    choices=["random", "roundrobin"],
                    default="random",
                    help="How to pick among multiple chord families each step.")
    ap.add_argument(
        "--instrument",
        type=str,
        default="piano",
        help="GM program: name alias (e.g., 'strings', 'flute') or 0–127")
    ap.add_argument(
        "--voice-instrument",
        action="append",
        default=[],
        metavar="VOICE=NAME",
        help="Per-voice instrument override, e.g. --voice-instrument bass=bass "
        "(repeatable). Voices: soprano, alto, tenor, bass. Voices not set use "
        "--instrument. Requires split stems (the default).")
    ap.add_argument(
        "--bass-style",
        choices=list(BASS_STYLES),
        default="follow",
        help="Bass line generator: 'follow' (bass tracks the SATB voicing), or "
        "an independent line: root, octaves, fifths, walking, arp. "
        "Requires split stems.")
    ap.add_argument(
        "--bass-step",
        type=float,
        default=0.5,
        help="Subdivision (in beats) for the bass line when --bass-style is not "
        "'follow' (0.5 = eighths, 1.0 = quarters).")
    # --- melody primitive (audition a hand-written line on the soprano voice) ---
    ap.add_argument(
        "--melody",
        type=str,
        default=None,
        help="Scale-degree melody on the soprano voice, e.g. \"q1 q3 q5 h1\". "
        "Loops to fill the piece; key/mode inferred from the chords. "
        "See docs/melody-grammar / docs/melody-primitive-plan.md.")
    ap.add_argument("--melody-relative", choices=["key", "chord"], default="key",
                    help="Degrees resolve against the section key, or anchor to "
                    "the current chord's root (motif fits each chord).")
    ap.add_argument("--melody-octave", type=int, default=5,
                    help="Register anchor for the melody.")
    ap.add_argument(
        "--melody-transform",
        choices=["none", "invert", "retrograde", "augment"],
        default="none",
        help="Apply a transform to the melody (demo the fugal operations).")
    ap.add_argument("--melody-key", type=str, default=None,
                    help="Override inferred key root (e.g. C, Eb, F#).")
    ap.add_argument("--melody-mode", type=str, default=None,
                    help="Override inferred mode (e.g. major, minor, dorian).")
    ap.add_argument("--bpm", type=int, default=120)
    ap.add_argument("--chord-length",
                    dest="chord_len",
                    choices=list(DUR_MAP.keys()),
                    default="e")
    ap.add_argument("--chord-interrupters",
                    nargs="*",
                    default=[],
                    help='Motifs like "ec,er,sc" (multiple allowed)')
    ap.add_argument("--satb-style",
                    choices=["block", "counterpoint", "arpeggio"],
                    default="block",
                    help="Voicing style for SATB harmony: block chords or counterpoint lines.")
    ap.add_argument(
        "--voicing",
        choices=["satb", "dense"],
        default="satb",
        help="satb = 4-voice voicing (default). dense = sound EVERY chord tone "
        "spread across the register (full 11ths/13ths, quartal, clusters, "
        "mystic/messiaen) on one timbre — for rich, colorful harmony.")
    ap.add_argument("--counterpoint-step",
                    type=float,
                    default=0.5,
                    help="Subdivision length in beats when using counterpoint SATB style.")
    ap.add_argument(
        "--counterpoint-suspension-prob",
        type=float,
        default=0.3,
        help=
        "Probability per voice that a chord change introduces a suspension (0–1)."
    )
    ap.add_argument(
        "--counterpoint-anticipation-prob",
        type=float,
        default=0.25,
        help=
        "Probability per voice that a chord change introduces an anticipation (0–1)."
    )

    # Percussion args (either explicit patterns or library lookups)
    ap.add_argument("--perc-main",
                    type=str,
                    default=None,
                    help='Pattern like "qk,eh,esh,er"')
    ap.add_argument("--perc-interrupters",
                    nargs="*",
                    default=None,
                    help='Motifs like "sh,sh,skh,sh" ...')
    ap.add_argument("--perc-lib", type=str, default=None)
    ap.add_argument("--perc-main-key", type=str, default=None)
    ap.add_argument("--perc-interrupter-keys",
                    dest="perc_intr_keys",
                    nargs="*",
                    default=None)
    ap.add_argument("--perc-stages",
                    nargs="*",
                    default=None,
                    help=(
                        "Sequential percussion stages like "
                        "'16:sh,sh,skh,sh|qk,er,qs,er' or '@grooveA'."))
    ap.add_argument("--perc-fill-curve",
                    type=str,
                    default=None,
                    help="Linear fill-rate ramp 'start:end' (0-1) applied across perc stages.")
    ap.add_argument(
        "--perc-fill-rate",
        type=float,
        default=0.20,
        help=
        "0–1. Probability a *percussion* interrupter replaces the main pattern. Default=0.20."
    )
    ap.set_defaults(split_stems=True)
    ap.add_argument("--velocity-mode-chords",
                    choices=["uniform", "random", "human"],
                    default="uniform",
                    help="Chord velocity behaviour: uniform, random, or humanised")
    ap.add_argument("--velocity-mode-drums",
                    choices=["uniform", "random", "human"],
                    default="uniform",
                    help="Drum velocity behaviour: uniform, random, or humanised")
    ap.add_argument(
        "--chord-fill-rate",
        type=float,
        default=0.00,
        help=
        "0–1. Probability a *chord* interrupter replaces the straight chord slice. Default=0.00."
    )
    ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument("--out", type=str, default="out")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--sf2", required=False, help="Path to SoundFont (.sf2)")
    ap.add_argument("--gain",
                    type=float,
                    default=0.5,
                    help="FluidSynth master gain (0.0–1.0)")
    ap.add_argument("--reverb", type=int, default=1, help="Enable reverb (0/1)")
    ap.add_argument("--chorus", type=int, default=1, help="Enable chorus (0/1)")
    ap.add_argument("--poly",
                    type=int,
                    default=256,
                    help="Maximum polyphony voices")
    ap.add_argument("--no-play",
                    action="store_true",
                    help="Generate MIDI only; do not launch FluidSynth.")
    ap.add_argument("--split-stems",
                    dest="split_stems",
                    action="store_true",
                    help="Write SATB voices to separate MIDI tracks/channels (default).")
    ap.add_argument("--no-split-stems",
                    dest="split_stems",
                    action="store_false",
                    help="Merge SATB voices into a single MIDI track.")

    return ap


def apply_arg_normalization(args) -> bool:
    """Clamp/normalize counterpoint + voicing-dependent args in place.

    Shared by the CLI and the web API so both honour the same guardrails
    (counterpoint forces split stems; dense voicing disables them). Returns
    whether split-stems was force-enabled by the counterpoint style.
    """
    counterpoint_forced_split = False
    if args.satb_style in ("counterpoint", "arpeggio"):
        if args.counterpoint_step <= 0.0:
            args.counterpoint_step = 0.5
        args.counterpoint_step = max(0.1, float(args.counterpoint_step))
        args.counterpoint_suspension_prob = max(
            0.0, min(1.0, float(args.counterpoint_suspension_prob)))
        args.counterpoint_anticipation_prob = max(
            0.0, min(1.0, float(args.counterpoint_anticipation_prob)))
        if not args.split_stems:
            args.split_stems = True
            counterpoint_forced_split = True
    else:
        args.counterpoint_step = max(0.1, float(args.counterpoint_step))
        args.counterpoint_suspension_prob = max(
            0.0, min(1.0, float(args.counterpoint_suspension_prob)))
        args.counterpoint_anticipation_prob = max(
            0.0, min(1.0, float(args.counterpoint_anticipation_prob)))

    # Dense voicing sounds every chord tone on one ensemble channel/timbre.
    if args.voicing == "dense":
        args.split_stems = False
    return counterpoint_forced_split


def main():
    start_time = datetime.now()
    music_generator_logger.info("Starting music generation")
    ap = build_parser()
    args = ap.parse_args()

    preset_used = None
    if getattr(args, "keys_preset", None):
        presets = load_key_presets()
        preset = presets.get(args.keys_preset)
        if not preset:
            raise ValueError(f"Unknown keys preset '{args.keys_preset}'")
        args.keys = ','.join(preset)
        preset_used = args.keys_preset

    ensure_dirs()

    if args.perc_lib:
        set_active_drum_map(args.perc_lib)
    else:
        set_active_drum_map(None)

    counterpoint_forced_split = apply_arg_normalization(args)

    if args.seed is not None:
        random.seed(args.seed)

    # ----- fugue path -----
    if args.fugue:
        import fugue as fug
        subject = fug.DEFAULT_SUBJECT if args.fugue == "__default__" else args.fugue
        if args.melody_key:
            key_pc, _ = parse_key_name(args.melody_key)
        else:
            key_pc = 0
        fmode = args.melody_mode or "major"
        fug_out = resolve_out_path(args.out, "fugue")
        fug_events, total = fug.build_fugue(subject, key_pc, fmode,
                                            countersubject=args.fugue_countersubject)
        _render_generated(fug_out, args.bpm, fug_events, total, args.instrument,
                          args.velocity_mode_chords, args.velocity_mode_drums)
        log_file_operation(music_generator_logger, "write", fug_out, True)
        print(f"Wrote {fug_out}")
        return 0

    # ----- process-music path -----
    if args.process:
        import process as proc
        cell = args.process_cell or proc.DEFAULT_CELL
        key_pc = parse_key_name(args.melody_key)[0] if args.melody_key else 0
        pmode = args.melody_mode or "major"
        proc_out = resolve_out_path(args.out, f"process_{args.process}")
        proc_events, total = proc.build_process(
            cell, key_pc, pmode, kind=args.process,
            reps=args.process_reps, stages=args.process_stages)
        _render_generated(proc_out, args.bpm, proc_events, total,
                          args.instrument, args.velocity_mode_chords,
                          args.velocity_mode_drums)
        log_file_operation(music_generator_logger, "write", proc_out, True)
        print(f"Wrote {proc_out}")
        return 0

    # ----- arrangement (song file) path -----
    if args.song:
        import arrangement
        default_slug = Path(args.song).stem
        song_out = resolve_out_path(args.out, default_slug)
        spec = arrangement.load_spec(
            args.song,
            vel_mode_chords=args.velocity_mode_chords,
            vel_mode_drums=args.velocity_mode_drums)
        arrangement.render(spec, song_out)
        log_file_operation(music_generator_logger, "write", song_out, True)
        print(f"Wrote {song_out}")
        return 0

    # ----- output path + sidecar JSON -----
    slug = args.out or "misc"
    mid_subdir = MIDI_DIR / slug
    mid_subdir.mkdir(parents=True, exist_ok=True)
    mid_name = ts_filename(slug)
    out_path = str(mid_subdir / mid_name)
    sidecar_path = write_manifest(out_path, args)
    update_master_catalog(sidecar_path)

    midi, meta = build_flat_midi(args)

    append_manifest_fields(
        sidecar_path, {
            "chord_families_passed": args.chords,
            "chord_family_order": args.chords_order,
            "chord_family_preview_first16":
                meta["chord_family_preview_first16"],
            "keys_preset": preset_used,
            "satb_style": args.satb_style,
            "split_stems": args.split_stems,
            "voice_instruments": args.voice_instrument,
            "bass_style": args.bass_style,
            "bass_step": args.bass_step,
            "counterpoint_step": args.counterpoint_step,
            "counterpoint_suspension_prob": args.counterpoint_suspension_prob,
            "counterpoint_anticipation_prob": args.counterpoint_anticipation_prob,
            "counterpoint_forced_split": counterpoint_forced_split
        })
    append_manifest_fields(
        sidecar_path, {
            "perc_stages_declared": meta["perc_stages_declared"],
            "perc_fill_curve": meta["perc_fill_curve"],
        })

    midi.save(out_path)

    # NOTE:
    # Originally this block auto-launched FluidSynth to play the generated MIDI.
    # It has been commented out because playback is now handled by the wrapper script (play_music.sh).
    # Keeping it here (commented) avoids double playback and ensures music_generator.py
    # is MIDI-only, leaving audio rendering/preview to the wrapper.
    # if args.sf2 and not args.no_play:
    #     cmd = [
    #         "fluidsynth",
    #         "-i",  # no interactive shell
    #         "-n",  # no MIDI input
    #         "-a", "coreaudio",
    #         "-g", str(args.gain),
    #         "-R", str(args.reverb),
    #         "-C", str(args.chorus),
    #         "-o", f"synth.polyphony={args.poly}",
    #         args.sf2,
    #         out_path  # or your audio_path if you route into audio/
    #     ]
    #     print(">>> Playing via FluidSynth:", " ".join(shlex.quote(c) for c in cmd))
    #     subprocess.run(cmd)

    print(f"Wrote {out_path}")
    
    # Log completion
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    log_performance(music_generator_logger, "Music generation", duration)
    log_music_generation(music_generator_logger, args.out or "misc", args.seconds, args.bpm, args.keys or "default")
    log_file_operation(music_generator_logger, "write", out_path, True)
    music_generator_logger.info(f"Music generation completed successfully in {duration:.3f}s")


if __name__ == "__main__":
    main()
