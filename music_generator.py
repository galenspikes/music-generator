#!/usr/bin/env python3
# Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
# https://github.com/galenspikes/music-generator
"""Music Generator — CLI entry point and render orchestration.

The slim top layer of the package. It parses CLI args, resolves output paths,
writes run manifests / the master catalog, applies optional melody, and drives
the render pipeline (tokens → composition → voicing → MidiOut). The music
engine itself lives in the sibling modules, layered by dependency:

    mtheory → percussion / tokens / voicing / midiout → composition → (here)

Public names from those modules are re-imported here so existing callers that
reach through ``music_generator`` (e.g. ``mg.build_harmony_events``) keep
working. See ``docs/architecture.md`` for the full module map and data flow.
"""
import argparse
import json
import math
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

from logging_config import music_generator_logger, log_performance, log_file_operation, log_music_generation

# The music engine lives in the layered sibling modules below. They are
# re-exported here (star imports, each module defines __all__) so existing
# callers reaching through ``music_generator`` (e.g. ``mg.build_harmony_events``)
# keep working. See docs/architecture.md for the module map and data flow.
from mtheory import *  # noqa: F401,F403
from percussion import *  # noqa: F401,F403
from tokens import *  # noqa: F401,F403
from voicing import *  # noqa: F401,F403
from midiout import *  # noqa: F401,F403
from composition import *  # noqa: F401,F403

# Names used directly in this module (also imported via * above; listed
# explicitly so static tools can see them and to document the dependency).
from mtheory import (  # noqa: F401
    VOICE_ORDER, DUR_MAP, SOP_RANGE, parse_key_name, resolve_instrument,
)
from percussion import (  # noqa: F401
    build_perc_from_args, build_drum_timeline_stages,
    build_drum_timeline_with_fills, build_drum_timeline_from_main,
    parse_chord_interrupters, set_active_drum_map,
)
from tokens import key_roots  # noqa: F401
from voicing import BASS_STYLES  # noqa: F401
from midiout import MidiOut  # noqa: F401
from composition import (  # noqa: F401
    build_progression, build_chord_timeline, build_dense_timeline,
    build_harmony_events, fill_chords_to_end, truncate_timeline_to,
    next_mode_picker,
)

