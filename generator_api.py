# Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
# https://github.com/galenspikes/music-generator
"""Programmatic API for the music generator — the seam the web UI builds on.

The CLI (`music_generator.main`) drives generation through ``sys.argv`` and writes
files to ``output/``. That's the wrong contract for an interactive app, which
wants to pass a structured spec and get a result *in memory* with metadata it can
render (stems, track info, warnings) — not scrape stdout or read a temp file.

This module is that contract:

    generate(spec)        -> GenerationResult   (midi bytes + tracks + warnings)
    validate(spec)        -> ValidationResult   (does this parse? where's the error?)
    parameter_schema()    -> list[ParamSpec]    (every flag, introspected from argparse)

It is a façade over the existing engine, reusing the shared, disk-free builders
(`build_flat_midi`, `build_generated`) extracted from ``main``. Generation is
serialised by a lock because the engine still keeps process-global state (active
drum map, RNG); each call is ~0.1s so this is fine for a demo. Removing that
global state (true concurrency) is a later, separate step.
"""

from __future__ import annotations

import argparse
import random
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path

import music_generator as mg

_LOCK = threading.Lock()


class GenerationError(RuntimeError):
    """A spec could not be turned into music (bad tokens, bad args, …)."""


@dataclass
class TrackInfo:
    index: int
    name: str | None
    program: int | None
    channel: int | None
    notes: int

    def as_dict(self) -> dict:
        return {
            "index": self.index, "name": self.name, "program": self.program,
            "channel": self.channel, "notes": self.notes,
        }


@dataclass
class GenerationResult:
    midi: bytes
    tracks: list[TrackInfo]
    duration_seconds: float
    mode: str
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "tracks": [t.as_dict() for t in self.tracks],
            "duration_seconds": self.duration_seconds,
            "mode": self.mode,
            "warnings": self.warnings,
        }


@dataclass
class ValidationResult:
    ok: bool
    error: str | None = None

    def as_dict(self) -> dict:
        return {"ok": self.ok, "error": self.error}


# --- spec -> argparse.Namespace ------------------------------------------------

def _action_by_dest() -> dict[str, argparse.Action]:
    return {a.dest: a for a in mg.build_parser()._actions if a.dest != "help"}


def _coerce(action: argparse.Action | None, value):
    """Coerce a JSON-decoded value to what the engine expects for this flag."""
    if action is None or value is None:
        return value
    is_list = action.nargs in ("*", "+") or isinstance(action, argparse._AppendAction)
    if is_list:
        if isinstance(value, (list, tuple)):
            return [str(v) for v in value]
        if isinstance(value, str) and value.strip() == "":
            return []
        return [str(value)]
    if action.type is int:
        return int(value)
    if action.type is float:
        return float(value)
    if action.nargs == 0:  # store_true / store_false → boolean flag
        return bool(value)
    return value


def _namespace_from_spec(spec: dict) -> argparse.Namespace:
    """Start from the parser's full set of defaults, then apply spec overrides.

    Defaults come from the parser itself, so every flag is present and in sync —
    the API never hand-maintains a parallel list.
    """
    args = mg.build_parser().parse_args([])
    actions = _action_by_dest()
    for key, value in (spec or {}).items():
        if not hasattr(args, key):
            continue  # unknown key: ignore rather than 500
        setattr(args, key, _coerce(actions.get(key), value))
    return args


# --- result extraction ---------------------------------------------------------

def _channel_name(channel: int | None) -> str | None:
    if channel is None:
        return None
    if channel == getattr(mg, "DRUM_CH", 9):
        return "drums"
    order = getattr(mg, "VOICE_ORDER", [])
    if 0 <= channel < len(order):
        return order[channel]
    return f"ch{channel}"


def _track_infos(midifile) -> list[TrackInfo]:
    infos: list[TrackInfo] = []
    for i, track in enumerate(midifile.tracks):
        name = program = channel = None
        notes = 0
        for msg in track:
            if msg.type == "track_name":
                name = msg.name
            elif msg.type == "program_change":
                program = msg.program
                if channel is None:
                    channel = msg.channel
            elif msg.type == "note_on" and msg.velocity > 0:
                notes += 1
                if channel is None:
                    channel = msg.channel
        if notes == 0 and program is None and name is None:
            continue  # skip the tempo/meta-only track
        infos.append(TrackInfo(i, name or _channel_name(channel), program,
                               channel, notes))
    # In merged/dense mode the single melodic track sits on channel 0 and would
    # be mislabeled "soprano" — call the lone harmony track "ensemble" instead.
    melodic = [t for t in infos if t.name != "drums"]
    if len(melodic) == 1 and melodic[0].name in getattr(mg, "VOICE_ORDER", []):
        melodic[0].name = "ensemble"
    return infos


