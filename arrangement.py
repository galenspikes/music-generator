# Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
# https://github.com/galenspikes/music-generator
"""Arrangement layer: sequence multiple sections into one evolving piece.

A *song* is global settings plus an ordered list of *sections*. Each section
overrides the song-level `defaults` and contributes its own chords,
instrumentation, bass, percussion density, tempo, and length. Sections are laid
end-to-end on a single timeline; the existing engine builders are reused per
section with a beat offset, and program/tempo changes are emitted at the
boundaries (hard cuts in v1 — transitions/fills come later).

See docs/design-notes/arrangement-plan.md for the design.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from pathlib import Path

import melody as mel
import music_generator as mg

BEATS_PER_BAR = 4.0  # v1 assumes 4/4 for `bars`-based section lengths

# Song-level defaults. A section (and the song's own `defaults:` block) overrides
# these via a deep merge.
BASE_DEFAULTS: dict = {
    "instrument": "piano",
    "voices": {},                       # voice name -> instrument
    "bass": {"style": "follow", "step": 0.5},
    "satb": "block",                    # block | static | arpeggio | counterpoint
    "chord_length": "h",
    "tempo": 120,
    "chords": ["triads", "sevenths"],   # families for bare roots (colon tokens ignore)
    "chords_order": "roundrobin",
    "perc": {"main": "qb,qc,qb,qc", "interrupters": [], "fill_rate": 0.0},
    "counterpoint": {"step": 0.25, "suspension_prob": 0.0,
                     "anticipation_prob": 0.0},
    # A real tune on top (scale-degree grammar). When set on a section it plays
    # on the soprano channel and replaces the SATB soprano for that section.
    "melody": None,
    "melody_relative": "key",   # "key" (degrees vs the section scale) | "chord"
    "key": None,                # tonic name (e.g. "C", "Eb"); None -> inferred
    "mode": None,               # major/minor/dorian/...; None -> inferred
    "swing": 0.0,               # off-beat swing warp (0=straight, 0.5=triplet)
    "pan_spread": 0.0,          # stereo width of the SATB voices (0=centred)
}


def _deep_merge(base: dict, override: dict | None) -> dict:
    out = copy.deepcopy(base)
    for key, val in (override or {}).items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], val)
        else:
            out[key] = copy.deepcopy(val)
    return out


@dataclass
class SongSpec:
    title: str
    tempo: int
    soundfont: str | None
    vel_mode_chords: str
    vel_mode_drums: str
    sections: list[dict] = field(default_factory=list)
    swing: float = 0.0
    pan_spread: float = 0.0


def build_spec(raw: dict,
               vel_mode_chords: str = "human",
               vel_mode_drums: str = "human",
               overrides: dict | None = None) -> SongSpec:
    """Validate a raw song dict and resolve per-section configs (merged over
    the song's defaults).

    ``overrides`` is applied on top of the YAML defaults but below any
    per-section explicit values — so a section that hard-codes
    ``instrument: saw`` keeps its saw even when the caller overrides the
    default instrument.
    """
    if not isinstance(raw, dict):
        raise ValueError("Song file must be a mapping at the top level.")
    sections_raw = raw.get("sections")
    if not sections_raw:
        raise ValueError("Song file needs a non-empty 'sections' list.")

    global_tempo = int(raw.get("tempo", BASE_DEFAULTS["tempo"]))
    defaults = _deep_merge(BASE_DEFAULTS, raw.get("defaults"))
    if overrides:
        defaults = _deep_merge(defaults, overrides)
    # Restore YAML tempo only when not explicitly overridden by the caller.
    if not (overrides and "tempo" in overrides):
        defaults["tempo"] = raw.get("defaults", {}).get("tempo", global_tempo)

    # When the caller overrides tempo, scale per-section explicit tempos
    # proportionally so the arrangement speeds up/slows down as a whole.
    tempo_scale = (defaults["tempo"] / global_tempo
                   if (overrides and "tempo" in overrides and global_tempo > 0)
                   else 1.0)

    sections: list[dict] = []
    for i, sec in enumerate(sections_raw):
        if not isinstance(sec, dict):
            raise ValueError(f"Section #{i + 1} must be a mapping.")
        merged = _deep_merge(defaults, sec)
        if tempo_scale != 1.0 and "tempo" in sec:
            merged["tempo"] = max(40, round(sec["tempo"] * tempo_scale))
        merged.setdefault("name", f"section{i + 1}")
        if not merged.get("keys"):
            raise ValueError(
                f"Section '{merged['name']}' is missing 'keys'.")
        if merged["chord_length"] not in mg.DUR_MAP:
            raise ValueError(
                f"Section '{merged['name']}': bad chord_length "
                f"'{merged['chord_length']}'.")
        if merged.get("bars") is None and merged.get("repeat") is None:
            merged["repeat"] = 1  # default: one pass through the chart
        sections.append(merged)

    return SongSpec(
        title=str(raw.get("title", "untitled")),
        tempo=defaults["tempo"],
        soundfont=raw.get("soundfont"),
        vel_mode_chords=vel_mode_chords,
        vel_mode_drums=vel_mode_drums,
        sections=sections,
        swing=float(defaults.get("swing", 0.0) or 0.0),
        pan_spread=float(defaults.get("pan_spread", 0.0) or 0.0),
    )


def load_spec(path: str,
              vel_mode_chords: str = "human",
              vel_mode_drums: str = "human",
              overrides: dict | None = None) -> SongSpec:
    import yaml
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return build_spec(raw, vel_mode_chords, vel_mode_drums, overrides)


def _section_beats(sec: dict, seq_len: int, chord_len: float) -> float:
    """Length of a section in beats, from `bars` (preferred) or `repeat`."""
    if sec.get("bars") is not None:
        return float(sec["bars"]) * BEATS_PER_BAR
    natural = seq_len * chord_len
    return float(sec.get("repeat", 1)) * natural


def _section_key(sec: dict, seq: list) -> tuple[int, str]:
    """Resolve (tonic_pc, mode) for a section's melody. Explicit key/mode win;
    otherwise infer from the section's chords."""
    kname = sec.get("key")
    mode = sec.get("mode")
    if kname:
        pc, is_minor = mg.parse_key_name(str(kname))
        return pc, (mode or ("minor" if is_minor else "major"))
    ikey, imode = mel.infer_key(seq)
    return ikey, (mode or imode)


def _chord_root_spans(seq: list, chord_len: float,
                      sec_beats: float) -> list[tuple[float, float, int]]:
    """Root pitch-class per chord slot across the section (for chord-relative
    melody). Mirrors build_chord_timeline's straight stepping."""
    spans: list[tuple[float, float, int]] = []
    pos, i = 0.0, 0
    while pos < sec_beats and seq:
        root = seq[i % len(seq)].root_pc
        spans.append((pos, min(pos + chord_len, sec_beats), root))
        pos += chord_len
        i += 1
    return spans


def build_events(spec: SongSpec) -> tuple[list, float]:
    """Build the full, time-sorted event stream for the arrangement.

    Event kinds: ('tempo', when, 0, bpm), ('program', when, 0, (voice, prog)),
    ('voice', when, dur, (voice, note)), ('drum', when, dur, hits).
    Returns (events, total_beats).
    """
    events: list = []
    cursor = 0.0

    for sec in spec.sections:
        start = cursor
        chord_len = mg.DUR_MAP[sec["chord_length"]]
        roots = mg.key_roots("ostinato", sec["keys"])
        seq = mg.build_progression(roots, sec["chords"], sec["chords_order"],
                                   max_chords=len(roots))
        sec_beats = _section_beats(sec, len(seq), chord_len)
        chord_tl = mg.build_chord_timeline(seq, sec_beats, chord_len,
                                           static=(sec["satb"] == "static"))

        # tempo + per-voice programs at the boundary
        events.append(("tempo", start, 0.0, int(sec["tempo"])))
        default_prog = mg.resolve_instrument(str(sec["instrument"]))
        voices = sec.get("voices") or {}
        for voice in mg.VOICE_ORDER:
            prog = (mg.resolve_instrument(str(voices[voice]))
                    if voice in voices else default_prog)
            events.append(("program", start, 0.0, (voice, prog)))

        # harmony + bass (shared builder), offset onto the global timeline
        bass = sec["bass"]
        cp = sec["counterpoint"]
        h_events, _ = mg.build_harmony_events(
            chord_tl,
            satb_style=sec["satb"],
            bass_style=bass.get("style", "follow"),
            bass_step=float(bass.get("step", 0.5)),
            counterpoint_step=float(cp.get("step", 0.25)),
            counterpoint_suspension_prob=float(cp.get("suspension_prob", 0.0)),
            counterpoint_anticipation_prob=float(cp.get("anticipation_prob", 0.0)),
            split_stems=True,
            when_offset=start,
        )
        mel_text = sec.get("melody")
        has_melody = bool(mel_text and str(mel_text).strip())

        # arrange always routes per-voice (so programs apply per voice); expand
        # any block 'chord' events into the four voices. When a melody is set it
        # takes over the soprano channel, so the SATB soprano is dropped here.
        for ev in h_events:
            if ev[0] == "chord":
                _, when, dur, notes = ev
                for voice, note in zip(mg.VOICE_ORDER, notes):
                    if has_melody and voice == "soprano":
                        continue
                    events.append(("voice", when, dur, (voice, note)))
            elif has_melody and ev[0] == "voice" and ev[3][0] == "soprano":
                continue
            else:
                events.append(ev)

        # melody: a real tune on the soprano channel, tiled to fill the section
        if has_melody:
            mel_notes = mel.parse_melody(str(mel_text))
            mel_beats = sum(n.beats for n in mel_notes)
            if mel_beats > 0:
                key_pc, mode = _section_key(sec, seq)
                relative = sec.get("melody_relative", "key")
                chord_roots = (_chord_root_spans(seq, chord_len, sec_beats)
                               if relative == "chord" else None)
                reps = max(1, int(math.ceil(sec_beats / mel_beats)))
                lo, hi = mg.SOP_RANGE
                realized = mel.realize_melody(
                    mel_notes * reps, key_pc, mode, base_octave=5,
                    lo=lo, hi=hi, relative=relative, chord_roots=chord_roots)
                for when, dur, note in realized:
                    if when >= sec_beats:
                        break
                    dur = min(dur, sec_beats - when)
                    if dur > 0:
                        events.append(
                            ("voice", start + when, dur, ("soprano", note)))

        # percussion
        perc = sec.get("perc") or {}
        main_pat = mg.parse_pattern(perc["main"]) if perc.get("main") else []
        intr = mg.parse_many_patterns(perc.get("interrupters") or []) or None
        drum_tl = mg.build_drum_timeline_with_fills(
            main_pat, intr, sec_beats, float(perc.get("fill_rate", 0.0)))
        for when, dur, hits in drum_tl:
            events.append(("drum", when + start, dur, hits))

        cursor += sec_beats

    priority = {"tempo": 0, "program": 1, "voice": 2, "drum": 3}
    events.sort(key=lambda e: (e[1], priority.get(e[0], 9)))
    return events, cursor


def render(spec: SongSpec, out_path: str) -> str:
    """Render the arrangement to a MIDI file at out_path. Returns out_path."""
    events, total = build_events(spec)

    midi = mg.MidiOut(spec.tempo, out_path,
                      vel_mode_chords=spec.vel_mode_chords,
                      vel_mode_drums=spec.vel_mode_drums,
                      split_stems=True,
                      swing=spec.swing,
                      pan_spread=spec.pan_spread)

    _t_ch, t_dr, _vmax = mg.render_events(midi, events)
    midi.flush_to_end(total, t_dr, total)
    midi.save()
    return out_path