class SpecError(ValueError):
    """A generation spec was invalid (bad ``--voice-instrument`` syntax, an
    unknown preset, …). Raised by the shared, disk-free builders so they stay
    free of any front-end's error convention: the CLI turns it into a clean
    ``argparse`` exit, and the web API turns it into a structured
    ``GenerationError``. Builders used to ``raise SystemExit`` here — a CLI-only
    signal that forced the platform seam to catch ``SystemExit`` specially."""


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
    """Load key presets from library/keys_presets.json (cached)."""

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
    # Guard against a malformed/legacy catalog missing the expected shape.
    if not isinstance(catalog, dict) or not isinstance(catalog.get("songs"), list):
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
    existing = next((s for s in catalog["songs"]
                     if s.get("manifest_file") == manifest_path), None)
    if not existing:
        catalog["songs"].append(song_entry)
        catalog["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Keep only last 100 songs to prevent catalog from growing too large
        if len(catalog["songs"]) > 100:
            catalog["songs"] = catalog["songs"][-100:]

        # Write updated catalog
        with open(catalog_path, "w", encoding="utf-8") as f:
            json.dump(catalog, f, indent=2)


def ts_filename(stem: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    base = stem if stem else "out"
    return f"{base}_{ts}.mid"


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


def _swing_time(t: float, s: float) -> float:
    """Warp a beat position ``t`` for a swing amount ``s`` (0 = straight).

    Each beat is split at its midpoint into two eighths; the on-beat eighth is
    stretched by ``(1 + s)`` and the off-beat compressed by ``(1 - s)``, so the
    "and" is delayed toward the back of the beat while beat boundaries (whole
    numbers) stay put. At ``s = 0.5`` the off-beat lands on the triplet (0.75).
    """
    b = math.floor(t)
    f = t - b
    if f < 0.5:
        return b + f * (1.0 + s)
    return b + 0.5 * (1.0 + s) + (f - 0.5) * (1.0 - s)


def apply_swing(events: list, s: float) -> list:
    """Return ``events`` with every start (and end, to keep durations honest)
    warped by :func:`_swing_time`. A no-op when ``s`` is zero."""
    if not s:
        return events
    out = []
    for kind, when, dur, payload in events:
        w0 = _swing_time(when, s)
        w1 = _swing_time(when + dur, s)
        out.append((kind, w0, max(0.0, w1 - w0), payload))
    return out


def render_events(midi: "MidiOut",
                  events: list) -> tuple[float, float, float]:
    """Dispatch a time-sorted event stream onto a MidiOut. Handles every event
    kind (tempo, program, voice, chord, densechord, drum). Returns the final
    (chord_cursor, drum_cursor, voice_max) so the caller can flush to the end.

    Shared by the flat render, the arrangement renderer, and the fugue/process
    modes — one dispatch loop instead of several copies.
    """
    events = apply_swing(events, getattr(midi, "swing", 0.0))
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
                    vel_drums: str, swing: float = 0.0,
                    pan_spread: float = 0.0) -> "MidiOut":
    """Create a single-timbre MidiOut for the fugue/process modes and return it
    in memory (no save). They emit raw (voice, when, dur, note) tuples — wrap
    them into the standard ('voice', when, dur, (voice, note)) event form."""
    midi = MidiOut(bpm, None, vel_mode_chords=vel_chords,
                   vel_mode_drums=vel_drums, split_stems=True,
                   swing=swing, pan_spread=pan_spread)
    midi.set_program(resolve_instrument(instrument))
    events = [("voice", when, dur, (voice, note))
              for (voice, when, dur, note) in voice_events]
    render_events(midi, events)
    midi.flush_to_end(total, 0.0, total)
    return midi


def _build_from_voice_events(args, voice_events: list,
                             total: float) -> "MidiOut":
    """Wrap the fugue/process ``(voice, when, dur, note)`` stream into an
    in-memory MidiOut, reading timbre/velocity/swing from ``args``. Shared tail
    of :func:`build_fugue_midi` and :func:`build_process_midi`."""
    return build_generated(args.bpm, voice_events, total, args.instrument,
                           args.velocity_mode_chords, args.velocity_mode_drums,
                           swing=getattr(args, "swing", 0.0),
                           pan_spread=getattr(args, "pan_spread", 0.0))


def build_fugue_midi(args) -> tuple["MidiOut", float]:
    """Build a fugal exposition into an in-memory MidiOut (no disk). Shared by
    the CLI and the web API so the subject/key/mode resolution lives in one
    place instead of being copied into each front-end's dispatch."""
    import fugue as fug
    subject = fug.DEFAULT_SUBJECT if args.fugue == "__default__" else args.fugue
    key_pc = parse_key_name(args.melody_key)[0] if args.melody_key else 0
    events, total = fug.build_fugue(subject, key_pc, args.melody_mode or "major",
                                    countersubject=args.fugue_countersubject)
    return _build_from_voice_events(args, events, total), total


def build_process_midi(args) -> tuple["MidiOut", float]:
    """Build a process-music piece into an in-memory MidiOut (no disk). Shared by
    the CLI and the web API (see :func:`build_fugue_midi`)."""
    import process as proc
    cell = args.process_cell or proc.DEFAULT_CELL
    key_pc = parse_key_name(args.melody_key)[0] if args.melody_key else 0
    events, total = proc.build_process(
        cell, key_pc, args.melody_mode or "major", kind=args.process,
        reps=args.process_reps, stages=args.process_stages)
    return _build_from_voice_events(args, events, total), total


def song_overrides_from_args(args, include) -> dict:
    """Build the arrangement-override dict from parsed args, shared by the CLI
    and the web API.

    ``include(dest, *flags) -> bool`` decides whether a flag contributes an
    override. The CLI passes a predicate that is true only for flags the user
    actually set, so a song's authored YAML defaults aren't clobbered by
    argparse defaults; the web API passes ``lambda *a: True`` because every UI
    control is an explicit value.
    """
    ov: dict = {}
    if include("bpm", "--bpm"):
        ov["tempo"] = args.bpm
    if include("instrument", "--instrument"):
        ov["instrument"] = args.instrument
    if include("chord_len", "--chord-length"):
        ov["chord_length"] = args.chord_len
    if include("satb_style", "--satb-style"):
        ov["satb"] = args.satb_style
    if include("swing", "--swing"):
        ov["swing"] = float(args.swing)
    if include("pan_spread", "--pan-spread"):
        ov["pan_spread"] = float(args.pan_spread)
    bass: dict = {}
    if include("bass_style", "--bass-style"):
        bass["style"] = args.bass_style
    if include("bass_step", "--bass-step"):
        bass["step"] = float(args.bass_step)
    if bass:
        ov["bass"] = bass
    perc: dict = {}
    if include("perc_fill_rate", "--perc-fill-rate"):
        perc["fill_rate"] = float(args.perc_fill_rate)
    if getattr(args, "no_perc", False):
        perc["main"] = ""  # explicit silence (gap-analysis I1)
    elif args.perc_main is not None and include("perc_main", "--perc-main"):
        perc["main"] = args.perc_main
    if perc:
        ov["perc"] = perc
    if args.voice_instrument:
        voices: dict = {}
        for vi in args.voice_instrument:
            if "=" in str(vi):
                v, instr = str(vi).split("=", 1)
                voices[v.strip()] = instr.strip()
        if voices:
            ov["voices"] = voices
    return ov


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
                                    chord_fill_rate=args.chord_fill_rate,
                                    static=(args.satb_style == "static"))
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
                   split_stems=args.split_stems,
                   swing=getattr(args, "swing", 0.0),
                   pan_spread=getattr(args, "pan_spread", 0.0))

    program = resolve_instrument(args.instrument)

    voice_programs: dict[str, int] = {}
    for spec in args.voice_instrument:
        if "=" not in spec:
            raise SpecError(
                f"--voice-instrument expects VOICE=NAME, got '{spec}'")
        voice, name = (part.strip() for part in spec.split("=", 1))
        voice = voice.lower()
        if voice not in VOICE_ORDER:
            raise SpecError(
                f"--voice-instrument unknown voice '{voice}'; "
                f"choose from {', '.join(VOICE_ORDER)}")
        if not name:
            raise SpecError(
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
                    help="Name of preset from library/keys_presets.json")
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
        help="Bass line generator: 'follow' (bass tracks the SATB voicing), "
        "'none' (no bass voice at all), or an independent line: root, "
        "octaves, fifths, walking, arp. Requires split stems.")
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
                    choices=["block", "static", "counterpoint", "arpeggio"],
                    default="block",
                    help="Voicing style for SATB harmony: block chords (re-voices "
                    "each hit), static (freezes the voicing across an unchanged "
                    "chord — no wobble), or counterpoint/arpeggio lines.")
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
                    help='Pattern like "qk,eh,esh,er". Pass "" for silence.')
    ap.add_argument("--no-perc",
                    action="store_true",
                    help="Silence percussion entirely (same as --perc-main '').")
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
    ap.add_argument(
        "--swing",
        type=float,
        default=0.0,
        help="0–0.75. Off-beat swing: delays the 'and' of each beat "
             "(0=straight eighths, 0.5=triplet swing). Default=0.0.")
    ap.add_argument(
        "--pan-spread",
        dest="pan_spread",
        type=float,
        default=0.0,
        help="0–1. Stereo width of the SATB voices across the field "
             "(0=centred/mono, 1=widest). Needs split stems. Default=0.0.")

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
    """CLI entry point. Owns only the front-end concerns — parse argv, translate
    a :class:`SpecError` into a clean argparse exit — and delegates the actual
    orchestration to :func:`_run`."""
    ap = build_parser()
    args = ap.parse_args()
    try:
        return _run(ap, args)
    except SpecError as exc:
        ap.error(str(exc))  # standard argparse: usage + message, exit 2