# --- the seam ------------------------------------------------------------------

def generate(spec: dict) -> GenerationResult:
    """Turn a spec into music, in memory. Never writes to ``output/``."""
    with _LOCK:
        try:
            return _generate_locked(spec)
        except GenerationError:
            raise
        except SystemExit as exc:  # argparse/engine guard rails
            raise GenerationError(str(exc) or "invalid arguments") from exc
        except Exception as exc:  # surface a readable message to the UI
            raise GenerationError(f"{type(exc).__name__}: {exc}") from exc


def _generate_locked(spec: dict) -> GenerationResult:
    args = _namespace_from_spec(spec)

    if getattr(args, "keys_preset", None):
        presets = mg.load_key_presets()
        preset = presets.get(args.keys_preset)
        if not preset:
            raise GenerationError(f"Unknown keys preset '{args.keys_preset}'")
        args.keys = ",".join(preset)

    mg.set_active_drum_map(args.perc_lib if args.perc_lib else None)
    mg.apply_arg_normalization(args)
    if args.seed is not None:
        random.seed(args.seed)

    # ----- fugue -----
    if args.fugue:
        import fugue as fug
        subject = fug.DEFAULT_SUBJECT if args.fugue == "__default__" else args.fugue
        key_pc = mg.parse_key_name(args.melody_key)[0] if args.melody_key else 0
        events, total = fug.build_fugue(
            subject, key_pc, args.melody_mode or "major",
            countersubject=args.fugue_countersubject)
        midi = mg.build_generated(args.bpm, events, total, args.instrument,
                                  args.velocity_mode_chords,
                                  args.velocity_mode_drums)
        return _result(midi, total, "fugue")

    # ----- process music -----
    if args.process:
        import process as proc
        cell = args.process_cell or proc.DEFAULT_CELL
        key_pc = mg.parse_key_name(args.melody_key)[0] if args.melody_key else 0
        events, total = proc.build_process(
            cell, key_pc, args.melody_mode or "major", kind=args.process,
            reps=args.process_reps, stages=args.process_stages)
        midi = mg.build_generated(args.bpm, events, total, args.instrument,
                                  args.velocity_mode_chords,
                                  args.velocity_mode_drums)
        return _result(midi, total, f"process:{args.process}")

    # ----- arrangement (YAML song): renders to disk; round-trip a temp file -----
    if args.song:
        import tempfile
        import arrangement
        song_spec = arrangement.load_spec(
            args.song, vel_mode_chords=args.velocity_mode_chords,
            vel_mode_drums=args.velocity_mode_drums)
        with tempfile.TemporaryDirectory(prefix="mg_song_") as tmp:
            out = str(Path(tmp) / "song.mid")
            arrangement.render(song_spec, out)
            data = Path(out).read_bytes()
        import mido
        mid = mido.MidiFile(file=__import__("io").BytesIO(data))
        return GenerationResult(data, _track_infos(mid), float(mid.length),
                                "song")

    # ----- flat (ostinato / mixed / complete) -----
    midi, _meta = mg.build_flat_midi(args)
    return _result(midi, float(args.seconds), args.mode)


def _result(midi, duration: float, mode: str) -> GenerationResult:
    return GenerationResult(
        midi=midi.to_bytes(),
        tracks=_track_infos(midi.mid),
        duration_seconds=duration,
        mode=mode,
    )


# --- chord-token parsing (powers the harmony editor's chip strip + errors) -----

# Pitch-class → note name, flats (matches the engine's sharp→flat normalization).
_PCN = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]


def _split_top_level(s: str) -> list[tuple[str, int]]:
    """Comma-split, respecting [...] groups. Returns (token, start_offset)."""
    parts: list[tuple[str, int]] = []
    depth = 0
    cur = ""
    start = 0
    for i, ch in enumerate(s):
        if ch == "[":
            depth += 1; cur += ch
        elif ch == "]":
            depth -= 1; cur += ch
        elif ch == "," and depth == 0:
            parts.append((cur, start)); cur = ""; start = i + 1
        else:
            if cur == "":
                start = i
            cur += ch
    parts.append((cur, start))
    return parts


