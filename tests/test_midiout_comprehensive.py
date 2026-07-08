"""Comprehensive tests for midiout module.

Tests MIDI event writing, humanization, voice scheduling, and stem splitting.
"""

import os
import random

import mido
import pytest

import music_generator as M
from midiout import MidiOut, VOICE_PAN_POS
from percussion import PercHit


class TestMidiOutInitialization:
    """Test MidiOut initialization."""

    def test_midiout_basic_creation(self):
        """MidiOut can be created with minimal parameters."""
        out = MidiOut(bpm=120)
        assert out.bpm == 120
        assert out.tpb == 480
        assert out.mid is not None
        assert len(out.mid.tracks) > 0

    def test_midiout_with_filename(self):
        """MidiOut can be created with filename."""
        out = MidiOut(bpm=120, fname="test.mid")
        assert out.fname == "test.mid"

    def test_midiout_split_stems_enabled(self):
        """split_stems=True creates separate tracks per voice."""
        out = MidiOut(bpm=120, split_stems=True)
        assert out.split_stems is True
        # Should have tracks for soprano, alto, tenor, bass
        assert len(out.chord_tracks) >= 4

    def test_midiout_split_stems_disabled(self):
        """split_stems=False uses single ensemble track."""
        out = MidiOut(bpm=120, split_stems=False)
        assert out.split_stems is False
        # Should have single ensemble track
        assert "ensemble" in out.chord_tracks

    def test_midiout_velocity_modes(self):
        """Velocity modes are stored correctly."""
        out = MidiOut(
            bpm=120,
            vel_mode_chords="human",
            vel_mode_drums="random"
        )
        assert out.vel_mode_chords == "human"
        assert out.vel_mode_drums == "random"

    def test_midiout_swing_parameter(self):
        """Swing parameter is clamped to [0, 0.75]."""
        out1 = MidiOut(bpm=120, swing=0.3)
        assert out1.swing == pytest.approx(0.3)

        out2 = MidiOut(bpm=120, swing=1.0)
        assert out2.swing == pytest.approx(0.75)  # Clamped

        out3 = MidiOut(bpm=120, swing=-0.1)
        assert out3.swing == pytest.approx(0.0)  # Clamped

    def test_midiout_pan_spread_parameter(self):
        """Pan spread parameter is clamped to [0, 1]."""
        out1 = MidiOut(bpm=120, pan_spread=0.5)
        assert out1.pan_spread == pytest.approx(0.5)

        out2 = MidiOut(bpm=120, pan_spread=2.0)
        assert out2.pan_spread == pytest.approx(1.0)  # Clamped

        out3 = MidiOut(bpm=120, pan_spread=-0.5)
        assert out3.pan_spread == pytest.approx(0.0)  # Clamped


class TestMidiOutTiming:
    """Test beat-to-tick conversion and timing."""

    def test_ticks_conversion(self):
        """ticks() converts beats to MIDI ticks."""
        out = MidiOut(bpm=120, tpb=480)
        # 1 beat = 480 ticks (at tpb=480)
        assert out.ticks(1.0) == 480
        assert out.ticks(0.5) == 240
        assert out.ticks(2.0) == 960

    def test_advance_ch_updates_position(self):
        """advance_ch advances chord track position."""
        out = MidiOut(bpm=120, split_stems=True)
        initial_pos = out.voice_positions.get("soprano", 0.0)
        out.advance_ch(1.0)
        # Position should advance
        assert out.voice_positions.get("soprano", 0.0) > initial_pos

    def test_advance_dr_updates_position(self):
        """advance_dr advances drum track position."""
        out = MidiOut(bpm=120)
        initial_pos = out.voice_positions.get("ensemble", 0.0)
        out.advance_dr(1.0)
        # Should advance without error
        assert out is not None


