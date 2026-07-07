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
import io
import random
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path

import mido
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
    envelope: list[float] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "tracks": [t.as_dict() for t in self.tracks],
            "duration_seconds": self.duration_seconds,
            "mode": self.mode,
            "warnings": self.warnings,
            "envelope": self.envelope,
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


def envelope_from_bytes(data: bytes, duration: float, buckets: int = 60) -> list[float]:
    """A coarse, time-bucketed note-density envelope (0..1 per bucket) for a
    lightweight "waveform" visual in the webapp (webapp-ui-design.md's
    waveform display, still missing as of ui-ux-roadmap.md Thread C).

    Computed here via ``mido``'s tempo-aware absolute timing (iterating a
    ``MidiFile`` merges tracks and converts tick deltas to seconds using the
    tempo map) rather than re-parsed client-side — MIDI tick/tempo math is
    easy to get subtly wrong in a hand-rolled parser, and this project
    already trusts mido elsewhere (tests, MidiOut).
    """
    if duration <= 0 or buckets <= 0:
        return [0.0] * max(buckets, 0)
    mid = mido.MidiFile(file=io.BytesIO(data))
    counts = [0.0] * buckets
    t = 0.0
    for msg in mid:
        t += msg.time
        if msg.type == "note_on" and msg.velocity > 0:
            idx = min(buckets - 1, max(0, int((t / duration) * buckets)))
            counts[idx] += msg.velocity
    peak = max(counts) or 1.0
    return [round(c / peak, 3) for c in counts]


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
    # Raw song YAML text (e.g. from the lead-sheet importer) — an alternative
    # to args.song's file path so the webapp never has to write the imported
    # song anywhere durable. Not an argparse flag, so pulled from the raw
    # spec dict directly rather than through _namespace_from_spec.
    song_yaml_text = spec.get("song_yaml")
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
                                  args.velocity_mode_drums,
                                  swing=getattr(args, "swing", 0.0),
                                  pan_spread=getattr(args, "pan_spread", 0.0))
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
                                  args.velocity_mode_drums,
                                  swing=getattr(args, "swing", 0.0),
                                  pan_spread=getattr(args, "pan_spread", 0.0))
        return _result(midi, total, f"process:{args.process}")

    # ----- arrangement (YAML song): renders to disk; round-trip a temp file -----
    if args.song or song_yaml_text:
        import tempfile
        import arrangement

        # Forward UI params as overrides so changes (bpm, instrument, etc.) take
        # effect.  Params load_song() doesn't extract (chords, chords_order) keep
        # the arrangement YAML's own defaults.
        arr_overrides: dict = {
            "tempo": args.bpm,
            "instrument": args.instrument,
            "chord_length": args.chord_len,
            "satb": args.satb_style,
            "bass": {"style": args.bass_style, "step": float(args.bass_step)},
            "perc": {"fill_rate": float(args.perc_fill_rate)},
            "swing": float(getattr(args, "swing", 0.0)),
            "pan_spread": float(getattr(args, "pan_spread", 0.0)),
        }
        if getattr(args, "no_perc", False):
            arr_overrides["perc"]["main"] = ""  # explicit silence (gap-analysis I1)
        elif args.perc_main is not None:
            arr_overrides["perc"]["main"] = args.perc_main
        if args.voice_instrument:
            voices: dict = {}
            for vi in args.voice_instrument:
                if "=" in str(vi):
                    v, instr = str(vi).split("=", 1)
                    voices[v.strip()] = instr.strip()
            if voices:
                arr_overrides["voices"] = voices

        with tempfile.TemporaryDirectory(prefix="mg_song_") as tmp:
            song_path = args.song
            if song_yaml_text:
                song_path = str(Path(tmp) / "uploaded_song.yml")
                Path(song_path).write_text(song_yaml_text, encoding="utf-8")
            song_spec = arrangement.load_spec(
                song_path, vel_mode_chords=args.velocity_mode_chords,
                vel_mode_drums=args.velocity_mode_drums,
                overrides=arr_overrides)
            out = str(Path(tmp) / "song.mid")
            arrangement.render(song_spec, out)
            data = Path(out).read_bytes()
        mid = mido.MidiFile(file=io.BytesIO(data))
        duration = float(mid.length)
        return GenerationResult(data, _track_infos(mid), duration, "song",
                                envelope=envelope_from_bytes(data, duration))

    # ----- flat (ostinato / mixed / complete) -----
    midi, _meta = mg.build_flat_midi(args)
    return _result(midi, float(args.seconds), args.mode)