def _describe_token(tok: str) -> dict:
    """Structured description of a single chord token (strips a trailing *N)."""
    t = tok.strip()
    m = re.search(r"\*(\d+)\s*$", t)
    if m:
        t = t[:m.start()].strip()
    if ":" not in t:  # bare root — quality comes from --chords families
        pc, is_minor = mg.parse_key_name(t)
        return {
            "token": t, "label": _PCN[pc] + ("m" if is_minor else ""),
            "root": _PCN[pc], "recipe": "min" if is_minor else None,
            "inversion": None, "bass": None, "notes": [], "bare": True,
        }
    cd = mg.parse_colon_key_token(t)
    base, slash = (t.rsplit("/", 1) + [None])[:2] if "/" in t else (t, None)
    seg = [p.strip() for p in base.split(":")]
    root_part = seg[0]
    inv = seg[1] if len(seg) > 1 and seg[1] else None
    rec = seg[2] if len(seg) > 2 and seg[2] else None
    root_pc, is_minor = mg.parse_key_name(root_part)
    recipe_name = rec or ("min" if is_minor else "maj")
    bass_name = _PCN[cd.bass_pc] if cd and cd.bass_pc is not None else None
    label = _PCN[root_pc] + recipe_name + (f"/{bass_name}" if bass_name else "")
    return {
        "token": t, "label": label, "root": _PCN[root_pc],
        "recipe": recipe_name, "inversion": int(inv) if inv else None,
        "bass": bass_name, "notes": [_PCN[p] for p in (cd.pcs if cd else ())],
        "bare": False,
    }


def _segment_keys(keys: str) -> list[dict]:
    """Top-level structure of a chart: each entry is a single chord or a
    ``[...]`` group, with its repeat count. Lets the UI show a long, repetitive
    chart compactly (e.g. ``[A G]×16`` instead of 32 chips) instead of the full
    flat expansion."""
    segs: list[dict] = []
    for tok, _off in _split_top_level(keys):
        t = tok.strip()
        if not t:
            continue
        reps = 1
        body = t
        m = re.search(r"\*(\d+)\s*$", t)
        if m:
            reps = int(m.group(1))
            body = t[:m.start()].strip()
        if body.startswith("[") and body.endswith("]"):
            inner = [x.strip() for x in body[1:-1].split(",") if x.strip()]
            segs.append({
                "type": "group", "reps": reps,
                "chords": [_describe_token(x) for x in inner],
            })
        else:
            d = _describe_token(body)
            d.update({"type": "chord", "reps": reps})
            segs.append(d)
    return segs


def parse_keys(keys: str, mode: str = "ostinato") -> dict:
    """Parse a --keys chart into structured chords for the editor.

    Returns ``{ok, chords, segments, total, error, error_index, error_span}``.
    ``chords`` is the fully expanded progression (after ``*N`` / ``[...]``);
    ``segments`` is the top-level structure (chords + groups with repeat counts)
    so the UI can render long, repetitive charts compactly. ``total`` is the
    expanded chord count. On error, ``error_index``/``error_span`` point at the
    offending top-level token.
    """
    keys = keys or ""
    try:
        expanded = mg.key_roots(mode, keys)
        chords = [_describe_token(t) for t in expanded]
        return {"ok": True, "chords": chords, "segments": _segment_keys(keys),
                "total": len(chords), "error": None}
    except Exception as exc:
        # Find which top-level token is to blame (best effort) for inline marking.
        err_index = err_span = None
        for idx, (tok, off) in enumerate(_split_top_level(keys)):
            if not tok.strip():
                continue
            try:
                mg.key_roots(mode, tok)
            except Exception:
                err_index = idx
                err_span = [off, off + len(tok)]
                break
        return {"ok": False, "chords": [], "segments": [], "total": 0,
                "error": str(exc), "error_index": err_index,
                "error_span": err_span}


# --- percussion / interrupter parsing (powers the perc editors' chip strips) --

def _drum_note_labels() -> dict:
    """note-number → friendly label, from the percussion library."""
    import json
    try:
        lib = json.loads(
            (REPO_ROOT / "library" / "percussion_library.json").read_text())
        out = {}
        for info in (lib.get("drum_map") or {}).values():
            if isinstance(info, dict) and "note" in info:
                out[info["note"]] = info.get("label", str(info["note"]))
        return out
    except Exception:
        return {}


