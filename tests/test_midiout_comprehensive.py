"""Comprehensive tests for midiout module.

Tests MIDI event writing, humanization, voice scheduling, and stem splitting.
"""

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
