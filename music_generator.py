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
