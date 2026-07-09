# Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
# https://github.com/galenspikes/music-generator
"""In-process MIDI → WAV synthesis: audio preview with zero system deps.

A small additive/noise synthesizer over numpy (already a dependency) that
turns the engine's MIDI bytes into a listenable WAV entirely in-process —
no FluidSynth binary, no SoundFont file. It exists for the *web* preview
path (``POST /api/audio``): production-quality renders should still go
through ``render.py`` + FluidSynth with a real SoundFont; this trades
timbre realism for having no dependency at all.

Design, in one breath: mido's tempo-aware iteration gives absolute note
times; each melodic note is a stack of a few harmonics whose spectrum and
envelope are picked by General-MIDI program family (struck/plucked decay
vs. sustained organ/string/pad, darker bass); channel 10 hits are
synthesized drums (swept-sine kick, noise+tone snare, first-differenced
"bright" noise for hats/cymbals); everything is mixed into one float
buffer, peak-normalized, soft-clipped, and written as 16-bit mono WAV via
the stdlib ``wave`` module.

Public surface: :func:`render_wav` (and :func:`synthesize` if you want the
raw float samples). Deterministic: same MIDI bytes → same WAV bytes.
"""
from __future__ import annotations

import io
import wave

import mido
import numpy as np

__all__ = ["render_wav", "synthesize", "DEFAULT_SAMPLE_RATE", "MAX_SECONDS"]

DEFAULT_SAMPLE_RATE = 22050
# Safety valve for a server rendering untrusted specs: the engine's own UI
# caps pieces at 600s; refuse to allocate buffers meaningfully beyond that.
MAX_SECONDS = 660.0

_DRUM_CHANNEL = 9
_RELEASE_S = 0.06  # melodic release tail beyond note-off


def _note_freq(note: int) -> float:
    return 440.0 * 2.0 ** ((note - 69) / 12.0)


# --- melodic voices ------------------------------------------------------------

def _family(program: int) -> str:
    """Collapse the GM program map into the few timbre families we model."""
    p = int(program)
    if 32 <= p <= 39:
        return "bass"
    if 16 <= p <= 23 or 40 <= p <= 55 or 88 <= p <= 95:
        return "sustained"  # organs, strings/ensembles, pads
    return "struck"  # pianos, chromatic percussion, guitars, the rest


# harmonic amplitudes per family (fundamental first)
_HARMONICS = {
    "struck": (1.0, 0.55, 0.3, 0.15, 0.08),
    "sustained": (1.0, 0.35, 0.2, 0.1),
    "bass": (1.0, 0.4, 0.1),
}


def _melodic_note(sr: int, freq: float, dur_s: float, family: str) -> np.ndarray:
    """One note's samples: harmonic stack × family envelope."""
    n = max(1, int((dur_s + _RELEASE_S) * sr))
    t = np.arange(n, dtype=np.float32) / sr
    wave_sum = np.zeros(n, dtype=np.float32)
    for k, amp in enumerate(_HARMONICS[family], start=1):
        f = freq * k
        if f > sr / 2 - 200:  # keep partials under Nyquist
            break
        # struck strings/keys lose upper partials faster than the fundamental
        partial_decay = np.exp(-t * (0.8 * k)) if family == "struck" else 1.0
        wave_sum += amp * partial_decay * np.sin(2 * np.pi * f * t,
                                                 dtype=np.float32)

    attack_n = max(1, int(0.005 * sr))
    env = np.ones(n, dtype=np.float32)
    env[:attack_n] = np.linspace(0.0, 1.0, attack_n, dtype=np.float32)
    if family == "sustained":
        release_n = max(1, min(n - 1, int(_RELEASE_S * sr)))
        env[-release_n:] *= np.linspace(1.0, 0.0, release_n, dtype=np.float32)
    else:
        # exponential ring-down scaled so long notes ring longer
        tau = 0.25 + 0.5 * min(dur_s, 2.0)
        env *= np.exp(-t / tau).astype(np.float32)
        env[-min(n, attack_n):] *= np.linspace(1.0, 0.0, min(n, attack_n),
                                               dtype=np.float32)
    return wave_sum * env


# --- drums ----------------------------------------------------------------------

def _noise(n: int, seed: int) -> np.ndarray:
    """Deterministic white noise (seeded per hit so renders are stable)."""
    return np.random.default_rng(seed).standard_normal(n).astype(np.float32)


def _bright(noise: np.ndarray) -> np.ndarray:
    """First difference ≈ one-pole high-pass: turns white noise into the
    'bright' hiss used for hats and cymbals."""
    out = np.empty_like(noise)
    out[0] = 0.0
    np.subtract(noise[1:], noise[:-1], out=out[1:])
    return out


