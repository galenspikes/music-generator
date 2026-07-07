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

import arrangement as arr
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
    # Cap the length so the suite stays fast.
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


# --- claims must match reality -------------------------------------------
def _recipe_argv(name, slug, extra=()):
    return [str(a) for a in COOKBOOK[name]["args"]] + list(extra) + \
        ["--no-play", "--seed", "1", "--out", slug]


PRESET_PROGRAM = {               # preset -> a GM program its description promises
    "counterpoint": 52,          # choir
    "bach_counterpoint": 6,      # harpsichord
    "bach_prelude": 0,           # piano
    "dense_colors": 50,          # slow strings
}


@pytest.mark.parametrize("name,prog", list(PRESET_PROGRAM.items()))
def test_preset_instrument_matches_description(name, prog, slug):
    _run(_recipe_argv(name, slug, extra=("--seconds", "6")))
    mid = _load_midi(slug)
    progs = {m.program for tr in mid.tracks for m in tr
             if m.type == "program_change"}
    assert prog in progs, f"{name}: expected GM {prog}, got {sorted(progs)}"


def test_perc_evolution_actually_builds(slug):
    _run(_recipe_argv("perc_evolution", slug))
    mid = _load_midi(slug)
    t, hits = 0.0, []
    for msg in mid:
        t += msg.time
        if msg.type == "note_on" and msg.velocity > 0 and msg.channel == 9:
            hits.append(t)
    assert hits, "no drum hits"
    end = max(hits)
    q = [0, 0, 0, 0]
    for h in hits:
        q[min(3, int(h / end * 4))] += 1
    # four stages of rising density — each quarter busier than the last
    assert q[0] < q[1] < q[2] < q[3], f"perc doesn't build across stages: {q}"


def _song_files_with_melody():
    return [p for p in SONG_FILES if "melody:" in p.read_text(encoding="utf-8")]


@pytest.mark.parametrize("song", _song_files_with_melody(),
                         ids=lambda p: p.stem)
def test_song_melody_is_monophonic(song):
    # A song that declares a melody must play it as a single soprano line — if
    # the SATB soprano weren't suppressed, melody + arpeggio would overlap.
    events, _ = arr.build_events(arr.load_spec(str(song)))
    sop = sorted((w, d) for (k, w, d, p) in events
                 if k == "voice" for (v, n) in [p] if v == "soprano")
    assert all(sop[i][0] >= sop[i - 1][0] + sop[i - 1][1] - 1e-6
               for i in range(1, len(sop))), \
        f"{song.stem}: soprano not monophonic (melody doubled with SATB?)"