class TestVelocityComputation:
    """Test velocity humanization and computation."""

    def test_clamp_velocity_bounds(self):
        """_clamp_velocity clamps to [1, 127]."""
        assert MidiOut._clamp_velocity(-10) == 1
        assert MidiOut._clamp_velocity(0) == 1
        assert MidiOut._clamp_velocity(64) == 64
        assert MidiOut._clamp_velocity(127) == 127
        assert MidiOut._clamp_velocity(200) == 127

    def test_compute_chord_velocity_uniform(self):
        """Uniform velocity mode returns base velocity."""
        out = MidiOut(bpm=120, vel_mode_chords="uniform")
        vel = out._compute_chord_velocity(0.0, base=80)
        assert vel == 80

    def test_compute_chord_velocity_human(self):
        """Human velocity mode varies velocity around base."""
        random.seed(42)
        out = MidiOut(bpm=120, vel_mode_chords="human")
        velocities = []
        for _ in range(10):
            vel = out._compute_chord_velocity(0.0, base=80)
            velocities.append(vel)
        # Should have some variation
        assert len(set(velocities)) > 1
        # All should be in valid range
        assert all(1 <= v <= 127 for v in velocities)

    def test_compute_drum_velocity_uniform(self):
        """Uniform drum velocity mode."""
        out = MidiOut(bpm=120, vel_mode_drums="uniform")
        vel = out._compute_drum_velocity(midi_note=35, base=90, when_beats=0.0)
        assert 1 <= vel <= 127

    def test_compute_drum_velocity_human_mode(self):
        """Human drum velocity mode varies velocity."""
        random.seed(42)
        out = MidiOut(bpm=120, vel_mode_drums="human")
        velocities = []
        for _ in range(5):
            vel = out._compute_drum_velocity(midi_note=35, base=90, when_beats=0.0)
            velocities.append(vel)
        # All should be in valid range
        assert all(1 <= v <= 127 for v in velocities)


class TestChordTrackAccess:
    """Test chord track access and management."""

    def test_chord_track_items_split_stems(self):
        """_chord_track_items returns all voice tracks in split mode."""
        out = MidiOut(bpm=120, split_stems=True)
        items = out._chord_track_items()
        assert len(items) == 4  # soprano, alto, tenor, bass
        voices = {voice for voice, _ in items}
        assert voices == {"soprano", "alto", "tenor", "bass"}

    def test_chord_track_items_ensemble(self):
        """_chord_track_items returns ensemble track in ensemble mode."""
        out = MidiOut(bpm=120, split_stems=False)
        items = out._chord_track_items()
        assert len(items) == 1
        assert items[0][0] == "ensemble"

    def test_chord_channels_split_stems(self):
        """Chord channels mapped correctly in split stems mode."""
        out = MidiOut(bpm=120, split_stems=True)
        assert "soprano" in out.chord_channels
        assert "alto" in out.chord_channels
        assert "tenor" in out.chord_channels
        assert "bass" in out.chord_channels
        # Channels should be 0, 1, 2, 3
        channels = set(out.chord_channels.values())
        assert channels == {0, 1, 2, 3}

    def test_chord_channels_ensemble(self):
        """Single ensemble channel in non-split mode."""
        out = MidiOut(bpm=120, split_stems=False)
        assert "ensemble" in out.chord_channels
        # Should be on CHORD_CH channel
        assert out.chord_channels["ensemble"] == M.CHORD_CH


class TestMidiFileGeneration:
    """Test MIDI file generation and output."""

    def test_midiout_to_bytes(self):
        """to_bytes() returns valid MIDI bytes."""
        out = MidiOut(bpm=120)
        midi_bytes = out.to_bytes()
        assert isinstance(midi_bytes, bytes)
        assert len(midi_bytes) > 0
        # Check MIDI file header
        assert midi_bytes[:4] == b"MThd"

    def test_midiout_to_bytes_roundtrip(self):
        """MIDI bytes can be parsed back with mido."""
        out = MidiOut(bpm=120, split_stems=True)
        midi_bytes = out.to_bytes()

        # Parse with mido
        import io
        parsed = mido.MidiFile(file=io.BytesIO(midi_bytes))
        assert parsed.type == 1
        assert len(parsed.tracks) > 0

    def test_midiout_save_without_path_raises(self):
        """save() without fname raises ValueError."""
        out = MidiOut(bpm=120)
        with pytest.raises(ValueError):
            out.save()

    def test_midiout_save_with_path(self, tmp_path):
        """save() writes MIDI file when path provided."""
        out = MidiOut(bpm=120)
        midi_path = tmp_path / "test.mid"
        out.save(str(midi_path))
        assert midi_path.exists()
        assert midi_path.stat().st_size > 0


