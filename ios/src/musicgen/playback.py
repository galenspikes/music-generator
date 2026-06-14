"""On-device MIDI playback via AVFoundation's ``AVMIDIPlayer`` (rubicon-objc).

``AVMIDIPlayer`` renders a Standard MIDI File through a SoundFont entirely
on-device, with no FluidSynth/ffmpeg and no network. We hand it the MIDI file
the engine produced plus the bundled ``.sf2`` SoundFont.

Apple docs: AVMIDIPlayer(contentsOf:soundBankURL:) loads a sequence and a
DLS/SoundFont bank; play(_:) / stop() control transport.
"""

from __future__ import annotations

from pathlib import Path

from rubicon.objc import ObjCClass

NSURL = ObjCClass("NSURL")
AVMIDIPlayer = ObjCClass("AVMIDIPlayer")


class Player:
    """Thin wrapper around a single ``AVMIDIPlayer`` instance."""

    def __init__(self, soundfont: Path | str):
        self._soundfont_url = NSURL.fileURLWithPath(str(soundfont))
        self._player = None

    def load(self, midi_path: Path | str) -> bool:
        """Prepare a MIDI file for playback. Returns ``True`` on success."""
        self.stop()
        midi_url = NSURL.fileURLWithPath(str(midi_path))
        self._player = AVMIDIPlayer.alloc().initWithContentsOfURL(
            midi_url, soundBankURL=self._soundfont_url, error=None)
        if self._player is not None:
            self._player.prepareToPlay()
        return self._player is not None

    def play(self) -> None:
        if self._player is not None:
            # play(completionHandler:) — None means "don't notify".
            self._player.play(None)

    def stop(self) -> None:
        if self._player is not None:
            self._player.stop()
            self._player = None

    @property
    def duration(self) -> float:
        return float(self._player.duration) if self._player is not None else 0.0

    @property
    def is_loaded(self) -> bool:
        return self._player is not None
