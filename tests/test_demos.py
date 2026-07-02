"""Demo library smoke tests.

Every song (``songs/*.yml``) and every preset (``library/song_cookbook.py``)
must render to a valid, non-empty MIDI. Plus a regression guard for the
arrangement renderer: ``--song`` must honour a song's authored tempo/length and
not clobber the YAML ``defaults`` with argparse defaults (``--bpm 120``,
``--chord-length e``, ...), while an *explicit* ``--bpm`` must still rescale.
"""

import glob
import importlib.util
import shutil
import sys
from pathlib import Path

import mido
import pytest

import music_generator as mg

OUT = mg.MIDI_DIR
REPO = Path(__file__).resolve().parent.parent
SONG_FILES = sorted((REPO / "songs").glob("*.yml"))
KISS = REPO / "songs" / "kiss.yml"


def _load_cookbook():
    path = REPO / "library" / "song_cookbook.py"
    spec = importlib.util.spec_from_file_location("song_cookbook", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


COOKBOOK = _load_cookbook().SONG_COOKBOOK


def _run(argv):
    old = sys.argv
    sys.argv = ["music_generator.py", *argv]
    try:
        mg.main()
    finally:
        sys.argv = old


def _load_midi(slug, min_notes=1):
    files = sorted(glob.glob(str(OUT / slug / "*.mid")))
    assert files, f"no MIDI produced for {slug}"
    mid = mido.MidiFile(files[-1])
    notes = [m for tr in mid.tracks for m in tr
             if m.type == "note_on" and m.velocity > 0]
    assert len(notes) >= min_notes, f"{slug}: only {len(notes)} notes"
    assert mid.length > 0
    return mid


def _tempos(mid):
    return {round(60_000_000 / m.tempo)
            for tr in mid.tracks for m in tr if m.type == "set_tempo"}


@pytest.fixture
def slug(request):
    name = "_dtest_" + request.node.name.replace("[", "_").replace("]", "")
    d = OUT / name
    if d.exists():
        shutil.rmtree(d)
    yield name
    if d.exists():
        shutil.rmtree(d)


@pytest.mark.parametrize("song", SONG_FILES, ids=[p.stem for p in SONG_FILES])
def test_song_renders(song, slug):
    _run(["--song", str(song), "--out", slug])
    _load_midi(slug)


@pytest.mark.parametrize("recipe", sorted(COOKBOOK), ids=sorted(COOKBOOK))
def test_recipe_renders(recipe, slug):
    args = [str(a) for a in COOKBOOK[recipe]["args"]]
    # Cap the length so the suite stays fast (later --seconds wins on the flat
    # path; the fugue/process paths ignore it).
    _run([*args, "--no-play", "--seed", "1", "--seconds", "6", "--out", slug])
    _load_midi(slug)


def test_song_honors_yaml_tempo_and_length(slug):
    # Regression: kiss.yml is authored at 140-152 bpm and ~2.5 min. The old
    # arrangement path forced 120 bpm and 4x-compressed (~47s) renders because
    # it applied argparse defaults as overrides.
    _run(["--song", str(KISS), "--out", slug])
    mid = _load_midi(slug, min_notes=100)
    tempos = _tempos(mid)
    assert 120 not in tempos, f"argparse default tempo leaked in: {tempos}"
    assert max(tempos) >= 148, f"authored tempo missing: {tempos}"
    assert mid.length > 100, f"song too short ({mid.length:.0f}s) — 4x compression?"


def test_cli_bpm_override_still_scales(slug):
    # Explicitly passing --bpm must still rescale the whole arrangement.
    _run(["--song", str(KISS), "--bpm", "90", "--out", slug])
    mid = _load_midi(slug)
    tempos = _tempos(mid)
    assert max(tempos) <= 100, f"expected scaled-down tempos, got {tempos}"
