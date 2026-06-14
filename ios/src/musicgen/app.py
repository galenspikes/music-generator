"""Music Generator — an offline generative-MIDI iOS app (BeeWare/Toga).

The UI lets you pick a built-in style preset (or type your own chord keys),
generate a piece with the pure-Python engine, and play it back natively through
a bundled SoundFont. Everything runs on-device with no network.
"""

from __future__ import annotations

from pathlib import Path

import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

from . import generate

_RESOURCES = Path(__file__).resolve().parent / "resources"
# Prefer a user-supplied font (drop in resources/soundfont.sf2); otherwise fall
# back to the small General MIDI font bundled with the app.
_USER_SOUNDFONT = _RESOURCES / "soundfont.sf2"
_DEFAULT_SOUNDFONT = _RESOURCES / "default_gm.sf2"
SOUNDFONT = _USER_SOUNDFONT if _USER_SOUNDFONT.exists() else _DEFAULT_SOUNDFONT

# A few sensible custom-mode defaults for when no preset is chosen.
DEFAULT_KEYS = "C::maj7, A::min9, D::min7, G::13"


class MusicGenerator(toga.App):
    def startup(self):
        self._player = None
        self._midi_path = None
        self._presets = generate.load_presets()

        # ----- preset picker -----
        preset_items = ["Custom (use keys below)"]
        self._preset_by_label: dict[str, str] = {}
        for name, recipe in self._presets.items():
            label = recipe.get("title", name)
            preset_items.append(label)
            self._preset_by_label[label] = name
        self._preset_select = toga.Selection(
            items=preset_items,
            on_change=self._on_preset_change,
            style=Pack(flex=1),
        )

        self._desc = toga.Label(
            "Type a chord progression and tap Generate.",
            style=Pack(padding=(4, 0), font_size=12),
        )

        # ----- custom keys + length -----
        self._keys_input = toga.TextInput(
            value=DEFAULT_KEYS,
            placeholder="e.g. C::maj7, A::min9, D::min7, G::13",
            style=Pack(flex=1),
        )
        self._seconds = toga.Slider(
            min=15, max=180, value=45, tick_count=12,
            style=Pack(flex=1),
        )
        self._seconds_label = toga.Label("Length: 45s", style=Pack(width=110))
        self._seconds.on_change = self._on_seconds_change

        # ----- transport -----
        self._generate_btn = toga.Button(
            "Generate", on_press=self._on_generate, style=Pack(flex=1))
        self._play_btn = toga.Button(
            "Play", on_press=self._on_play, enabled=False, style=Pack(flex=1))
        self._stop_btn = toga.Button(
            "Stop", on_press=self._on_stop, enabled=False, style=Pack(flex=1))

        self._status = toga.Label("Ready.", style=Pack(padding_top=8))

        # ----- layout -----
        box = toga.Box(
            children=[
                toga.Label("Style", style=Pack(padding_top=8)),
                self._preset_select,
                self._desc,
                toga.Label("Chord keys (Custom)", style=Pack(padding_top=8)),
                self._keys_input,
                toga.Box(
                    children=[self._seconds_label, self._seconds],
                    style=Pack(direction=ROW, padding_top=8),
                ),
                self._generate_btn,
                toga.Box(
                    children=[self._play_btn, self._stop_btn],
                    style=Pack(direction=ROW, padding_top=8),
                ),
                self._status,
            ],
            style=Pack(direction=COLUMN, padding=16),
        )

        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = box
        self.main_window.show()

    # ----- helpers -----
    @property
    def _output_dir(self) -> Path:
        return Path(self.paths.data) / "output"

    def _selected_preset(self) -> str | None:
        label = self._preset_select.value
        return self._preset_by_label.get(label)

    def _build_args(self) -> tuple[list[str], str]:
        """Return (engine args, output name) for the current UI state."""
        seconds = str(int(self._seconds.value))
        preset = self._selected_preset()
        if preset is not None:
            recipe = self._presets[preset]
            args = list(recipe.get("args", []))
            return args, preset
        keys = self._keys_input.value.strip() or DEFAULT_KEYS
        args = ["--mode", "ostinato", "--keys", keys, "--seconds", seconds]
        return args, "custom"

    # ----- event handlers -----
    def _on_preset_change(self, widget):
        preset = self._selected_preset()
        if preset is None:
            self._desc.text = "Type a chord progression and tap Generate."
            self._keys_input.enabled = True
            self._seconds.enabled = True
        else:
            recipe = self._presets[preset]
            self._desc.text = recipe.get("description", "")
            # Presets carry their own length/keys; dim the custom controls.
            self._keys_input.enabled = False
            self._seconds.enabled = False

    def _on_seconds_change(self, widget):
        self._seconds_label.text = f"Length: {int(self._seconds.value)}s"

    def _on_generate(self, widget):
        self._on_stop(widget)
        self._status.text = "Generating…"
        self._generate_btn.enabled = False
        try:
            args, name = self._build_args()
            self._midi_path = generate.generate(
                args, output_dir=self._output_dir, out_name=name)
        except Exception as exc:  # surface failures rather than crash
            self._status.text = f"Generation failed: {exc}"
            self._play_btn.enabled = False
            return
        finally:
            self._generate_btn.enabled = True

        if not SOUNDFONT.exists():
            self._status.text = (
                "Generated MIDI, but no SoundFont bundled — see "
                "resources/README.md.")
            self._play_btn.enabled = False
            return

        from . import playback  # imported lazily (needs the ObjC runtime)
        self._player = playback.Player(SOUNDFONT)
        if self._player.load(self._midi_path):
            self._play_btn.enabled = True
            self._status.text = "Ready to play."
        else:
            self._status.text = "Could not load MIDI for playback."

    def _on_play(self, widget):
        if self._player is not None:
            self._player.play()
            self._stop_btn.enabled = True
            self._status.text = "Playing…"

    def _on_stop(self, widget):
        if self._player is not None:
            self._player.stop()
        self._stop_btn.enabled = False
        self._status.text = "Stopped."


def main():
    return MusicGenerator()