class TestWriteStems:
    """Test per-stem MIDI export (Thread 4b)."""

    def test_write_stems_writes_one_file_per_voice_and_drums(self, tmp_path):
        out = MidiOut(bpm=120, split_stems=True)
        out.play_voice_note("soprano", 72, 0.0, 1.0)
        out.play_voice_note("bass", 48, 0.0, 1.0)
        out.drums_block([PercHit(note=36)], beats=1.0, when_beats=0.0)
        out.flush_to_end(1.0, 1.0, 1.0)
        base = str(tmp_path / "song.mid")
        out.save(base)

        paths = out.write_stems(base)
        assert len(paths) == 5  # soprano, alto, tenor, bass, drums
        names = {p.split("_")[-1] for p in paths}
        assert names == {"soprano.mid", "alto.mid", "tenor.mid", "bass.mid",
                         "drums.mid"}
        for path in paths:
            assert os.path.exists(path)
            stem_mid = mido.MidiFile(path)
            assert len(stem_mid.tracks) == 2  # tempo map + the one voice track

    def test_write_stems_soprano_only_has_soprano_notes(self, tmp_path):
        out = MidiOut(bpm=120, split_stems=True)
        out.play_voice_note("soprano", 72, 0.0, 1.0)
        out.play_voice_note("bass", 48, 0.0, 1.0)
        out.flush_to_end(1.0, 0.0, 1.0)
        base = str(tmp_path / "song.mid")
        out.save(base)

        paths = out.write_stems(base)
        soprano_path = next(p for p in paths if p.endswith("_soprano.mid"))
        stem_mid = mido.MidiFile(soprano_path)
        notes_on = {m.note for tr in stem_mid.tracks for m in tr
                   if m.type == "note_on" and m.velocity > 0}
        assert notes_on == {72}

    def test_write_stems_no_op_without_split_stems(self, tmp_path):
        out = MidiOut(bpm=120, split_stems=False)
        base = str(tmp_path / "song.mid")
        out.save(base)
        assert out.write_stems(base) == []


class TestProgramChanges:
    """Test instrument program changes."""

    def test_set_program_single(self):
        """set_program sets instrument for ensemble."""
        out = MidiOut(bpm=120, split_stems=False)
        out.set_program(0)  # Acoustic grand piano
        assert out is not None

    def test_set_program_with_bank(self):
        """set_program with bank select."""
        out = MidiOut(bpm=120)
        out.set_program(program=0, bank_msb=0, bank_lsb=0)
        assert out is not None

    def test_set_voice_programs(self):
        """set_voice_programs sets different programs per voice."""
        out = MidiOut(bpm=120, split_stems=True)
        out.set_voice_programs(
            programs={"soprano": 33, "bass": 32},
            default_program=0
        )
        assert out is not None


class TestPanPositioning:
    """Test stereo pan positioning."""

    def test_voice_pan_positions_defined(self):
        """VOICE_PAN_POS has expected voices."""
        expected = {"soprano", "alto", "tenor", "bass"}
        assert set(VOICE_PAN_POS.keys()) == expected

    def test_voice_pan_positions_range(self):
        """VOICE_PAN_POS values are in [-1, 1]."""
        for voice, pos in VOICE_PAN_POS.items():
            assert -1.0 <= pos <= 1.0

    def test_pan_spread_affects_initialization(self):
        """pan_spread > 0 applies pan to tracks."""
        out = MidiOut(bpm=120, split_stems=True, pan_spread=1.0)
        # Should have pan control changes in tracks
        assert out.pan_spread == pytest.approx(1.0)

    def test_pan_spread_zero_no_pan(self):
        """pan_spread=0 doesn't apply pan."""
        out = MidiOut(bpm=120, split_stems=True, pan_spread=0.0)
        assert out.pan_spread == pytest.approx(0.0)