# REPO_ROOT for the library path (generator_api lives at the repo root).
REPO_ROOT = Path(__file__).resolve().parent


def _describe_drum_token(tok: str, drum_map, note_labels: dict) -> dict:
    try:
        beats, hits = mg.parse_single_token(tok, drum_map)
        return {
            "token": tok, "ok": True, "dur": tok.strip()[0].lower(),
            "beats": beats, "rest": len(hits) == 0,
            "hits": [note_labels.get(h.note, f"n{h.note}") for h in hits],
        }
    except Exception as exc:
        return {"token": tok, "ok": False, "error": str(exc)}


def _describe_chord_interrupt_token(tok: str) -> dict:
    t = tok.strip()
    ln = t[:1].lower()
    if ln not in mg.DUR_MAP:
        return {"token": tok, "ok": False, "error": f"Bad duration in '{tok}'"}
    flag = t[1:].strip().lower()
    if flag not in ("c", "r"):
        return {"token": tok, "ok": False,
                "error": f"Must end with c (chord) or r (rest): '{tok}'"}
    return {"token": tok, "ok": True, "dur": ln, "beats": mg.DUR_MAP[ln],
            "rest": flag == "r", "hits": [] if flag == "r" else ["chord"]}


def parse_perc(pattern: str, kind: str = "drums") -> dict:
    """Parse a percussion / interrupter motif into per-token structured info.

    ``kind='drums'`` uses the active drum map (perc_main / perc_interrupters);
    ``kind='chord'`` is the chord-interrupter grammar (``c``=play chord, ``r``=rest).
    Returns ``{ok, tokens:[{token, dur, beats, rest, hits, ok, error?}], error}``.
    """
    pattern = pattern or ""
    note_labels = _drum_note_labels() if kind == "drums" else {}
    drum_map = mg.get_drum_map() if kind == "drums" else None
    tokens, first_err = [], None
    # Split on commas but not inside [...] modifier blocks (e.g. qk[vel+10,prob0.5]).
    for raw, _off in _split_top_level(pattern):
        tok = raw.strip()
        if not tok:
            continue
        d = (_describe_chord_interrupt_token(tok) if kind == "chord"
             else _describe_drum_token(tok, drum_map, note_labels))
        tokens.append(d)
        if not d["ok"] and first_err is None:
            first_err = d["error"]
    return {"ok": first_err is None, "tokens": tokens, "error": first_err}


def validate(spec: dict) -> ValidationResult:
    """Cheap check: can this spec be generated? Returns the failure message if
    not, so the editor can show inline feedback instead of a dead player."""
    try:
        generate(spec)
        return ValidationResult(ok=True)
    except GenerationError as exc:
        return ValidationResult(ok=False, error=str(exc))


# --- schema (introspected, never hand-mirrored) --------------------------------

def parameter_schema() -> list[dict]:
    """Every CLI parameter as a UI-renderable spec, derived from build_parser.

    Annotations (group + control hint + range) live in PARAM_ANNOTATIONS; any
    flag not annotated still appears (group 'More', inferred control), so the
    UI can never silently omit a parameter.
    """
    defaults = vars(mg.build_parser().parse_args([]))
    out: list[dict] = []
    seen: set[str] = set()
    for action in mg.build_parser()._actions:
        dest = action.dest
        if dest in ("help",) or dest in seen:
            continue
        seen.add(dest)
        out.append(_param_spec(action, defaults.get(dest)))
    return out


def _param_spec(action: argparse.Action, default) -> dict:
    dest = action.dest
    ann = PARAM_ANNOTATIONS.get(dest, {})
    choices = list(action.choices) if action.choices else None
    is_list = action.nargs in ("*", "+") or isinstance(action, argparse._AppendAction)
    if action.nargs == 0:
        kind = "bool"
    elif choices and is_list:
        kind = "multichoice"
    elif choices:
        kind = "choice"
    elif action.type is int:
        kind = "int"
    elif action.type is float:
        kind = "float"
    elif is_list:
        kind = "list"
    else:
        kind = "str"
    spec = {
        "name": dest,
        "flag": (action.option_strings or [dest])[-1],
        "kind": kind,
        "choices": choices,
        "default": default,
        "help": (action.help or "").strip(),
        "group": ann.get("group", "More"),
        "control": ann.get("control", _default_control(kind, choices)),
    }
    for opt in ("min", "max", "step", "multiline"):
        if opt in ann:
            spec[opt] = ann[opt]
    return spec


