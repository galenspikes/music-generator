"""
Live web UI for the Music Generator, built with Gradio for Hugging Face Spaces.

Design: the server generates a MIDI file with the existing CLI (pure Python --
mido/numpy/pyyaml only, no native audio dependencies), and playback happens in
the browser via the html-midi-player web component using a hosted SoundFont.
This keeps the Space free to host: no FluidSynth, ffmpeg, or SoundFont on the
server.

Locally, run from the repo root or this folder:  python space/app.py
On a Space, app.py clones the generator repo (and pulls it fresh on rebuild) so
the engine, songs, and presets track the latest ``main``.
"""

import base64
import glob
import os
import pathlib
import subprocess
import sys
import time

import gradio as gr

HERE = pathlib.Path(__file__).resolve().parent
GENERATOR_REPO = os.environ.get(
    "GENERATOR_REPO", "https://github.com/galenspikes/music-generator"
)
SITE = "https://galenspikes.github.io/music-generator"


def locate_repo() -> pathlib.Path:
    """Find the generator checkout, cloning (or refreshing) it on a Space."""
    for cand in (HERE, HERE.parent):
        if (cand / "music_generator.py").exists():
            return cand
    dest = HERE / "music-generator"
    if (dest / "music_generator.py").exists():
        # refresh a cached clone so a factory reboot picks up the latest main
        subprocess.run(["git", "-C", str(dest), "pull", "--ff-only"], check=False)
    else:
        subprocess.run(
            ["git", "clone", "--depth", "1", GENERATOR_REPO, str(dest)], check=True
        )
    return dest


REPO = locate_repo()

HEAD = (
    '<script src="https://cdn.jsdelivr.net/combine/'
    "npm/tone@14.7.77,npm/@magenta/music@1.23.1/es6/core.js,"
    'npm/focus-visible@5,npm/html-midi-player@1.5.0"></script>'
)

CHORD_FAMILIES = [
    "triads",
    "sevenths",
    "ninths",
    "extended-chords",
    "quartal",
    "sus",
    "add6",
    "chromatic-mediants",
    "lyd-dom",
]


def list_songs() -> list[str]:
    """Song stems available in the checkout (e.g. 'kiss', 'autumn_leaves')."""
    return sorted(p.stem for p in (REPO / "songs").glob("*.yml"))


SONGS = list_songs()
DEFAULT_SONG = "kiss" if "kiss" in SONGS else (SONGS[0] if SONGS else None)


def _run(args: list[str]) -> str:
    """Invoke the generator CLI and return the path to the newest MIDI file."""
    slug = f"web_{int(time.time() * 1000)}"
    cmd = [sys.executable, str(REPO / "music_generator.py"), *args,
           "--out", slug, "--no-play"]
    proc = subprocess.run(
        cmd, cwd=str(REPO), capture_output=True, text=True, timeout=180
    )
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-6:]
        raise RuntimeError("Generation failed:\n" + "\n".join(tail))
    midis = glob.glob(str(REPO / "output" / "midi" / slug / "*.mid"))
    if not midis:
        raise RuntimeError("No MIDI was produced.")
    return max(midis, key=os.path.getmtime)


def _player_html(midi_path: str) -> str:
    data = base64.b64encode(pathlib.Path(midi_path).read_bytes()).decode()
    src = f"data:audio/midi;base64,{data}"
    vid = f"viz_{int(time.time() * 1000)}"
    return (
        f'<div class="player">'
        f'<midi-player src="{src}" sound-font visualizer="#{vid}"></midi-player>'
        f'<midi-visualizer id="{vid}" type="piano-roll"></midi-visualizer>'
        f"</div>"
    )


def _feel(swing: float, pan: float) -> list[str]:
    """Swing / stereo-spread flags, added only when non-zero so an authored
    song keeps its own tempo map and defaults untouched."""
    out: list[str] = []
    if float(swing) > 0:
        out += ["--swing", str(round(float(swing), 3))]
    if float(pan) > 0:
        out += ["--pan-spread", str(round(float(pan), 3))]
    return out