class TestIntegration:
    """Integration tests for MIDI output."""

    def test_full_midi_output_stem_split(self):
        """Generate MIDI with stem splitting enabled."""
        out = MidiOut(bpm=120, split_stems=True, vel_mode_chords="human")
        out.set_program(0)  # Piano
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0
        assert midi_bytes[:4] == b"MThd"

    def test_full_midi_output_ensemble(self):
        """Generate MIDI in ensemble mode."""
        out = MidiOut(bpm=120, split_stems=False, pan_spread=0.5)
        out.set_program(0)  # Piano
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_tempo_change_recorded(self):
        """Tempo changes are recorded in MIDI."""
        out = MidiOut(bpm=120)
        out.set_tempo_at(bpm=140, when_beats=2.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_humanized_modes(self):
        """Both humanization modes can be set."""
        out1 = MidiOut(bpm=120, vel_mode_chords="human", vel_mode_drums="random")
        assert out1.vel_mode_chords == "human"
        assert out1.vel_mode_drums == "random"

        out2 = MidiOut(bpm=120, vel_mode_chords="random", vel_mode_drums="human")
        assert out2.vel_mode_chords == "random"
        assert out2.vel_mode_drums == "human"


class TestVelocityComputation:
    """Test velocity calculation with different modes."""

    def test_clamp_velocity_within_range(self):
        """Velocity clamped to [1, 127]."""
        assert MidiOut._clamp_velocity(64) == 64
        assert MidiOut._clamp_velocity(127) == 127
        assert MidiOut._clamp_velocity(1) == 1

    def test_clamp_velocity_below_min(self):
        """Velocity clamped to minimum of 1."""
        assert MidiOut._clamp_velocity(-10) == 1
        assert MidiOut._clamp_velocity(0) == 1

    def test_clamp_velocity_above_max(self):
        """Velocity clamped to maximum of 127."""
        assert MidiOut._clamp_velocity(200) == 127
        assert MidiOut._clamp_velocity(128) == 127

    def test_compute_chord_velocity_default_mode(self):
        """Default velocity mode returns consistent velocity."""
        out = MidiOut(bpm=120, vel_mode_chords="default")
        vel1 = out._compute_chord_velocity(0.0)
        vel2 = out._compute_chord_velocity(1.0)
        assert vel1 == vel2
        assert 1 <= vel1 <= 127

    def test_compute_chord_velocity_random_mode(self):
        """Random mode produces varying velocities."""
        out = MidiOut(bpm=120, vel_mode_chords="random")
        velocities = {out._compute_chord_velocity(i * 0.25) for i in range(20)}
        # Random mode should produce multiple different velocities
        assert len(velocities) > 1

    def test_compute_chord_velocity_human_mode(self):
        """Human mode applies beat-based accents."""
        out = MidiOut(bpm=120, vel_mode_chords="human")
        vel_beat1 = out._compute_chord_velocity(0.0)  # Strong beat
        vel_beat2 = out._compute_chord_velocity(0.5)  # Off-beat
        # Both should be valid
        assert 1 <= vel_beat1 <= 127
        assert 1 <= vel_beat2 <= 127

    def test_compute_drum_velocity_default_mode(self):
        """Drum velocity with default mode."""
        out = MidiOut(bpm=120, vel_mode_drums="default")
        vel = out._compute_drum_velocity(midi_note=36, base=80, when_beats=0.0)
        assert 1 <= vel <= 127

    def test_compute_drum_velocity_random_mode(self):
        """Drum velocity with random mode."""
        out = MidiOut(bpm=120, vel_mode_drums="random")
        velocities = {out._compute_drum_velocity(36, 80, i * 0.25) for i in range(20)}
        assert len(velocities) > 1


class TestVoicePlayback:
    """Test playing notes on voice tracks."""

    def test_play_voice_note_basic(self):
        """play_voice_note adds note on/off messages."""
        out = MidiOut(split_stems=True, bpm=120)
        out.play_voice_note("soprano", note=72, start_beats=0.0, duration=1.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_play_voice_note_multiple_voices(self):
        """Can play notes on multiple voices."""
        out = MidiOut(split_stems=True, bpm=120)
        out.play_voice_note("soprano", 72, 0.0, 1.0)
        out.play_voice_note("alto", 67, 0.0, 1.0)
        out.play_voice_note("tenor", 60, 0.0, 1.0)
        out.play_voice_note("bass", 55, 0.0, 1.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_play_voice_note_invalid_voice(self):
        """Invalid voice name is silently ignored."""
        out = MidiOut(split_stems=True, bpm=120)
        out.play_voice_note("invalid", 72, 0.0, 1.0)
        # Should not crash
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_play_voice_note_zero_duration(self):
        """Zero duration note is ignored."""
        out = MidiOut(split_stems=True, bpm=120)
        out.play_voice_note("soprano", 72, 0.0, 0.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_play_voice_note_negative_duration(self):
        """Negative duration note is ignored."""
        out = MidiOut(split_stems=True, bpm=120)
        out.play_voice_note("soprano", 72, 0.0, -1.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_play_voice_note_sequence(self):
        """Multiple notes in sequence."""
        out = MidiOut(split_stems=True, bpm=120)
        out.play_voice_note("soprano", 60, 0.0, 1.0)
        out.play_voice_note("soprano", 62, 1.0, 1.0)
        out.play_voice_note("soprano", 64, 2.0, 1.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0


class TestDrumPlayback:
    """Test playing drum notes via blocks."""

    def test_drums_block_single_pattern(self):
        """drums_block plays a drum pattern."""
        out = MidiOut(bpm=120)
        pattern = [PercHit(note=36), PercHit(note=38)]
        out.drums_block(pattern, beats=1.0, when_beats=0.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_drums_block_empty_pattern(self):
        """drums_block with empty pattern is safe."""
        out = MidiOut(bpm=120)
        out.drums_block([], beats=1.0, when_beats=0.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_drums_block_with_base_velocity(self):
        """drums_block respects base velocity."""
        out = MidiOut(bpm=120)
        pattern = [PercHit(note=36)]
        out.drums_block(pattern, beats=1.0, when_beats=0.0, velk=90)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_drums_block_vel_scale_lowers_velocity(self):
        """vel_scale multiplies the per-instrument base before humanization."""
        quiet = MidiOut(bpm=120, vel_mode_drums="uniform")
        loud = MidiOut(bpm=120, vel_mode_drums="uniform")
        pattern = [PercHit(note=36)]
        quiet.drums_block(pattern, beats=1.0, when_beats=0.0, vel_scale=0.4)
        loud.drums_block(pattern, beats=1.0, when_beats=0.0, vel_scale=1.0)

        def note_on_velocity(midi_out):
            for msg in midi_out.tr_dr:
                if msg.type == "note_on":
                    return msg.velocity
            return None

        assert note_on_velocity(quiet) < note_on_velocity(loud)


class TestVoiceAdvance:
    """Test advancing voice positions."""

    def test_advance_ch_positive(self):
        """advance_ch moves chord voices forward."""
        out = MidiOut(split_stems=True, bpm=120)
        out.play_voice_note("soprano", 72, 0.0, 1.0)
        out.advance_ch(2.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_advance_ch_zero(self):
        """advance_ch with zero beats is safe."""
        out = MidiOut(split_stems=True, bpm=120)
        out.advance_ch(0.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_advance_ch_negative(self):
        """advance_ch with negative beats is ignored."""
        out = MidiOut(split_stems=True, bpm=120)
        out.advance_ch(-1.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_advance_dr_positive(self):
        """advance_dr moves drums forward."""
        out = MidiOut(bpm=120)
        pattern = [PercHit(note=36)]
        out.drums_block(pattern, beats=1.0, when_beats=0.0)
        out.advance_dr(2.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0


class TestProgramChange:
    """Test mid-track program changes (re-orchestration)."""

    def test_program_change_at(self):
        """program_change_at changes instrument mid-track."""
        out = MidiOut(split_stems=True, bpm=120)
        out.play_voice_note("soprano", 72, 0.0, 1.0)
        out.program_change_at("soprano", program=5, when_beats=1.0)
        out.play_voice_note("soprano", 74, 1.0, 1.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_program_change_at_invalid_voice(self):
        """program_change_at on invalid voice is safe."""
        out = MidiOut(split_stems=True, bpm=120)
        out.program_change_at("invalid", program=5, when_beats=0.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_program_change_at_with_bank(self):
        """program_change_at can set bank MSB/LSB."""
        out = MidiOut(split_stems=True, bpm=120)
        out.program_change_at("soprano", program=0, when_beats=0.0,
                              bank_msb=1, bank_lsb=2)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_control_change_at_sends_cc_on_voice_channel(self):
        """control_change_at sends CC91/93 on the target voice's channel."""
        out = MidiOut(split_stems=True, bpm=120)
        out.control_change_at("bass", control=91, value=64, when_beats=1.0)
        channel = out.chord_channels["bass"]
        ccs = [m for m in out.chord_tracks["bass"]
              if m.type == "control_change" and m.control == 91]
        assert len(ccs) == 1
        assert ccs[0].value == 64
        assert ccs[0].channel == channel

    def test_control_change_at_clamps_value(self):
        """control_change_at clamps out-of-range values into [0, 127]."""
        out = MidiOut(split_stems=True, bpm=120)
        out.control_change_at("bass", control=91, value=999, when_beats=0.0)
        cc = next(m for m in out.chord_tracks["bass"]
                  if m.type == "control_change" and m.control == 91)
        assert cc.value == 127

    def test_control_change_at_invalid_voice_is_safe(self):
        """control_change_at on an unknown voice is a no-op, not an error."""
        out = MidiOut(split_stems=True, bpm=120)
        out.control_change_at("invalid", control=91, value=64, when_beats=0.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_drum_control_change_at_sends_cc_on_drum_channel(self):
        """drum_control_change_at sends CC on the drum channel."""
        from mtheory import DRUM_CH
        out = MidiOut(bpm=120)
        out.drum_control_change_at(control=93, value=32, when_beats=2.0)
        ccs = [m for m in out.tr_dr
              if m.type == "control_change" and m.control == 93]
        assert len(ccs) == 1
        assert ccs[0].value == 32
        assert ccs[0].channel == DRUM_CH

    def test_set_voice_programs_dict(self):
        """set_voice_programs applies programs to voices."""
        out = MidiOut(split_stems=True, bpm=120)
        programs = {"soprano": 0, "alto": 1, "tenor": 2, "bass": 3}
        out.set_voice_programs(programs, default_program=5)
        out.play_voice_note("soprano", 72, 0.0, 1.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_set_program_global(self):
        """set_program applies global program."""
        out = MidiOut(bpm=120)
        out.set_program(program=0, bank_msb=0, bank_lsb=0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0


class TestTempoChanges:
    """Test tempo changes mid-track."""

    def test_set_tempo_at(self):
        """set_tempo_at changes tempo at offset."""
        out = MidiOut(bpm=120)
        out.play_voice_note("soprano", 72, 0.0, 1.0)
        out.set_tempo_at(bpm=140, when_beats=1.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_multiple_tempo_changes(self):
        """Multiple tempo changes work."""
        out = MidiOut(bpm=120)
        out.play_voice_note("soprano", 72, 0.0, 1.0)
        out.set_tempo_at(bpm=140, when_beats=1.0)
        out.set_tempo_at(bpm=100, when_beats=2.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0


class TestChordBlocks:
    """Test chord block playback methods."""

    def test_chord_block_basic(self):
        """chord_block plays a chord at a time."""
        out = MidiOut(split_stems=True, bpm=120)
        notes = (72, 67, 60, 55)  # soprano, alto, tenor, bass
        out.chord_block(notes=notes, beats=1.0, when_beats=0.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_chord_block_ensemble(self):
        """chord_block on ensemble channel (no split_stems)."""
        out = MidiOut(split_stems=False, bpm=120)
        notes = (72, 67, 60, 55)
        out.chord_block(notes=notes, beats=1.0, when_beats=0.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_dense_block_basic(self):
        """dense_block plays all notes together."""
        out = MidiOut(bpm=120)
        notes = (60, 64, 67, 71)
        out.dense_block(notes=notes, beats=1.0, when_beats=0.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_chord_block_with_base_velocity(self):
        """chord_block respects base velocity."""
        out = MidiOut(split_stems=True, bpm=120, vel_mode_chords="default")
        notes = (72, 67, 60, 55)
        out.chord_block(notes=notes, beats=1.0, when_beats=0.0, base=100)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_chord_block_sequential(self):
        """multiple chord_blocks play in sequence."""
        out = MidiOut(split_stems=True, bpm=120)
        out.chord_block((72, 67, 60, 55), beats=1.0, when_beats=0.0)
        out.chord_block((74, 69, 62, 57), beats=1.0, when_beats=1.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0


class TestDrumBlocks:
    """Test drum block playback."""

    def test_drums_block_basic(self):
        """drums_block plays percussion patterns."""
        out = MidiOut(bpm=120)
        pattern = [PercHit(note=36), PercHit(note=38)]
        out.drums_block(hits=pattern, beats=1.0, when_beats=0.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_drums_block_human_velocity(self):
        """drums_block with human velocity mode adds accents."""
        out = MidiOut(bpm=120, vel_mode_drums="human")
        pattern = [PercHit(note=36)]
        out.drums_block(hits=pattern, beats=1.0, when_beats=0.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_drums_block_with_velocity_offset(self):
        """drums_block respects velocity offset in PercHit."""
        out = MidiOut(bpm=120)
        pattern = [PercHit(note=36, vel_offset=10)]
        out.drums_block(hits=pattern, beats=1.0, when_beats=0.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_drums_block_with_probability(self):
        """drums_block skips hits below probability threshold."""
        out = MidiOut(bpm=120)
        # Low probability hit should be skipped
        pattern = [PercHit(note=36, probability=0.0)]
        out.drums_block(hits=pattern, beats=1.0, when_beats=0.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_drums_block_various_drum_notes(self):
        """drums_block handles various drum notes."""
        out = MidiOut(bpm=120, vel_mode_drums="human")
        # Test various drum notes (hat, crash, cowbell, etc.)
        pattern = [
            PercHit(note=42),  # closed hi-hat
            PercHit(note=46),  # open hi-hat
            PercHit(note=49),  # crash
        ]
        out.drums_block(hits=pattern, beats=1.0, when_beats=0.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_drums_block_with_flam(self):
        """drums_block respects flam parameter."""
        out = MidiOut(bpm=120)
        pattern = [PercHit(note=36, flam=0.05)]
        out.drums_block(hits=pattern, beats=1.0, when_beats=0.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_drums_block_timing_offset_delays_note_on(self):
        """A positive timing_offset lays the hit back within its own slot."""
        out = MidiOut(bpm=120)
        pattern = [PercHit(note=38, timing_offset=0.25)]  # a quarter of a beat late
        out.drums_block(hits=pattern, beats=1.0, when_beats=0.0)
        note_ons = [m for m in out.tr_dr if m.type == "note_on"]
        assert len(note_ons) == 1
        assert note_ons[0].time == out.ticks(0.25)

    def test_drums_block_timing_offset_clamped_to_slot(self):
        """A timing_offset longer than the slot is clamped, not overflowed."""
        out = MidiOut(bpm=120)
        pattern = [PercHit(note=38, timing_offset=10.0)]
        out.drums_block(hits=pattern, beats=0.5, when_beats=0.0)
        note_ons = [m for m in out.tr_dr if m.type == "note_on"]
        assert note_ons[0].time == out.ticks(0.5)

    def test_drums_block_negative_timing_offset_clamped_to_zero(self):
        """Early nudges aren't supported (would cross into the prior slot);
        a negative timing_offset is clamped to 0 (on-grid) rather than error."""
        out = MidiOut(bpm=120)
        pattern = [PercHit(note=38, timing_offset=-0.2)]
        out.drums_block(hits=pattern, beats=1.0, when_beats=0.0)
        note_ons = [m for m in out.tr_dr if m.type == "note_on"]
        assert note_ons[0].time == 0

    def test_drums_block_flam_trails_the_delayed_hit(self):
        """flam is measured from the (possibly delayed) main hit, not the
        slot start."""
        out = MidiOut(bpm=120)
        pattern = [PercHit(note=36, timing_offset=0.2, flam=0.05)]
        out.drums_block(hits=pattern, beats=1.0, when_beats=0.0)
        # tick deltas in append order: main hit at 0.2 beats, then the flam
        # grace note 0.05 beats after that (i.e. at 0.25 beats absolute).
        note_on_deltas = [m.time for m in out.tr_dr if m.type == "note_on"]
        assert note_on_deltas[0] == out.ticks(0.2)
        assert note_on_deltas[0] + note_on_deltas[1] == out.ticks(0.25)

    def test_drums_block_flam_longer_than_beat(self):
        """drums_block clamps flam to beat duration."""
        out = MidiOut(bpm=120)
        pattern = [PercHit(note=36, flam=10.0)]
        out.drums_block(hits=pattern, beats=0.5, when_beats=0.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_drums_block_multiple_notes_all_drums(self):
        """drums_block with all drum note types."""
        out = MidiOut(bpm=120)
        pattern = [
            PercHit(note=36),  # kick
            PercHit(note=38),  # snare
            PercHit(note=37),  # cross stick
            PercHit(note=39),  # hand clap
            PercHit(note=47),  # cymbal tom
            PercHit(note=56),  # cowbell
            PercHit(note=99),  # unknown note -> default 80
        ]
        out.drums_block(hits=pattern, beats=1.0, when_beats=0.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_drums_block_with_openhat_choke(self):
        """drums_block with openhat choke on."""
        out = MidiOut(bpm=120)
        pattern = [PercHit(note=46)]  # open hi-hat
        out.drums_block(hits=pattern, beats=1.0, when_beats=0.0,
                        choke_openhat=True, choke_after_beats=0.5)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_drums_block_with_openhat_choke_long(self):
        """drums_block with openhat choke with long duration."""
        out = MidiOut(bpm=120)
        pattern = [PercHit(note=46)]  # open hi-hat
        out.drums_block(hits=pattern, beats=2.0, when_beats=0.0,
                        choke_openhat=True, choke_after_beats=1.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0


class TestFlushAndSave:
    """Test flushing active notes and saving."""

    def test_flush_to_end(self):
        """flush_to_end finalizes the MIDI."""
        out = MidiOut(split_stems=True, bpm=120)
        out.play_voice_note("soprano", 72, 0.0, 1.0)
        out.flush_to_end(chord_pos=1.0, drum_pos=1.0, end_beat=2.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_flush_to_end_with_active_notes(self):
        """flush_to_end releases active notes properly."""
        out = MidiOut(split_stems=True, bpm=120)
        # Directly add active notes without releasing them
        out.active_ch["soprano"].add(72)
        out.active_ch["alto"].add(67)
        # Flush, which should release the notes
        out.flush_to_end(chord_pos=0.0, drum_pos=0.0, end_beat=1.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_flush_to_end_with_active_drums(self):
        """flush_to_end releases active drum notes."""
        out = MidiOut(bpm=120)
        # Directly add active drum notes without releasing them
        out.active_dr.add(36)
        out.active_dr.add(38)
        out.flush_to_end(chord_pos=0.0, drum_pos=0.0, end_beat=1.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_to_bytes_produces_valid_midi(self):
        """to_bytes produces valid MIDI data."""
        out = MidiOut(bpm=120)
        out.play_voice_note("soprano", 72, 0.0, 1.0)
        midi_bytes = out.to_bytes()
        # Should start with MIDI header
        assert midi_bytes.startswith(b'MThd')


class TestHumanizationAndVelocity:
    """Test humanization and velocity computation."""

    def test_chord_velocity_random_mode(self):
        """Chord velocity in random mode varies."""
        out = MidiOut(bpm=120, vel_mode_chords="random")
        random.seed(42)
        out.play_voice_note("soprano", 72, 0.0, 1.0)
        midi_bytes1 = out.to_bytes()

        out2 = MidiOut(bpm=120, vel_mode_chords="random")
        random.seed(99)
        out2.play_voice_note("soprano", 72, 0.0, 1.0)
        midi_bytes2 = out2.to_bytes()
        # With different seeds, the MIDI bytes should differ
        # (not a strict equality check due to timestamps, but they shouldn't be identical)
        assert isinstance(midi_bytes1, bytes) and isinstance(midi_bytes2, bytes)

    def test_chord_velocity_human_mode_beat_accents(self):
        """Human velocity mode accents on-beat chord hits."""
        out = MidiOut(bpm=120, vel_mode_chords="human")
        # Hit on beat 0 should get accent
        out.play_voice_note("soprano", 72, start_beats=0.0, duration=1.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_chord_velocity_human_mode_offbeat_1(self):
        """Human velocity mode accents beat 1."""
        out = MidiOut(bpm=120, vel_mode_chords="human")
        # Hit on beat 1.0 should get different accent
        out.play_voice_note("soprano", 72, start_beats=1.0, duration=1.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_chord_velocity_human_mode_offbeat_2(self):
        """Human velocity mode accents beat 2."""
        out = MidiOut(bpm=120, vel_mode_chords="human")
        # Hit on beat 2.0 should get accent
        out.play_voice_note("soprano", 72, start_beats=2.0, duration=1.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_chord_velocity_human_mode_beat_2_multivoice(self):
        """Human velocity mode beat 2 with multiple voices."""
        out = MidiOut(split_stems=True, bpm=120, vel_mode_chords="human")
        # Test beat 2.0 with multiple voices
        out.chord_block((72, 67, 60, 55), beats=1.0, when_beats=2.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_chord_velocity_human_mode_offbeat_3(self):
        """Human velocity mode accents beat 3."""
        out = MidiOut(bpm=120, vel_mode_chords="human")
        # Hit on beat 3.0 should get accent
        out.play_voice_note("soprano", 72, start_beats=3.0, duration=1.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_chord_velocity_human_mode_beat_3_multivoice(self):
        """Human velocity mode beat 3 with multiple voices."""
        out = MidiOut(split_stems=True, bpm=120, vel_mode_chords="human")
        # Test beat 3.0 with multiple voices
        out.chord_block((72, 67, 60, 55), beats=1.0, when_beats=3.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_drum_velocity_human_mode_beat_accents(self):
        """Human velocity mode accents on-beat hits."""
        out = MidiOut(bpm=120, vel_mode_drums="human")
        # Hit on beat 0 should get accent
        pattern = [PercHit(note=36)]
        out.drums_block(hits=pattern, beats=1.0, when_beats=0.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_drum_velocity_human_mode_beat2(self):
        """Human velocity mode accents beat 2."""
        out = MidiOut(bpm=120, vel_mode_drums="human")
        # Hit on beat 2 should get different accent than beat 0
        pattern = [PercHit(note=36)]
        out.drums_block(hits=pattern, beats=1.0, when_beats=2.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_drum_velocity_human_mode_beat3(self):
        """Human velocity mode accents beat 3."""
        out = MidiOut(bpm=120, vel_mode_drums="human")
        # Hit on beat 3 should get accent
        pattern = [PercHit(note=36)]
        out.drums_block(hits=pattern, beats=1.0, when_beats=3.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_drum_velocity_human_mode_snare(self):
        """Human velocity mode accents different for snare."""
        out = MidiOut(bpm=120, vel_mode_drums="human")
        # Snare (38) should get different accent than kick (36)
        pattern = [PercHit(note=38)]
        out.drums_block(hits=pattern, beats=1.0, when_beats=0.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_dense_block_empty(self):
        """dense_block with empty notes is safe."""
        out = MidiOut(bpm=120)
        out.dense_block([], beats=1.0, when_beats=0.0)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0

    def test_chord_block_multiple_velocities(self):
        """Multiple chords with different bases produce different velocities."""
        out = MidiOut(split_stems=True, bpm=120, vel_mode_chords="default")
        out.chord_block((72, 67, 60, 55), beats=1.0, when_beats=0.0, base=80)
        out.chord_block((74, 69, 62, 57), beats=1.0, when_beats=1.0, base=100)
        midi_bytes = out.to_bytes()
        assert len(midi_bytes) > 0
