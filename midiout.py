"""MIDI writer: the :class:`MidiOut` track/event serializer.

Wraps :mod:`mido` to accumulate chord/voice and drum events on a tempo-mapped
timeline (optionally split into per-voice stems), apply velocity humanisation,
and save a Type-1 MIDI file. Depends on :mod:`mtheory` (channels, voice order)
and :mod:`percussion` (:class:`PercHit`).
"""
import copy
import os
import random

from mido import Message, MidiFile, MidiTrack, MetaMessage, bpm2tempo

from mtheory import CHORD_CH, DRUM_CH, LEAD_CH, VOICE_ORDER
from percussion import PercHit

__all__ = ["MidiOut"]

# Stereo placement per SATB voice, as a fraction of the pan_spread (−1 = hard
# left, +1 = hard right). Soprano/bass are pushed widest, alto/tenor sit inside;
# scaled by ``pan_spread`` (0 keeps everyone centred). See build_parser's
# ``--pan-spread`` and docs/design-notes/roadmap-phase2.md (Thread 4a).
VOICE_PAN_POS = {"soprano": 1.0, "alto": 0.4, "tenor": -0.4, "bass": -1.0}


class MidiOut:

    STEM_VOICES = VOICE_ORDER

    def __init__(self,
                 bpm: int,
                 fname: str | None = None,
                 tpb: int = 480,
                 vel_mode_chords: str = "uniform",
                 vel_mode_drums: str = "uniform",
                 split_stems: bool = False,
                 swing: float = 0.0,
                 pan_spread: float = 0.0,
                 with_lead: bool = False) -> None:
        """Set up the Type-1 MIDI file and its track layout.

        Two layouts, chosen by ``split_stems``:

        - merged (default): one chord track + one drum track; all melodic
          voices share channel 0 (per-voice instruments are impossible);
        - split stems: one track/channel per SATB voice (plus an optional
          5th "lead" voice on LEAD_CH when ``with_lead``), then the drum
          track — required for per-voice programs, panning, and stems.

        Each melodic track gets tempo + volume/expression CCs at time 0,
        and pan CCs when ``pan_spread`` > 0 (0 = mono, 1 = widest, per
        VOICE_PAN_POS). ``vel_mode_chords``/``vel_mode_drums`` pick the
        velocity humanisation ('uniform', 'random', 'human'); ``swing``
        (0..0.75) is stored for render_events' off-beat warp. ``fname`` is
        the default save path — save() accepts an explicit one too.

        Example::

            out = MidiOut(bpm=96, split_stems=True, pan_spread=0.6)
            out.chord_block((72, 67, 60, 48), beats=4.0, when_beats=0.0)
            out.save("take1.mid")
        """
        self.bpm = bpm
        self.fname = fname
        self.tpb = tpb
        self.vel_mode_chords = (vel_mode_chords or "uniform").lower()
        self.vel_mode_drums = (vel_mode_drums or "uniform").lower()
        self.split_stems = bool(split_stems)
        # Optional 5th melodic voice ("lead") on its own channel (LEAD_CH),
        # registered in chord_tracks like the SATB voices so per-voice notes,
        # program changes, mix CCs, and stems all work on it unchanged.
        # Needs split stems (a merged ensemble has no per-voice channels).
        self.with_lead = bool(with_lead) and self.split_stems
        # Off-beat swing warp applied in render_events (0 = straight eighths).
        self.swing = max(0.0, min(0.75, float(swing or 0.0)))
        # Stereo spread of the SATB voices (0 = mono/centred, 1 = widest).
        self.pan_spread = max(0.0, min(1.0, float(pan_spread or 0.0)))

        self.mid = MidiFile(type=1, ticks_per_beat=self.tpb)
        self.chord_tracks: dict[str, MidiTrack] = {}
        self.chord_channels: dict[str, int] = {}
        self.active_ch: dict[str, set[int]] = {}
        self.voice_positions: dict[str, float] = {}
        self.active_dr: set[int] = set()
        self.dr_position = 0.0

        tempo = bpm2tempo(self.bpm)

        if self.split_stems:
            voice_channels = [(voice, idx)
                              for idx, voice in enumerate(self.STEM_VOICES)]
            if self.with_lead:
                voice_channels.append(("lead", LEAD_CH))
            for voice, channel in voice_channels:
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
                if self.pan_spread > 0.0:
                    pan = VOICE_PAN_POS.get(voice, 0.0) * self.pan_spread
                    value = max(0, min(127, round(64 + pan * 63)))
                    track.append(
                        Message('control_change',
                                control=10,
                                value=value,
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

    def control_change_at(self,
                          voice: str,
                          control: int,
                          value: int,
                          when_beats: float) -> None:
        """Send a control-change (e.g. CC91 reverb send, CC93 chorus send) on
        a voice's channel at a beat offset — the per-section mix/FX knob.
        Requires split stems (per-voice channels), like `program_change_at`.
        """
        if voice not in self.chord_tracks:
            return
        track = self.chord_tracks[voice]
        channel = self.chord_channels[voice]
        self._seek_voice(voice, when_beats)
        track.append(
            Message('control_change', control=control,
                    value=max(0, min(127, int(value))), channel=channel,
                    time=0))

    def drum_control_change_at(self,
                               control: int,
                               value: int,
                               when_beats: float) -> None:
        """Send a control-change on the drum channel at a beat offset (the
        percussion side of `control_change_at`)."""
        delta = when_beats - self.dr_position
        if delta > 0:
            self.advance_dr(delta)
        self.tr_dr.append(
            Message('control_change', control=control,
                    value=max(0, min(127, int(value))), channel=DRUM_CH,
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
        self.dr_position += beats

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
        """Sound one four-voice (SATB) chord for ``beats`` at ``when_beats``.

        In split-stems mode each voice's note goes to its own track/channel
        (via play_voice_note, so per-voice programs apply); merged mode
        writes all four notes as a block on the single "ensemble" track.
        ``base`` is the pre-humanisation velocity — the actual strike
        velocity comes from ``vel_mode_chords``.

        Example::

            out = MidiOut(bpm=120)
            out.chord_block((72, 67, 64, 48), beats=2.0, when_beats=0.0)
            out.chord_block((74, 69, 65, 50), beats=2.0, when_beats=2.0)
        """
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
            choke_after_beats: float = 0.06,
            vel_scale: float = 1.0) -> None:
        """Schedule one percussion-token's worth of drum hits on the drum track.

        ``hits`` is the parsed token payload (:func:`percussion.parse_single_token`);
        an empty list is a rest — the drum cursor still advances by ``beats``.
        Per-hit fields are honoured here: ``probability`` (chance the hit
        plays), ``vel_offset``, ``timing_offset`` (push/pull in beats), and
        ``flam`` (a grace hit that many beats later). The ``vel*`` kwargs set
        the pre-humanisation base velocity per GM note (kick/snare/hat/…),
        scaled by ``vel_scale``; final velocities come from ``vel_mode_drums``.
        ``choke_openhat`` closes an open hi-hat shortly after it sounds
        (``choke_after_beats``) for a tighter feel.

        Example::

            beats, hits = parse_single_token("qbc")   # quarter: kick+snare
            out.drums_block(hits, beats, when_beats=0.0)
        """
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
            base = round(base_velocity(note) * vel_scale) + hit.vel_offset
            hit_offset = max(0.0, float(hit.timing_offset))
            if beats > 0.0:
                hit_offset = min(hit_offset, beats)
            vel = self._compute_drum_velocity(note, base, when_beats + hit_offset)
            events.append((hit_offset, note, vel))

            if hit.flam is not None:
                flam_offset = hit_offset + max(0.0, float(hit.flam))
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
            self.dr_position = when_beats + beats
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
        self.dr_position = when_beats + beats

    def save(self, path: str | None = None) -> None:
        target = path or self.fname
        if target is None:
            raise ValueError("MidiOut.save() needs a path (none set at init)")
        self.mid.save(target)

    def write_stems(self, base_path: str) -> list[str]:
        """Write each voice (+ drums) as its own standalone MIDI file
        alongside the main render, e.g. `song.mid` -> `song_soprano.mid`,
        `song_bass.mid`, ..., `song_drums.mid` — directly importable into a
        DAW for external mixing. Requires split stems (per-voice channels);
        a merged ensemble render has nothing to split, so this is a no-op.
        Call after `flush_to_end` so notes are properly terminated. Returns
        the written paths.
        """
        if not self.split_stems:
            return []
        stem_base, ext = os.path.splitext(base_path)
        ext = ext or ".mid"
        paths: list[str] = []
        for name, track in list(self.chord_tracks.items()) + [("drums", self.tr_dr)]:
            stem_mid = MidiFile(type=1, ticks_per_beat=self.tpb)
            stem_mid.tracks.append(copy.deepcopy(self.tr_meta))
            stem_mid.tracks.append(copy.deepcopy(track))
            path = f"{stem_base}_{name}{ext}"
            stem_mid.save(path)
            paths.append(path)
        return paths

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