def _result(midi, duration: float, mode: str) -> GenerationResult:
    data = midi.to_bytes()
    return GenerationResult(
        midi=data,
        tracks=_track_infos(midi.mid),
        duration_seconds=duration,
        mode=mode,
        envelope=envelope_from_bytes(data, duration),
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
            depth += 1
            cur += ch
        elif ch == "]":
            depth -= 1
            cur += ch
        elif ch == "," and depth == 0:
            parts.append((cur, start))
            cur = ""
            start = i + 1
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
            "root_pc": pc, "pcs": [], "bass_pc": None,
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
        "root_pc": root_pc, "pcs": list(cd.pcs) if cd else [],
        "bass_pc": cd.bass_pc if cd else None,
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
    """Every controllable CLI parameter as a UI-renderable spec, derived from
    build_parser.

    Annotations (group + control hint + range) live in PARAM_ANNOTATIONS; any
    flag not annotated still appears (group 'More', inferred control), so the
    UI can never silently omit a real instrument control. HIDDEN_PARAMS is the
    one deliberate exception: baggage (mode, the parked process/fugue group,
    CLI/render plumbing) that the controllability audit flagged for removal
    from the surface. Those flags stay fully functional on the CLI and in song
    YAML — they're just not rendered as rack controls. See
    docs/design-notes/controllability-audit.md.
    """
    defaults = vars(mg.build_parser().parse_args([]))
    out: list[dict] = []
    seen: set[str] = set()
    for action in mg.build_parser()._actions:
        dest = action.dest
        if dest in ("help",) or dest in seen or dest in HIDDEN_PARAMS:
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
        # A UI-facing "why you'd use it" tooltip can override the terser CLI
        # help via PARAM_ANNOTATIONS["…"]["help"]; otherwise fall back to the
        # argparse help so every control still gets *some* explanation.
        "help": (ann.get("help") or action.help or "").strip(),
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


# Baggage cut from the webapp control surface (controllability-audit.md): the
# parked mode switch and process/fugue group, plus CLI/render plumbing that
# isn't an instrument control. The underlying flags still work on the CLI and
# in song YAML — see parameter_schema()'s docstring.
HIDDEN_PARAMS: set[str] = {
    "mode",
    "process", "process_cell", "process_reps", "process_stages",
    "fugue", "fugue_countersubject",
    "out", "no_play", "song", "sf2", "perc_lib",
}

# Presentation metadata: which rack panel a flag lives in, its control, ranges.
# Completeness is guaranteed by parameter_schema's catch-all, so this only needs
# to grow when we want nicer placement — never to keep the UI in sync.
PARAM_ANNOTATIONS: dict[str, dict] = {
    # Engine
    "seconds": {"group": "Engine", "control": "slider", "min": 4, "max": 600, "step": 2,
                "help": "How long the piece runs, in seconds. (Songs use their "
                        "own per-section lengths, so this is ignored for them.)"},
    "bpm": {"group": "Engine", "control": "slider", "min": 40, "max": 300, "step": 1,
            "help": "Tempo, in beats per minute — higher is faster."},
    "seed": {"group": "Engine", "control": "int", "min": 0, "max": 999999,
             "help": "The random seed. Same seed + same settings replays the "
                     "exact same music; change it (or hit ⚄ new take) for a "
                     "fresh variation."},
    "chord_len": {"group": "Engine", "control": "segmented",
                  "help": "How long each chord rings before the next: q=quarter, "
                          "e=eighth, s=sixteenth, h=half. Shorter = busier."},
    # Harmony
    "keys": {"group": "Harmony", "control": "text", "multiline": True,
             "help": "The chord progression, in the token grammar (e.g. "
                     "'C::maj7, A::min9, D::min7, G::13'). The heart of the patch."},
    "keys_preset": {"group": "Harmony", "control": "text"},
    "chords": {"group": "Harmony", "control": "chips",
               "help": "When no explicit keys are given, the chord families the "
                       "generator draws from (triads, sevenths, quartal, …)."},
    "chords_order": {"group": "Harmony", "control": "segmented",
                     "help": "With several chord families on, how the next chord "
                             "is chosen: random, or round-robin (cycles through "
                             "them in turn)."},
    "chord_interrupters": {"group": "Harmony", "control": "taglist"},
    "chord_fill_rate": {"group": "Harmony", "control": "knob", "min": 0, "max": 1, "step": 0.01,
                        "help": "0 = every chord plays straight; higher = chord "
                                "'interrupter' motifs break up the changes more often."},
    # Voicing
    "voicing": {"group": "Voicing", "control": "segmented",
                "help": "SATB = clean 4-voice harmony. Dense = sounds every chord "
                        "tone across the register (lush 11ths/13ths, clusters) on "
                        "one timbre — richer and more complex."},
    "satb_style": {"group": "Voicing", "control": "segmented",
                   "help": "Block = re-voice a fresh chord each hit. Static = "
                           "hold one voicing (no wobble). Counterpoint / arpeggio "
                           "= flowing, independent melodic lines."},
    "instrument": {"group": "Voicing", "control": "text",
                   "help": "The sound for the harmony — a name alias like 'epiano' "
                           "or 'strings', or a raw GM program number 0–127."},
    "voice_instrument": {"group": "Voicing", "control": "taglist"},
    "counterpoint_step": {"group": "Voicing", "control": "knob", "min": 0.1, "max": 2, "step": 0.05,
                          "help": "How fast counterpoint lines move, in beats per "
                                  "note — lower is faster and busier. "
                                  "(Counterpoint style only.)"},
    "counterpoint_suspension_prob": {"group": "Voicing", "control": "knob", "min": 0, "max": 1, "step": 0.01,
                                     "help": "Chance a voice holds its note through "
                                             "a chord change (a suspension) for "
                                             "tension. 0 = never, 1 = always."},
    "counterpoint_anticipation_prob": {"group": "Voicing", "control": "knob", "min": 0, "max": 1, "step": 0.01,
                                       "help": "Chance a voice moves early into the "
                                               "next chord (an anticipation). "
                                               "0 = never, 1 = always."},
    # Bass
    "bass_style": {"group": "Bass", "control": "dropdown",
                   "help": "How the bass line is built: 'follow' tracks the "
                           "harmony, or pick an independent line (root, octaves, "
                           "fifths, walking, arp). 'none' drops the bass entirely."},
    "bass_step": {"group": "Bass", "control": "knob", "min": 0.125, "max": 2, "step": 0.125,
                  "help": "Bass note speed, in beats: 0.5 = eighths, 1 = quarters. "
                          "(Ignored when bass style is 'follow'.)"},
    # Melody
    "melody": {"group": "Melody", "control": "text", "multiline": True,
               "help": "A hand-written top line in scale degrees (e.g. "
                       "'q1 q3 q5 h1'); loops to fill the piece, key inferred "
                       "from the chords. Leave empty for no lead."},
    "melody_relative": {"group": "Melody", "control": "segmented",
                        "help": "Degrees resolve against the section key, or "
                                "anchor to each chord's root so the motif refits "
                                "every chord."},
    "melody_octave": {"group": "Melody", "control": "slider", "min": 2, "max": 8, "step": 1,
                      "help": "Which octave the melody sits in — higher is brighter."},
    "melody_transform": {"group": "Melody", "control": "segmented",
                         "help": "Apply a classic transform to the line: invert "
                                 "(flip up/down), retrograde (reverse), or augment "
                                 "(stretch)."},
    "melody_key": {"group": "Melody", "control": "text"},
    "melody_mode": {"group": "Melody", "control": "text"},
    # Percussion
    "perc_main": {"group": "Percussion", "control": "text", "multiline": True,
                  "help": "The main drum loop, as tokens (e.g. 'qk, eh, qc, eh'). "
                          "Leave empty for no drums."},
    "perc_interrupters": {"group": "Percussion", "control": "taglist",
                          "help": "Fill motifs that occasionally break up the main "
                                  "loop; how often is set by perc fill rate."},
    "perc_stages": {"group": "Percussion", "control": "taglist"},
    "perc_fill_rate": {"group": "Percussion", "control": "knob", "min": 0, "max": 1, "step": 0.01,
                       "help": "0 = a locked, repeating groove; higher = drums swap "
                               "in fill motifs more often. 1 = constantly changing."},
    "perc_fill_curve": {"group": "Percussion", "control": "text"},
    "perc_main_key": {"group": "Percussion", "control": "text",
                      "help": "Pick a named groove from the percussion library "
                              "instead of typing a pattern."},
    "perc_intr_keys": {"group": "Percussion", "control": "taglist"},
    # Dynamics
    "velocity_mode_chords": {"group": "Dynamics", "control": "segmented",
                             "help": "How hard chords are struck: uniform (even), "
                                     "random, or human (subtle natural variation)."},
    "velocity_mode_drums": {"group": "Dynamics", "control": "segmented",
                            "help": "How hard drums are struck: uniform (even), "
                                    "random, or human (subtle natural variation)."},
    "swing": {"group": "Dynamics", "control": "knob", "min": 0, "max": 0.75, "step": 0.01,
              "help": "Delays each off-beat for a swung feel. 0 = straight "
                      "eighths, 0.5 = triplet swing."},
    "pan_spread": {"group": "Dynamics", "control": "knob", "min": 0, "max": 1, "step": 0.01,
                   "help": "Spreads the voices across the stereo field. "
                           "0 = centered, 1 = wide."},
    # Render
    "split_stems": {"group": "Render", "control": "toggle",
                    "help": "On = each voice on its own MIDI track/channel (needed "
                            "for per-voice instruments & independent bass). "
                            "Off = merge into one track."},
}


# --- songs and presets -------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent
SONGS_DIR = REPO_ROOT / "songs"
PRESETS_DIR = REPO_ROOT / "presets" / "user"

_SLUG_UNSAFE_RE = re.compile(r"[^a-z0-9_-]+")
_SLUG_DASH_RUN_RE = re.compile(r"-{2,}")


def slugify(name: str) -> str:
    """Turn arbitrary text into a filesystem-safe identifier: lowercase,
    ``[a-z0-9_-]+``, no leading/trailing hyphens or repeated hyphens.

    Every preset/song name that reaches the filesystem goes through this —
    it's the only thing standing between a name coming from an HTTP path
    parameter and a path-traversal write (``../../etc/passwd``), since a raw
    ``PRESETS_DIR / f"{name}.json"`` does not resolve or reject ``..``
    segments. Underscores are kept literal (not folded to ``-``) so this is
    idempotent for existing ``songs/*.yml`` filenames like
    ``four_organs`` / ``girl_from_ipanema`` — a raw name already in that form
    round-trips unchanged, so it's safe to apply on every read as well as
    every write.
    """
    slug = _SLUG_UNSAFE_RE.sub("-", name.strip().lower())
    slug = _SLUG_DASH_RUN_RE.sub("-", slug).strip("-")
    return slug or "untitled"


def _safe_path_for(directory: Path, name: str, suffix: str) -> Path:
    """Slugify ``name`` and join it to ``directory``, then verify the result
    can't have escaped (defense in depth on top of slugify's character
    restriction)."""
    path = directory / f"{slugify(name)}{suffix}"
    if path.resolve().parent != directory.resolve():
        raise GenerationError(f"Invalid name '{name}'")
    return path


def list_songs() -> list[dict]:
    """List all available songs (from songs/*.yml)."""
    songs = []
    if SONGS_DIR.exists():
        for yml in sorted(SONGS_DIR.glob("*.yml")):
            try:
                content = yml.read_text()
                lines = content.split("\n")
                title = yml.stem
                description = ""
                for line in lines[:12]:
                    if line.startswith("title:"):
                        title = line.split(":", 1)[1].strip()
                    elif line.startswith("description:"):
                        description = line.split(":", 1)[1].strip()
                songs.append({"name": yml.stem, "title": title, "description": description})
            except Exception:
                songs.append({"name": yml.stem, "title": yml.stem, "description": ""})
    return songs


def load_song(name: str) -> dict:
    """Load a song YAML and return all params (defaults + derived)."""
    import yaml

    song_path = _safe_path_for(SONGS_DIR, name, ".yml")
    if not song_path.exists():
        raise GenerationError(f"Song '{name}' not found")

    try:
        song_data = yaml.safe_load(song_path.read_text())
    except Exception as e:
        raise GenerationError(f"Failed to parse song '{name}': {e}")

    spec = {"song": str(song_path)}

    # Extract top-level song properties
    if "tempo" in song_data:
        spec["bpm"] = song_data["tempo"]
    if "soundfont" in song_data:
        spec["sf2"] = song_data["soundfont"]

    # Extract defaults section
    defaults = song_data.get("defaults", {})
    if "instrument" in defaults:
        spec["instrument"] = defaults["instrument"]
    if "voices" in defaults:
        voices = defaults["voices"]
        if voices:
            voice_instrument = []
            for voice, instr in voices.items():
                voice_instrument.append(f"{voice}={instr}")
            spec["voice_instrument"] = voice_instrument

    bass_cfg = defaults.get("bass", {})
    if isinstance(bass_cfg, dict):
        if "style" in bass_cfg:
            spec["bass_style"] = bass_cfg["style"]
        if "step" in bass_cfg:
            spec["bass_step"] = bass_cfg["step"]

    if "satb" in defaults:
        spec["satb_style"] = defaults["satb"]
    if "chord_length" in defaults:
        spec["chord_len"] = defaults["chord_length"]

    perc_cfg = defaults.get("perc", {})
    if isinstance(perc_cfg, dict):
        if "main" in perc_cfg:
            spec["perc_main"] = perc_cfg["main"]
        if "interrupters" in perc_cfg:
            spec["perc_interrupters"] = perc_cfg["interrupters"]
        if "fill_rate" in perc_cfg:
            spec["perc_fill_rate"] = perc_cfg["fill_rate"]

    # Extract chord progression from sections
    sections = song_data.get("sections", [])
    if sections:
        keys_list = []
        for section in sections:
            section_keys = section.get("keys", "")
            if section_keys:
                reps = section.get("repeat", 1)
                for _ in range(reps):
                    keys_list.append(section_keys)
        if keys_list:
            spec["keys"] = ", ".join(keys_list)

    return spec


def list_presets() -> list[dict]:
    """List user presets with metadata."""
    presets = []
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    for preset_file in sorted(PRESETS_DIR.glob("*.json")):
        try:
            import json
            data = json.loads(preset_file.read_text())
            presets.append({
                "name": preset_file.stem,
                "title": data.get("title", preset_file.stem),
                "description": data.get("description", ""),
                "saved": data.get("saved", ""),
            })
        except Exception:
            pass
    return presets


def load_preset(name: str) -> dict:
    """Load a user preset and return the spec."""
    import json

    preset_path = _safe_path_for(PRESETS_DIR, name, ".json")
    if not preset_path.exists():
        raise GenerationError(f"Preset '{name}' not found")

    try:
        data = json.loads(preset_path.read_text())
        return data.get("spec", {})
    except Exception as e:
        raise GenerationError(f"Failed to load preset '{name}': {e}")


def save_preset(name: str, spec: dict, title: str = "", description: str = "") -> dict:
    """Save a user preset with metadata."""
    import json
    from datetime import datetime

    PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    preset_path = _safe_path_for(PRESETS_DIR, name, ".json")

    data = {
        "title": title or name,
        "description": description,
        "spec": spec,
        "saved": datetime.now().isoformat(),
    }

    try:
        preset_path.write_text(json.dumps(data, indent=2))
        return data
    except Exception as e:
        raise GenerationError(f"Failed to save preset '{name}': {e}")


def delete_preset(name: str) -> None:
    """Delete a user preset. No-op (not an error) if it doesn't exist."""
    preset_path = _safe_path_for(PRESETS_DIR, name, ".json")
    preset_path.unlink(missing_ok=True)


# The reserved preset name the app tries to boot into (docs/design-notes/
# ui-homework.md: "the home, or a user-defined home preset" instead of always
# the same hardcoded demo). Saving a preset under this name is how a user
# designates their home; it's just a preset like any other otherwise.
HOME_PRESET_NAME = "home"


def has_home_preset() -> bool:
    return _safe_path_for(PRESETS_DIR, HOME_PRESET_NAME, ".json").exists()


# Chord-progression presets: a lighter save format than the full-spec presets
# above — just a `keys` token string plus display metadata, for the standalone
# chord-recipes instrument (webapp/chords-frontend). Deliberately not a `spec`
# dict: this app never touches instrument/percussion/arrangement params.
PROGRESSIONS_DIR = REPO_ROOT / "presets" / "progressions"


def list_progressions() -> list[dict]:
    """List saved chord progressions with metadata."""
    progressions = []
    PROGRESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    for prog_file in sorted(PROGRESSIONS_DIR.glob("*.json")):
        try:
            import json
            data = json.loads(prog_file.read_text())
            progressions.append({
                "name": prog_file.stem,
                "title": data.get("title", prog_file.stem),
                "tags": data.get("tags", []),
                "keys": data.get("keys", ""),
                "tempo": data.get("tempo"),
                "saved": data.get("saved", ""),
            })
        except Exception:
            pass
    return progressions


def load_progression(name: str) -> dict:
    """Load a saved chord progression."""
    import json

    prog_path = _safe_path_for(PROGRESSIONS_DIR, name, ".json")
    if not prog_path.exists():
        raise GenerationError(f"Progression '{name}' not found")

    try:
        return json.loads(prog_path.read_text())
    except Exception as e:
        raise GenerationError(f"Failed to load progression '{name}': {e}")


def save_progression(
    name: str,
    keys: str,
    title: str = "",
    tags: list[str] | None = None,
    tempo: int | None = None,
    voicing: str | None = None,
) -> dict:
    """Save a chord progression with metadata."""
    import json
    from datetime import datetime

    PROGRESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    prog_path = _safe_path_for(PROGRESSIONS_DIR, name, ".json")

    data = {
        "title": title or name,
        "tags": tags or [],
        "keys": keys,
        "tempo": tempo,
        "voicing": voicing,
        "saved": datetime.now().isoformat(),
    }

    try:
        prog_path.write_text(json.dumps(data, indent=2))
        return data
    except Exception as e:
        raise GenerationError(f"Failed to save progression '{name}': {e}")


def delete_progression(name: str) -> None:
    """Delete a saved chord progression. No-op (not an error) if it doesn't exist."""
    prog_path = _safe_path_for(PROGRESSIONS_DIR, name, ".json")
    prog_path.unlink(missing_ok=True)