def _default_control(kind: str, choices) -> str:
    if kind == "bool":
        return "toggle"
    if kind == "multichoice":
        return "chips"
    if kind == "choice":
        return "segmented" if choices and len(choices) <= 4 else "dropdown"
    if kind == "int":
        return "slider"
    if kind == "float":
        return "knob"
    if kind == "list":
        return "taglist"
    return "text"


# Presentation metadata: which rack panel a flag lives in, its control, ranges.
# Completeness is guaranteed by parameter_schema's catch-all, so this only needs
# to grow when we want nicer placement — never to keep the UI in sync.
PARAM_ANNOTATIONS: dict[str, dict] = {
    # Engine / mode
    "mode": {"group": "Engine", "control": "segmented", "help": "Render style: ostinato (loop chords), mixed (full arrangement), complete (solo + full), fugue (subject+voices), process (generative cell)"},
    "seconds": {"group": "Engine", "control": "slider", "min": 4, "max": 600, "step": 2, "help": "Duration in seconds"},
    "bpm": {"group": "Engine", "control": "slider", "min": 40, "max": 300, "step": 1, "help": "Tempo in beats per minute"},
    "seed": {"group": "Engine", "control": "int", "min": 0, "max": 999999, "help": "Random seed for reproducible generation (leave blank for new each time)"},
    "chord_len": {"group": "Engine", "control": "segmented", "help": "How long each chord sounds (quarter, eighth, etc.)"},
    # Harmony
    "keys": {"group": "Harmony", "control": "text", "multiline": True, "help": "Chord sequence (e.g., C::maj7, A::min9, G::13). Use colon notation: root::recipe or root:inversion:recipe. Group with [A,G]*16."},
    "keys_preset": {"group": "Harmony", "control": "text", "help": "Named chord progression (optional; overrides keys if set)"},
    "chords": {"group": "Harmony", "control": "chips", "help": "Chord quality families to use (maj, min, sus, extended, etc.)"},
    "chords_order": {"group": "Harmony", "control": "segmented", "help": "How to pick chords: chromatic (nearby), random, roundrobin"},
    "chord_interrupters": {"group": "Harmony", "control": "taglist", "help": "Fill motifs: replace the main loop occasionally for variation (e.g., ec, er, sc)"},
    "chord_fill_rate": {"group": "Harmony", "control": "knob", "min": 0, "max": 1, "step": 0.01, "help": "How often fills trigger (0=never, 1=every beat)"},
    # Voicing
    "voicing": {"group": "Voicing", "control": "segmented", "help": "How to voice chords: satb (4-part), dense (all-in-one), or complete (full orchestration)"},
    "satb_style": {"group": "Voicing", "control": "segmented", "help": "Voice leading: block (jump to nearest), smooth (minimize motion), or counterpoint (voice-independent)"},
    "instrument": {"group": "Voicing", "control": "text", "help": "Main instrument (piano, organ, vibraphone, etc.)"},
    "voice_instrument": {"group": "Voicing", "control": "taglist", "help": "Per-voice instrument overrides (e.g., soprano=trumpet)"},
    "counterpoint_step": {"group": "Voicing", "control": "knob", "min": 0.1, "max": 2, "step": 0.05, "help": "Interval step size for independent voice motion (in semitones)"},
    "counterpoint_suspension_prob": {"group": "Voicing", "control": "knob", "min": 0, "max": 1, "step": 0.01, "help": "Probability of suspensions (4→3 dissonance) in counterpoint"},
    "counterpoint_anticipation_prob": {"group": "Voicing", "control": "knob", "min": 0, "max": 1, "step": 0.01, "help": "Probability of anticipations (early note entry) in counterpoint"},
    # Bass
    "bass_style": {"group": "Bass", "control": "dropdown", "help": "Bass pattern: root (chord root), walking (stepwise), or arpeggiated"},
    "bass_step": {"group": "Bass", "control": "knob", "min": 0.125, "max": 2, "step": 0.125, "help": "Duration of each bass note (in beats)"},
    # Melody
    "melody": {"group": "Melody", "control": "text", "multiline": True, "help": "Melody pattern using pitch letters (c d e f g a b) or durations (e, s, q, w)"},
    "melody_relative": {"group": "Melody", "control": "segmented", "help": "Is melody relative to chord tones or absolute pitches?"},
    "melody_octave": {"group": "Melody", "control": "slider", "min": 2, "max": 8, "step": 1, "help": "Starting octave for the melody (2=low, 8=high)"},
    "melody_transform": {"group": "Melody", "control": "segmented", "help": "Apply transformation: invert, retrograde, or augment the melody"},
    "melody_key": {"group": "Melody", "control": "text", "help": "Root key for melody (default: song key)"},
    "melody_mode": {"group": "Melody", "control": "text", "help": "Scale mode (major, minor, dorian, etc.)"},
    # Percussion
    "perc_main": {"group": "Percussion", "control": "text", "multiline": True, "help": "Main drum pattern (e.g., qb, eg, qc, eg). Use grid mode for visual step sequencing."},
    "perc_interrupters": {"group": "Percussion", "control": "taglist", "help": "Fill patterns: randomly replace main pattern with these (e.g., sh,er,skh)"},
    "perc_stages": {"group": "Percussion", "control": "taglist", "help": "Timed drum sections: 'beats:pattern' (e.g., 32:qb,eg,qc,eg)"},
    "perc_fill_rate": {"group": "Percussion", "control": "knob", "min": 0, "max": 1, "step": 0.01, "help": "How often fills trigger (0=never, 1=every beat)"},
    "perc_fill_curve": {"group": "Percussion", "control": "text", "help": "Ramp fill rate across stages: 'start:end' (e.g., 0:0.8 = get busier)"},
    "perc_lib": {"group": "Percussion", "control": "text", "help": "Path to percussion library JSON (auto-filled with default)"},
    "perc_main_key": {"group": "Percussion", "control": "text", "help": "Use preset groove from library instead of custom pattern"},
    "perc_intr_keys": {"group": "Percussion", "control": "taglist", "help": "Borrow fills from preset grooves (checkboxes or comma-separated names)"},
    # Dynamics
    "velocity_mode_chords": {"group": "Dynamics", "control": "segmented", "help": "How to vary chord velocities: uniform, random, or human-like"},
    "velocity_mode_drums": {"group": "Dynamics", "control": "segmented", "help": "How to vary drum velocities: uniform, random, or human-like"},
    # Process / fugue
    "process": {"group": "Process", "control": "segmented", "help": "Generative algorithm: phase (rotational), additive (layering), or segment (cells)"},
    "process_cell": {"group": "Process", "control": "text", "multiline": True, "help": "Seed cell for process (e.g., e1 e2 e3 e5 e7 e5 e3 e2)"},
    "process_reps": {"group": "Process", "control": "slider", "min": 1, "max": 16, "step": 1, "help": "How many times to repeat the cell"},
    "process_stages": {"group": "Process", "control": "slider", "min": 1, "max": 16, "step": 1, "help": "Number of transformations or stages"},
    "fugue": {"group": "Process", "control": "text", "help": "Fugue subject or '__default__' for a generated one"},
    "fugue_countersubject": {"group": "Process", "control": "text", "help": "Fugue countersubject (optional; leaves blank for auto-generate)"},
    # Render / audio (FluidSynth — used by the Phase-2 audio path)
    "sf2": {"group": "Render", "control": "text", "help": "Path to SoundFont file for audio rendering (.sf2)"},
    "gain": {"group": "Render", "control": "knob", "min": 0, "max": 1, "step": 0.01, "help": "Master volume (0=silent, 1=max)"},
    "reverb": {"group": "Render", "control": "toggle", "help": "Apply reverb effect to audio output"},
    "chorus": {"group": "Render", "control": "toggle", "help": "Apply chorus effect to audio output"},
    "poly": {"group": "Render", "control": "slider", "min": 16, "max": 512, "step": 16, "help": "Maximum simultaneous note voices"},
    "split_stems": {"group": "Render", "control": "toggle", "help": "Render each voice as a separate audio file"},
    "song": {"group": "Render", "control": "text", "help": "YAML song file to render (instead of generating from above)"},
    "out": {"group": "Render", "control": "text", "help": "Output filename slug (without extension)"},
    "no_play": {"group": "Render", "control": "toggle", "help": "Skip auto-playback after generation"},
}