def _run(ap, args):
    start_time = datetime.now()
    music_generator_logger.info("Starting music generation")

    preset_used = None
    if getattr(args, "keys_preset", None):
        presets = load_key_presets()
        preset = presets.get(args.keys_preset)
        if not preset:
            raise SpecError(f"Unknown keys preset '{args.keys_preset}'")
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
        fug_out = resolve_out_path(args.out, "fugue")
        midi, _total = build_fugue_midi(args)
        midi.save(fug_out)
        log_file_operation(music_generator_logger, "write", fug_out, True)
        print(f"Wrote {fug_out}")
        return 0

    # ----- process-music path -----
    if args.process:
        proc_out = resolve_out_path(args.out, f"process_{args.process}")
        midi, _total = build_process_midi(args)
        midi.save(proc_out)
        log_file_operation(music_generator_logger, "write", proc_out, True)
        print(f"Wrote {proc_out}")
        return 0

    # ----- arrangement (song file) path -----
    if args.song:
        import arrangement
        default_slug = Path(args.song).stem
        song_out = resolve_out_path(args.out, default_slug)
        # Only override a song's YAML defaults with a CLI flag the user actually
        # set. Otherwise argparse defaults (--bpm 120, --chord-length e, ...)
        # would silently clobber the authored arrangement — forcing every song
        # to 120 bpm and eighth-note chords. A flag counts as "set" when its
        # value differs from the parser default or it appears in argv (so an
        # explicit value that happens to equal the default still applies).
        argv_tokens = sys.argv[1:]

        def _cli_set(dest: str, *flags: str) -> bool:
            if getattr(args, dest) != ap.get_default(dest):
                return True
            return any(tok == f or tok.startswith(f + "=")
                       for tok in argv_tokens for f in flags)

        arr_overrides = song_overrides_from_args(args, _cli_set)
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

    # music_generator.py is MIDI-only; audio rendering/preview lives in render.py.
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