def generate(mode, song, keys, chords, voicing, instrument, chord_length,
             process_cell, subject, melody_key, melody_mode, bpm, seconds,
             swing, pan):
    try:
        feel = _feel(swing, pan)

        if mode == "song":
            if not song:
                return None, "Pick a song from the dropdown."
            # No --bpm: keep the song's authored (per-section) tempo map.
            args = ["--song", f"songs/{song}.yml", *feel]

        elif mode in ("ostinato", "complete"):
            if not keys.strip():
                return None, "Enter at least one chord token, e.g. `C::maj7, G::13`."
            args = ["--bpm", str(int(bpm)), "--mode", mode, "--keys", keys.strip(),
                    "--seconds", str(int(seconds)),
                    "--instrument", instrument.strip() or "piano",
                    "--voicing", voicing, "--chord-length", chord_length, *feel]
            if chords:
                args += ["--chords", *chords]

        elif mode.startswith("process:"):
            kind = mode.split(":", 1)[1].strip()
            if not process_cell.strip():
                return None, "Enter a melodic cell, e.g. `e1 e2 e3 e5 e7 e5 e3 e2`."
            args = ["--bpm", str(int(bpm)), "--process", kind,
                    "--process-cell", process_cell.strip(),
                    "--instrument", instrument.strip() or "organ",
                    "--melody-key", melody_key.strip() or "C",
                    "--melody-mode", melody_mode, *feel]

        elif mode == "fugue":
            args = ["--bpm", str(int(bpm)),
                    "--instrument", instrument.strip() or "organ",
                    "--melody-key", melody_key.strip() or "C",
                    "--melody-mode", melody_mode, *feel]
            args += ["--fugue", subject.strip()] if subject.strip() else ["--fugue"]

        else:
            return None, f"Unknown mode: {mode}"

        midi_path = _run(args)
        return midi_path, _player_html(midi_path)
    except Exception as exc:  # surface a readable message to the UI
        return None, f"<pre style='color:#c0392b'>{exc}</pre>"


with gr.Blocks(head=HEAD, title="Music Generator", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        "# Music Generator\n"
        "A token DSL for generative music. Play a finished **song**, or describe "
        "chords or a melodic process and generate MIDI on the server &mdash; "
        "playback happens right in your browser.\n\n"
        f"[Home]({SITE}/) &middot; "
        f"[Chords]({SITE}/chords.html) &middot; "
        "[Docs](https://galenspikes.github.io/music-generator/docs/) &middot; "
        "[GitHub](https://github.com/galenspikes/music-generator)"
    )

    with gr.Row():
        with gr.Column(scale=2):
            mode = gr.Dropdown(
                ["song", "ostinato", "complete", "process: additive",
                 "process: phase", "process: augment", "fugue"],
                value="song", label="Mode",
            )
            song = gr.Dropdown(
                SONGS, value=DEFAULT_SONG, label="Song (song mode)",
                info="Full multi-section arrangements from songs/*.yml.",
            )
            keys = gr.Textbox(
                value="C::maj7, A::min9, D::min7, G::13",
                label="Chord tokens (ostinato / complete)",
                info="root[:inversion][:recipe][/bass] — e.g. C::maj7, A:1:min9, G::maj/C",
            )
            chords = gr.CheckboxGroup(
                CHORD_FAMILIES, value=["sevenths", "ninths"],
                label="Chord families to draw from",
            )
            voicing = gr.Radio(["satb", "dense"], value="satb", label="Voicing")
            with gr.Accordion("Melodic process / fugue inputs", open=False):
                process_cell = gr.Textbox(
                    value="e1 e2 e3 e5 e7 e5 e3 e2",
                    label="Process cell (scale degrees)",
                )
                subject = gr.Textbox(
                    value="q1 q5 e4 e3 e2 e1 q7",
                    label="Fugue subject (blank = built-in)",
                )
                with gr.Row():
                    melody_key = gr.Textbox(value="C", label="Melody key")
                    melody_mode = gr.Radio(
                        ["major", "minor"], value="major", label="Mode"
                    )
        with gr.Column(scale=1):
            instrument = gr.Textbox(value="epiano", label="Instrument (name or GM 0-127)")
            chord_length = gr.Dropdown(
                ["w", "h", "q", "e", "s", "t"], value="q", label="Chord length"
            )
            bpm = gr.Slider(60, 200, value=120, step=1, label="BPM (chord / process modes)")
            seconds = gr.Slider(10, 180, value=40, step=5, label="Seconds (chord modes)")
            swing = gr.Slider(0, 0.75, value=0, step=0.05,
                              label="Swing (0 = straight, 0.5 = triplet)")
            pan = gr.Slider(0, 1, value=0, step=0.05,
                            label="Stereo spread (0 = centred)")
            go = gr.Button("Generate", variant="primary")

    out_html = gr.HTML(label="Playback")
    out_file = gr.File(label="Download MIDI")

    go.click(
        generate,
        [mode, song, keys, chords, voicing, instrument, chord_length,
         process_cell, subject, melody_key, melody_mode, bpm, seconds,
         swing, pan],
        [out_file, out_html],
    )

    gr.Markdown(
        "Built from [galenspikes/music-generator]"
        "(https://github.com/galenspikes/music-generator) · MIT licensed."
    )


if __name__ == "__main__":
    demo.launch()
