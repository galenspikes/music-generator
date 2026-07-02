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
from mtheory import (
    ChordDef,
    CHORD_CH,
    DRUM_CH,
    BASS_RANGE,
    TENOR_RANGE,
    ALTO_RANGE,
    SOP_RANGE,
    VOICE_ORDER,
    VOICE_RANGE_MAP,
    GM_ALIASES,
    NOTE_TO_PC,
    DUR_MAP,
    parse_key_name,
    resolve_instrument,
    clamp_to_range,
    nearest_in_register,
    pc,
    load_chord_recipes,
    get_chord_recipe,
)
from percussion import (
    PercHit,
    PercStage,
    PercPlan,
    DEFAULT_PERC_LIB,
    FALLBACK_DRUM_MAP,
    load_drum_map_from,
    set_active_drum_map,
    get_drum_map,
    choose_perc_pattern,
    parse_single_token,
    parse_pattern,
    parse_many_patterns,
    GRID_STEP,
    quantize_to_grid,
    build_drum_timeline_from_main,
    build_drum_timeline_with_fills,
    build_drum_segment,
    build_drum_timeline_stages,
    parse_chord_interrupters,
    build_perc_from_args,
)
from tokens import (
    parse_colon_key_token,
    parse_repetition_token,
    parse_chain_repetition,
    key_roots,
)
from voicing import (
    build_counterpoint_lines,
    build_arpeggio_events,
    BASS_STYLES,
    build_bass_line,
    pick_soprano,
    pick_in_part_range,
    recenter_if_needed,
    realize_SATB,
    realize_dense,
)
from midiout import MidiOut

# --- project folders (relative to the script location) ---
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "output"
AUDIO_DIR = OUTPUT_DIR / "audio"
META_DIR = OUTPUT_DIR / "metadata"
LIB_DIR = SCRIPT_DIR / "library"
CHORD_RECIPES_PATH = LIB_DIR / "chord_recipes.py"
KEY_PRESETS_PATH = LIB_DIR / "keys_presets.json"
MIDI_DIR = OUTPUT_DIR / "midi"

_KEY_PRESETS_CACHE: dict[str, list[str]] | None = None


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
def ensure_dirs():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    META_DIR.mkdir(parents=True, exist_ok=True)
    LIB_DIR.mkdir(parents=True, exist_ok=True)
    MIDI_DIR.mkdir(parents=True, exist_ok=True)


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


def ts_filename(stem: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    base = stem if stem else "out"
    return f"{base}_{ts}.mid"


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
        "See docs/reference/token-grammar.md / docs/design-notes/melody-primitive-plan.md.")
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
        arr_overrides: dict = {
            "tempo": args.bpm,
            "instrument": args.instrument,
            "chord_length": args.chord_len,
            "satb": args.satb_style,
            "bass": {"style": args.bass_style, "step": float(args.bass_step)},
            "perc": {"fill_rate": float(args.perc_fill_rate)},
        }
        if args.perc_main:
            arr_overrides["perc"]["main"] = args.perc_main
        if args.voice_instrument:
            voices: dict = {}
            for vi in args.voice_instrument:
                if "=" in str(vi):
                    v, instr = str(vi).split("=", 1)
                    voices[v.strip()] = instr.strip()
            if voices:
                arr_overrides["voices"] = voices
        spec = arrangement.load_spec(
            args.song,
            vel_mode_chords=args.velocity_mode_chords,
            vel_mode_drums=args.velocity_mode_drums,
            overrides=arr_overrides)
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