def _drum_hit(sr: int, note: int, seed: int) -> np.ndarray:
    """Synthesize one percussion hit for a GM drum note number."""
    def decay(dur_s: float, tau: float) -> tuple[np.ndarray, np.ndarray]:
        n = max(1, int(dur_s * sr))
        t = np.arange(n, dtype=np.float32) / sr
        return t, np.exp(-t / tau).astype(np.float32)

    if note in (35, 36):  # kick: sine swept 120→45 Hz
        t, env = decay(0.20, 0.06)
        freq = 45.0 + 75.0 * np.exp(-t / 0.03)
        phase = 2 * np.pi * np.cumsum(freq) / sr
        return np.sin(phase).astype(np.float32) * env * 1.2
    if note in (38, 40):  # snare: noise + 190 Hz body
        t, env = decay(0.16, 0.045)
        body = 0.4 * np.sin(2 * np.pi * 190.0 * t, dtype=np.float32)
        return (0.8 * _noise(len(t), seed) * 0.5 + body) * env
    if note in (37, 39):  # rimshot / clap: short noise snap
        t, env = decay(0.08, 0.02)
        return _bright(_noise(len(t), seed)) * env * 0.7
    if note in (42, 44):  # closed / pedal hat
        t, env = decay(0.05, 0.012)
        return _bright(_noise(len(t), seed)) * env * 0.5
    if note == 46:  # open hat
        t, env = decay(0.30, 0.09)
        return _bright(_noise(len(t), seed)) * env * 0.5
    if note in (49, 52, 55, 57):  # crashes / splash / chinese
        t, env = decay(1.2, 0.35)
        return _bright(_noise(len(t), seed)) * env * 0.6
    if note in (51, 53, 59):  # rides / ride bell
        t, env = decay(0.6, 0.18)
        return _bright(_noise(len(t), seed)) * env * 0.4
    if 41 <= note <= 50:  # toms: pitched sine thump
        t, env = decay(0.25, 0.08)
        base = 70.0 + (note - 41) * 12.0
        freq = base * (1.0 + 0.5 * np.exp(-t / 0.04))
        phase = 2 * np.pi * np.cumsum(freq) / sr
        return np.sin(phase).astype(np.float32) * env
    # everything else (shakers, cowbell, ...): a short generic tick
    t, env = decay(0.09, 0.03)
    return _bright(_noise(len(t), seed)) * env * 0.4


# --- MIDI event extraction -------------------------------------------------------

def _extract_events(midi_bytes: bytes):
    """(melodic_notes, drum_hits, total_seconds) from raw MIDI bytes.

    melodic: (start_s, dur_s, note, velocity, program)
    drums:   (start_s, note, velocity)
    """
    mid = mido.MidiFile(file=io.BytesIO(midi_bytes))
    programs: dict[int, int] = {}
    open_notes: dict[tuple[int, int], tuple[float, int, int]] = {}
    melodic: list[tuple[float, float, int, int, int]] = []
    drums: list[tuple[float, int, int]] = []
    now = 0.0

    for msg in mid:  # merged iteration: msg.time is delta seconds
        now += msg.time
        if msg.type == "program_change":
            programs[msg.channel] = msg.program
        elif msg.type == "note_on" and msg.velocity > 0:
            if msg.channel == _DRUM_CHANNEL:
                drums.append((now, msg.note, msg.velocity))
            else:
                open_notes[(msg.channel, msg.note)] = (
                    now, msg.velocity, programs.get(msg.channel, 0))
        elif msg.type in ("note_off", "note_on"):  # note_on vel=0 == off
            started = open_notes.pop((msg.channel, msg.note), None)
            if started is not None:
                start, vel, prog = started
                melodic.append((start, max(1e-3, now - start), msg.note,
                                vel, prog))
    # anything left dangling rings to the end of the file
    for (channel, note), (start, vel, prog) in open_notes.items():
        melodic.append((start, max(1e-3, now - start), note, vel, prog))
    return melodic, drums, now


# --- top level -------------------------------------------------------------------

def synthesize(midi_bytes: bytes,
               sample_rate: int = DEFAULT_SAMPLE_RATE) -> np.ndarray:
    """MIDI bytes → mono float32 samples in [-1, 1]."""
    melodic, drums, total = _extract_events(midi_bytes)
    total = min(float(total), MAX_SECONDS)
    n_total = int((total + 1.5) * sample_rate) + 1  # room for tails
    buf = np.zeros(n_total, dtype=np.float32)

    for start, dur, note, vel, prog in melodic:
        if start >= total:
            continue
        amp = 0.28 * (vel / 127.0) ** 1.5
        samples = _melodic_note(sample_rate, _note_freq(note),
                                min(dur, total - start), _family(prog))
        i = int(start * sample_rate)
        j = min(n_total, i + len(samples))
        buf[i:j] += amp * samples[:j - i]

    for idx, (start, note, vel) in enumerate(drums):
        if start >= total:
            continue
        amp = 0.5 * (vel / 127.0) ** 1.5
        # seed by position+note so renders are deterministic
        samples = _drum_hit(sample_rate, note, seed=note * 100003 + idx)
        i = int(start * sample_rate)
        j = min(n_total, i + len(samples))
        buf[i:j] += amp * samples[:j - i]

    peak = float(np.max(np.abs(buf))) if len(buf) else 0.0
    if peak > 0.9:
        buf *= 0.9 / peak
    return np.tanh(buf * 1.2).astype(np.float32)


def render_wav(midi_bytes: bytes,
               sample_rate: int = DEFAULT_SAMPLE_RATE) -> bytes:
    """MIDI bytes → 16-bit mono WAV bytes. Deterministic; no system deps."""
    samples = synthesize(midi_bytes, sample_rate)
    pcm = (np.clip(samples, -1.0, 1.0) * 32767.0).astype("<i2")
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm.tobytes())
    return out.getvalue()
